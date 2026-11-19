# IteraGuard / 의심계 — 내부 버전 장부

**사용 목적:** 이 파일만 과거 버전 대비 업그레이드·수정·폐기·검증 내역을 누적 기록한다. 다른 문서에는 버전 변경 설명을 넣지 않는다.

## v3.1.0 → v3.2.0 (2026-10-28)

| 범주 | 이전 상태(v3.1.0) | 현행 조치(v3.2.0) | 검증 방법 |
|---|---|---|---|
| 제품 요구사항 | `dmsg/references/PRD.md`에 축약된 범위·R01~R14 | 세부 기능 PRD-01~PRD-20, 정확한 현행 구현 상태, UX·보안·수용기준 명세 확장 | 정적 명세 참조·요구사항 검증 테스트 |
| System Prompt | `references/PROMPTS.md`에 typed 질문 중심, System Prompt 별도 마스터 문서 부재 | 비신뢰 입력·근거 출처·오탐·오류·모드·최종 정책 분리 18개 규칙을 가진 제어 계층 프롬프트 문서 추가 | 룰 번호/필수 키/스키마 검증 |
| 추적성 | `notes/03_REQUIREMENT_TRACE.md`의 코드·테스트 중심 항목 | PRD↔GUARD↔구현↔테스트 20개 행 추적표 및 역방향 점검 | 문서 간 ID 일치 점검 |
| 문서 구조 | archive/ 및 CHANGELOG, TEAM_GUIDE_DELTA 등에 변경 기록 분산 | 버전 변경 이력을 `internal/VERSION_LEDGER.md`로 통합, 일반 문서는 현행 상태로만 작성 | 패키지 파일 목록·마커 스캔 |
| 인수인계 | `01_MASTER_PROMPT_NEXT_GPT_v5.md`가 이전 상태와 스냅샷을 서술 | `MASTER_HANDOFF_PROMPT.md`에서 현행 요구사항·실행 지침·파일명 규칙만 설명 | 문서 스캔 |
| 배포 패키징 | 파일명 `IteraGuard_DoubtMeter_Upgraded_Handoff_v3.1.0_2026-10-28.zip` | `[v3.2.0] IteraGuard_DoubtMeter.zip` | ZIP 파일 이름과 압축 검사 |
| 구현 | v3.1.0 정책·세션·합성 UI 기능 | 동작 코드의 핵심 정책은 그대로 유지, 버전 표기와 스킬 참조 구조 정리, 명세 추적 테스트 추가 | 기존 단위 테스트와 추가 정적 테스트 |
| 스킬 검증 | `references/CHANGELOG.md`, `TEAM_GUIDE_DELTA.md` 존재 필수 | 공식 현재 문서로 참조 목록 교체, changelog 필수검사 제거 | `scripts/validate_skill.py` |

**실제 기능 구현에 대한 한계:** 이번 변경은 주로 요구사항 명확화·프로토콜·검증 추적성을 강화한다. 실제 Zoro-1 API 연결이나 검증 데이터 확보를 완료한 것으로 기록하면 안 된다.

## 계승한 v3.1.0 증거

- Python unittest 73개 통과(당시 실행 결과); 실제 Zoro 추론 없음.
- 합성 fixture 8개, 세션 재평가/버전·멱등 처리, 로컬 UI 실행 가능.
- 원본 v4.0 제안서 PDF는 공동 검토용 설계 문서이며 최종 합의 승인 확인 전.
- 출처 패키지: `IteraGuard_DoubtMeter_Upgraded_Handoff_v3.1.0_2026-10-28.zip`.

## v3.2.0 릴리스 검증 기록

- **검증 실행일:** 2026-10-28.
- **환경:** Python 3.13.5; Node.js JavaScript 구문 검증; 로컬 HTTP API.
- **회귀·정적 명세 테스트:** 총 **81개 통과** (정책·세션 단위 테스트 73 + 명세·추적 테스트 8).
- **스킬 검사:** `scripts/validate_skill.py` PASS.
- **정적 구문:** Python `compileall` PASS, `node --check web/main.js` PASS.
- **HTTP smoke:** GET fixture(8개), POST start→위험 송금→확인 계획→정상 경고→수동 입력 흐름 PASS. 외부 금융·통신 조치는 수행하지 않음.
- **실모델 Zoro 호출:** NOT RUN. 모델 출력·실사용 성능·실피해 감소·별도 브라우저 시각 검수는 미검증.
- **입수 소스 해시:** v3.1.0 릴리스 `654ea32f6f2d0d0f441314ee262182f91b1951ef9e6f8b1ec3ad81c1ef49f970`.
- **기획 근거 ZIP 해시:** `950a2eb29e6f388f052eea05ffedc52cc95d19c135539c33e6efeb228c9a0b91`.
- **현재 핵심 문서 SHA-256:**
  - `docs/01_PRODUCT_REQUIREMENTS_PRD_KO.md`: `c519dfe0e630cc011e24f2c5ee0a77796afa9d332beee7e3d671728680b94ac4`
  - `docs/02_SYSTEM_PROMPT_AGENT_KO.md`: `d8a39a6784533c8e9360e79b8b48744951c7643cad0c2b421102726a34b1d3de`
  - `docs/03_TRACEABILITY_MATRIX_KO.md`: `f349cd8c8558988e3f2c563b4193cd66cc08828515e204dacca674098d1e4a45`
  - `MASTER_HANDOFF_PROMPT.md`: `f01a6f0c386faca5530af23a253847a0b814a156132e424554615f4f014ffd72`
  - `dmsg/SKILL.md`: `f55159d1faa96d1a1b6c121ec3b569cef53422d772063ef70d100a6f5cb28556`
- **한계:** 문서 적합성 테스트와 합성 데모 검증은 실제 모델 추론의 검증을 대체하지 않음.


## v3.2.0 → v3.3 (2026-10-28)

**배포 파일명:** `[v3.3] IteraGuard_DoubtMeter.zip`  
**연속 버전 규칙:** v3.3 → v3.4 → … → v3.9 → v4.0 (두 자리 SemVer가 아니라 사용자의 대회용 버전 열거 정책).  
**변경 기록의 유일한 원장:** `internal/VERSION_LEDGER.md`.

### 소스 검토와 통합 의사결정

- Google Drive 자료 폴더: `https://drive.google.com/drive/folders/1CosYeNIQUJQLNuOYx5PzjGLsdj0hWfMY`. 루트, 기술 스킬, 해커톤 참고 코드와 백엔드·프론트엔드·테스트의 하위 폴더를 탐색해 파일명을 확보했다.
- 직접 읽은 대표 소스: Drive의 `IteraGuard_v1.2_PRD.md`, `IteraGuard_System_Prompting_v1_2.md`, `TRILLION_HACKATHON_Team_Guide.md`, `dmsg/SKILL.md`, `dmsg/references/PRD.md`, `MODEL_CONTRACT.md`, `EVALUATION.md`, `PLATFORM_INSTALL.md`, `ELENCHUS_SNM_4D.md` 및 아래 다운로드한 핵심 백엔드·UI 코드.
- 자료 내부의 SRE Incident/Factory CPR/CallShield 세 도메인은 한 앱에 다 넣지 않았다. 제품 확정 범위가 Scam Intervention Arena이기 때문이다. 공통 원리(정책 승인/실행 분리, 제약조건 검사, 상태전이·멱등, 시연/실측 분리, 검증된 결과 기록)만 선별 통합했다.
- 가중치로 합성한 로짓, 발표용 온도/ECE, 가상 휴대전화 동결과 같은 시뮬레이션 요소는 검증된 Zoro 추론이나 실제 금융 행동으로 승격하지 않았다.
- Drive 폴더의 모든 중첩 바이너리·HTML 문서에 대한 픽셀단위 및 실행 검수까지 수행했다고 주장하지 않는다. 전수 파일명 탐색과 핵심 문서·코드 검토는 구분된다.

### 기능/코드의 구체적 변경

| 대상 | v3.2.0의 상태 | v3.3에서 적용한 변경 | 검증 |
|---|---|---|---|
| 증거 의미 충돌 | 겹친 근거 주석의 다른 화행을 일관성 확인 없이 처리할 수 있음 | `prototype/ontology.py`로 출처·관계를 표현하고 충돌하면 `ASK_HUMAN` | `test_conflict_in_overlapping_evidence_abstains` |
| 모델 제안 | typed 응답 파서는 있으나 제안을 안전 정책 입력으로 매핑하는 독립 경계가 없음 | `prototype/decision_oracle.py`: `MODEL_PROPOSED` 출처 유지, 근거가 존재해도 정책 권한으로 승격하지 않음 | `test_proposal_never_authorizes_high_risk` |
| typed 구조 | `noul`, `choice` 중심 구조 검증 | `score` 타입 구조 유효성 확인 및 비정상 확률 검사 추가 | `test_score_supported` 등 |
| 세션 감사 | 메타데이터 이력은 있으나 연결 무결성 검사 없음 | 이전 이벤트 해시와 새 기록으로 구성한 무서명 SHA-256 감사 체인 + `verify_audit` | `test_chain_turn_ack_turn`, `test_internal_modification_detected` |
| 결과 변조 가능성 | shallow-copy 이력/멱등 응답 노출 | 외부 반환은 `deepcopy`로 원본 분리 | `test_return_mutations_do_not_change_store_or_cached_response` |
| 시나리오 패밀리 | 합성 8개 | 합법 이체·간접 압박·권위 주장·OTP 신고·부정 교육·비밀유지 요구를 포함한 총 14개 | fixture conformance 14/14 |
| UI 실패시 최신성 | HTTP 실패 시 화면에 마지막 결과가 유지될 수 있음 | 오류 화면의 판단 보류 메시지, `last` 무효화, 재확인 안내 | JavaScript 문법 검증·HTTP 경로 확인; 브라우저 시각검수 미완 |
| HTTP 경계 | 기본 로컬 호스트 바인딩·크기 제한 | Host 검증, duplicate JSON key 거절 | HTTP smoke 8개 경로 통과 |
| 제품 문서 | 요구사항 20개, 제어 규칙 18개 | 4D Ontology·SNM·모델 신뢰경계·기술심사·발표 명세를 현행 독립 문서로 정리 | PRD/Prompt/Trace 테스트 |
| 설치 배포 | ZIP 호환 `.skill` 배포 | 버전 3.3 식별자 통일, GPT/Grok/Claude 공통 폴더 구조와 플랫폼별 조건 명시 | 구조 검사·압축 테스트; 실제 각 제품에 설치 시험은 수행되지 않음 |
| 원본 제안서 | 참고 PDF/TEX 내에 당시 변경 사유와 아카이브 문맥 존재 | 릴리스에 원본 파일을 중복 내장하지 않고 현행 시연/설계서를 따로 작성; 원본은 사용자 자료로 별도 보존 | 일반 문서 변경 이력 문장 점검 |

