#!/bin/bash

# 一键部署到 GitHub Pages 脚本
# 使用方法：./deploy.sh

set -e

echo "🚀 开始部署到 GitHub Pages..."

# 检查是否已设置 git 用户信息
if ! git config user.name &> /dev/null; then
    echo "⚠️  请先设置 git 用户名和邮箱："
    echo "   git config --global user.name '你的名字'"
    echo "   git config --global user.email '你的邮箱'"
    exit 1
fi

# 创建仅包含 web 文件的临时分支
echo "📦 准备部署文件..."

# 确保 web 文件已提交
git add 排阵/web/
git commit -m "feat: 更新 web 应用" || echo "✅ 没有新更改"

# 提示用户创建仓库
echo ""
echo "📋 请按以下步骤操作："
echo ""
echo "1️⃣  在 GitHub 创建新仓库："
echo "   👉 访问：https://github.com/new"
echo "   👉 仓库名：badminton-score（或你喜欢的名字）"
echo "   👉 设为 Public"
echo "   👉 不要勾选 'Initialize with README'"
echo ""
read -p "2️⃣  创建完成后，输入仓库地址（如：https://github.com/zhangsan/badminton-score.git）: " REPO_URL

# 添加远程仓库
git remote add origin "$REPO_URL" 2>/dev/null || git remote set-url origin "$REPO_URL"

# 推送到 GitHub
echo ""
echo "📤 推送到 GitHub..."
git branch -M main
git push -u origin main

echo ""
echo "✅ 推送成功！"
echo ""
echo "📋 接下来："
echo "   1. 进入你的 GitHub 仓库页面"
echo "   2. 点击 Settings → Pages"
echo "   3. Source 选择 'Deploy from a branch'"
echo "   4. Branch 选择 'main'，文件夹 '/'"
echo "   5. 点击 Save"
echo ""
echo "⏳ 等待 1-3 分钟后，你的网站将上线："
echo "   👉 https://你的用户名.github.io/badminton-score/"
echo ""
