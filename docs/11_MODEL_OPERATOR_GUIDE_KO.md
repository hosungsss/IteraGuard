# 운영자용 로컬 실행 및 모델 연계 가이드

**로컬 시연**

```bash
cd dmsg
python -m unittest discover -s tests -q
python scripts/validate_skill.py
python -m prototype.server
```

브라우저에서 `http://127.0.0.1:8765`에 접속한다. 시작 화면은 합성 입력용이다. 실제 전화번호, 실계좌, OTP, 민감한 녹취는 입력하지 않는다.

**운영자 연결 옵션**

다음 설정은 호환성이 검증된 **운영자 소유의 신뢰할 수 있는** /v1/systemone endpoint가 있는 경우에만 사용한다. 기본값은 비활성화. 프로덕션 권장 구성은 아니다.

```bash
# 아래 2개 조건은 외부 텍스트 전송에 대한 명시적 운영 승인과 호스트 제한을 뜻함
export DMSG_REMOTE_TEXT_CONSENT=1
export DMSG_REMOTE_HOST_ALLOWLIST='YOUR-VERIFIED-HOST'
export DMSG_MODEL_ENABLED=1
export DMSG_SYSTEMONE_ENDPOINT='https://YOUR-VERIFIED-HOST/v1/systemone'
export DMSG_MODEL_ID='EXACT_OPERATOR_VERIFIED_MODEL_ID'
# 인증이 필요한 경우에만
export DMSG_MODEL_API_KEY='...'
python -m prototype.server
```

`/api/model-status`는 구성 여부만 반환한다. `/api/model-turn`은 운영자 설정 endpoint에 응답을 요청하고, 형식 검사를 통과한 응답에만 비파괴 안내를 생성한다. 응답이 기록된 모델의 진품 여부를 검증하지 않는다. 모델 서버가 없으면 보류한다. 질문 세트는 공개 System One 예시를 참고해 작성한 내부 규약이며 실제 Zoro endpoint와 맞는지는 별도로 입증해야 한다.

**공식 API 계약 검증:** https://trida.trillionlabs.co/decision/ 및 https://docs.system-one.dev/en/docs/api . 서비스별 실제 키·엔드포인트·모델 ID를 임의로 발명하지 않는다.

**미구현:** '모를 때만 생각' 생성형 추론 2차 단계는 인터페이스/연구 요구사항에 포함하되 모델 런타임 검증 전 실행했다고 주장하지 않는다.

**네트워크 전송 안전 장치:** 모델 클라이언트는 외부 모델 주소에서 HTTPS, 정확한 host 허용 목록, 명시적 발화 전송 동의를 요구한다. 리다이렉트·중복 JSON 키·비JSON 응답·초과 본문을 거부하고 환경 프록시를 사용하지 않는다. 허용 목록과 동의를 설정해도 외부 제공자에게 실제 민감 통화를 보내라는 권장은 아니다. DNS 변경/프록시 및 실제 운영환경 보안 시험은 미완료다. 로컬 합성 테스트만 먼저 실행한다.

## 로컬 kev 서버 연결 절차

공개 모델카드 기준으로 kev는 `python -m kev.serve --run <dir> --port 8008` 형태로 실행하며, 체크포인트 내보내기에는 trida-stack의 `scripts/export_kev_checkpoint.py`를 쓴다. 저장소 접근에는 Hugging Face 약관 동의가 필요하다. 이 절차는 이 프로젝트에서 실행된 적이 없다.

```bash
export DMSG_MODEL_ENABLED=1
export DMSG_SYSTEMONE_ENDPOINT='http://127.0.0.1:8008/v1/systemone'
export DMSG_MODEL_ID='trillionlabs/Zoro-1'
export DMSG_MODEL_TIMEOUT_S=20          # 0.5–60, 현장 장비에서 실측 후 조정
# 선택: 서버가 model 필드를 요구하거나 반향을 강제하고 싶을 때만
# export DMSG_SEND_MODEL_FIELD=1
# export DMSG_REQUIRE_MODEL_ECHO=1

cd dmsg
python scripts/smoke_zoro.py --url "$DMSG_SYSTEMONE_ENDPOINT" \
  --model-id "$DMSG_MODEL_ID" --revision <HF_COMMIT_SHA> --out /secure/smoke.json --timeout 30
```

출력의 `overall`이 `CONTRACT_AND_POLICY_PROBES_PASS_NOT_ATTESTED`이면 응답 형태가 어댑터와 맞고 4개 합성 프로브가 기대 정책 범위에 들어왔다는 뜻이다. 모델 진품·정확도·보정 증거는 아니다. `FINDINGS_PRESENT`이면 각 프로브의 `schema_check`, `response_shape`, `policy_reason`을 확인한다.

| 증상 | 원인 후보 | 조치 |
|---|---|---|
| `ModelUnavailable:MODEL_ID_MISMATCH` | 서버가 다른 모델 이름을 반향 | 서버 설정·모델 ID 확인 |
| `ModelUnavailable:MODEL_TRANSPORT_ERROR_TimeoutError` | prefill이 타임아웃보다 오래 걸림 | `DMSG_MODEL_TIMEOUT_S` 상향, 장비 확인 |
| `ContractError` 계열 (`INVALID_OPTIONS` 등) | 점수형 응답 키 형식이 다름 | `response_shape` 확인 후 어댑터 수정 |
| `ModelUnavailable:INVALID_TIMEOUT_CONFIG` | 타임아웃 값 형식·범위 오류 | 0.5–60 사이 숫자로 설정 |

`python scripts/npu_readiness.py --params-b 5 --prompt-tokens 900 --questions 6 --timeout-s 20`은 메모리 하한과 필요 처리량을 계산할 뿐이며 실행 결과가 아니다.
