# IteraGuard v5.3 선택·정책·UI 진단 후보

2026-11-12. 기본 판단 계약 v5.1 유지. 소스/화면 설명 및 Windows 배포 도구 수정 후보다. 실제 Zoro 추론 0회, 사용자 원시 사건 미재현, 정책·질문·임계값 변경 없음.

먼저 docs/V53_VALIDATION_REPORT.md, docs/IteraGuard_Zoro_Jev_Strategy_Review_2026-11-12_v1.1.md를 읽는다. 변경 내역은 internal/VERSION_LEDGER.md에 있다. internal/evidence/v53/가 이번 실행 기록이다. v51/v52 기록은 과거 증거다.

## 실행
프로젝트 루트에서 `python -X utf8 tools/replay_choice_path_v53.py`와 `node tests_v53/test_choice_ui.js`로 오프라인 재현한다.
Arena는 `python -X utf8 -m arena.server --port 8769`로 시작한다. 실모델은 기존 운영자 설정과 검증된 endpoint가 별도로 필요하다. 미연결 시 실제 결과를 모의 결과로 숨겨 대체하지 않는다.
단문 데스크톱은 `bun apps/desktop/server.js --port=8770 --no-browser`. 번들 자산은 재생성했다.

## 버전 구분
외부 패키지 v5.3, 판단 엔진/생성 앱 내부 버전 5.1. 기존 모델/프로필 지문은 유지한다. Android는 디버그 빌드이고 실기기 미검증이다. 이 폴더 안의 구버전 skill/APK는 보존 자료다. 현재 스킬 별칭 dmsg.skill/dmsg.zip은 진단 안내를 포함한다. 새 MANIFEST_V53_SHA256.json만 현재 패키지 파일 무결성 기준이다. 이전 manifest는 해당 시점 기록이다.
