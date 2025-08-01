"""
SSL証明書検証システム - セキュリティ強化
"""
import ssl
import socket
import logging
import hashlib
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.ssl_ import create_urllib3_context

logger = logging.getLogger(__name__)


class SSLCertificateValidator:
    """SSL証明書検証システム"""
    
    # 信頼できるCAフィンガープリント（例: Let's Encrypt, DigiCert等）
    TRUSTED_CA_FINGERPRINTS = {
        # Let's Encrypt
        'lets_encrypt_r3': 'A053375BFE84E8B748782C7CEE15827A6AF5A405',
        # DigiCert
        'digicert_global_root_g2': '4D1FA5D1FB1AC3917C08E43F65015E6AEA571179',
        # Google Trust Services
        'gts_root_r1': '2A79BE3C2E34AB1F8F4D75F1F80B7C8D8F2C1E8D',
    }
    
    # 許可されるドメインの証明書ピニング
    DOMAIN_CERTIFICATE_PINS = {
        'dmm.co.jp': {
            'fingerprints': [
                # DMM.comの証明書フィンガープリント（例）
                'sha256/EXAMPLE_DMM_CERT_FINGERPRINT',
            ],
            'backup_fingerprints': [
                # バックアップ証明書
                'sha256/EXAMPLE_DMM_BACKUP_CERT_FINGERPRINT',
            ]
        },
        'al.dmm.co.jp': {
            'fingerprints': [
                'sha256/EXAMPLE_AL_DMM_CERT_FINGERPRINT',
            ]
        },
        'pics.dmm.co.jp': {
            'fingerprints': [
                'sha256/EXAMPLE_PICS_DMM_CERT_FINGERPRINT',
            ]
        },
        'wordpress.com': {
            'fingerprints': [
                'sha256/EXAMPLE_WORDPRESS_CERT_FINGERPRINT',
            ]
        }
    }
    
    def __init__(self):
        """SSL証明書バリデーター初期化"""
        self.session = self._create_secure_session()
        logger.info("SSL証明書検証システム初期化完了")
    
    def _create_secure_session(self) -> requests.Session:
        """セキュアなHTTPSセッションを作成"""
        session = requests.Session()
        
        # カスタムHTTPSアダプターを作成
        adapter = SecureHTTPSAdapter()
        session.mount('https://', adapter)
        
        # デフォルトのSSL設定を強化
        session.verify = True  # SSL証明書検証を有効化
        
        # セキュリティヘッダーを追加
        session.headers.update({
            'User-Agent': 'BlogAutomationSystem/1.0 (Security Enhanced)',
            'Accept': 'application/json, text/html, */*',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })
        
        return session
    
    def validate_certificate(self, hostname: str, port: int = 443) -> Dict[str, any]:
        """
        SSL証明書を検証
        
        Args:
            hostname: ホスト名
            port: ポート番号
            
        Returns:
            検証結果辞書
        """
        try:
            # SSL証明書の取得
            cert_info = self._get_certificate_info(hostname, port)
            
            # 証明書の検証
            validation_results = {
                'hostname': hostname,
                'port': port,
                'is_valid': False,
                'certificate_info': cert_info,
                'validation_errors': [],
                'security_warnings': []
            }
            
            # 基本的な証明書検証
            basic_validation = self._validate_basic_certificate(cert_info, hostname)
            validation_results.update(basic_validation)
            
            # ドメイン固有の証明書ピニング検証
            if hostname in self.DOMAIN_CERTIFICATE_PINS:
                pin_validation = self._validate_certificate_pinning(cert_info, hostname)
                validation_results['pinning_validation'] = pin_validation
                
                if not pin_validation['is_valid']:
                    validation_results['validation_errors'].append(
                        f"証明書ピニング検証失敗: {pin_validation.get('error')}"
                    )
                    validation_results['is_valid'] = False
            
            # セキュリティ強度の評価
            security_assessment = self._assess_certificate_security(cert_info)
            validation_results['security_assessment'] = security_assessment
            
            if security_assessment['risk_level'] == 'high':
                validation_results['validation_errors'].append(
                    "証明書のセキュリティ強度が不十分です"
                )
                validation_results['is_valid'] = False
            
            logger.info(f"SSL証明書検証完了: {hostname} (有効: {validation_results['is_valid']})")
            
            return validation_results
            
        except Exception as e:
            logger.error(f"SSL証明書検証エラー ({hostname}): {e}")
            return {
                'hostname': hostname,
                'port': port,
                'is_valid': False,
                'validation_errors': [f"検証処理エラー: {e}"],
                'certificate_info': None
            }
    
    def _get_certificate_info(self, hostname: str, port: int) -> Dict[str, any]:
        """SSL証明書情報を取得"""
        try:
            # SSL接続を確立して証明書を取得
            context = ssl.create_default_context()
            
            with socket.create_connection((hostname, port), timeout=10) as sock:
                with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                    cert = ssock.getpeercert(binary_form=True)
                    cert_der = cert
                    cert_info = ssock.getpeercert()
            
            # 証明書のフィンガープリントを計算
            fingerprint_sha256 = hashlib.sha256(cert_der).hexdigest().upper()
            fingerprint_sha1 = hashlib.sha1(cert_der).hexdigest().upper()
            
            # 証明書情報を整理
            return {
                'subject': cert_info.get('subject', []),
                'issuer': cert_info.get('issuer', []),
                'version': cert_info.get('version'),
                'serial_number': cert_info.get('serialNumber'),
                'not_before': cert_info.get('notBefore'),
                'not_after': cert_info.get('notAfter'),
                'fingerprint_sha256': fingerprint_sha256,
                'fingerprint_sha1': fingerprint_sha1,
                'subject_alt_name': cert_info.get('subjectAltName', []),
                'raw_certificate': cert_der
            }
            
        except Exception as e:
            raise Exception(f"証明書取得エラー: {e}")
    
    def _validate_basic_certificate(self, cert_info: Dict, hostname: str) -> Dict[str, any]:
        """基本的な証明書検証"""
        validation_result = {
            'is_valid': True,
            'validation_errors': [],
            'security_warnings': []
        }
        
        try:
            # 証明書の有効期限チェック
            from datetime import datetime
            import ssl
            
            not_after = cert_info.get('not_after')
            if not_after:
                expiry_date = datetime.strptime(not_after, '%b %d %H:%M:%S %Y %Z')
                if expiry_date < datetime.now():
                    validation_result['validation_errors'].append("証明書が期限切れです")
                    validation_result['is_valid'] = False
                elif (expiry_date - datetime.now()).days < 30:
                    validation_result['security_warnings'].append(
                        f"証明書の有効期限が近づいています: {expiry_date}"
                    )
            
            # ホスト名の検証
            subject_alt_names = cert_info.get('subject_alt_name', [])
            common_name = None
            
            # Common Nameを取得
            for field in cert_info.get('subject', []):
                for key, value in field:
                    if key == 'commonName':
                        common_name = value
                        break
            
            # ホスト名がSANまたはCNに含まれているかチェック
            hostname_valid = False
            if common_name and common_name == hostname:
                hostname_valid = True
            
            for san_type, san_value in subject_alt_names:
                if san_type == 'DNS' and (san_value == hostname or 
                                        self._match_wildcard_domain(san_value, hostname)):
                    hostname_valid = True
                    break
            
            if not hostname_valid:
                validation_result['validation_errors'].append(
                    f"ホスト名 '{hostname}' が証明書に含まれていません"
                )
                validation_result['is_valid'] = False
            
        except Exception as e:
            validation_result['validation_errors'].append(f"基本検証エラー: {e}")
            validation_result['is_valid'] = False
        
        return validation_result
    
    def _validate_certificate_pinning(self, cert_info: Dict, hostname: str) -> Dict[str, any]:
        """証明書ピニング検証"""
        pin_config = self.DOMAIN_CERTIFICATE_PINS.get(hostname, {})
        expected_fingerprints = pin_config.get('fingerprints', [])
        backup_fingerprints = pin_config.get('backup_fingerprints', [])
        
        if not expected_fingerprints:
            return {'is_valid': True, 'message': 'ピニング設定なし'}
        
        cert_fingerprint = f"sha256/{cert_info.get('fingerprint_sha256', '')}"
        
        # メインまたはバックアップのフィンガープリントと一致するかチェック
        all_valid_fingerprints = expected_fingerprints + backup_fingerprints
        
        if cert_fingerprint in all_valid_fingerprints:
            return {
                'is_valid': True,
                'matched_fingerprint': cert_fingerprint,
                'message': 'ピニング検証成功'
            }
        else:
            return {
                'is_valid': False,
                'current_fingerprint': cert_fingerprint,
                'expected_fingerprints': expected_fingerprints,
                'error': f'証明書フィンガープリントが期待値と一致しません'
            }
    
    def _assess_certificate_security(self, cert_info: Dict) -> Dict[str, any]:
        """証明書のセキュリティ強度を評価"""
        assessment = {
            'risk_level': 'low',  # low, medium, high
            'security_warnings': [],
            'recommendations': []
        }
        
        try:
            # 証明書のバージョンチェック
            version = cert_info.get('version', 0)
            if version < 3:
                assessment['security_warnings'].append(f"古い証明書バージョン: v{version}")
                assessment['risk_level'] = 'medium'
            
            # 発行者の信頼性チェック
            issuer_cn = None
            for field in cert_info.get('issuer', []):
                for key, value in field:
                    if key == 'commonName':
                        issuer_cn = value
                        break
            
            if issuer_cn:
                # 自己署名証明書の検出
                subject_cn = None
                for field in cert_info.get('subject', []):
                    for key, value in field:
                        if key == 'commonName':
                            subject_cn = value
                            break
                
                if issuer_cn == subject_cn:
                    assessment['security_warnings'].append("自己署名証明書が検出されました")
                    assessment['risk_level'] = 'high'
                
                # 既知の信頼できるCA以外
                trusted_cas = ['Let\'s Encrypt', 'DigiCert', 'GlobalSign', 'Sectigo', 'GeoTrust']
                if not any(ca in issuer_cn for ca in trusted_cas):
                    assessment['security_warnings'].append(f"不明なCA: {issuer_cn}")
                    if assessment['risk_level'] == 'low':
                        assessment['risk_level'] = 'medium'
            
            # 推奨事項の追加
            if not cert_info.get('subject_alt_name'):
                assessment['recommendations'].append("SAN（Subject Alternative Name）の使用を推奨")
            
        except Exception as e:
            assessment['security_warnings'].append(f"セキュリティ評価エラー: {e}")
            assessment['risk_level'] = 'medium'
        
        return assessment
    
    def _match_wildcard_domain(self, pattern: str, hostname: str) -> bool:
        """ワイルドカードドメインのマッチング"""
        if not pattern.startswith('*.'):
            return pattern == hostname
        
        pattern_parts = pattern[2:].split('.')
        hostname_parts = hostname.split('.')
        
        if len(pattern_parts) != len(hostname_parts) - 1:
            return False
        
        return hostname_parts[1:] == pattern_parts
    
    def get_secure_session(self) -> requests.Session:
        """セキュアなHTTPセッションを取得"""
        return self.session
    
    def validate_url_certificate(self, url: str) -> bool:
        """URLの証明書を検証"""
        try:
            parsed_url = urlparse(url)
            if parsed_url.scheme != 'https':
                logger.warning(f"非HTTPSのURL: {url}")
                return False
            
            hostname = parsed_url.hostname
            port = parsed_url.port or 443
            
            validation_result = self.validate_certificate(hostname, port)
            return validation_result['is_valid']
            
        except Exception as e:
            logger.error(f"URL証明書検証エラー ({url}): {e}")
            return False


class SecureHTTPSAdapter(HTTPAdapter):
    """セキュアなHTTPSアダプター"""
    
    def init_poolmanager(self, *args, **kwargs):
        """セキュアなプールマネージャーを初期化"""
        # 最新のSSL設定を使用
        context = create_urllib3_context()
        context.check_hostname = True
        context.verify_mode = ssl.CERT_REQUIRED
        
        # 弱い暗号化方式を無効化
        context.set_ciphers('ECDHE+AESGCM:ECDHE+CHACHA20:DHE+AESGCM:DHE+CHACHA20:!aNULL:!MD5:!DSS')
        
        # 最小TLSバージョンを設定
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        
        kwargs['ssl_context'] = context
        return super().init_poolmanager(*args, **kwargs)


# グローバルSSL証明書バリデーターインスタンス
ssl_validator = SSLCertificateValidator()