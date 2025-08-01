<?php
/**
 * DMM画像プロキシシステム
 * 
 * DMM APIから取得した画像をプロキシ経由で配信するためのシステム
 * Referrer Policyや外部参照制限を回避
 * 
 * 使用方法:
 * https://your-site.com/dmm-image-proxy.php?url=base64_encoded_image_url
 */

// セキュリティ設定
header('X-Content-Type-Options: nosniff');
header('X-Frame-Options: DENY');
header('X-XSS-Protection: 1; mode=block');

// 許可されたドメインのリスト
$allowed_domains = [
    'doujin-assets.dmm.co.jp',
    'pics.dmm.co.jp',
    'doujin-assets.dmm.com',
    'pics.dmm.com'
];

// キャッシュ設定（24時間）
$cache_duration = 24 * 60 * 60;

/**
 * ドメインが許可されているかチェック
 */
function is_allowed_domain($url, $allowed_domains) {
    $parsed_url = parse_url($url);
    if (!$parsed_url || !isset($parsed_url['host'])) {
        return false;
    }
    
    return in_array($parsed_url['host'], $allowed_domains);
}

/**
 * 画像のMIMEタイプを取得
 */
function get_image_mime_type($image_data) {
    $finfo = new finfo(FILEINFO_MIME_TYPE);
    $mime_type = $finfo->buffer($image_data);
    
    // 許可された画像タイプのみ
    $allowed_types = ['image/jpeg', 'image/png', 'image/gif', 'image/webp'];
    
    return in_array($mime_type, $allowed_types) ? $mime_type : false;
}

/**
 * キャッシュファイル名を生成
 */
function get_cache_filename($url) {
    $cache_dir = __DIR__ . '/cache/';
    if (!is_dir($cache_dir)) {
        mkdir($cache_dir, 0755, true);
    }
    
    return $cache_dir . md5($url) . '.cache';
}

/**
 * エラーレスポンスを送信
 */
function send_error_response($message, $code = 400) {
    http_response_code($code);
    header('Content-Type: text/plain');
    echo "Error: " . $message;
    exit;
}

try {
    // URLパラメータの取得
    if (!isset($_GET['url']) || empty($_GET['url'])) {
        send_error_response('画像URLが指定されていません', 400);
    }
    
    // Base64デコード
    $encoded_url = $_GET['url'];
    $image_url = base64_decode($encoded_url);
    
    if (!$image_url || !filter_var($image_url, FILTER_VALIDATE_URL)) {
        send_error_response('無効な画像URLです', 400);
    }
    
    // ドメインチェック
    if (!is_allowed_domain($image_url, $allowed_domains)) {
        send_error_response('許可されていないドメインです', 403);
    }
    
    // キャッシュファイルのチェック
    $cache_file = get_cache_filename($image_url);
    if (file_exists($cache_file) && (time() - filemtime($cache_file)) < $cache_duration) {
        // キャッシュから配信
        $cached_data = file_get_contents($cache_file);
        $cache_info = json_decode(substr($cached_data, 0, strpos($cached_data, "\n")), true);
        $image_data = substr($cached_data, strpos($cached_data, "\n") + 1);
        
        // キャッシュヘッダー設定
        header('Content-Type: ' . $cache_info['mime_type']);
        header('Content-Length: ' . strlen($image_data));
        header('Cache-Control: public, max-age=' . $cache_duration);
        header('Expires: ' . gmdate('D, d M Y H:i:s', time() + $cache_duration) . ' GMT');
        header('X-Cache: HIT');
        
        echo $image_data;
        exit;
    }
    
    // 画像を取得
    $context = stream_context_create([
        'http' => [
            'method' => 'GET',
            'header' => [
                'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept: image/webp,image/apng,image/*,*/*;q=0.8',
                'Accept-Language: ja,en-US;q=0.9,en;q=0.8',
                'Accept-Encoding: gzip, deflate, br',
                'Referer: https://www.dmm.co.jp/',
                'Connection: keep-alive',
                'Upgrade-Insecure-Requests: 1'
            ],
            'timeout' => 30,
            'follow_location' => true,
            'max_redirects' => 3
        ]
    ]);
    
    $image_data = file_get_contents($image_url, false, $context);
    
    if ($image_data === false) {
        send_error_response('画像の取得に失敗しました', 404);
    }
    
    // MIMEタイプチェック
    $mime_type = get_image_mime_type($image_data);
    if (!$mime_type) {
        send_error_response('サポートされていない画像形式です', 415);
    }
    
    // キャッシュに保存
    $cache_info = json_encode(['mime_type' => $mime_type, 'cached_at' => time()]);
    file_put_contents($cache_file, $cache_info . "\n" . $image_data);
    
    // レスポンスヘッダー設定
    header('Content-Type: ' . $mime_type);
    header('Content-Length: ' . strlen($image_data));
    header('Cache-Control: public, max-age=' . $cache_duration);
    header('Expires: ' . gmdate('D, d M Y H:i:s', time() + $cache_duration) . ' GMT');
    header('X-Cache: MISS');
    
    // 画像データを出力
    echo $image_data;
    
} catch (Exception $e) {
    error_log('DMM Image Proxy Error: ' . $e->getMessage());
    send_error_response('内部エラーが発生しました', 500);
}
?>