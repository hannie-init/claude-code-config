#!/bin/bash
set -e

echo "=== figma-web-compare 초기 설치 ==="
echo ""
echo "[1/2] playwright Python 패키지 설치 중..."
pip install playwright
echo ""
echo "[2/2] Chromium 브라우저 바이너리 설치 중..."
playwright install chromium
echo ""
echo "설치 완료! 이제 Chrome을 디버그 모드로 실행하세요:"
echo ""
echo '  open -a "Google Chrome" --args --remote-debugging-port=9222'
echo ""
echo "alias로 등록하려면:"
echo '  echo '"'"'alias chrome-debug="open -a \"Google Chrome\" --args --remote-debugging-port=9222"'"'"' >> ~/.zshrc'
