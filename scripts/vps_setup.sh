#!/bin/bash

# VPS初期セットアップスクリプト
# システム全体の初期化とディレクトリ作成

# 設定
PROJECT_ROOT="${BLOG_AUTOMATION_ROOT:-/opt/blog-automation}"
PYTHON_PATH="${PYTHON_PATH:-/usr/bin/env python3}"

echo "=== VPS自動投稿システム初期セットアップ ==="
echo "プロジェクトルート: $PROJECT_ROOT"

# 必要ディレクトリの作成
echo "必要ディレクトリを作成中..."
mkdir -p "$PROJECT_ROOT"/{data/schedule,locks,logs/{daily,error},scripts}

# 権限設定
echo "権限設定中..."
chmod 755 "$PROJECT_ROOT"
chmod 755 "$PROJECT_ROOT/logs" "$PROJECT_ROOT/data" "$PROJECT_ROOT/scripts"
chmod 700 "$PROJECT_ROOT/locks"  # ロックファイル用は厳格に

# 暗号化キーファイルの権限設定（存在する場合）
if [ -f "$PROJECT_ROOT/.encryption_key" ]; then
    chmod 600 "$PROJECT_ROOT/.encryption_key"
    echo "✅ 暗号化キーファイルの権限を設定しました"
fi

# 環境変数設定ファイルの作成
ENV_FILE="$PROJECT_ROOT/.vps_env"
cat > "$ENV_FILE" << EOF
# VPS環境変数設定
export BLOG_AUTOMATION_ROOT="$PROJECT_ROOT"
export VPS_MODE="true"
export PYTHON_PATH="$PYTHON_PATH"
EOF

chmod 644 "$ENV_FILE"

# Python環境チェック
echo "Python環境をチェック中..."
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version)
    echo "✅ Python環境: $PYTHON_VERSION"
else
    echo "❌ Python3が見つかりません"
    exit 1
fi

# 仮想環境チェック
if [ -d "$PROJECT_ROOT/venv" ]; then
    echo "✅ Python仮想環境が存在します"
else
    echo "⚠️ Python仮想環境が見つかりません"
    echo "以下のコマンドで仮想環境を作成してください:"
    echo "  cd $PROJECT_ROOT"
    echo "  python3 -m venv venv"
    echo "  source venv/bin/activate"
    echo "  pip install -r requirements.txt"
fi

# 設定ファイルチェック
CONFIG_FILE="$PROJECT_ROOT/config/config.vps.ini"
if [ -f "$CONFIG_FILE" ]; then
    echo "✅ VPS設定ファイルが存在します"
else
    echo "❌ VPS設定ファイルが見つかりません: $CONFIG_FILE"
    exit 1
fi

# ディスク容量チェック
DISK_USAGE=$(df "$PROJECT_ROOT" | awk 'NR==2 {gsub(/%/, "", $5); print $5}')
echo "現在のディスク使用率: ${DISK_USAGE}%"

if [ "$DISK_USAGE" -gt 80 ]; then
    echo "⚠️ ディスク使用率が高いです (${DISK_USAGE}%)"
else
    echo "✅ ディスク容量は十分です"
fi

# ネットワーク接続テスト
echo "ネットワーク接続をテスト中..."
if ping -c 1 google.com &> /dev/null; then
    echo "✅ インターネット接続: OK"
else
    echo "❌ インターネット接続: NG"
    exit 1
fi

# 各種スクリプトに実行権限付与
echo "スクリプトに実行権限を付与中..."
for script in "$PROJECT_ROOT"/scripts/*.sh "$PROJECT_ROOT"/*.py; do
    if [ -f "$script" ]; then
        chmod +x "$script"
        echo "✅ 実行権限付与: $(basename "$script")"
    fi
done

# ログファイル初期化
echo "ログファイルを初期化中..."
touch "$PROJECT_ROOT/logs/cron.log"
echo "$(date '+%Y-%m-%d %H:%M:%S') - VPS初期セットアップ完了" >> "$PROJECT_ROOT/logs/cron.log"

# 環境確認サマリー
echo ""
echo "=== セットアップ完了サマリー ==="
echo "プロジェクトルート: $PROJECT_ROOT"
echo "Python実行パス: $PYTHON_PATH"
echo "ディスク使用率: ${DISK_USAGE}%"

# 作成されたディレクトリ構造表示
echo ""
echo "作成されたディレクトリ構造:"
tree "$PROJECT_ROOT" -L 3 2>/dev/null || find "$PROJECT_ROOT" -type d | head -20

echo ""
echo "=== 次の手順 ==="
echo "1. WordPress認証設定:"
echo "   - WordPress管理画面でアプリケーションパスワードを生成"
echo "   - config/config.vps.ini のパスワードを更新"
echo ""
echo "2. 認証テスト実行:"
echo "   cd $PROJECT_ROOT"
echo "   source venv/bin/activate"
echo "   python scripts/wordpress_auth_diagnostic.py"
echo ""
echo "3. cron設定:"
echo "   ./scripts/setup_cron.sh"
echo ""
echo "4. システム稼働開始:"
echo "   python main.py --vps-mode --test-connections"
echo ""
echo "✅ VPS初期セットアップが完了しました！"