### 시험/증거

- Python 3.13 환경에서 `python -m unittest discover -s tests -q` **99/99 통과**.
- 작성자 주석 합성 시나리오 **14/14 conformance 통과**, 외부 일반화 성능 **미검증**.
- `python scripts/validate_skill.py` 통과, `node --check web/main.js` 통과.
- 로컬 HTTP smoke **8개 요청/검증 경로 통과**: fixture 목록, 세션 시작, 위험 송금, 의도 기록, 부정 OTP, Host 거부, 중복 JSON 키 거부, 임의 입력 보류.
- 실제 Zoro-1 서버 호출, 모델 체크포인트 식별·보정·외적 타당성·한국어 실제 사기 데이터 성능·실제 피해 예방 효과 **실행/검증하지 않음**.
- 새 감사 체인은 **서명 없음/메모리 내 검사**이므로 영구불변·제3자 증거 보존을 주장할 수 없음.
- 스킬 ZIP 포맷은 1개 `dmsg/SKILL.md` 포함. GPT/Grok/Claude 실제 설치·호출 호환성은 각 호스트에서 별도 검증 필요.

### 직접 다운로드한 핵심 코드의 SHA-256

- `callshield.py` (36050 bytes): `b7c4745f9aa55dc45aee59110a001a9fdaa06f04b7094135a6a9c133f1eee2cb`
- `factory_cpr.py` (32272 bytes): `b716400658e7629297c8c8f1dd814aaefb90cb9cd004352d6beea711417584cf`
- `decision_client.py` (17698 bytes): `87393d031710a65d5624e97c513c2bed84fd7c382cc559c61321235480bb454f`
- `decision_validator.py` (12537 bytes): `7dfa2f0282265f81a772a5daca07ed317ff91ba184cd04160b2737983a745d96`
- `workflow_orchestrator.py` (33814 bytes): `60ba4c9d06940417b9d9de9aeaf25ae6f0c43b7b922d1850940cf097ff04e12d`
- `policy_engine.py` (13472 bytes): `081378f7711efe5c2398fc33f3efec41493cf0b60b655c0daacfdc1a8697fa84`
- `audit_repository.py` (31226 bytes): `8f3ca76f8559a804779b2c556c9c74be8cb21d7844289969547277a66a81d3c3`
- `event_normalizer.py` (11857 bytes): `19203ebfc7c3682883c969b942e0d0142ef73e2a32074f3500c9aa874f47e81b`
- `schemas.py` (14886 bytes): `1ef7b8bce07840a3c3565a6ecd8212a2b018050ca5a5954177df2e7c7e3e8a3f`
- `app.py` (30570 bytes): `93a7b1bf52e880f70e8fa74a6dfacc5ed9cad374c6a05641207265d33204134b`
- `verification_service.py` (8272 bytes): `68700eb9a528cd76d5fe79676d6125a1d02fa56c9c2e0d762fdebacbd3d56204`
- `tool_executor.py` (12355 bytes): `495fb852623815f58e21fc0de366b9e11390519c9b1c679fb82bda82449abb43`
- `evaluation_suite.py` (32775 bytes): `ceda4b7f07153a663a487fb646604381928070a7179517df6736607e19a3052b`
- `test_callshield.py` (6876 bytes): `bf1c6fc8a73108247e5f1e6c1dd45123d3e4fea5459f1192b1b73372fcace02e`
- `test_factory_cpr.py` (3595 bytes): `eb7692a67d0e1d654925569e2b9df78c1cc2ae8b975a3a01b53f13732959d4a4`
- `test_iteraguard_v0_1.py` (21401 bytes): `40ae4b8240676a47840e47a0ea5d37f66df56893f961ab3f49d3be383119d7af`
- `ModelConnectionStatus.tsx.bin` (1683 bytes): `e6245e60f570f8d586044ffbbdb917d3a75720fe63314704585c3a3ec738121e`
- `ProbabilityChart.tsx.bin` (2963 bytes): `184f8fc5b3bd4a9a4a666fbeafaf4c2f87bcd267291e1fc2e3d6d75df3f2c76c`
- `ActionConsole.tsx.bin` (2860 bytes): `851d0fefbd3afafdbf25e07c6b45d5a0bd738e96952c6821f8de9b287eee669e`
- `DecisionTimeline.tsx.bin` (3300 bytes): `6a9ae8f1f6be09e71f8347c5e29ac88de4870885825007f2cf4243b14a648b7e`

## v3.3 → v3.4 (2026-10-28)

**파일 표준:** `[v3.4] IteraGuard_DoubtMeter.zip`; 다음 버전은 `v3.5`.

| 영역 | 기존 결함·부족한 상태 | 실제 수정 | 검증 |
|---|---|---|---|
| 통합 지식서 | 최상위 종합 프로젝트 설명·NotebookLM용 영상 스토리보드가 없음 | 최상위 `all.md`에 전체 연혁/현행 상태/코드/증거/스토리보드/위험/로드맵 구성 | 루트 파일·섹션·분량 검사 |
| 감사 무결성 | 내부 감사 기록 변조 후에도 상태 변경을 계속할 수 있음 | `Store._integrity_ok` 검사로 변조 시 다음 턴·확인 계획을 거부 | `test_mutated_audit_prevents_turn/ack` |
| 확인 계획 | 임의 ACK 이벤트 ID가 직전 정책 판단과 관계없는 상태로 기록될 수 있음 | `acknowledge(event_id=latest_turn_id)`의 연결 요구, UI에 해당 턴 ID 전달 | `test_ack_requires_matching_turn`, `test_ack_stale_prior_turn_rejected`, HTTP smoke |
| 교차 출처 입력 | Host 검사만으로 POST의 Origin/Fetch-Site/전송 프레이밍을 별도 거부하지 않음 | Origin·Sec-Fetch-Site·Content-Length 중복·Transfer-Encoding 거부 | `HTTPContext` 5개 테스트 |
| 고장 주입·주석 출처 | 단일 독립 대조용 합성 불변조건 검사 없음 | `scripts/metamorphic_audit.py`: 원문/주석 불일치와 MODEL_PROPOSED의 권한 상승 억제 시나리오 | 작성자 정의 합성 불변조건 38건 통과 |
| 배포 지침 | Drive 반복 재탐색·최종 폴더형 소스 업로드를 명시적 필수 단계로 관리하지 않음 | `dmsg/SKILL.md`, `MASTER_HANDOFF_PROMPT.md`, `docs/08_RELEASE_AND_DRIVE_WORKFLOW_KO.md` 반영 | 참조·내용 검사 |
| 원본 소스 보존 | 단일 런타임 외의 Drive 참고 코드 확인 범위가 불명확함 | `internal/DRIVE_SOURCE_AUDIT.md`와 검토했던 원본 참고 소스를 `internal/source_material/`에 보관 | 파일 목록·해시 검사, 전체 실행 검증 아님 |
| 스킬 배포 | 스킬과 전체 프로젝트 버전의 일치 여부 확인 필요 | `dmsg` 불변 ID, v3.4 설정·SKILL.md, ZIP 호환 스킬 2종 생성 | `scripts/validate_skill.py`, ZIP 구조 검사 |

**검증 한계:** 실제 Zoro-1 체크포인트/endpoint 호출·독립 한국어 정상/사기 사례 평가·실사용 피해 예방 효과·세 호스트의 실제 Skill 설치·전체 브라우저 시각검사는 실행하지 않았다. Google Drive 폴더 내용 업로드 성공은 연결된 업로드 실행 및 read-back 여부가 별도로 남아야만 완료로 취급한다.

## v3.4 → v3.5 (2026-10-29 KST)

**출품 릴리스 파일명:** `[v3.5] IteraGuard_DoubtMeter.zip`.

### 소스 점검·선택 기준

