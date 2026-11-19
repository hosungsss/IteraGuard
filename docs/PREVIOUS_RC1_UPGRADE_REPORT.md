# 의심계 v4.9-rc1 / 키트 v1.2 업그레이드 보고서

2026-11-04. 사용자 요청: 최신 패키지와 우승 기획을 반영해 PRD·System Prompting을 개정하고, 로컬 Zoro를 실행해 문제를 찾고 수정한 뒤 기존 Drive 패키지 폴더에 새 버전 저장.

## 1. 결론과 버전 판단

**공개 Zoro를 실제 RTX 3060에 로드했고, 생성 종료 설정 문제를 발견·수정했으며, 웹 화면에서도 실제 생성 비교를 실행했다.** PRD/System Prompting과 로컬 확인 아레나를 v4.9-rc1로 개정하고, 실험 키트를 v1.2로 업그레이드했다.

다만 사용자께서 제공한 `trillionlabs/Zoro`와 기존 설계의 `trillionlabs/Zoro-1`은 별도 모델이다. Zoro-1 판단 헤드는 확보되지 않았고, 7문항 Typed Decision endpoint는 유효 응답 0/4였다. 따라서 제품 정식 완료판으로 승격하지 않고 **rc1**로 남긴다. 실제 생성의 실행 성공을 Typed Decision 성공·사기 정확도·우승 가능성으로 바꾸어 설명하지 않는다.

| 요청 | 실제 수행 | 상태 |
|---|---|---|
| 1. 조로 로컬 실행 | 공개 Zoro 9,680,472,424바이트 가중치 설치·해시 검증·GPU 추론·HTTP·UI 호출 | PASS: 공개 생성 모델 실행 |
| Zoro-1/kev Typed Decision | 실제 loopback 8008 요청 4건, 응답 0건. 공식 파일 미인증 접근 401 | FAIL 연결 / 가중치·헤드 추론 NOT_RUN |
| 2. 문제 발견 | 누락 자산, Windows 시작 오류, SQLite 연결, 생성 종료·형식, 경고문 의미 한계 분리 | 확인됨 |
| 3. 최종 업데이트 | 코드 수정·39/325 테스트·PRD/프롬프트·실험 증거·패키지 | PASS: 로컬 후보 산출물 |
| 동일 Drive 저장 | 배포 기록 DELIVERY_RECEIPT.json 및 Drive 파일 메타데이터 확인 | 별도 전송 증거로 확인 |

## 2. 최신 기반과 보존

- Drive 키트 v1.1 ZIP: `1_dCsdNQxmY1isOfdIWHX7DTcylWfI2mz`.
- 원본 dmsg v4.8 ZIP: `1zex9RUsHGKZRWjj-P5cwW2adOhc1n84z`.
- 원본 dmsg 53개 파일은 바꾸지 않았다. 전체 프로젝트의 상위 자산 117개를 추가 복원해 vendor 170개 파일 모두 원본 배포 manifest와 일치했다. `vendor_provenance.json` 참고.
- 새 기능은 arena/에 분리했다. 기존 Android APK·NPU·전체 PWA의 새 빌드·실기기 설치는 수행하지 않았다.
- 최신 우승 기획 4개 파일을 docs/winning_plan/에 함께 보존했다. 기존 v1.1 문서·증거도 역사 기록으로 남겼다.

## 3. 발견한 문제와 수정

| 문제 | 관측·원인 | 수정 | 남은 한계 |
|---|---|---|---|
| 원본 테스트 누락 | ZIP의 53개 skill 소스만으로 상위 tools/apps/평가 자산 불충분 | 동기화된 v4.8 전체 자산 회수, 원본 해시 대조 | 복원한 범위만 보증. 전체 APK 시험 아님 |
| Windows 시작 실패 | 콘솔 cp949에서 시작 메시지의 em dash 인코딩 오류 | 시작 메시지 ASCII화, 실제 서버 재시작 | 한국어 입출력 파일은 UTF-8 사용 |
| SQLite 파일 잠금 | connection context는 트랜잭션만 정리하고 연결을 닫지 않음 | finally에서 연결 close | DB 자체는 변조 방지 인증 로그가 아님 |
| 확인 계획만 존재 | 기존 ack는 확인 계획 기록, 후속 작업 상태 조회·관측 연결 부족 | SQLite 작업 ID·OPEN/REPORTED_COMPLETE·관측·재판단 | 실제 기관 확인·연락은 미구현 |
| 과거 위험의 조기 해제 | 새 발화가 약해지면 과거 요청 위험을 잃을 수 있음 | 현재 발화 안내와 세션 안내 분리, 이전 PAUSE 유지 | 이 보수성으로 정상 보류가 늘 수 있음. 개선 효과 미검증 |
| 생성 답 뒤 역할·설명 이어짐 | checkpoint eos=248044, tokenizer im_end=248046. 초기 2개 모두 추가 출력 | 런타임 종료 토큰 둘 다 적용. 출력 전체 exact-label 검증 | 원본 파일 수정 없음. 다른 입력에서도 형식 보장되는 것은 아님 |
| 단일 레이블 첫 단어만 채택할 위험 | 초기 출력 앞에 레이블이 있어도 뒤에 reasoning·역할 문구 존재 | 전체가 허용 레이블일 때만 VALID, 나머지 거부 | 생성 레이블은 어떤 경우에도 typed 확률로 변환하지 않음 |
| 정상 경고문 의미 판단 | 실제 “인증번호를 알려주지 마세요.” → UNCLEAR | 한계로 기록, 기본 정책으로 승격 금지 | 의미 분류 개선 미완료 |
| Zoro/Zoro-1 혼동 | 제공 URL은 공개 생성 모델. 기존 헤드는 접근 제한 | UI·API·문서에서 생성 비교 모드 분리 | 공식 Zoro-1 모델·헤드·kev 환경 필요 |

