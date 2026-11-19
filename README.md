# 의심계 · IteraGuard

의심스러운 문자나 이메일을 받았을 때 **상대가 요구한 행동, 다시 읽어야 할 원문, 다음에 할 확인**을 보여주는 로컬 웹 시연입니다. Zoro-1 System 1의 선택형 응답을 읽고, 앱의 정책으로 표시와 확인 업무를 결정합니다.

현재 소스는 **v5.9**, Arena 엔진은 **v5.6**, Zoro 응답 계약은 **v5.1**입니다. [버전 정보](LATEST_VERSION.json)

## 연구모형

![IteraGuard 연구모형. 입력 메시지, Zoro-1의 두 응답, 경보 교차 확인, 결과 카드와 551건 피싱 탐지율](docs/assets/iteraguard-research-model.svg)

## 현재 시연에서 할 수 있는 일

| 화면 | 기능 |
| --- | --- |
| **문자 신호등** `/` | 합성·비식별 메시지를 넣으면 **빨강·주황·초록·회색** 등급, **요청한 행동**, 네 색의 Zoro 선택 점수를 보여줍니다. 가능한 경우 **확인이 필요한 원문 한 구절**을 강조합니다. |
| **성능검증** `/` | 고정 한국어 테스트 551건의 집계와 색별 분포를 보여줍니다. 원본 CSV와 로컬 Zoro를 연결하면 화면에서 재측정할 수 있습니다. |
| **상세 Arena** `/arena` | 상황에 따라 중단·독립 확인·추가 질문을 안내합니다. 새 위험을 확인 업무로 저장하고, 다음 입력이 평범해도 이전 미해결 업무를 유지합니다. |
| **링크 확인** `/link-review` | 별도 화면에서 설정된 조회 자료를 확인할 수 있습니다. 조회 결과가 있을 때 사용자가 선택하면 로컬 Zoro가 메시지와 조회 결과를 함께 읽습니다. |

### 문자 신호등의 판단 과정

1. 원문을 한 번 보내 조로에게 두 가지를 묻습니다. 신호등 네 색 중 하나와 발신자가 현재 요청한 행동 후보 20개 중 하나를 고르게 합니다.
2. 기존 문맥 보정을 적용합니다. 기본 `high-recall` 프로필에서는 초록·회색이어도 **고위험 행동 10종 중 하나가 선택되고 빨강·주황 선택 점수 합계가 45% 이상**이면 주황으로 표시합니다. 확인된 예방 경고와 과거 보고는 이 교차 확인에서 제외합니다.
3. 원문에서 요청이 담긴 구절을 후보로 뽑아 Zoro로 따로 평가합니다. 조로가 빨강·주황을 고른 구절 중 두 색의 점수 합이 가장 높은 구절 하나를 원문에 표시합니다. 점수 막대는 전체 원문의 네 색 선택 분포를 보여줍니다.

회계 관련 요청에는 결과 바로 아래에 조로가 선택한 절차의 단계와 문서 ID를 표시합니다. **FIN-01 · 은행 계좌정보 재확인**은 등록 정보 대조를, **FIN-02 · 새 계좌 송금 전 이중 확인**은 지급 보류와 독립 연락·별도 승인을 안내합니다. 화면의 등록 계좌는 가상 예시입니다. 절차는 회계팀의 확인 작업을 안내합니다.

상세 Arena는 별도 평가 경로를 사용합니다. Zoro의 후보 선택과 예·아니오 응답을 현재 문장의 근거와 함께 읽어 조치를 정합니다. 확인 업무와 기록은 SQLite에 저장됩니다. [Arena 시연과 검증 범위](docs/V56_ARENA_DEMO_UPDATE.md)

### 확장 아이디어 · PointerHead를 검색 엔진으로 활용

Zoro-1의 **PointerHead를 로컬 목록을 조회하는 검색기(신경망 인덱스)**로 활용합니다. 문자 원문 하나에 아래 세 질문을 묶어 보내면, 하나의 Zoro 요청에서 위험도와 검색 결과를 함께 받을 수 있습니다.

| 질문 | Zoro가 선택하는 값 | 앱이 보여주는 내용 |
| --- | --- | --- |
| 위험도 판정 | 신호등 네 색 중 하나 | 현재 문장의 위험도 |
| 공개 피해·피싱 사례 검색 | 원문과 유도 수법이 비슷한 사례 ID 또는 보류 | 저장된 요약과 공개 출처 |
| 사내 대응 매뉴얼 검색 | 현재 요청에 적용되는 절차 ID 또는 보류 | 확인 단계와 참조 문서 |