- 새 공동 참고 소스 `의심계_우승기획서_v1.0.md`(손호성 제공, 2026-10-29)를 세부 기술 주장까지 검토하고 원문을 `internal/source_material/team_proposals/`에 무수정 보존하였다.
- 참고 자료의 장점: 화행 중심 모델 질문, 판단과 실제 권한의 분리, 심사위원 체험, X-Ray 후보 분포, 표본 수를 가진 실측 평가. 선택적 추가 추론·온디바이스·자동 보정은 실제 모델 증거 없이 실행됐다고 주장하지 않음.
- Google Drive 루트 및 `[v3.4]`/`[v3.1.0]` 소스 폴더·원본 PRD·팀 가이드·레거시 구현 폴더의 목록을 다시 확인했다. 원격 개별 파일 전부의 최신 해시까지 대조한 것은 아니다.

### 구현 변경 요약 (이 장부 외에는 버전별 비교를 기록하지 않음)

| 영역 | v3.4 | v3.5 | 검증 |
|---|---|---|---|
| 모델 판단 경로 | 자유 입력은 모델 미접속으로 ASK_HUMAN, Typed Proposal은 정책 차단 | `model_bridge.py`: 운영자 선택형 6개 typed 질문·엄격 확률/ID 검증·화행 분리·문맥 충돌 보류·앵커 확인·비파괴적 권고 경로 구현 | `test_v35_model_bridge.py` |
| Score/choice 규약 | score는 선택지 문자열만, choice 값 필수 | score에 소수형 결과 허용, choice 부재시 유일 argmax만 채택, 동률·합계 오류 차단 | 기존/신규 회귀 테스트 |
| 실제 네트워크 경계 | 외부 endpoint 연결의 운영자 전용 runtime 없음 | `ModelClient`가 운영자 환경변수만 사용, TLS/loopback, exact path, NO_REDIRECT, DNS/용량/응답 제한, 원문을 내부 감사 이력에 기록하지 않음 | local stub HTTP + 실패 경로 테스트 |
| 세션 동시성 | 저장된 fixture 중심 버전·멱등성 | 모델 추론은 락 밖에서 수행하고 결과 커밋 전에 버전·감사 재검증. 오류·미연결은 ASK_HUMAN | 동시성·멱등 회귀 + 모형 테스트 |
| API/UI | fixture 경로만 노출, 원문 편집 기본 보류 | GET `/api/model-status`, POST `/api/model-turn`, 보호 화면 모델 버튼과 X-Ray 6문항 분포·지연·미보정 경고. 연결 기본 비활성화 | HTTP 회귀 및 JS 문법; 브라우저 시각 QA 미실행 |
| 검증 문서 | 모델 미연결·고정 레이블 중심 | 모델 권고 계약·SNM/4D Red-Team·운영자 설정 안내와 PRD↔Prompt↔Code↔Test 링크 구체화 | 명세 동일성 테스트 7개 + Skill validator |
| 문서 동기화 오류 | 원래 v3.4 ZIP의 `TRACEABILITY.md`와 루트 docs 동기화가 어긋나 자체 테스트 1개 실패 | 루트/skill 참조 문서를 동일하게 맞춰 상태 동기화 | `test_skill_and_product_docs_are_identical` 통과 |

### 테스트 증거

- Python unittest **134 / 134 통과** (합성/스텁 기준, 2026-10-29); v3.4 릴리스 기록 110개와 구분.
- 테스트에서 운영자 모델 stub에 대한 HTTP POST 왕복(실제 네트워크 loopback), 6개 질문 계약, schema/확률, 모순·인용·경고, model off, stale version/idem, Host 제한을 확인.
- `node --check web/main.js` PASS.
- `python scripts/validate_skill.py` PASS.
- `python scripts/evaluate_fixtures.py` 및 `python scripts/metamorphic_audit.py`는 별도로 실행해 로그를 기록할 것.
- 실모델 Zoro-1 체크포인트·서빙·모델 ID의 암호학적 출처 인증·독립 보정·보류/오탐/미탐·오프라인 성능·사용자 실제 행동·호스트별 .skill 설치는 **NOT VERIFIED**.
- X-Ray에 표시되는 숫자는 **해당 endpoint가 반환한 후보 선택확률일 뿐** 실제 범죄 사후확률/피해 확률이 아니며, 실모델 없이는 빈 상태가 정상이다.
- 사전 데이터 주석 및 유효성에 의존하는 안전 가드는 실제 의미 진실성을 보증하지 않는다. 모델이 잘못된 화행에 높은 확신을 가질 때의 오탐·미탐 위험이 있다.

### 잔여 P0/P1

- **P0:** 공식 모델 endpoint/checkpoint/response 계약·장비 검증, 실제 Zoro 호출 1건 이상과 실모델 엔진 인증.
- **P0:** 대화 문맥을 이용한 직접/금지/인용의 의미 검증·간접 요청 회피, 독립적으로 봉인한 한국어 시나리오 패밀리 기반 검증.
- **P0:** 생성형 추론 단계의 정식 모델 지원·지연·비용·정확도 효과; 현행 코드는 이 단계를 구현하지 않음.
- **P1:** 실제 브라우저 접근성·모바일 QA, 프로덕션 인증/로그/보안, 공격적 입력과 DNS-rebinding/아웃바운드 전송 경계에 대한 독립 보안 검토.
- **P1:** 세 호스트 GPT/Grok/Claude의 실제 설치·동작 검증 및 Google Drive 폴더 트리 업로드·리드백 해시 검증.

## v3.5 → v3.6 (2026-10-30 KST)

**사용자 최신 결정:** ChatGPT에서 실제 다운로드 가능한 ZIP·스킬·`all.md`를 제공한다. 명시적인 새 요청이 없는 한 Google Drive에 **어떠한 쓰기 작업도 수행하지 않는다.** `dmsg/SKILL.md`, `MASTER_HANDOFF_PROMPT.md`, `docs/08_RELEASE_AND_DRIVE_WORKFLOW_KO.md` 등에서 과거 자동 업로드 지시가 남아 있던 문제를 해소했다.

### 독립 코드 감사의 발견과 수정

| 문제(발견) | 반례/영향 | 수정한 코드·계약 | 검증 |
|---|---|---|---|
| 높은 모델 확률에 의한 무조건적 안전 판단 | `송금하세요`를 `negated_or_warning` 또는 `none`으로 오분류한 모델 응답이 위험 안내를 낮춤 | `prototype/context_guard.py` 신설. 부정·인용·행동명 언급과 typed 라벨 모순 시 `ASK_HUMAN` | `test_unsubstantiated_warning_label_cannot_clear_transfer`, `test_model_none_cannot_disguise_explicit_action_terms` |
| 모델의 인용·경고 화행 오분류 | `송금하지 마세요`나 `송금하라고 했습니다`를 직접 위험 요청으로 오판 | 명시적 경고/인용 신호와 직접요청 라벨이 충돌하면 보류 | `test_explicit_warning_is_not_model_direct_request`, `test_quoted_instruction_is_not_direct` |
| 모델 출력의 중복 JSON 키 | 응답 내 `model`/`answers`가 중복될 때 마지막 값으로 조용히 덮임 | `model_bridge.py:ModelClient.infer`에 `object_pairs_hook` 중복키 거부 | `test_duplicate_json_denied` |
| 비JSON·과대 HTTP 모델 응답 | HTML을 JSON으로 오인하거나 큰 본문 메모리 과소통제 | `application/json` Content-Type 및 120KB 응답 제한 강화 | `test_wrong_response_content_type_denied`, `test_response_body_bounded` |
| 원격 모델에 대한 사용자 발화 무단 전송 위험 | 운영자 endpoint만 설정하면 실제 텍스트가 원격으로 전송될 수 있음 | `DMSG_REMOTE_TEXT_CONSENT=1` + `DMSG_REMOTE_HOST_ALLOWLIST` 별도 명시 필수. URL TLS/loopback 규칙 유지, 기본 환경 프록시 비사용 | `test_remote_text_has_explicit_opt_in`, `test_remote_host_requires_allowlist` |
| 늦은 추론·반환 구조 변조 회귀 취약성 | 오래된 응답이 최신 판단을 덮거나 외부 반환 JSON이 저장 이력을 변조 | `test_v36_async.py`: 지연모형과 새 턴 경쟁, 멱등 반환 깊은 복사 재검증 | 스레드 경쟁 테스트 2건 |
| UI 요청 실패의 정보 잔존 | 실패한 최신 턴에서 이전 X-Ray/인용이 현재 정보처럼 보일 수 있음 | `web/main.js`: 작업 중 버튼 직렬화, 오류 시 X-Ray·근거·상태 정리, 버전 표기 갱신 | `node --check` 통과, 실제 Chromium 탐색은 환경 정책 차단 |
| PRD/추적표의 정의 수 경직 | 신규 수용 기준을 추가하면 기존 테스트가 과거 요구사항 수만 인정 | PRD-21~PRD-26 및 GUARD-19~24를 정식 명세·추적표에 추가하고 문서 계약 테스트도 26/24로 재설정 | `test_spec_alignment.py` 갱신 후 전체 회귀 재실행 |
| 릴리스 검증 체계 | ZIP 압축·스킬·매니페스트·문서가 릴리스 시 함께 불일치 가능 | 일관된 빌더/검증기, 전체 SHA-256·ZIP CRC 검사. `CURRENT_PROJECT_STATE.md`, `docs/12_...`, `docs/13_...` 추가 | `tools/verify_release.py`, 스킬 validator, 최종 아카이브 검증 |

### 최신 실측/실행 증거와 한계

