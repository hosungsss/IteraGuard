# v5.1 구현·개발 검증 보고

기준일: 2026-11-04. 최종 판정 로컬 개발·잠금 AI 게이트를 통과한 v5.1 개발 후보. 인간 독립·실기기 평가는 미완료. 이 문서는 합성 개발/잠금 검증과 제품 실행 검사를 구분한다. 모든 수치를 일반 정확도·사기 방지율로 읽어서는 안 된다. 실패한 실험과 잔여 오류도 결과에 포함한다.

## 구현 범위

1. 질문 profile registry와 요청 binding을 추가했다. 원본7문항, evidence 문구 후보7문항, 의미 확장10문항, 요청 구체성 포함11문항을 구분한다. 기준선 raw를 새 schema로 조용히 승격하지 않는다. 질문·criteria 순서, schema, profile/policy/실행 source 지문이 Python/JS에서 연결된다.
2. 요청 범위, 현재 민감정보/원격 노출, 비정상 송금, 요청 구체성의 모델 답을 원문의 행동/요구/압박 단서와 함께 평가한다. semantic policy /4는 기존 PAUSE를 보존하고 원래 0.70 임계값을 유지한다. 이는 모델 확률 보정이나 실제 기관 인증이 아니다.
3. 표시용 근거를 원래 앵커에서 분리했다. 행동·대상·요구가 포함된 절을 표시하며 어미 단독과 모호한 경고/인용 범위를 보류한다. 원래 정책 행동은 변경하지 않는다. 예시/경고 제목 뒤 절의 범위를 성급하게 해제하지 않도록 수정했고 Unicode 공백과 code point 위치를 Python/JS에 맞췄다.
4. 아레나·웹/desktop Typed 경로에 요청 profile/binding을 연결했다. 조건 충족과 실제 규칙 적용을 분리하며 계층의 첫 일치 우선순위를 trace에 반영한다. prior_pause, 종료/재개, 자기보고, 중복/버전 보호는 유지한다. 단문 앱은 현재 문장만 분석한다.
5. v51 전용 배포 도구를 구현했다. 실제 release_selection을 build-info에 기록하고, 비웹 정책 소스를 포함한 계약 지문을 읽기 전용 검증한다. source→PWA→APK/desktop, service worker, Android 51/5.1, 스킬 네 별칭, 소스 밖 FULL을 검사한다. 새 개인키 파일을 소스에 저장하지 않는다.

실제 소스·계약 동결: 질문/판단 실행 manifest SHA-256 48b0bbd05a51de8d2612186f7420090e0ab4330071f42abdb856b195838afdb7 (정책 /4·11문항 동결; 잠금 후 전송 오류 처리만 별도 수정). 최종 통합 회귀: Python 181건 중179 PASS·선택적 개발 replay2 SKIP, Node UI/desktop/session59 PASS·근거18 PASS. 원본 Python core26개 hash 동일. 최종 로그: internal/evidence/v51/consolidated_checks/summary.json. 이 항목들을 실기기나 모델 성능 인증으로 합산하지 않는다.

## 데이터·측정 정의

기존98개는 이미 본 개발/회귀셋이고 빈 입력1개를 포함한다. 새 AI60개는 20family×3개 대조 사례로 작성하고 가족 단위로 개발36/12family와 잠금24/8family를 분리했다. 라벨을 모델 출력 전에 동결했다. 새 자료도 AI 합성이므로 인간 독립 평가는 아니다. 기존48개는 허용 안내 범위가 넓어 합산 점수를 일반 정확도로 사용할 수 없다.

- 기대 안내 일치: 주석의 허용 안내 집합 안에 있는 결과. 유일한 정답을 맞힌 실서비스 정확도가 아니다.
- 불필요 정상 ASK: 정상 주석이고 ASK가 허용 집합 밖인 사례. 정상이라는 이유만으로 모든 ASK를 오답 처리하지 않는다.
- 필수중단 누락: pause_required인데 PAUSE_AND_VERIFY가 아닌 결과. ASK_HUMAN도 이 지표에서는 누락이다.
- 정상 false PAUSE: 정상 주석인데 PAUSE_AND_VERIFY로 나온 사례. 위험/맥락부족 NO_STRONG_SIGNAL과 별도로 기록한다.
- 모델 호출: 비어 있지 않은 입력의 실제 제공자 호출. 빈 입력 처리와 저장 raw의 정책 replay는 합산하지 않는다.

