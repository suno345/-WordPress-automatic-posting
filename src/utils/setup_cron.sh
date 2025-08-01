#!/bin/bash

# WordPress自動投稿システムのcronジョブ設定スクリプト

# 色付き出力用の定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}WordPress自動投稿システム - Cronジョブ設定${NC}"
echo "=================================="

# スクリプトのディレクトリを取得
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Pythonパスの確認
PYTHON_PATH=$(which python3)
if [ -z "$PYTHON_PATH" ]; then
    echo -e "${RED}エラー: Python3が見つかりません${NC}"
    exit 1
fi

echo -e "プロジェクトディレクトリ: ${YELLOW}$PROJECT_DIR${NC}"
echo -e "Python実行パス: ${YELLOW}$PYTHON_PATH${NC}"

# main.pyの存在確認
if [ ! -f "$PROJECT_DIR/main.py" ]; then
    echo -e "${RED}エラー: main.pyが見つかりません${NC}"
    exit 1
fi

# config.iniの存在確認
if [ ! -f "$PROJECT_DIR/config.ini" ]; then
    echo -e "${YELLOW}警告: config.iniが見つかりません${NC}"
    echo "config.ini.exampleをコピーして設定してください"
fi

# cronジョブの設定内容
CRON_JOB="*/15 * * * * cd $PROJECT_DIR && $PYTHON_PATH main.py >> logs/cron.log 2>&1"

echo ""
echo "以下のcronジョブを設定します:"
echo -e "${YELLOW}$CRON_JOB${NC}"
echo ""
echo "この設定により、15分ごとにスクリプトが実行されます。"
echo ""

# ユーザーに確認
read -p "cronジョブを設定しますか？ (y/N): " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    # 現在のcrontabを取得
    crontab -l > /tmp/current_cron 2>/dev/null || touch /tmp/current_cron
    
    # 既に同じジョブが存在するかチェック
    if grep -F "$PROJECT_DIR/main.py" /tmp/current_cron > /dev/null; then
        echo -e "${YELLOW}警告: 既に同じプロジェクトのcronジョブが存在します${NC}"
        echo "既存のジョブ:"
        grep -F "$PROJECT_DIR/main.py" /tmp/current_cron
        echo ""
        read -p "既存のジョブを置き換えますか？ (y/N): " -n 1 -r
        echo ""
        
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            # 既存のジョブを削除
            grep -vF "$PROJECT_DIR/main.py" /tmp/current_cron > /tmp/new_cron
            mv /tmp/new_cron /tmp/current_cron
        else
            echo "設定をキャンセルしました"
            rm /tmp/current_cron
            exit 0
        fi
    fi
    
    # 新しいジョブを追加
    echo "$CRON_JOB" >> /tmp/current_cron
    
    # crontabを更新
    crontab /tmp/current_cron
    
    # 一時ファイルを削除
    rm /tmp/current_cron
    
    echo -e "${GREEN}✓ cronジョブを設定しました${NC}"
    echo ""
    echo "設定されたcronジョブを確認するには:"
    echo "  crontab -l"
    echo ""
    echo "cronジョブを削除するには:"
    echo "  crontab -e"
    echo "  (該当行を削除して保存)"
    
else
    echo "設定をキャンセルしました"
fi

echo ""
echo "=================================="
echo -e "${GREEN}設定完了${NC}"