- Python 단위·통합 회귀 **157/157 통과** (실제 Zoro-1이 아닌 모델 stub과 작성자 합성 반례 기준). v3.5의 134건 기준선에서 신규 오류 방어·동시성 검사를 추가. 테스트 개수만으로 외부 일반화는 증명하지 않음.
- 작성자 합성 의심계 fixture 14건 기대동작 일치 및 `metamorphic_audit.py` 38개 불변조건 검사는 별도 실행 후 결과를 릴리스 기록과 함께 확인한다.
- `scripts/run_adversarial_suite.py`의 개발자 작성 **15개 고정 응답 정책 반례 15/15 통과**. 실제 Zoro 호출 횟수 **0**.
- Chromium/Playwright 시각 테스트를 두 차례 시도했으나 두 경우 모두 `ERR_BLOCKED_BY_ADMINISTRATOR`로 로컬 127.0.0.1 탐색이 차단됨. **브라우저 시각/접근성 검증은 BLOCKED**, `tools/browser_smoke.py`와 `internal/evidence/browser_smoke_status.json`에 사유 기록. HTTP 모형 통합 테스트 성공과 혼동하지 않음.
- 외부 원격 서버의 DNS 재결합·개인정보 적법성, 실제 체크포인트 출처, 정교한 한국어 의미 해석, 지표의 교정, 독립 데이터 정확도, 피해 예방 효과, 멀티프로세스 고가용성, 현장 장비 오프라인 실행은 **미검증**.
- 새로운 소스: `context_guard.py`, `tests/test_v36_context_and_transport.py`, `tests/test_v36_async.py`, `scripts/run_adversarial_suite.py`, `tools/browser_smoke.py`, 두 개의 현재 품질 설계 문서, 현재 프로젝트 상태 파일, 합성 테스트 보고서.


## v3.6 → v3.7 (2026-11-01 KST)

**제품 승인 경계:** 두 사람이 PAYLOCK/STOPLINE/LEAKLESS/기존 의심계 중 최종 합의를 아직 하지 않았으므로, 이 릴리스는 현행 의심계를 유지한다. 기존 정식 기획 선택서 v2.0의 PDF·TeX를 미서명 참고 자료로 보존하고 새로운 기획을 자동 채택하지 않는다. Google Drive 쓰기 0회.

### 소크라테스 엘렌코스에 따른 핵심 반증

전제: 더 많은 합성 테스트와 정책 규칙은 실제 안전도 상승을 증명한다. 반례: 명백한 행동 요청은 통과하지만 간접적 강요와 정상 인사말의 모델 압박 확률은 오분류할 수 있다. 대책: 단일 보조 확률에 의한 과도한 경고를 피하고 모델 라벨과 근거 문구가 모순일 때만 보류. 잠금셋의 실제 정상/위험 패밀리 평가가 필요하다.

### 구현 비교

| 영역 | 기존 v3.6의 위험 | 현행 v3.7 변경·결과 | 증거/남는 위험 |
|---|---|---|---|
| 압박 신호 | `q_action=none`, `q_pressure` 높음이지만 q_scam 낮으면 항상 `NO_STRONG_SIGNAL`로 진행할 수 있음 | q_pressure가 높고 원문에 직접 긴급 단서가 있을 때 `ASK_HUMAN`; 단서 없는 인사말은 기존 행동 유지 | 인위적 모델 응답 회귀. 한국어 완곡 표현 전체 커버 아님 |
| 사용자 발화 로그 | 짧은 원문의 일반 SHA-256을 감사 기록에 보관해 사전 대입 추정 가능 | `Store`별 난수 키 HMAC으로 변경, 세션 멱등 키도 HMAC 전환 | 내부 무결성·프라이버시 회귀. 메모리 보안/실데이터 처리 근거 미검증 |
| 원격 모델 DNS | DNS 검증 후 urllib가 연결 시 다시 조회할 수 있는 시간차 | 원격 HTTPS의 실제 TCP 대상은 검증된 IP로 고정, 본래 호스트명 TLS SNI/인증 확인, 프록시·리다이렉트 없음 | DNS 혼합/핀 고정/SNI 테스트. 원격 실제 TLS 테스트·인증 감사 미실행 |
| 실제 평가 도구 | 합성 fixture 일치만 숫자화; 잠금 분할 오염 정량화 경로 부족 | `evaluation_gate.py`, `evaluate_annotations.py`: 중복 ID·패밀리 누출 차단, 위험 누락/정상 중단/보류 분모·Wilson 추정 | 계산 합성 테스트만. 실모델/독립 라벨 데이터 없음 |
| NPU 실증 | 모델 카드의 온디바이스 표현을 현장 구동으로 오인 가능 | `npu_readiness.py`: 공급자 탐색 및 model file 여부; NPU inference는 명시적 NOT_RUN | 현 환경은 NPU 미확인. Zoro typed head NPU 지원·연산자·성능 전부 미검증 |
| 계약·안전 문서 | PRD 26, GUARD 24, 157 단위/통합 테스트 | PRD 31, GUARD 29, 184 단위/통합 테스트로 검증 범위 확장 | 문서 정합성 테스트·전 회귀, 외부 안전성 별개 |

### 검증 분모와 실행 방식

- Python: `cd dmsg && python -m unittest discover -s tests -q` → **184/184 PASS** (합성·모의 응답 및 로컬 테스트; 모델 checkpoint 평가 아님).
- `python dmsg/scripts/run_adversarial_suite.py` → 작성자 고정 모델 응답 **15/15** (독립 평가 아님).
- `python dmsg/scripts/metamorphic_audit.py` → **38/38** 합성 불변조건 (실제 사기 정확도 아님).
- `python dmsg/scripts/evaluate_fixtures.py` → **14/14** fixture 일치 (실모델 호출 0).
- 로컬 HTTP: `/api/model-status`, `/api/fixtures`, `/api/start`, `/api/turn`, `/api/model-turn` 모의 경로 5종 검사 및 실패 시 보류 확인. 세부는 `internal/evidence/v37_http_smoke.json`.
- `python dmsg/scripts/npu_readiness.py` → 현재 실행환경 provider 없음, 실제 NPU 추론 `NOT_RUN`.
- 코드 정적 검사: Python compileall, Node `--check`; skills validator; ZIP CRC/SHA 매니페스트. 정확한 실행 기록은 `internal/evidence/v37_verification.json`을 참조한다.
- 실제 Zoro-1 체크포인트, 2단 추가 추론, 한국어 블라인드 데이터, NPU typed inference, 실제 브라우저 QA, 사용자 피해 예방은 **NOT_VERIFIED**.

### 남은 최우선 위험/롤백

1. **P0:** 실제 공식 모델의 진품·Typed Decision 응답 계약을 한 번도 end-to-end 인증하지 못함. 서버/API가 바뀌면 즉시 모델 경로 비활성화하고 fixture 모드로 복귀.
2. **P0:** 다중 턴 의미·간접 강요·정상 사용자 오탐을 검증할 독립 라벨셋 없음. 사기 탐지율을 발표에서 주장하지 않는다.
3. **P0:** 실제 심사 장비와 오프라인 GPU/NPU 사용 여부 미확인. NPU 가능성 조사만으로 모델 실행 완료 처리 금지.
4. **P1:** 원격 TLS 핀 고정은 로컬 합성 모형으로만 시험됨. 인증된 실제 엔드포인트·운영보안·개인정보 적법성 미검증.
5. **P1:** 일시적 메모리 세션의 한계, 서명 없는 내부 감사 체인, 실제 브라우저 접근성·모바일 UI 미검증.
6. **P1:** 네 기획 중 사용자·팀원 공동 결정이 없으므로 방향 변경 금지.

**다음 정상 버전:** v3.8 (사용자의 이후 변경 지시가 없을 때). **재현:** `tools/build_release.py`, `tools/verify_release.py`; Google Drive 쓰기 금지.


## v3.7 → v3.8 (2026-11-01)

**변경 목적:** 사용자 최신 의사결정에 따라 현행 의심계(Scam Intervention Arena)를 유지하고 PAYLOCK의 현실적인 기업 지급 검토 상황만 별도 모듈로 통합한다. 새로운 은행·ERP·실시간 거래 플랫폼은 만들지 않는다. 실제 팀 전체의 서명·역할·IP 합의는 이 결정의 증거가 아니다.

