#!/bin/bash
# GitHub推送脚本 - 使用gh CLI自动处理认证

cd /Users/hercmoray/.openclaw/workspace/openclaw-investment

# 确保使用gh的credential helper
git config --global credential.https://github.com.helper ""
git config --global --unset-all credential.https://github.com.helper 2>/dev/null || true
git config --global --add credential.helper ""
git config --global --add credential.https://github.com.helper "!/opt/homebrew/bin/gh auth git-credential"

# 创建仓库并推送
echo "Creating GitHub repository..."
gh repo create openclaw-investment \
  --public \
  --description "AI驱动的自我进化投资分析与模拟系统 - Self-Evolving Investment Analyst" \
  --source=. \
  --remote=origin \
  --push

echo "Done!"