기존 v4.8 0.70 문턱과 7문항은 임의 변경하지 않았다. 과거 보고서의 높은 정상 보류율이 해결됐다고 주장하지 않는다. q_action의 무해한 요청 범주 공백, q_speech/lexical veto, 분산 확률 등의 후보 원인은 실제 Zoro-1 재실험이 필요하다.

## 4. 실제 모델 실행

모델: trillionlabs/Zoro. Revision: e8b7dc33b6e30b01ba59c46364fced85342ff4ff.
가중치 SHA-256: fb015df41f21b290d0103a35a23859144b6add47686190fa4aa75be7ca9c24b1.
공식 metadata의 파일 10개를 대조했고 전부 일치했다. 큰 파일은 LFS SHA-256, 작은 파일은 Git blob digest를 확인했다. `public_model_provenance.json` 참고.

장비: NVIDIA RTX 3060 12GB, driver 617.42. Python 3.12.10, torch 2.11.0+cu128, transformers 5.22.1, accelerate 1.15.0, safetensors 0.8.0. 기존 보고서의 RTX 5080 실행과 다른 장비다. BF16, eager attention, PyTorch reference kernels, causal greedy, use_cache=False, 최대 32 새 토큰. self-speculative 가속을 사용하거나 측정하지 않았다.

| 개발 예문 | 초기 checkpoint 종료 설정 | 종료 토큰 보완 후 | 해석 |
|---|---|---|---|
| 인증번호를 알려주지 마세요. | UNCLEAR 뒤 역할/설명 출력, 형식 불량 | UNCLEAR, 단일 레이블 | 문장은 경고로 작성했지만 모델은 불명확으로 응답. 의미 개선 아님 |
| 지금 인증번호를 알려주시겠어요? | DIRECT_REQUEST 뒤 reasoning/설명, 형식 불량 | DIRECT_REQUEST, 단일 레이블 | 이 예문에서 직접 요구 출력 |

초기 전체 출력 exact-label 적합 0/2, 종료 보완 후 2/2. 이는 형식 준수에 대한 개발 회귀 2건이며 의미 정확도나 일반 성능의 평가가 아니다. 새 미열람 데이터가 아니다.

실측 생성 시간(모델 로딩 제외, CUDA synchronize 사용): 초기 warning 4.765s, direct 4.250s; 종료 보완 후 warning 0.468s, direct 0.203s.

토큰 수·종료 시점과 로딩/워밍업이 달라졌으므로 이를 모델 속도 향상률로 발표하지 않는다. 두 문장으로 p50/p95·신뢰구간을 일반 성능처럼 보고하지 않는다.

별도 지속 서버: 127.0.0.1:8010. 직접 HTTP 2건과 아레나 proxy 1건을 기록했다. proxy는 HTTP 200/DIRECT_REQUEST를 반환했다. 브라우저 실제 버튼에서도 DIRECT_REQUEST를 확인했다. 생성 비교는 세션 version·작업·정책 결과를 변경하지 않는다. `generation_http.json`, `arena_public_zoro_live.jpg` 참고.

## 5. 확인 아레나 구현과 검증

SQLite에는 session/version/과거 위험, 작업 ID/상태/관측, 정책 결과·분포·offset만 기록한다. 원문과 인용은 기록하지 않는다. 요청 digest 키는 DB에 함께 있으므로 공격자에 대한 익명화·변조 방지를 보증하지 않는다. 합성 문장만 사용한다.

관측은 USER_REPORTED이며 은행·기관 검증이 아니다. 새 text를 새로 추론하고 버전을 증가시키지만, 누적 대화 전체를 모델에 넣는 방식은 아니다. 과거 PAUSE는 자동 해제하지 않는다. 사람 검토·미해결 종료가 필요하다.