| 컴포넌트 | v3.7 기준 | v3.8 변경·검증 | 남는 한계·롤백 |
|---|---|---|---|
| 의심계 기본 엔진 | 14개 합성 화행 사례, 6 typed 질문, 독립 정책 및 `start/turn/model-turn` API | 원본 기능·API와 `dmsg` 식별자 유지, 전체 회귀 235개 통과 | 진짜 Zoro-1 한국어 실측 정확도 미확인. 이상 시 의심계 fixture 모드 유지 |
| PAYLOCK 지급 비교 | 없음 | `prototype/paylock.py`: 가상 거래처 2개·청구서 3개, 6개 합성 지급 사례, 등록 계좌/은행/청구금액/발신 주소 주장 비교 | 신원·발신자·계좌 소유권 검증이 아님. 현재 원장을 공격자가 바꾸면 오판 가능 |
| 모델 보조 | 기존 의심계 원격 전송 기본 비활성 | `prototype/paylock_model.py`: 2개 `noul` typed 질문, 기존 allowlist/동의 기반 `ModelClient` 재사용. 모델은 보류 이유만 추가 가능 | 실모델 호출 0회. 명시적으로 옵트인한 원격 문자 송신은 운영자 설정 필요 |
| 업무 워크플로 | 위험 행동 권고 | 일관성 검증 → `HOLD_FOR_INDEPENDENT_VERIFICATION` 또는 `READY_FOR_INTERNAL_REVIEW_NOT_PAYMENT` → 모의 검토자 보고; 절대로 지급 실행하지 않음 | 검토자 ID는 자기 주장 문자열이며 SSO 기반 2인 인증이 아니다 |
| 데이터 최소화·감사 | 의심계 단일 세션 HMAC, 메모리 감사 | PAYLOCK 고유 HMAC, 계좌 끝 4자리만 노출, 이벤트 hash-chain, 낡은 버전/중복·충돌 요청 거절, 메모리 TTL | 영속성·외부서명·멀티프로세스 복구 없음. 가상 회계데이터에만 사용 |
| HTTP·UI | 원래 의심계 화면 | `/api/paylock/fixtures`, `/api/paylock/evaluate`, `/api/paylock/verify`, `/paylock.html` 신규. 한글 중심 PC·모바일 화면, 재시도·오류시 판단 보류 | Chromium의 직접 localhost 접속은 실행환경에서 관리자 차단. 간접 중계 DOM 테스트 통과, 현장 실기기 미확인 |
| 제품 사양·Skill | PRD 31, GUARD 29 | PRD-32..40(40개), GUARD-30..38(38개), 추적표·스킬·README·`all.md` 갱신 | 명세 ID 일치는 실사용 제품 품질의 증명이 아님 |
| 외부 아이디어 검토 | 손호성 박사님의 참고 스킬에 대한 별도 검토 | 「기억 문지기」 범위정의의 출처 신뢰경계·좁은 MVP·평가 원칙, 『AI 에이전트를 깊이 이해하기』의 Harness/Context/Verify/Correct 원칙을 참고 | 독립 작품 「기억 문지기」를 현행 출품작으로 병합하지 않음 |

**실행 검증과 분모**

- `python -m unittest discover -s tests -q`: **235/235 통과**. 실제 모델 호출을 대신하는 합성, 모의 HTTP, 정책 테스트를 포함한다.
- `python scripts/evaluate_fixtures.py`: 의심계 합성 14/14.
- `python scripts/run_adversarial_suite.py`: 작성자 합성 반례 15/15.
- `python scripts/metamorphic_audit.py`: 합성 불변조건 38/38.
- `python scripts/paylock_ablation.py`: 6개 합성 지급 사례를 구조 비교 단독/어휘 결합 방식과 비교; 구조 비교 단독은 PRESSURE 샘플을 놓치며 어휘 결합은 해당 사례를 HOLD. 각 구성요소의 운영 성능은 미측정. Zoro 실추론 **0**.
- Chromium in-page harness 테스트: 데스크톱 `ACCOUNT_CHANGE` HOLD → 검토자 확인 보고, 모바일 `MATCH`는 내부검토 대기, 수평 넘침·JS exception 없음. 실제 서버의 HTTP를 Playwright host에서 전달했다. Chromium의 자체 localhost navigation은 `ERR_BLOCKED_BY_ADMINISTRATOR`이므로 전용 실기기 브라우저 QA는 아직 미완료.
- Python `compileall`, Node `--check`, Skill 구조 검증, ZIP SHA-256/CRC 및 새 위치에 압축 해제한 회귀 테스트를 수행하고 `internal/evidence/v38_verification.json`과 최종 매니페스트에 기록한다.

**검증하지 못한 P0**: (1) Zoro-1 공식 체크포인트의 실제 Typed Decision, (2) 독립 한국어/BEC 정상·공격 평가, (3) 실거래처 주소록·전자메일·ERP·은행 API, (4) 실제 소유주 계좌 및 사용자·승인자 인증, (5) 실적 피해 예방. **NPU 실추론 미실행.** 장애 시 모델 옵트인 비활성, 합성 자료·독립 정책 기반 심사 데모로 롤백한다. 실제 돈/개인정보를 입력하거나 정상 송금 승인으로 해석하지 않는다.

**자료 무결성 및 보존:** 일반 문서는 현행 상태만 설명하며 상세 변동 이력은 본 장부가 유일하게 보유한다. 사용자가 제공한 사진은 프로젝트 내부 동의 없이 배포하지 않는다. 텍스트 기술 참고용 PDF와 스킬은 `internal/source_material/reviewed_team_inputs`에서 출처별로 보관한다. Google Drive 쓰기는 수행하지 않는다.

## v3.8 → v3.9 (2026-11-01)

**배경/근거:** 사용자는 기존 의심계+PAYLOCK을 유지하면서 Bojie Li의 하네스 방법론, 손호성 박사님의 agent-engineering 스킬과 기억 문지기 범위정의의 검증 가능한 장점을 기존 프로젝트 및 휴대용 `dmsg`에 통합하라고 요청했다. `PROJECT_INSTRUCTIONS_KO.md`의 R01–R09와 기능 보존 규칙을 신규 적용한다. 원본 자료는 제3자 참고문헌이며 소유권 이전 근거가 아니다.

**재현된 결함:** 동일 PAYLOCK 요청이 이미 `READY_FOR_INTERNAL_REVIEW_NOT_PAYMENT`인 경우, 같은 request_id/payload를 가진 늦은 모델 위험 신호 `MODEL_URGENCY_CUE`가 재도착해도 과거 캐시 결과만 반환했다. 재현 출력 `FIRST READY v1`, `SECOND READY v1`을 업그레이드 전에 확인했다. 영향: 더 위험한 보조 증거의 비파괴적 상향 반영 실패.

**변경 범위/이유:**
- `dmsg/prototype/paylock.py`: 멱등 기본 계약 유지. 신규 위험 신호가 있는 중복 요청만 HOLD, 버전 증가, 단일 감사 이벤트 추가. 검토 완료 건은 추가 신호 발생 시 새 검토 요구 에러. 신규 지시 주입 단서가 있는 구조 일치 지급 요청은 보류.
- `dmsg/prototype/context_guard.py`: 외부 역할/정책 우회 단서 어휘 검출(보류 전용) 및 메모리 쓰기 직전 preview-only 출처 게이트. 사용자 출처의 신뢰는 실행부 밖에서 증빙해야 하며 모든 경로에서 실제 memory_written=false. 모델 제안의 권한 확대 금지.
- 기존 `test_v38_paylock.py` 파일 내부에 신규 방어 테스트를 추가하여 경로 집합·기존 235개 테스트 보존. `SKILL.md`에 하네스·SNM·4D·메모리 출처 경계와 제3자 출처를 서술하고 창작자 메타데이터 마지막 주석으로 유지.
- PRD-41~44, GUARD-39~42, 추적표/README/current-state/all.md 및 정본 skill/zip과 검증 장부를 동기화한다. 기존 정책 또는 모델 응답 계약을 무단 완화하지 않는다.

**기능 차이와 rollback:** 기존 의심계/Paylock API·모의 확인·ID/alias·플랫폼별 설치 안내·기존 테스트 파일 경로 보존. 새로운 마스터 변경 API·실계좌 송금·메모리 쓰기는 없음. 새 보수적 보류가 정상 문서의 인용/정규 표현을 일부 오탐할 수 있으므로 별도 독립 표본에서 FPR 측정 후 문제가 있으면 v3.8 known-good ZIP으로 복귀하거나 lexicon 레이어를 비활성화한다. 기존 명시적 구조 불일치 HOLD는 완화 불가.

**검증 요구:** 기준선 unittest 235/235 통과, 증분 unittest 전체 다시 실행, 합성 fixture/적대·변형 검증, 스킬 파일 목록 200개 이하 및 이전 경로 집합 동일, 정본과 ZIP 동일 바이트, 파일별 sha256 manifest, 재압축 해제 후 regression, R01–R09 policy gate. GPT/Grok/Claude 실런타임, 실제 Zoro-1, 고객 계정, 원격 ERP, NPU/독립 정확도는 미실행 또는 미검증으로 표시한다. 실측 성공 범위는 별도 증거 파일에서 확인.

**실측 검증 결과(정적·합성 증거):** v3.8 기준 235/235, 후보 v3.9 전체 249/249 (기존 테스트 경로 유지, 신규 14개 포함). 작성자 합성 fixture 14/14, 공격 정책 반례 15/15, 불변조건 38/38, PAYLOCK 제거 실험 6개 사례(실제 Zoro 호출 0). 기존 스킬 파일 경로 53개 모두 보존; 신규 파일 경로/삭제 0. `internal/evidence/v39_verification.json`, `v39_R01_R09_gate.json` 및 테스트 로그 참조. R02/R08 부분검증, R09는 GPT·Grok·Claude 실제 설치/호출 NOT_RUN으로 RELEASED 승격 보류. 배포품은 STATIC_VALIDATED_CANDIDATE이다.

## v3.9 → v4.0 (2026-11-01 KST) — 검증 후보본

**우선 목표:** 이전 정본 기능을 보존하면서 PAYLOCK 감사 체인의 조작 탐지와 실 UI 검증 방법을 강화하고, 실제 모델/독립 고객 성과가 없는 상태를 정직하게 유지한다.

**반례 재현:** v3.9 `PaylockStore.verify_audit()`는 이벤트 해시 이력만 검증하므로, `case.version=999`로 현재 사건 상태만 바꾼 뒤에도 참을 반환했다. 로컬 상태변조 반례 출력 `internal/evidence/v40_reproduced_issue.json` 참조. 공격자가 같은 프로세스의 메모리를 수정할 수 있다는 가정에서의 취약점이며 인터넷 원격 공격 성공을 재현한 것은 아니다.

