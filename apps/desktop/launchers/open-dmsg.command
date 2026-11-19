#!/bin/bash
# 의심계 실행 (macOS). 이 창이 열려 있는 동안 앱이 동작합니다. 종료: 창 닫기 또는 Ctrl+C
cd "$(dirname "$0")"
xattr -d com.apple.quarantine ./dmsg-desktop 2>/dev/null
chmod +x ./dmsg-desktop
exec ./dmsg-desktop "$@"