앱은 사례와 매뉴얼을 로컬 JSON에 저장합니다. 요청 시 각 질문에 후보의 ID와 짧은 설명을 넣고, Zoro가 고른 ID로 저장된 상세 정보를 읽습니다. **별도 DB 서버나 벡터 검색 서비스 없이 Zoro 모델 하나**로 이 조회를 구성할 수 있습니다. 로컬 엔진의 상한은 질문당 255개 선택지이며, 필요한 경우 그 안에 보류 선택지도 포함합니다.

현재 의심계는 [회계 확인 절차](configs/accounting_procedures.json) 조회를 붙인 상태입니다. 공개 사례 검색은 별도 로컬 실험에서 살폈으며, 세 질문을 한 요청에 묶는 방식은 확장 구상입니다. 로컬 합성 요청 한 건에서 세 응답을 함께 받았습니다. 새 계좌 송금 요청에 대해 빨강, 공개 사례 후보 AT01, 회계 절차 FIN-02에 해당하는 ID가 선택됐습니다.

## 피싱 탐지율 실측

같은 한국어 테스트 551건에서 **피싱 탐지율이 34.0% → 84.0%**로 올랐습니다. 피싱 탐지율은 피싱으로 라벨된 50건 중 빨강·주황 경보가 나온 비율입니다.

| 적용 조건 | 피싱 탐지율 | 정상 탐지율 |
| --- | ---: | ---: |
| 이전 기본 질문 | 34.0% (17/50) | 90.8% (455/501) |
| 고감도 질문과 문맥 보정 | 78.0% (39/50) | 88.2% (442/501) |
| **현재 기본값** · 고감도 질문과 고위험 행동 교차 확인 | **84.0% (42/50)** | **84.8% (425/501)** |

**정상 탐지율**은 정상 501건 중 경보가 없었던 비율로 초록 325건과 회색 100건을 셉니다. 피싱을 25건 더 탐지했고 정상 문자에 뜬 경보는 46건에서 76건으로 늘었습니다. 최종 이진 정확도는 **84.8% (467/551)**, 정상의 초록만 정답으로 세는 엄격 일치율은 **66.6% (367/551)**입니다.

로컬 Zoro-1 `bf1b76b9`, CUDA BF16, 온도 **1.59**로 Arena 재측정 API에서 **551회 요청**을 실행해 최종 집계를 재현했습니다. 소요 시간은 **209.446초**였습니다. 질문과 규칙을 검토한 고정 표본의 결과입니다. 새 표본에서의 탐지 성능과 원문 구절 표시 정확도는 미검증입니다. [실측 환경과 채점 기준](docs/SIGNAL_BENCHMARK_UI_20261120.md)

### 평가 데이터 출처와 이용 조건

고려대학교 Autonomous AI Lab의 `MessengerPhishingDetection`에서 제공하는 **한국어 테스트 분할**을 사용했습니다. 이 실험에서는 551건을 로컬 모델의 평가 입력으로 사용했습니다.

| 항목 | 평가 기준 |
| --- | --- |
| 원본 파일 | `messenger_phishing_dataset/kor/test.csv` |
| 원본 리비전 | `438cfbb251410fee791f49d75d928520847030c3` |
| 라벨 | `0` 정상 501건, `1` 피싱 50건 |
| CSV SHA-256 | `31bed1a63581de43b1c81b84c8714873199ace1f92a4d93830478842df5443bf` |

