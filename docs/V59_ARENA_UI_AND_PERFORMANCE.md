# v5.9 source candidate — Arena 판단 속도와 화면 재설계

작성 2026-11-19 KST · 기준 커밋 `046feef` (v5.8 Rule Tweak shadow 병합) · 작업 브랜치 `feature/v59-arena-ui-performance`

## 1. 무엇을 바꿨나

### 1.1 판단 경로 속도 (결정 결과 불변)
**프로파일 근거:** Arena 요청 1건이 질문 프로필 레지스트리 전체를 **12번** 다시 만들고 검증했다.
- 위치: `v51_profiles.build_registry`
- 비용: 50건 프로파일에서 전체 6.0초 중 4.7초

**변경 내용:** 요청 범위 검증(`integration/v51_profiles.verification_scope`)을 도입했다.
- 한 요청 안에서는 첫 호출이 지금과 같은 전체 fail-closed 검증을 수행한다.
- 같은 스레드·같은 범위의 이후 호출은 그 검증 결과의 **복사본**을 쓴다.
- Arena는 모델 호출 **전**과 **후**에 각각 범위를 두고(`refresh_scope`), 네트워크 호출 동안 바뀐 계약을 잡아낸다.
- 범위 밖 호출(테스트·도구·정책 직접 호출)은 예전처럼 매번 검증한다.
- 스레드 로컬이므로 다른 요청과 섞이지 않는다.

| 지표 (통제 응답 10종 × 300회, Python 3.12, 동일 머신) | 기준 046feef | v5.9 |
|---|---|---|
| evaluate 전체 p50 / p95 (ms) | 53.99 / 70.43 | 19.59 / 28.85 |
| 서버 pipeline_ms p50 / p95 | 42.33 / 56.82 | 16.63 / 24.10 |
| 요청당 레지스트리 재구성 | 12회 | ≤3회 (식별 바인딩 1 + 모델 전 1 + 모델 후 1) |

- **동일성:** 단일 턴 10건과 다중 턴 10시퀀스(위험 → 평범 → 모델 실패 → 복구)의 정규화 결과를 비교했다. 정규화 결과는 60개 객체이며, 기준 커밋과 **바이트 단위로 동일**하다(SHA-256 `2162b9d7…e9fb`). 정규화에서 제외한 항목은 요청 ID, 시각, 지연, 무작위 업무 ID, 계약 지문이다.
- **계약 지문:**
  - 바뀐 것: `integration/v51.py`와 `v51_profiles.py`의 소스 해시. 이에 따라 `profile_registry_fingerprint`와 v51 `manifest_fingerprint`(`7a6df762…` → `86e02915…`)도 바뀌었다. 저장소의 exporter(`tools/export_v51_profiles.py`, `tools/export_v51_contract.py`)로 다시 생성했고, 4개 exporter의 `--check`가 모두 통과한다.
  - **그대로인 것:** 모델로 가는 질문·응답 계약. `question_contract_sha256 63c2ff24…`, `questions_sha256`, 응답 스키마가 이에 해당한다.
- **한계:**
  - 통제 응답 기준의 서버 내부 처리 시간이다. 실제 Zoro-1 추론 시간과 브라우저 전체 지연은 포함하지 않는다.
  - 다른 머신·다른 부하에서는 수치가 달라진다.

### 1.2 Arena 화면 재설계 (`arena/web`)
- **원칙:** 첫 화면에는 꼭 필요한 것만 둔다(문장 입력, 판단하기 버튼, 결과, 판단 과정). 세션 관리·기록·증거·실행 계약은 오른쪽 시트(`세션 · 기록`)로 옮겼다. 확인 업무 패널은 열린 업무가 있을 때만 보인다.
- **판단 과정 시각화(`visual.js`):** 입력 → Zoro-1 제안 → 계약 검증 → 독립 정책 → 확인 업무 5단계를 진행 중·완료·주의·실패로 표시한다. 단계 문구는 **서버 응답의 실제 필드**로 만든다.
  - 모델 단계: `model_status`, `provenance.execution_source`, `latency_ms`
  - 계약 단계: `manifest_fingerprint`, `question_profile_id`
  - 정책 단계: `current_turn_action`, `reason`
  - 업무 단계: `open_task_count`
  - 서버 처리 시간: `provenance.pipeline_ms`
  - 단, 요청 도중의 단계 진행 애니메이션은 표시용이다. 서버가 단계별 진행을 실시간으로 보내지는 않는다.