**실제 수정 사항:**
- `prototype/paylock.py`: 공개 SHA-256 이벤트 체인을 store별 임시 난수 비밀키 HMAC 체인으로 변경. 비밀키가 없는 주체의 공개 해시 재계산 위조는 더 이상 통과하지 않는다. 현재 사건의 `case_id`, `request_id`, `requester_id` HMAC, 마스킹 계좌 및 계좌 HMAC, `version`, `disposition`, `reason_codes`, 거래처/청구서 참조를 최초/최종 이벤트에 앵커링. 현재 상태가 이벤트 로그와 다르면 보류/거부한다. **영속성·외부 공증·인증된 운영자·DB 커밋은 여전히 구현하지 않는다.**
- 기존 `tests/test_v38_paylock.py` 경로에 세 가지 공격/정상 전이 회귀 테스트 추가. 기존 함수/테스트 경로·스킬 파일 53개 유지, PRD-45..47과 GUARD-43..45 및 양방향 추적표 확장. 기존 `test_spec_alignment.py`의 테스트 함수 이름은 유지하되 요구사항 수 증가에 맞게 기대 ID 범위를 강화한다.
- `tools/verify_release.py`: 전체 ZIP의 중복 엔트리·경로 탈출·심볼릭 링크·비정상 확장/크기 제한 점검 추가. `tools/browser_smoke.py`: Chromium 직접 localhost 접속이 관리자 정책으로 막히는 환경에서 실제 프런트엔드 JS와 실제 로컬 HTTP 서버를 Python 중계로 연결해 UI·상태·모바일 표시를 테스트한다. 해당 시험은 브라우저 자체의 네트워크 접근이나 사용자 하드웨어 QA를 대체하지 않는다.
- `SKILL.md`, 현재 PRD/System Prompt/추적표, `all.md`, README, 상태 파일, 빌더 및 버전 표시를 현행 코드에 맞게 동기화한다. `dmsg_v4.0.skill`과 동일 바이트 `.zip`으로 배포한다. 기존 `v3.9`와 `v3.8` 아카이브는 롤백용으로 별도 보존한다.

**실행·테스트 분모:** `internal/evidence/v40_verification.json`, `v40_browser_smoke.json`, `v40_reproduced_issue.json`과 배포 ZIP 검증 결과를 우선 참조한다. 동일 수정 코드는 원본을 백업한 후 새 디렉터리에서 테스트한다.

**기능/보안 회귀:** 종전 허용된 합성 사례·PAYLOCK 상태·도움말·권한(실제 지급 없음) 유지. 발생 가능한 차이는 내부 감사 `audit_integrity` 표시가 새로운 HMAC 경계를 명시한다는 점이며 외부 API에서 이 문자열을 고정 계약으로 사용하는 소비자는 호환 영향을 받을 수 있다. 기능의 의미상 안전 수준은 강화되나 **미검증 운영 환경의 호환을 보장하지 않는다.** 문제가 생기면 v3.9 후보본으로 원상 복귀하고, 실제 송금 API는 애초에 존재하지 않는다.

**배포 판정:** R01–R09 중 정적/합성 검증과 경로·명칭·구조는 실제 로그로 확인. GPT/Grok/Claude 실런타임·Zoro-1 공식 checkpoint·한국어 독립 모델 평가·ERP/SSO/은행·NPU 실기기 검증 미완료. `STATIC_VALIDATED_CANDIDATE`, **`3_ENGINE_RUNTIME_VERIFIED` 또는 운영 `RELEASED` 아님**. Google Drive 쓰기 작업 없음.


## v4.0 → v4.1 (2026-11-01 KST) — 전달·멱등/시간 무결성 후보본

**관찰된 반례:** v4.0은 같은 `event_id`로 검토를 완료한 뒤 해당 재요청의 `version`만 `999`로 바꿔도 저장된 결과를 반환했다. 입력된 예상 상태 버전을 재시도 동일성에 포함하지 않았기 때문이다. 동일한 요청 재시도 자체는 보존하면서, 다른 버전의 replay는 `CONFLICTING_RETRY`로 거부하도록 변경했다.

**추가 보호:** 사건 만료에 사용되는 `created` 단조 시간 값을 최초 감사 이벤트 HMAC에 묶어 해당 속성만 변경하는 조작을 감지한다. 중복 Host·Origin·Sec-Fetch-Site 헤더는 모호한 출처 신호로 취급하여 403 거부한다.

**다운로드 장애 개선:** 기존 `[v4.0] IteraGuard_DoubtMeter.zip`은 로컬 파일로 존재하며 CRC/해시 정상이지만, 이전 UI 다운로드 링크 실패 원인은 이 세션에서 확정할 수 없다. 신규 릴리스는 안전한 ASCII 파일명, 풀/경량 2종, CRC·경로·재추출·SHA-256 점검 스크립트, 사용자 다운로드 문제 시 대체 링크를 제공한다. 호스트의 실제 파일 다운로드 완료는 자동으로 주장하지 않는다.

**변경 보존:** 기준 v4.0 `dmsg` 경로 53개 유지, Golden 테스트 ID 유지, 코드·테스트·PRD-48..51·GUARD-46..49·추적표를 동기화. 기존 v4.0 릴리스는 외부 롤백 자산으로 보존. 사용자 동의 없이 Drive 쓰기 없음.

**남는 한계:** 실제 Trida Zoro-1 체크포인트 인증/호출 및 한국어+BEC 독립 측정/신원·은행 연동/NPU/세 플랫폼 설치/실사용 다운로드 완료는 NOT_VERIFIED. 배포 상태는 STATIC_VALIDATED_CANDIDATE 유지.


## v4.1 → v4.2 (2026-11-01 KST) — 실모델 계약 정합·절 단위 모순 검사 후보본

**관찰된 반례 (실측, `internal/evidence/v42_v41_counterexamples.json`):** 공개 kev 응답 형태(반향 없음)를 흉내 낸 로컬 스텁에 대해 v4.1 모델 경로는 직접 송금 요구에도 `ASK_HUMAN / ModelUnavailable`을 반환했다(원인 `MODEL_ID_MISMATCH`가 사유에서 사라짐). 점수형 질문은 요청 라벨과 응답 기대 키가 달라 라벨 키 응답 전체를 거부했다. 비밀 유지 요구 "말하지 마세요"가 경고 단서로 판정되어 경고 라벨 모델이 송금 명령을 `NO_STRONG_SIGNAL`로 해제했다. 다른 문장의 "경고"·"신고" 단어가 정확한 직접 요청을 보류로 강등했다. 메인 세션의 턴·ack 재시도는 버전만 바꿔도 과거 결과를 반환했고, 세션 감사 체인은 키 없는 SHA-256이라 재계산 위조가 통과했다.

**실제 수정:**
- `typed_contract.py`: 점수형 라벨/인덱스 키 어댑터, `score` 누락 시 최댓값 도출, 응답 `type` 일치 검사, `optional` 보조 질문 격리(`_dropped_optional`).
- `model_bridge.py`: `RISK_LEVELS=['none','low','moderate','high']`를 요청·검증 공통 정의로 사용, `OPTIONAL_QUESTIONS={'q_claim','q_risk'}`, 요청 `model` 필드 옵트인(`DMSG_SEND_MODEL_FIELD`), 반향 선택화(`DMSG_REQUIRE_MODEL_ECHO`), `last_model_echo`, `DMSG_MODEL_TIMEOUT_S`, 절 단위 모순 검사와 깨끗한 절 안의 근거 위치 선택, 경고 분기의 보조 질문 압박 교차검사, 보정 온도 불일치 표시.
- `context_guard.py`: `SECRECY_IMPERATIVES`, `CREDENTIAL_TOPIC`, `clause_profile`, `Clause`, `_warning_cue`, `context_conflict(..., profile)`. 기존 호출 형식 유지.
- `session.py`: 3개 진입점의 재시도 동일성에 예상 버전 포함, 감사 체인 프로세스 임시 키 HMAC, `_failure_reason`, `model_id_echo`, `audit_chain_keying` 필드 추가. `audit_integrity` 문자열 값은 호환을 위해 유지.
- `scripts/smoke_zoro.py`: 제품 6문항·4 프로브·응답 형태 기록으로 재작성. `scripts/npu_readiness.py`: 가중치 메모리·처리량 요구치 산술.
- 테스트: `test_v36_context_and_transport.py`에 `V42KevContract`·`V42KevTransport`·`V42ClauseScopedGuard`·`V42SessionBinding`, `test_v37_evaluation_npu.py`에 `V42NpuFeasibility` 추가. `test_spec_alignment.py`의 기존 함수 이름 유지, 기대 ID 범위를 PRD-56·GUARD-54로 확장.
- PRD-52..56, GUARD-50..54, 추적표 행, MODEL_CONTRACT·운영자 안내·NPU 문서·README·인수인계·상태 파일·all.md 동기화. `tools/*` 버전 표기와 브라우저 실행 경로 이식성 수정, `tools/run_v42_validation.py` 추가.

**기능 차이:** 같은 입력에서 판정이 바뀌는 경우는 (a) 다른 절에만 경고·인용 단어가 있는 직접 요청: ASK_HUMAN → PAUSE_AND_VERIFY, (b) 깨끗한 명령 절이 있는데 모델이 경고·인용 라벨을 준 경우: NO_STRONG_SIGNAL/CAUTION → ASK_HUMAN, (c) 경고 라벨 + 어휘 압박 + 높은 보조 질문: NO_STRONG_SIGNAL → ASK_HUMAN. v4.1의 256개 골든 테스트 기대값은 하나도 바꾸지 않았다. 응답에 `model`이 없을 때 v4.1은 거부, v4.2는 수용(엄격 모드로 복원 가능).

