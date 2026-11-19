# 의심계 v5.0 앱

| 실행면 | 진입점 | 범위 |
|---|---|---|
| PC 아레나 | `python -m arena.server --port 8769` | 실제 Typed endpoint + SQLite 확인 작업/관측/종료/재개 |
| PC 단일 문장 앱 | `bun apps/desktop/server.js --port=8770 --no-browser` | 로컬 relay + 공통 계약, 오프라인 NLP/LinkGuard/도메인 기능 |
| PWA | `dist/IteraGuard_DoubtMeter_v5_0_web_pwa.zip` | 최신 웹 자산, 기기 내 NLP, HTTPS 호스팅 설치형 웹앱 |
| Android 개발 APK | `dist/IteraGuard_DoubtMeter_v5_0_android_debug.apk` | version 5.0/code 50, 오프라인, 디버그 서명, 실기기 NOT_RUN |

앱/아레나의 Typed 기본은 legacy이며 DRA는 비교다. NLP indicator는 기기 내 NLP에서만 적용한다. 모델/실행 모드와 정책/후처리를 하나의 모델 정확도로 합산하지 않는다. PC 아레나의 세션 기능은 PWA/APK에 없다. Android에는 PC GPU 모델·인터넷 권한을 포함하지 않는다. iOS/크로스컴파일 새 실행 근거도 없다.

빌드는 `python tools/build_distribution_v50.py`, 전체 패키지는 `python tools/build_release_v50.py <외부출력폴더>`, 검사는 `python tools/validate_v50.py --report-dir <외부출력폴더>` 및 `python tools/verify_release.py <FULL_ZIP>`다. 이전 v4 빌더/파일명은 역사용이다. 상세 상태는 루트 README와 docs/V50_IMPLEMENTATION_REPORT.md를 따른다.
