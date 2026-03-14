#!/bin/bash
# GitHub Desktop 推送脚本
# 在macOS终端运行此脚本

echo "🚀 准备推送 openclaw-investment 到 GitHub..."

cd /Users/hercmoray/.openclaw/workspace/openclaw-investment

# 检查GitHub Desktop是否运行
if pgrep -x "GitHub Desktop" > /dev/null; then
    echo "✅ GitHub Desktop 正在运行"
else
    echo "⚠️  GitHub Desktop 未运行，请先启动它"
    open -a "GitHub Desktop"
    sleep 3
fi

# 配置git使用GitHub Desktop的凭据
git config --local credential.helper osxkeychain

# 删除旧的remote（如果存在）
git remote remove origin 2>/dev/null

# 使用HTTPS添加remote（GitHub Desktop会自动处理认证）
git remote add origin https://github.com/MaHsiChu/openclaw-investment.git

# 创建GitHub仓库（如果不存在）
echo "📦 创建GitHub仓库..."
gh repo create openclaw-investment \
  --public \
  --description "AI自我进化投资分析系统 - Self-Evolving Investment Analyst" \
  --source=. \
  --remote=origin 2>/dev/null || echo "仓库可能已存在，继续推送..."

# 推送到GitHub
echo "📤 推送到GitHub..."
git push -u origin master

if [ $? -eq 0 ]; then
    echo "✅ 推送成功！"
    echo "🌐 仓库地址: https://github.com/MaHsiChu/openclaw-investment"
else
    echo "❌ 推送失败"
    echo ""
    echo "💡 请尝试手动方式："
    echo "1. 打开 GitHub Desktop"
    echo "2. 点击 File → Add Local Repository"
    echo "3. 选择文件夹: /Users/hercmoray/.openclaw/workspace/openclaw-investment"
    echo "4. 点击 'Publish Repository'"
fi
