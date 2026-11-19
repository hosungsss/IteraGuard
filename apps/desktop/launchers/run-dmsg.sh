#!/bin/sh
# 의심계 실행 (Linux). 종료: Ctrl+C
cd "$(dirname "$0")" && chmod +x ./dmsg-desktop && exec ./dmsg-desktop "$@"