| 검증 | 결과 | 증거 |
|---|---|---|
| 키트·신규 아레나·생성 경계 테스트 | 39개 PASS | kit_tests.txt |
| 복원 원본 v4.8 회귀 | 325개 PASS | source_suite.txt |
| fixture 실험 | 12개 실행 | runs/v12_fixture |
| STUB→원본 정책 replay | 12개 변환·실행, 새 모델 호출 0건 | runs/v12_stub*, runs/v12_replay |
| 실제 로컬 Typed endpoint | 요청 4, 유효 응답 0 | typed_endpoint_attempt.json |
| 공개 Zoro GPU 생성 | 수정 전/후 각 2개 실행 | public_zoro_generation*.json |
| 공개 생성 HTTP·UI | 실제 endpoint/proxy/브라우저 응답 확인 | generation_http.json, 화면 JPG |
| UI 작업·관측·재조회 | 모델 미연결 상태에서 version 1→2와 작업 유지 확인 | arena_model_unavailable.jpg |
| JavaScript 구문 | PASS | node --check arena/web/main.js 실행 |

39개 테스트 중 모델 클라이언트/생성 서버 STUB은 명시적 테스트 대역이다. 실제 모델 성공과 합산하지 않는다. 원본 테스트 통과가 과거 48/25 문장의 판단 정확도 개선을 뜻하지 않는다.

## 6. 우승 기획 반영과 미완료

반영: 현재 계약 보존, 원인별 trace, 확인 작업 서버 상태, 사용자 관측, 새 version, stale 응답 거부, 장애 시 fixture 대체 금지, 실제 생성 모델 비교, 실행 안내와 증거 장부.

남은 우선순위:
1. 승인된 Zoro-1 원본+jev_head.pt와 kev export 확보. 공식 로그인/접근 동의는 사용자가 정상 절차로 처리한다. 환경변수 인증값 직접 읽기·전송 명령은 자동 승인 검토에서 거부됐고 실행되지 않았다. 이후 공개 Zoro는 인증 없이 설치했다.
2. 같은 장비·입력·정책으로 실제 7문항 판단과 규칙 기준선·무조건 보류 기준선을 비교한다.
3. 정상 경고·무해한 요청·혼합 절 반례를 개발 split에서 다룬 뒤 새 미열람 세션과 독립 주석으로 평가한다.
4. 실제 Typed 경로로 재시작·관측·재판단을 3회 재현한다. 현재는 모델/상태 검증을 별도 수행했으며 완전한 실모델 루프 성공은 NOT_RUN이다.
5. 공식 제출·외부 도구·GPU 제공 조건과 발표 시간을 주최 측에서 확정한다. 수상 가능성은 확률로 산출하지 않는다.

| 내부 게이트 | 상태 |
|---|---|
| G1 실제 Typed 핵심 경로 3회 재현 | NOT_RUN |
| G2 모델 구분/생성 가중치 provenance | PASS, Typed 신원·경로는 NOT_RUN |
| G3 구조·버전·중복·실행 권한 | PASS deterministic/STUB 범위 |
| G4 로컬 작업 생성·재조회 | PASS |
| G5 관측·재판단·과거 위험 보존 | PASS 로직/STUB, 실제 Typed는 NOT_RUN |
| G6 대상 과제 독립 성능 평가 | NOT_RUN |
| G7 실행/모의/미확인 주장 구분 | 본 보고서와 증거로 공개 |

## 7. 파일·실행·저장

개정 문서는 docs/PRD_v4_9_rc1.md와 docs/SYSTEM_PROMPTING_v4_9_rc1.md다. 빠른 실행은 README.md, run_arena.ps1, run_local_zoro.ps1, validate.ps1을 따른다. 실행 환경·모델 가중치·자격증명·실험 DB는 ZIP에서 제외한다. 같은 PC의 모델은 work/models/Zoro, 환경은 work/zoro-runtime에 유지한다.

저장 대상: [기존 실험 패키지 폴더](https://drive.google.com/drive/folders/1ZOyMmEqNRXJktX2qSdINWszYP7li-rZz). 기존 파일을 덮어쓰거나 삭제하지 않고 새 ZIP/PRD/프롬프트/보고서/체크섬을 추가한다. 업로드 후 Drive 파일 ID·크기·해시/메타데이터를 별도 DELIVERY_RECEIPT.json에 기록한다. ZIP 안의 설명만으로 업로드 완료를 주장하지 않는다.

## 8. 공식 출처

- [대회 안내](https://hackathon.trillionlabs.co/#top): Track 1 Decision Model로 판단·행동하는 에이전트, 세부 심사는 당일 공지.
- [Trida Decision](https://trida.trillionlabs.co/decision/): typed 질문·독립 다중 질문·옵션 분포 설명.
- [공개 Zoro](https://huggingface.co/trillionlabs/Zoro): 생성 모델. 이번 실제 실행의 원본.
- [Zoro-1](https://huggingface.co/trillionlabs/Zoro-1): 별도 판단 헤드 및 fitted temperature 1.52 설명. 대상 과제 보정 증거 아님.
- [공식 kev 변환 도구](https://github.com/trillion-labs/trida-stack/blob/main/scripts/export_kev_checkpoint.py): jev_head.pt를 포함한 원본에서 head.pt export.

공식 설명, 사용자 과거 보고서, 현재 실행 결과를 서로 대체하지 않는다. 보고서의 수치는 합성 개발 예문·현재 장비의 관측값이다.