[고려대 Autonomous AI Lab](https://github.com/ku-autoai) · [고정 리비전 데이터 설명](https://github.com/ku-autoai/MessengerPhishingDetection/blob/438cfbb251410fee791f49d75d928520847030c3/README.md) · [고정 CSV](https://github.com/ku-autoai/MessengerPhishingDetection/blob/438cfbb251410fee791f49d75d928520847030c3/messenger_phishing_dataset/kor/test.csv)

고정 리비전의 문서와 데이터 디렉터리에서 CSV의 라이선스 및 재배포 조건을 확인하지 못했습니다. 이 저장소에는 출처 링크, 해시와 실측 집계를 실었습니다. CSV를 다시 배포하거나 다른 용도로 이용할 때는 원 게시처에 적용 조건을 확인하세요. [외부 자료 고지](THIRD_PARTY_NOTICES.md)

## 로컬에서 실행하기

Python 3.12와 로컬 Zoro-1 System 1 서버를 준비합니다. 저장소에는 모델 가중치와 서빙 환경이 포함되어 있지 않습니다. `.env.example`의 예시는 자동으로 읽히지 않으므로 서버에 맞는 포트와 모델 ID를 직접 설정합니다.

```bash
export DMSG_MODEL_ENABLED=1
export DMSG_SYSTEMONE_ENDPOINT=http://127.0.0.1:8008/v1/systemone
export DMSG_MODEL_ID=trillionlabs/Zoro-1
export DMSG_SEND_MODEL_FIELD=1
export DMSG_REQUIRE_MODEL_ECHO=1
export DMSG_MODEL_TIMEOUT_S=20
python -X utf8 -m arena.server --port 8769
```

Windows PowerShell에서는 같은 변수를 `$env:DMSG_MODEL_ENABLED = "1"` 형식으로 설정하고 `./run_hackathon.ps1 -Port 8769`를 실행할 수 있습니다. 서버 연결과 응답 형식은 실제 판단 요청에서 확인합니다.

브라우저에서 <http://127.0.0.1:8769/>를 열고 합성·비식별 문자로 **판단하기**를 누릅니다. 확인 업무와 이력은 <http://127.0.0.1:8769/arena>에서 확인합니다.

### 551건 재측정하기

위 고정 리비전에서 원본 `test.csv`를 내려받아 모델 환경을 설정한 셸에서 실행합니다. 재측정 서버는 사용 전에 CSV의 SHA-256과 라벨 구성을 검증합니다.

```bash
python -X utf8 -m arena.server --port 8769 --signal-benchmark-csv /path/to/test.csv
```

메인 화면에서 **성능검증 → 재측정 시작**을 누르면 진행 건수를 볼 수 있습니다. 551건을 마치면 네 색의 건수와 지표를 갱신합니다. 이전 기본 질문을 비교할 때는 `--signal-profile baseline`을 지정합니다.

## 검증과 참고 문서

```bash
python -X utf8 -m unittest discover -s tests_v56 -v
python -X utf8 -m unittest discover -s tests_v54 -v
node --test tests_demo_validation/test_api_ui.js tests_v50/test_session_ui.js tests_v53/test_choice_ui.js
python -X utf8 tools/run_judge_scenarios.py --mode controlled --out runs/controlled
python -X utf8 tools/run_judge_scenarios.py --mode live --out runs/live
```

`controlled`는 고정 응답으로 앱의 동작을 검증합니다. `live`는 설정된 로컬 모델 서버에 요청합니다. 상세 Arena의 `GET /api/evidence?session_id=...`는 요청·정책·업무 이력을 공개 증거 형식으로 제공합니다.

- **상세 기능과 규칙** · [Arena v5.6](docs/V56_ARENA_DEMO_UPDATE.md) · [신호등 질문 비교](docs/SIGNAL_PAIRED_EVALUATION_KO.md) · [심사 증거 안내](docs/JUDGE_EVIDENCE_GUIDE.md)
- **산업별 확인 절차** · 별도 Rulebook은 계좌 변경과 환불 템플릿에 대해 확인 업무를 제안합니다. [구성 및 로컬 실행법](docs/V58_RULEBOOK_ARCHITECTURE.md)
- **추가 연구 자료** · [경고 문맥 관찰](docs/V58_RULE_TWEAK_SHADOW_REVIEW.md) · [사기 유형의 합성 사례](docs/research/SCAM_EVIDENCE_ATLAS_2026_KO.md) · [선택형 Jev 관찰](docs/V58_JEV_CLOUD_TEXT_STUDIO.md)
- **이력** · [현재 프로젝트 상태](CURRENT_PROJECT_STATE.md) · [인계 기록](HANDOFF_CHANGELOG.md) · [버전 장부](internal/VERSION_LEDGER.md) · [v5.9 초기 UI·처리 시간 검토](docs/V59_ARENA_UI_AND_PERFORMANCE.md)

이 저장소의 시연 범위는 합성·비식별 입력에 대한 판단과 확인 안내입니다. 실제 송금, 결제 승인, 계좌 변경은 담당자의 별도 확인이 필요한 업무입니다. Zoro 선택 점수는 주어진 보기 사이의 상대 점수입니다.

## 라이선스

- **IteraGuard 원저작물**은 [Apache-2.0](LICENSE)입니다. [라이선스 적용 범위](LICENSE_SCOPE.md)
- **Zoro-1 가중치**는 Apache-2.0입니다. Hugging Face에서 모델 파일을 받으려면 해당 저장소의 접근 조건에 동의해야 합니다. 모델은 실행 환경에서 별도로 준비합니다. [Zoro-1 모델 카드](https://huggingface.co/trillionlabs/Zoro-1#license) · [실측 리비전의 LICENSE](https://huggingface.co/trillionlabs/Zoro-1/resolve/bf1b76b9b4df03b05fcbb73444e1cd4db0f566da/LICENSE)
- **외부 데이터와 이전 APK·ZIP 등**은 자료별 조건을 따릅니다. [외부 자료 고지](THIRD_PARTY_NOTICES.md)
