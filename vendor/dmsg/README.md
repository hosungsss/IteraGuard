# dmsg — IteraGuard / 의심계

스킬 식별자 `dmsg`, 출품작 `의심계(Doubt Meter)`, 팀명 `IteraGuard`, 버전 v4.0.

이 디렉터리는 **합성 대화용 보이스피싱 위험 행동 개입 시연**과 그 검증 명세를 포함한다. 운영자 지정 선택형 모델 통합 경로가 존재하지만 실제 Zoro-1 체크포인트 인증은 완료되지 않았다. 모델을 사용하지 않는 수동 입력은 `ASK_HUMAN`으로 보류된다. 외부 금융·전화·메시징 조치는 수행하지 않는다.

## 핵심 명세

- `references/PRD.md` — 제품 목표, 요구사항, acceptance criteria.
- `references/SYSTEM_PROMPT.md` — 제안된 오케스트레이터 System Prompt, 출력/권한 계약.
- `references/PROMPTS.md` — typed decision 질문 구조.
- `references/MODEL_CONTRACT.md` — 실모델 검증 게이트.
- `references/EVALUATION.md` — 평가·반증 프로토콜.
- `SKILL.md` — 개발·검수 스킬 운영 지침.

## 구동

```bash
python -m unittest discover -s tests -v
python scripts/validate_skill.py
python scripts/evaluate_fixtures.py
python -m prototype.server
```

브라우저 `http://127.0.0.1:8765`; Python 3.11+ 필요. `scripts/smoke_zoro.py`는 인가된 서버에서 운영자가 별도 실행할 실모델 계약 확인 도구로, 웹 데모 코드에 자동 연결되지 않는다.

`.skill`은 ZIP 포맷의 배포 컨테이너이며 네이티브 slash 명령 인식 여부는 호스트별로 다르다. 설치 방법은 `references/PLATFORM_INSTALL.md` 참조.

외부 모델로 텍스트를 전송하려면 `DMSG_REMOTE_TEXT_CONSENT=1`과 `DMSG_REMOTE_HOST_ALLOWLIST`를 모두 구성해야 한다. 승인되지 않은 원격 전송은 거부되며, 로컬 합성 테스트에는 필요하지 않다. 작성자 합성 공격 반례는 `python scripts/run_adversarial_suite.py`로 별도 확인한다.

추가 평가 명령: `python scripts/npu_readiness.py` 및 `python scripts/evaluate_annotations.py <주석.jsonl>`; 둘 다 실모델 실행·독립 정답 증거와 구별합니다.

## PAYLOCK 연동 업무 모듈

`http://127.0.0.1:8765/paylock.html`에서 지급 요청 합성 시나리오를 실험한다. 모델 없이 구조적 차이로만 보류할 수 있으며, Zoro-1 선택형 질문은 실제 검증 전 미인증이다. 은행·이메일 송신·ERP 연동은 전혀 없다.
