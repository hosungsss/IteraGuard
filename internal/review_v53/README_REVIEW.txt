IteraGuard v5.3 검토 자료 사용법

1. IteraGuard_v53_Critical_Review_20261119.txt가 전체 검토보고서다.
2. 코드·데이터 검산 결과 JSON과 Python 테스트 로그를 함께 제공한다.
3. 아래 명령의 PROJECT_ROOT는 원래 구조를 보존한 IteraGuard v5.3 프로젝트 복사본이다. 제품 소스와 기존 데이터는 이 ZIP에 다시 포함하지 않았다.

python code_audit_repro.py PROJECT_ROOT
python recheck_saved_evidence.py PROJECT_ROOT

첫 스크립트는 통제 Typed 응답으로 현행 평가·SQLite 업무 경로를 검사하고 endpoint 허용 여부를 확인한다. 모델·네트워크를 호출하지 않으며 임시 SQLite와 새 임시 결과 파일을 만든다. 두 번째는 기존 AI24의 라벨·응답·결과만 읽고 stdout으로 검산 결과를 내보낸다. 원래의 검토 JSON을 덮어쓰지 않는다.

기존 제품 테스트는 PROJECT_ROOT에서 다음처럼 실행한다.
python -m unittest tests_v51.test_execution -v
python -m unittest tests_v51.test_profiles -v
node tests_v53/test_choice_ui.js

Python/Node가 필요하며 일부 Python 테스트가 Node를 사용한다. 외부 패키지를 자동 설치하지 않는다. 기록은 2026-11-19의 소스에 대한 것이며 제품 수정 후 성공을 보장하지 않는다. 25개 Python과16개 Node 테스트 통과는 모델의 사기 탐지 정확도와 별개다.

HANDOFF_CHANGELOG.md는 이번 검토의 변경·검증·미수행·복구 범위를 기록한다.