아래 stage 수치는 **현재 턴 정책 코어**의 결과다. user-review/LinkGuard/세션 결합까지 포함한 최종 결과는 PASS — 비빈157개×2조건=314개 raw에 대해 Python/JS 정책 및 전체 처리 객체628개 일치. user-review/LinkGuard 경로의 action/reason 변경0. 세션 위험은 별도 UI 경로로 확인이다.

## stage 1~6 개발 실험

| 단계 | 고정/변경과 실행 | 관측과 판단 |
|---|---|---|
| 1 legacy/evidence | 기존98의 비빈97개×원본/evidence 문구2조건, 실제194호출 | 기대 안내56→59/98, 불필요 정상 ASK26→23, 필수중단 누락14 유지. evidence만으로 중단 누락 해결 불가 |
| 2 semantic | 새 의미10문항, 비빈97개 실제호출 | 기대 안내67/98, 불필요 정상 ASK21, 필수중단 누락8. 원문과 현재 요구를 함께 볼 추가 조건 검토 |
| 3 scoped replay | stage2 raw에 사전등록한 정책 보강, 새 호출0 | 기대 안내78/98, 불필요 정상 ASK14, 필수중단 누락4. 이미 본 자료의 개발 재생이며 독립 평가 아님 |
| 4 development36 | 새 개발36개×기준선/semantic, 실제72호출 | 기대 안내8→19/36, 불필요 정상 ASK16→11/정상19, 필수중단 누락11→5/필수12. 정상 false PAUSE는 양쪽1 |
| 5 specified /3 | 요청 구체성 추가11문항, 기존98+개발36의 비빈133개 실제호출 | 일부 개선과 함께 V13의 새 위험 NO_STRONG_SIGNAL 1건 발생. semantic policy /3은 HOLD. 좋은 합산 점수로 실패를 숨기지 않음 |
| 6 final policy /4 replay | 같은 stage5 raw에 요청범위·간접 이동 guard 수정, 새 호출0 | 새 위험/맥락부족 정상처리0, 기존 허용 안내 손실0을 개발 집계에서 확인. 필수중단 누락3·정상 false PAUSE1이 남아 최종 잠금 검증으로 진행 |

stage1·2·4·5 실제 요청은 194+97+72+133=496회이고 각 run_summary의 오류 수는0이다. stage3·6은 재생이며 새로운 모델 호출이 아니다. 브라우저/후속 검증 호출은 이 합계에 섞지 않는다.

semantic policy /3의 실패 원인은 요청이 명확하다는 답을 일상적인 요청의 충분조건처럼 사용한 것이다. /4는 scope가 other_request를 선택해야 하고, 간접 주소/페이지/접속 유도가 있으면 정상화 경로를 막는다. 임계값을 낮추지 않았다. 이 수정은 잠금24 결과를 열기 전에 동결했다. `/3`, `/4`는 v5.1 내부 정책 실험 번호이며 제품 v3.x/v4.x를 뜻하지 않는다.

## 최종 개발 코어 결과 — 집합별 수치가 우선

| 자료 | 기대 안내 기준선→후보 | 불필요 정상 ASK 기준선→후보 | 필수중단 누락 기준선→후보 | 정상 false PAUSE 기준선→후보 |
|---|---:|---:|---:|---:|
| 기존 V2 48 | 35→40 /48 | 6→6 /정상21 | 7→2 /필수9 | 0→0 |
| 이전 AI25 | 7→17 /25 | 12→6 /정상12 | 4→0 /필수10 | 0→0 |
| 추가 AI25 | 14→22 /25 | 8→2 /정상12 | 3→1 /필수8 | 0→0 |
| 신규 개발36 | 8→28 /36 | 16→7 /정상19 | 11→0 /필수12 | 1→1 |

보조 합산은 기대 안내64→107/134, 불필요 정상 ASK42→21/정상64, 필수중단 누락25→3/필수39다. 그러나 집합별 rubric과 주석 범위가 달라 단일 일반 정확도로 홍보하지 않는다. 최종 개발 필수중단 누락은 V15, V18, V50-AI-21이다. 정상 false PAUSE인 V51-F03_THEATRE_RESERVATION_FEE-01은 기준선에서도 발생했고 후보에서도 남았다. 기존 PAUSE 보존은 새 해제 회귀를 막지만 이 오경보를 해결하지 못했다.

## 잠금 AI24 결과

정책 /4·11문항 profile을 결과 확인 전에 동결하고 기준선/후보 각24개, 실제48호출을 수행했다. 사전등록 잠금 검증 상태는 PASS이며 입력·라벨·raw를 이 문서에 다시 싣지 않는다.

