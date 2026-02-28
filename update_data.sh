#!/bin/bash
# 更新活动数据并推送到 GitHub
# 使用方法：./update_data.sh 或 ./update_data.sh "自定义活动名称"

set -e

echo "🏸 开始更新活动数据..."
echo ""

# 从微信接龙文件提取活动名称和日期
SIGNUP_FILE="排阵/微信接龙.txt"
EVENT_NAME=""

if [ -f "$SIGNUP_FILE" ]; then
    # 读取第一行（非注释行）
    FIRST_LINE=$(grep -v "^#" "$SIGNUP_FILE" | head -1)
    
    # 尝试提取日期（支持多种格式）
    # 例如："2026-02-28 周一活动" 或 "2 月 28 日 周一活动" 或 "02-28 周一活动"
    if echo "$FIRST_LINE" | grep -qE '[0-9]{4}-[0-9]{2}-[0-9]{2}'; then
        DATE_STR=$(echo "$FIRST_LINE" | grep -oE '[0-9]{4}-[0-9]{2}-[0-9]{2}' | head -1)
        EVENT_NAME="$DATE_STR 活动"
    elif echo "$FIRST_LINE" | grep -qE '[0-9]{1,2}月[0-9]{1,2}日'; then
        DATE_PART=$(echo "$FIRST_LINE" | grep -oE '[0-9]{1,2}月[0-9]{1,2}日' | head -1)
        MONTH=$(echo "$DATE_PART" | sed 's/月.*//')
        DAY=$(echo "$DATE_PART" | sed 's/.*月\([0-9]*\)日/\1/')
        YEAR=$(date +%Y)
        DATE_STR=$(printf "%04d-%02d-%02d" $YEAR $MONTH $DAY)
        EVENT_NAME="$DATE_STR 活动"
    elif echo "$FIRST_LINE" | grep -qE '[0-9]{1,2}-[0-9]{1,2}'; then
        DATE_PART=$(echo "$FIRST_LINE" | grep -oE '[0-9]{1,2}-[0-9]{1,2}' | head -1)
        MONTH=$(echo "$DATE_PART" | cut -d'-' -f1)
        DAY=$(echo "$DATE_PART" | cut -d'-' -f2)
        YEAR=$(date +%Y)
        DATE_STR=$(printf "%04d-%02d-%02d" $YEAR $MONTH $DAY)
        EVENT_NAME="$DATE_STR 活动"
    else
        # 没有日期，使用当前日期
        DATE_STR=$(date +%Y-%m-%d)
        EVENT_NAME="$DATE_STR 活动"
    fi
fi

# 允许命令行参数覆盖
if [ -n "$1" ]; then
    EVENT_NAME="$1"
fi

echo "📅 活动名称：$EVENT_NAME"
echo ""

# 1. 生成对阵表
echo "📋 生成对阵表..."
uv run python 排阵/lineup_scheduler.py

# 2. 导出 Web 数据 + 保存到数据库
echo "🌐 导出 Web 数据..."
uv run python docs/export_to_web.py "$EVENT_NAME"

# 3. 提交并推送
echo "📤 提交到仓库..."
git add .
git commit -m "$EVENT_NAME"
git push

echo ""
echo "✅ 完成！数据已更新并推送到 GitHub Pages"
echo "   访问：https://yyw794.github.io/badminton-score/"
echo ""
echo "📊 查看历史统计:"
echo "   uv run python db.py stats"