- **판정 문구:**
  - 코드 대신 사람이 읽는 제목을 보여 주고, 코드는 작게 남겼다.
  - 이전 위험 유지(`PRIOR_RISK_UNRESOLVED`), 모델 실패, 입력 변경 후 재판단 필요를 서로 다른 제목으로 구분한다.
  - 멈춤·보류·주의 상태에는 "확인 전까지 하지 말 일"을 한 줄로 보여 준다. 표시 문구일 뿐이며 서버 판단은 바뀌지 않는다.
- **디자인:**
  - 리퀴드 글래스 패널(배경 흐림, 채도, 상단 반사광, 미세 테두리)
  - 판정 색에 따라 바뀌는 오로라 배경
  - 캔버스로 그린 3D 유리 구체와 궤도 고리. 라이브러리를 쓰지 않았고, 판단 중에는 빨라지며, 화면 밖이나 백그라운드에서는 멈춘다.
  - 입력 카드의 미세한 3D 기울기
  - Toss식 단일 주 버튼
- **접근성:**
  - 키보드 포커스 표시, `aria-live`, ESC로 시트 닫기
  - `prefers-reduced-motion`이면 모든 애니메이션을 끈다.
  - backdrop-filter를 지원하지 않는 브라우저에서는 불투명 배경으로 대체한다.
  - Ctrl/⌘+Enter로 판단을 실행한다.
- **보안·계약:**
  - CSP(`script-src 'self'; style-src 'self'`)는 그대로다. 인라인 스크립트·스타일과 외부 글꼴·자원은 없다.
  - `visual.js`는 main.js의 fetch를 **관찰만** 한다. URL·요청 본문을 그대로 넘기고, 판단 필드·localStorage·입력값을 쓰지 않는다(`tests_v59/test_arena_ui_contract.py`).
  - main.js 변경은 업무 ID를 앞 8자리만 보이게 한 것 하나뿐이다.
  - 서버에는 `/visual.js` 정적 경로만 추가했다.
  - `visual.js`는 판단 출처 증명(`arena_sources`) 대상이 아니다. 화면 표시 계층이고, 판단·저장에 관여하지 않는다.

## 2. 검증 (이 커밋에서 실제 실행)
- **Python 3.12 unittest:**
  - 통과 스위트(테스트 수): rulebook 26, rule_tweak_shadow 12, v56 16, v54 9, v52, v50, v49, linkguard, v59 15
  - v51: 75개 중 2 skip
  - CI는 3.12를 쓴다. 3.13에서는 기존 Unicode 버전 불일치로 v51 테스트 1개가 실패한다. 이 실패는 기준 커밋에도 있었다.
- **Node:** `test_session_ui.js` + `test_choice_ui.js` 24/24
- **실제 Chromium(Playwright):**
  - 환경: 데스크톱 1360px, 모바일 390px
  - 흐름: 위험 문장 → 평범한 문장(이전 위험 유지) → 모델 실패 → 시트 열기·ESC 닫기
  - 결과: 콘솔 오류 0, 가로 넘침 없음(`internal/evidence/v59/ui/`)
  - **주의:** 모델 응답은 저장된 fixture를 재생했다(`tools/v59/fixture_demo_server.py`, `CONTROLLED_CLIENT`). 실제 Zoro-1 추론이 아니다.
- **성능·동일성:** `tools/v59/bench_arena.py`, `tools/v59/equivalence_dump.py`, `internal/evidence/v59/bench_*.json`

## 3. 실행하지 않은 것 (NOT_RUN / BLOCKED)
- 실제 Zoro-1 서버 추론과 그 지연 시간
- 배포 사이트(`*.chatgpt.site`). 자동 접근이 robots 정책으로 막혀 있어 확인하지 못했다.
- Safari·Firefox 실기 렌더링, Android·iOS 실기기, NPU
- 독립 사용자 평가와 판단 정확도 개선. **판단 정책은 의도적으로 바꾸지 않았다.**
- 기존 APK·PWA·desktop 자산(`apps/`)은 이 Arena 화면을 포함하지 않으며 다시 만들지 않았다.

## 4. 되돌리기
이 PR을 revert하면 된다. SQLite 마이그레이션은 없다. 계약 지문은 revert 시 이전 값으로 함께 돌아간다.
