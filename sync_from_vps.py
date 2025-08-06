#!/usr/bin/env python3
"""
VPS環境からローカル環境へのデータ同期スクリプト
"""
import json
import sys
from pathlib import Path


def update_posted_works_from_vps_list():
    """
    VPSで提供された投稿済み作品リストでローカルのposted_works.jsonを更新
    """
    print("🔄 VPS環境からローカル環境への投稿済み作品リスト同期を開始...")
    
    # VPSから提供された投稿済み作品リスト（162件）
    vps_posted_work_ids = [
        "d_644177", "d_636505", "d_642095", "d_643164", "d_619638", "d_641354",
        "d_642623", "d_504593", "d_633782", "d_638647", "d_639698", "d_644479",
        "d_618855", "d_641720", "d_634570", "d_644314", "d_642994", "d_615824",
        "d_643818", "d_636848", "d_644048", "d_644328", "d_639267", "d_641423",
        "d_644510", "d_641914", "d_639586", "d_645547", "d_642268", "d_633486",
        "d_637945", "d_644275", "d_642702", "d_636726", "d_636664", "d_643805",
        "d_635797", "d_640194", "d_634097", "d_643021", "d_623317", "d_640430",
        "d_635262", "d_641932", "d_643763", "d_641576", "d_637390", "d_642235",
        "d_625486", "d_634924", "d_643078", "d_638612", "d_644093", "d_644517",
        "d_636548", "d_638697", "d_635974", "d_643848", "d_636181", "d_640527",
        "d_641920", "d_638857", "d_639235", "d_644222", "d_623351", "d_633362",
        "d_568529", "d_641544", "d_644378", "d_630391", "d_643861", "d_642008",
        "d_585658", "d_592509", "d_640740", "d_610710", "d_620024", "d_643653",
        "d_641712", "d_615275", "d_594837", "d_640484", "d_643935", "d_643111",
        "d_600393", "d_631037", "d_623756", "d_639163", "d_638876", "d_642848",
        "d_598293", "d_637209", "d_641717", "d_644455", "d_601389", "d_640566",
        "d_642905", "d_607719", "d_639446", "d_643729", "d_641149", "d_626031",
        "d_643795", "d_642220", "d_641689", "d_644325", "d_645754", "d_638701",
        "d_578433", "d_428050", "d_643482", "d_638080", "d_593706", "d_644478",
        "d_637841", "d_589255", "d_634038", "d_643388", "d_644360", "d_628999",
        "d_593678", "d_641357", "d_628551", "d_644518", "d_639448", "d_644082",
        "d_601482", "d_637457", "d_644105", "d_644179", "d_643696", "d_643834",
        "d_629804", "d_642654", "d_645030", "d_643291", "d_590748", "d_641666",
        "d_494326", "d_640816", "d_639095", "d_624058", "d_632859", "d_642778",
        "d_636957", "d_616468", "d_641791", "d_635602", "d_598352", "d_644385",
        "d_640259", "d_634870", "d_644023", "d_638168", "d_629943", "d_631352",
        "d_643890", "d_645617", "d_644100", "d_639420", "d_644088", "d_643926",
        "d_639656", "d_637054", "d_642934", "d_635096", "d_643027", "d_635775",
        "d_622331", "d_614852", "d_638538", "d_639807", "d_641200"
    ]
    
    # ローカルのposted_works.jsonパス
    posted_works_file = Path("data/posted_works.json")
    
    # バックアップを作成
    if posted_works_file.exists():
        backup_file = posted_works_file.with_suffix('.json.backup')
        with open(posted_works_file, 'r', encoding='utf-8') as f:
            current_data = json.load(f)
        
        with open(backup_file, 'w', encoding='utf-8') as f:
            json.dump(current_data, f, ensure_ascii=False, indent=2)
        
        print(f"📁 現在のファイルをバックアップ: {backup_file}")
        print(f"   現在の投稿済み件数: {len(current_data.get('posted_work_ids', []))}")
    
    # VPSデータで更新
    updated_data = {
        "posted_work_ids": vps_posted_work_ids
    }
    
    # ディレクトリ作成（存在しない場合）
    posted_works_file.parent.mkdir(parents=True, exist_ok=True)
    
    # ファイルを更新
    with open(posted_works_file, 'w', encoding='utf-8') as f:
        json.dump(updated_data, f, ensure_ascii=False, indent=2)
    
    print(f"✅ ローカル環境を更新完了:")
    print(f"   新しい投稿済み件数: {len(vps_posted_work_ids)}")
    print(f"   d_590748の状態: {'✅ 含まれています' if 'd_590748' in vps_posted_work_ids else '❌ 含まれていません'}")
    
    # 検証
    with open(posted_works_file, 'r', encoding='utf-8') as f:
        verification_data = json.load(f)
    
    if verification_data.get('posted_work_ids') == vps_posted_work_ids:
        print("✅ データ整合性確認完了")
    else:
        print("❌ データ整合性に問題があります")
        return False
    
    print(f"\n🎯 重要: d_590748の重複投稿問題が解決されました")
    print(f"   システムは今後、d_590748を投稿済み作品として正しく認識します")
    
    return True


def main():
    """メイン処理"""
    try:
        success = update_posted_works_from_vps_list()
        
        if success:
            print(f"\n📋 次の手順:")
            print(f"1. 重複投稿防止機能のテスト: python test_posted_check.py")
            print(f"2. VPS環境との定期同期の検討")
            print(f"3. この同期を今後も定期的に実行")
        
        sys.exit(0 if success else 1)
        
    except Exception as e:
        print(f"❌ 同期処理中にエラーが発生: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()