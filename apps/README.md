# 의심계 v5.1 앱

| 실행면 | 진입점 | 범위 |
|---|---|---|
| PC 아레나 | `python -m arena.server --port 8769` | 실제 Typed + SQLite 확인 작업/관측/종료/재개 |
| PC 단문 앱 | `bun apps/desktop/server.js --port=8770 --no-browser` | 현재 문장 Typed + 별도 기기 내 NLP/LinkGuard/도메인 |
| PWA | `dist/IteraGuard_DoubtMeter_v5_1_web_pwa.zip` | 웹 자산·기기 내 NLP. 아레나 세션 위험 없음 |
| Android debug APK | `dist/IteraGuard_DoubtMeter_v5_1_android_debug.apk` | versionCode51/versionName5.1, 오프라인, 실기기 NOT_RUN |

Typed 요청은 profile/policy/질문 지문을 전송 전에 고정한다. 기본 선택은 configs/v51_release_selection.json과 실행 manifest가 정본이다. DRA 비교는 원본 v50-baseline과 결합한다. 기기 내 NLP는 Zoro-1 및 11문항 Typed 후보와 별도다. Android에 GPU 가중치나 인터넷 권한을 포함하지 않는다.

새 빌더는 tools/build_distribution_v51.py, FULL은 tools/build_release_v51.py이며 소스 밖 출력과 tools/verify_release.py 검사를 사용한다. 실제 배포 최종 기록은 PWA/APK/desktop 자산32 PASS, APK 독립 구조·v2 서명·변조검출 PASS(실기기 NOT_RUN). FULL/독립추출 검증 영수증은 배포 ZIP 옆 [Back Data/v5.1_구현기록_20261104/IMPLEMENTATION_RECEIPT.json](<../../Back Data/v5.1_구현기록_20261104/IMPLEMENTATION_RECEIPT.json>) 참고다. APK 임시 debug 키는 메모리에서만 만들며 이전 APK와 서명/업데이트 호환성을 보장하지 않는다. Android 실기기·iOS·데스크톱 크로스컴파일 실행은 NOT_RUN이다. 현재 상태와 실행 범위는 루트 README 및 docs/V51_IMPLEMENTATION_REPORT.md를 따른다.