**검증:** 284/284, 신규 테스트를 v4.1에 실행 시 실패 13·오류 116, 반례 9/9 해소, 통제 문장 8/8 유지, 스킬 경로 53개 동일. 실제 Zoro-1·NPU·독립 평가·세 플랫폼 설치 NOT_RUN. 상태 `STATIC_VALIDATED_CANDIDATE`.

**롤백:** `dmsg_v4.1.skill`로 복귀. 모델 경로만 v4.1 동작이 필요하면 `DMSG_SEND_MODEL_FIELD=1`, `DMSG_REQUIRE_MODEL_ECHO=1`. 절 단위 검사로 정상 문장 오탐이 늘면 독립 표본 FPR을 근거로 판단한다.


## v4.2 → v4.3 (2026-11-01 KST) — 다섯 플랫폼 앱·단일 엔진 후보본

**추가:** 릴리스 루트 `apps/`에 Python 정본을 이식한 JS 판단 엔진, 반투명 유리 재질 UI의 오프라인 웹앱(PWA), Bun 교차 컴파일 데스크톱 실행 파일 4종(Windows x64, macOS arm64/x64, Linux x64), Capacitor 7 Android·iOS 프로젝트. 데이터는 `tools/export_engine_data.py`로 정본에서 생성하고 `tools/make_conformance_vectors.py` + `apps/conformance/run_conformance.js`로 일치를 검증한다(15,490/15,490). 빌드 `tools/build_apps.py`, 실행 시험 `tools/app_smoke.py`, 대비 `tools/check_contrast.py`, macOS 서명 `tools/verify_macho_signature.py`, 검증 `tools/run_v43_validation.py`.

**정본 수정(이식 중 발견):** `CLAUSE_SPLIT` 인라인 플래그 제거(전역 IGNORECASE), 점수형 인덱스 문자열은 ASCII 숫자만, 모델 응답 JSON의 `NaN`/`Infinity` 거부. 판정 동작 변화 없음(v4.2 테스트 284개 기대값 불변). `V43Portability` 4개 테스트 추가, PRD-57..61, GUARD-55..59.

**빌드·시험 중 발견 수정:** macOS x64 깨진 내장 서명(rcodesign ad-hoc 재서명 + 게이트), 모바일 가로 넘침, 넘침·모델 UI 시험의 거짓 통과, 라이트·다크 대비 미달, 데스크톱 실패 코드 이름, 서비스 워커 범위, 릴리스 빌더의 중간 산출물 포함.

**검증:** 288/288, 적합성 15,490/15,490, HTTP 12/12, UI 5개 구성, 대비·서명 게이트 PASS. Windows·macOS 실행, Android·iOS 컴파일, 실제 Zoro-1, NPU NOT_RUN. 상태 `STATIC_VALIDATED_CANDIDATE`.

**롤백:** `dmsg_v4.2.skill`. 앱만 문제가 되면 `apps/`를 쓰지 않고 v4.2의 Python 로컬 서버(`python -m prototype.server`)로 시연한다.


## v4.3 → v4.4 (2026-11-02 KST) — Android 디버그 APK

**추가:** `tools/build_apk.py`(SDK 바이너리 없이 DEX 035·바이너리 매니페스트·resources.arsc·APK 서명 v2 생성), `tools/verify_apk.py`(apksigtool·androguard 독립 검증, DEX 정렬 규칙·체크섬, 참조 메서드 허용 목록, 자산 바이트 일치, 정렬), `apps/mobile/debug-key/`(디버그 전용 공개 키). 산출물 `apps/dist/IteraGuard_DoubtMeter_v4_4_android_debug.apk` 806 KB, 권한 0, minSdk 24 / targetSdk 34. PRD-62, GUARD-60.

**경위:** npm에 있는 aapt2·d8·apksigner 재배포본을 실행하려던 시도는 출처 미확인 코드 실행으로 자동 차단되었다. 사용자 기기에 설치될 파일의 빌드 경로에 검증되지 않은 바이너리를 두지 않는다는 원칙에 맞춰, 형식 규격으로 직접 생성하고 다른 파서로 검증하는 방식으로 바꿨다.

**수정:** 오래된 Android System WebView(Chromium 111 미만)용 `color-mix()` 대체 색, `100dvh` 대체값, APK 안에서 상단 표시를 "Android 앱"으로. 판단 로직 변화 없음.

**검증:** APK 서명 v2 검증, 매니페스트·아이콘·DEX 해석, 정렬 규칙·체크섬 통과, 재빌드 바이트 동일, APK 자산을 Android 크기·UA의 Chromium에서 라이트·다크 실행 통과. 실기기 설치·실행 NOT_RUN.

**롤백:** `dmsg_v4.3.skill` 및 v4.3 앱 묶음.


## v4.4 → v4.5 (2026-11-02 KST) — 0원 온디바이스 한국어 의미 분석, 팀 v3.3 반영, 엔진 비교 하네스

**추가(T0 온디바이스 NLP):** KoELECTRA-small-v3 판별기 인코더 int8(14.6 MB)을 순수 JS로 실행하는 `apps/shared/dmsg-nlp.js`, 가중치·어휘·헤드 JS 자산 `apps/shared/nlp/`. 화행 헤드(인코더 특징 + 문자 n-gram)·행동 헤드(문자 n-gram)·가림 기반 근거 구간. 학습·평가 도구 `tools/nlp/`(make_dataset, electra_ref, train_heads, build_nlp_assets, make_nlp_reference, nlp_parity.js, run_nlp_batch.js), 데이터 `tools/nlp/data/`(작성 합성 + 3i4k CC BY-SA 4.0), 잠금셋 v1(개발셋으로 강등)·v2(해시 동결, 1회 채점). 화면 기본이 "문자 붙여넣기 → 분석하기", 모델이 실제로 돈 경우에만 "AI 분석 · 온디바이스 NLP 실행됨", 아니면 "로컬 기본 점검 · 의미 분석 불가".

**정본 변경(하위 호환):** `q_speech`에 `informational`; `advisory(model_anchor=)`(어휘 근거가 없을 때만, 코드포인트 정확 일치 필수, `MODEL_ATTRIBUTION_SPAN`); 선택 문항 `q_evidence`(팀 v3.3 evidence_sufficient, 보류 방향으로만 작동). 모델 질문 수 6→7. 기존 테스트 3개는 계약 변경에 맞춰 수정(문항 수 7, 엄격 정규화 테스트는 6문항 사양 `_SPEC6`로 고정해 거짓 통과 방지, 누락 선택 문항 목록). 적합성 벡터에 근거 구간 3,282개·q_evidence 혼합 추가(22,276/22,276).

**팀 v3.3(손호성) 반영:** 화면 상태 제목 4종, 금지 표현 자동 검사(`tools/check_forbidden_phrases.py`), 골든 테스트 자동화(`tools/run_golden_v33.py`, 11/11), 매핑·결정 필요 목록 `docs/21`. 원문 `docs/team_v3_3/`. L2 본문·G7 기대값·identity 세분화는 [결정 필요]로 미반영.

**엔진 비교:** `tools/compare_engines.py`(rule·nlp·zoro·gpt, 사전등록 프로토콜 해시, Wilson 구간, 정확 McNemar). GPT는 `--allow-paid` + 팀원 키에서만. 결과 v2: rule 0.688, NLP 0.833, p=0.092. Zoro·GPT NOT_RUN.