| 지표 | 기준선 | 후보 |
|---|---:|---:|
| 기대 안내 일치 | 7/24 | 17/24 |
| 전체 ASK | 23/24 | 13/24 |
| 불필요 정상 ASK | 11/정상12 | 5/정상12 |
| 필수중단 누락 | 6/필수7 | 2/필수7 |
| 위험/맥락부족 NO_STRONG_SIGNAL | 0 | 0 |
| 정상 false PAUSE | 0 | 0 |

기존 허용 안내 손실 및 개별 회귀: PASS — 잠금24를 포함한158개 기준선/후보 쌍에서 기존 허용 안내 손실·새 위험/맥락부족 NO_STRONG_SIGNAL·새 정상 PAUSE·새 필수중단 누락 모두0. 전체 후처리 경로: PASS — 비빈157개×2조건=314개 raw에 대해 Python/JS 정책 및 전체 처리 객체628개 일치. user-review/LinkGuard 경로의 action/reason 변경0. 세션 위험은 별도 UI 경로로 확인. 작은 AI 합성 잠금셋의 개선 방향이며 독립 사람 평가나 실서비스 오류율이 아니다. 최종셋을 본 뒤 판단 코드 튜닝을 하지 않는다. 불필요 정상 ASK5건·필수중단 누락2건이 남아 문제 해결 완료로 표시하지 않는다.

## 잠금 이후 전송 오류 처리 수정

최종 잠금 후 아레나 manifest/profile binding에서 TypeError가 연결 종료로 번지던 경로를 정적 HTTP503으로 처리했다. 이는 오류 처리 순서의 수정이며 decision policy·동결된 판단 source hash는 변경하지 않았다. `internal/evidence/v51/post_lock_transport_fix.json`에 변경 전후 파일 hash와 decision_policy_changed=false를 기록했다. 이후 HTTP/session/실행 회귀를 재검사했으며 중복 실행은 테스트 총계에 합산하지 않았다. 잠금 결과에 맞춘 판단 튜닝으로 기록하지 않는다.

## 근거 표시 품질 — PARTIAL

비빈157문장의 표시 상태는 AVAILABLE35, PARTIAL13, UNAVAILABLE88, NOT_APPLICABLE21이다. 표시가 있는 문장은48/157이다. 후보 절163개 중 표시52개(31.9%), 미표시111개(68.1%)이며, 원래 모델 앵커19개 중9개를 표시하고10개(52.6%)는 보류했다. invalid upstream은0이다. 표시52개는 code point offset/quote52/52 일치했고, 표시 전후 action/reason/message/original evidence/trace157/157을 보존했다.

AI gold를 보조 기준으로 사용하면 개발36의 gold46span에서 gold code point 포함률38.5%, 표시 code point의 gold 내부 비율71.3%다. 잠금24의 gold35span에서는32.5%/66.3%다. 이는 문자 겹침이며 의미 정확도가 아니다. dev F06-02의 +33code point, locked F14-01의 +35code point처럼 지나치게 넓은 구간이 포함될 수 있다. 근거 표시를 완성했다고 주장하지 않으며 인간 독립 의미 평가는 NOT_RUN이다. 정본은 internal/evidence/v51/full_pipeline_validation/evidence_display_quality.json이다.

## 지연 관측 — 상주 GPU의 warm 요청만

동일 비빈157개 입력을 조건별157회씩 비교한 관측에서 원본7문항 p50은145.3ms, p95는156.608ms이고 후보11문항은275.9ms/289.008ms, 최대377ms였다. 양쪽 입력 길이는 Unicode code point 기준 최소1/최대158/중앙값47이다. RTX 로컬 상주 GPU·T=1.52 환경에서 문항 증가에 따른 지연 비용이 관측됐다.

cache 상태가 섞였고 실행 순서가 무작위가 아니므로 인과 배율이나 보편 속도로 설명하지 않는다. 모델 cold start는 기존 GPU 서버를 보존해 NOT_RUN이며, 앱 서버 재시작은 GPU 모델 cold start 검증이 아니다. 동시성·부하 시험도 NOT_RUN이다. 정본은 internal/evidence/v51/latency_summary.json이다.

## 전체 실제 호출과 런타임 검증

등록 실험544회(stage1~6의496회+잠금24의48회)와 런타임13회(브라우저8, desktop DRA API1, 세 차례 재시작에 연결한4호출)를 합쳐 실제 제공자 처리557회다. 제공자 counter792→1349 차이와 일치한다. replay/mock·도달 불가 endpoint 오류 probe는 실제 모델 호출에 합산하지 않는다. 정본은 internal/evidence/v51/actual_call_accounting.json과 browser/receipt.json, runtime_restart의 영수증이다.

