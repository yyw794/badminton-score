#!/bin/bash
# 更新活动数据并推送到 GitHub
# 使用方法：./update_data.sh "第 X 周活动"

set -e

# 获取注释参数，默认为当前日期
COMMENT="${1:-更新活动数据 $(date +%Y-%m-%d)}"

echo "🏸 开始更新活动数据..."
echo ""

# 1. 生成对阵表
echo "📋 生成对阵表..."
uv run python 排阵/lineup_scheduler.py

# 2. 导出 Web 数据 + 保存到数据库
echo "🌐 导出 Web 数据..."
uv run python docs/export_to_web.py

# 3. 提交并推送
echo "📤 提交到仓库..."
git add .
git commit -m "$COMMENT"
git push

echo ""
echo "✅ 完成！数据已更新并推送到 GitHub Pages"
echo "   访问：https://yyw794.github.io/badminton-score/"
echo ""
echo "📊 查看历史统计:"
echo "   uv run python db.py stats"
