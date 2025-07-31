#!/bin/bash

# WordPress自動投稿システム - Cron設定スクリプト
# 15分間隔で自動実行するためのスクリプト

# 現在のディレクトリを取得
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_PATH=$(which python3)

# Cron用のログディレクトリを作成
mkdir -p "${SCRIPT_DIR}/logs/cron"

# Cronジョブ設定用の一時ファイル作成
CRON_FILE="/tmp/doujin_blog_cron.txt"

# 既存のcronジョブを取得
crontab -l > "${CRON_FILE}" 2>/dev/null || echo "" > "${CRON_FILE}"

# 既存の同じジョブがあるかチェック
if ! grep -q "doujin_blog_auto_post" "${CRON_FILE}"; then
    echo "# WordPress同人ブログ自動投稿システム" >> "${CRON_FILE}"
    echo "*/15 * * * * cd \"${SCRIPT_DIR}\" && \"${PYTHON_PATH}\" main.py >> \"${SCRIPT_DIR}/logs/cron/auto_post.log\" 2>&1 # doujin_blog_auto_post" >> "${CRON_FILE}"
    
    # Cronに設定を適用
    crontab "${CRON_FILE}"
    
    echo "Cronジョブが設定されました："
    echo "- 実行間隔: 15分毎"
    echo "- スクリプト: ${SCRIPT_DIR}/main.py"
    echo "- ログファイル: ${SCRIPT_DIR}/logs/cron/auto_post.log"
    echo ""
    echo "設定を確認するには: crontab -l"
    echo "ログを確認するには: tail -f ${SCRIPT_DIR}/logs/cron/auto_post.log"
else
    echo "Cronジョブは既に設定されています。"
fi

# 一時ファイルを削除
rm -f "${CRON_FILE}"

echo ""
echo "=== Cron設定完了 ==="
echo "システムは15分間隔で自動実行されます。"
echo ""
echo "手動でCronジョブを削除する場合："
echo "crontab -e で編集し、該当行を削除してください。"