## 실행·표시·배포 검증과 미완료

최종 source 테스트와 Python/JS 회귀: Python 181건 중179 PASS·선택적 개발 replay2 SKIP, Node UI/desktop/session59 PASS·근거18 PASS. 원본 Python core26개 hash 동일. 최종 로그: internal/evidence/v51/consolidated_checks/summary.json. 아레나/단문 앱의 실제 브라우저 검증: 실제 Typed 브라우저8요청 성공. 정상 NSS·OTP PAUSE와 근거, 아레나 현재NSS/세션ASK, 자기보고·종료·새로고침·재개 뒤 위험/작업 보존 확인. 일반 Node 브라우저 연결 실패 후 CUA 경로로 확인; 경고문 ASK 잔여. 근거 offset·의미·미표시율/coverage: PARTIAL — 비빈157문장 중48문장에52구간 표시; offset/quote52/52 일치와 표시 전후 정책/원본 앵커157/157 보존. 표시 coverage와 과도한 포함 문제가 남으며 인간 의미 평가는 NOT_RUN. 최종 APK/PWA/desktop/skill/FULL·독립 추출: PWA/APK/desktop 자산32 PASS, APK 독립 구조·v2 서명·변조검출 PASS(실기기 NOT_RUN). FULL/독립추출 검증 영수증은 배포 ZIP 옆 [Back Data/v5.1_구현기록_20261104/IMPLEMENTATION_RECEIPT.json](<../../Back Data/v5.1_구현기록_20261104/IMPLEMENTATION_RECEIPT.json>) 참고.

배포 도구 자체의 inert fixture 검사15개와 이전 배포 회귀17개는 통과했다. 별도로 실제 PWA/APK/desktop32자산, APK v2 서명·인증서·변조사본 거부·DEX·manifest 51/5.1·SDK24/34·권한없음을 검증했다. 원본/root APK 바이트는 같고 검사 중 바뀌지 않았다. 이 검사는 실제 설치·실행 성공의 증거가 아니다. 임시 메모리 debug 서명 때문에 빌드 간 APK 바이트/서명 동일성과 이전 APK 위 업데이트 설치 호환성을 보장하지 않는다.

인간 독립 평가 NOT_RUN, Android 실기기/iOS NOT_RUN, model_attested=false, domain calibration NOT_ESTABLISHED다. L2/G7/기관 질문/L1 현행 유지, 실제 기관 확인/외부 평판/은행 제어/자동 위험 해제 미구현 경계는 그대로다. 추가 reasoning LLM이나 별도 추론 서버는 도입하지 않았다.

## 근거 위치

- `internal/evidence/v51/experiments/stage1_legacy_evidence`부터 `stage6_final_policy_replay`의 protocol/metrics/run_summary. 패키지 검증: PWA/APK/desktop 자산32 PASS, APK 독립 구조·v2 서명·변조검출 PASS(실기기 NOT_RUN). FULL/독립추출 검증 영수증은 배포 ZIP 옆 [Back Data/v5.1_구현기록_20261104/IMPLEMENTATION_RECEIPT.json](<../../Back Data/v5.1_구현기록_20261104/IMPLEMENTATION_RECEIPT.json>) 참고.
- final24 정본: internal/evidence/v51/experiments/stage7_locked_validation24. 최종 집계 대조: PASS — 잠금24를 포함한158개 기준선/후보 쌍에서 기존 허용 안내 손실·새 위험/맥락부족 NO_STRONG_SIGNAL·새 정상 PAUSE·새 필수중단 누락 모두0.
- profiles/contract/semantic/evidence 모듈과 생성기, `internal/evidence/v51/packaging_tools_validation.json`, `internal/evidence/v51/independent_code_review_findings.json`.
- v5.0 구현 보고·실험과 v5.1 개선 계획은 변경하지 않고 계보로 보존한다. 현재 버전 간 상세 차이는 VERSION_LEDGER를 따른다.

복사본에 남아 있던 기존 공개 debug 키 디렉터리도 배포 소스 밖으로 제외했다. 원래 v5.0은 변경하지 않았다. 현재 APK는 메모리 임시 키로 이미 서명돼 있어 제외 작업으로 APK 바이트는 달라지지 않았다. 근거는 internal/evidence/v51/debug_key_exclusion.json과 apk_validation/apk_independent_verification.json이다.

잔여 실패의 사례별 해석과 미들웨어 판단은 [실패 분석](V51_FAILURE_ANALYSIS.md)을 따른다.
