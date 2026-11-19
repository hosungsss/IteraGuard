# v5.0 실행·추적 계약

`configs/v50_contract.json`과 생성된 JS 데이터가 버전 정본이다. 원본 질문/선택지 순서는 question_signature 배열에 포함한다. 소스 지문 검증 실패는 성공 판단으로 처리하지 않는다. Python integration/v50.py와 JS DMSG_V50의 순수 현재 턴 평가 후 user-review와 오프라인 LinkGuard 후처리를 한 번 적용한다. 정책 기본값은 legacy, 비교는 dra다.

trace는 조건 충족/eligibility/실제 적용/최종 규칙을 구분한다. 현재 턴 추적과 세션 위험 결정을 합치지 않는다. 모델 unavailable은 명시 보류하고 fixture를 숨겨 대신하지 않는다. T=1.52는 제공자 실행 설정이며 evaluator 자체가 관측/인증했다는 뜻이 아니다. 모델 인증 false 및 도메인 보정 NOT_ESTABLISHED는 별도로 유지한다.

본문/인용/URL은 저장 trace에서 제거하고 분포/근거 offset/집계 링크 상태/작업/사용자 관측만 보관한다. 원문이 없는 trace는 재추론 입력이 아니다. 제품 v5 Typed 전송은 loopback 전용이다. 외부 조회, 실제 기관 확인, 전화/은행 제어, 자동 위험 해제, 다중 턴 모델 입력을 수행하지 않는다.

이 문서는 모델 API에 자동 주입되는 프롬프트가 아니다. 공식 생성 Zoro 비교와 Zoro-1 Typed 계약을 구분한다. 소스/빌드 지문, 테스트와 실제 실행 증거를 함께 확인한다.