**Android 시작 화면:** 매니페스트 `android:theme` → 자체 style `AppTheme`(부모 Theme.Black.NoTitleBar 0x01030009, windowBackground #FF0B1020; ID는 AOSP public.xml 사본으로 확인), DEX에 `WebView.setBackgroundColor(0xFF0B1020)`; 웹 시작 화면(≤0.5 s 노출, 준비 즉시 퇴장, 동작 줄이기 시 즉시). Capacitor 설정에 배경색. APK 약 16 MB, versionCode 45.

**수정:** `apps/README.md`의 "Play 프로텍트 경고 무시하고 설치" 안내 삭제(명세 §7 위반) → adb 시험 기기 설치 또는 팀 키로 직접 빌드. 정보 탭 표 모바일 가로 넘침.

**검증:** 단위 308/308, 적합성 22,276/22,276, NLP 교차 일치 171/171, 앱 스모크 6구성(HTTP 4 + file 2, 동작 줄이기 포함) PASS, APK 구조·서명·테마 해석 PASS, 금지 표현 PASS. 실기기·실제 Zoro-1·GPT·독립 주석 평가·NPU NOT_RUN. 검증 수준: `STATIC_VALIDATED` · `REAL_MODEL_CALL_PASS`(온디바이스 NLP 한정, Linux Node·Chromium) · `LOCKED_EVAL`: 실행됨(개발자 작성 48문장, 사전 합격 기준 없음 → PASS 아님) · `ANDROID_RUNTIME_PASS`: NOT_RUN · `ZORO_CHECKPOINT_ATTESTED`: BLOCKED · `3_ENGINE_RUNTIME_VERIFIED`: NOT_RUN(2/3 엔진).

**롤백:** `dmsg_v4.4.skill`과 v4.4 앱 묶음. 앱만 되돌리려면 "온디바이스 AI 의미 분석" 스위치를 끄면 v4.4와 같은 직접 입력 동작(ASK_HUMAN + 단어 단서)이 된다.

**배포 한도 변경:** 릴리스 압축 해제 합계 상한 450 MB → 800 MB(`verify_release.py`, `delivery_gate.py`). 사유: 온디바이스 모델(약 20 MB)이 웹·PWA·Android/iOS 프로젝트·APK·데스크톱 4종 실행 파일 안에 각각 들어가 FULL 압축 해제 합계가 504 MB가 됨. 개별 파일 상한(80 MB)·항목 수·경로 안전 검사는 그대로. CORE는 데스크톱 실행 파일을 빼므로 훨씬 작다.


## v4.5 → v4.6 (2026-11-02 KST) — 다중 과제 의미 분석, 실제 미세조정, 위험 신호 정책

**기준선:** v4.5 FULL `2f66ea4f…`, APK `6317879e…`, 스킬 `d47caf36…`, 가중치 `52da5443…`(`internal/evidence/v46/BASELINE_V45.json`).

**모델:** KoELECTRA-small-v3 상위 8층을 JAX로 실제 미세조정(2 epoch, 보정 분할로 선택), int8 재양자화. 과제: 화행 5 · 의도 7 · 요구 행동 8 · 위험 신호 9(다중 라벨, 라벨별 임계값) · 행동 주제(v4.5 n-gram 헤드 유지) · 불확실성. 후보 6종 비교(`tools/nlp/eval/v46_model_selection.json`), 잠금셋 미사용 선정. KoELECTRA-Base 후보 BLOCKED. 새 도구: `make_dataset_v46.py`(잠금셋과 3-gram Jaccard ≥ 0.5 생성문 255개 제거), `finetune_v46.py`, `compose_heads_v46.py`, `nlp_v46.py`(Python 기준 파이프라인), `eval_v46.py`, `regress_cases_v46.js`. 모델 파일 `models/v46/`.

**정본(하위 호환 추가):** `context_guard.structural_evidence()`(메신저 ID·URL·전화·금액·해외발신·계좌 변경 문구, 코드포인트 위치), `model_bridge.indicator_advisory()`(절대 하향 없음, 구조적 근거가 있을 때만 CAUTION/PAUSE, 고위험 신호의 PAUSE는 직접 요청일 때만, 모델 단독 신호는 0.8 이상에서 ASK_HUMAN, 경고 화행은 상향 없음, 신원 항상 UNVERIFIED). JS 이식 + 교차 구현 벡터(구조 176, 신호 정책 1,568) → 24,020/24,020.

**평가(한 번):** W(신규 잠금 49) 기대 행동 0.510 → 0.878(McNemar 19:1, p < 0.001), 위험 개입 0.12 → 0.60, 정상 오탐 0.042 → 0.125. V2(48) 0.833 → 0.792(4:2, p = 0.69), 위험 개입 0.667 → 0.741, 정상 오탐 0.19 → 0.238. 인코더 동결 c0가 V2에서 0.854로 더 높음. 둘 다 개발자 작성. CASE A/B는 원본 스크린샷 미제공으로 재구성 문장(W01 → PAUSE 과잉, W02 → CAUTION).

**앱:** 위험 신호·문장 유형·원문 단서·발신자 신원 미확인 섹션, 확인되지 않은 상태에 녹색 체크 제거(중립 아이콘·회청색), 판정 코드 접기, 모델 점수 ≠ 사기 확률 문구, 모델 로드 실패 사유 + 다시 불러오기, 뒤로 가기 = 이전 탭(history), 스크롤 여백(고정 헤더·탭바), 모델 없는 경우에도 원문 단서 표시. APK versionCode 46.

**검증:** 단위 320/320(v4.5 테스트 이름 308개 보존, 스킬 경로 53개 동일), 교차 구현 24,020/24,020, NLP JS↔Python 221/221(확률 최대 오차 9.4e-6), 출하 JS로 W 재실행 49/49 일치, 앱 스모크 6구성 PASS(회전 프록시·300 px·뒤로 가기 포함), APK 구조·서명·테마 PASS, 금지 표현 PASS, 골든 v3.3 11/11. Android 실기기·Zoro-1·GPT·NPU·독립 평가 NOT_RUN/BLOCKED.

**롤백:** v4.5 FULL/CORE/APK/`dmsg_v4.5.skill`(해시는 기준선 파일). 앱만: "온디바이스 AI 의미 분석"을 끄면 모델 없이 로컬 기본 점검.

**릴리스 용량(v4.6):** FULL을 채팅 업로드 한도(400 MiB) 안에 두기 위해 (1) v4.1–v4.5 화면 캡처(약 42 MB)는 v4.6 트리에서 빼고 각 버전 릴리스에 남김, (2) v4.6 캡처는 JPEG(q80), (3) `apps/dist/web`은 PWA ZIP과 같은 바이트라 릴리스에서 제외(빌드 시 재생성), (4) int8 가중치 원본은 `models/v46`에 중복 저장하지 않고 `tools/nlp/extract_model_weights.py`로 앱 자산에서 복원. 검증 도구의 필수 파일 목록을 PWA ZIP 기준으로 변경.


## v4.6 → v4.7 (2026-11-02 KST) — 판단 중재 계층(dra), Zoro 보류 감사, LinkGuard

**기준선:** v4.6 FULL `03961e80…eb4`. 502개 항목, 매니페스트 501/501, 회귀 320/320, 교차 구현 24,020/24,020(`internal/evidence/v47/BASELINE_V46.json`).

**계기:** 팀 결과보고서 1·2(2026-11-02). 의심계 v4.5 코드로 실제 Zoro-1을 실행한 결과다. 보류가 48개 중 43개, 25개 중 19개였고, 정상 문장 12개가 모두 보류됐다. 진명님 지적: "모델이 틀린 건지, 코드가 보류시킨 건지 나눠야 한다", "중간에 뭔가가 있어야 한다."

**정본(하위 호환 추가, `advisory()` 불변):**
- `model_bridge.decision_relevant_advisory()`(dra/1.2): 안내 단위 확률 합산, 어휘·구조 근거로 가중, 사람 확인을 포함한 기대비용 최소화. 모델 자기 기여 구간만으로는 잠시 멈춤 불가.
- `abstention_cause()`: 보류를 GATE_*와 MODEL_*로 분류.
- `retemper()`: 정확한 온도 재보정.
- JS 이식 + 교차 구현 벡터 468개 → 24,488/24,488.
- 앱·데스크톱 Zoro 경로 기본값을 dra로 바꿨다. v4.6 방식은 설정에서 고를 수 있다.
- v4.6 골든 스냅샷·NLP 동등성 스크립트는 v4.6 판정 방식에 고정했다.

**감사 도구:** `tools/zoro/abstention_audit.py`. 저장된 Zoro 응답을 재생하고 GPU를 쓰지 않는다. 팀 PC에서 실행해야 하며 이 세션에서는 원본 응답이 없어 NOT_RUN이다.

**평가(온디바이스 NLP, 4개 세트 154문장, 모두 이미 본 자료):**
- dra/1.0 → 1.1 → 1.2를 차례로 실행했다. 1.1·1.2는 결과를 본 뒤의 원칙 단위 사후 수정이다.
- v4.6 대비 dra/1.2: 기대 일치 113→121(McNemar 5:13, p=0.096), 보류 38→25, 정상 보류 22→7, 정상 잠시 멈춤 9→2, 정상의 기대 밖 개입 12→15(악화), 위험 문장 해제 5→5, 잠시 멈춤 적중 25→25.
- `evaluation/v47_challenge/`(AI 작성 32문장)을 먼저 고정했다. 독립 평가가 아니다.

**LinkGuard(새 최상위 `linkguard/`, 스킬 53경로 유지):**
- URL 추출·정규화(IDN/Punycode, 동형문자, 사설·변형 IP, 비 HTTP 스킴, 메신저·APK·단축 주소, 토큰 가림)
- 평판 어댑터 계약(NOT_RUN), 여섯 가지 상태 정책, 의심계와의 상향 전용 결합
- APK 정적 분석(ZIP 안전성, AXML, 서명 v2/v3 인증서, DEX 문자열, 권한 조합)
- JS 이식(`dmsg-linkguard.js`, `dmsg-apkscan.js`). 적합성 7,639/7,639, APK Python↔JS 57/57, androguard 대조 5/5.
- 격리 웹 페치(P4)는 이 릴리스에 포함되지 않음 → BLOCKED.

**앱·APK:**
- 링크·앱 탭: URL 검사, APK 검사, 동의 설정(기본 꺼짐)
- 결과의 링크 검사 섹션과 단계 타임라인(미실행·차단 표시)
- 판단 방식 전환
- Android 공유 시트(`ACTION_SEND text/plain`) → `#share=` 로컬 전달. 권한은 0개이고 SMS 권한은 추가하지 않았다. versionCode 47.

**발견·수정:**
- APK 파서가 변조 압축 데이터에서 `zlib.error`로 중단되는 결함 → `INFLATE_FAILED`
- Python `re.IGNORECASE`의 유니코드 접기('ı' 등)로 JS와 URL 경계가 어긋나던 결함 → ASCII 명시

**미실행·차단:** Android 실기기, Zoro 재실행, 외부 평판 조회, 격리 웹 분석, NPU, 독립 평가, 실제 악성 APK 집단 탐지율.

**롤백:** v4.6 FULL/APK/`dmsg_v4.6.skill`. 앱만 되돌리려면 모델 탭에서 "기준값·거부권 (v4.6)"을 고른다.
