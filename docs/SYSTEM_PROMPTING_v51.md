# v5.1 실행·추적 계약

정본은 configs/v51_contract.json, v51_profiles.json, v51_release_selection.json이다. 원본 v50 계약은 변경하지 않은 기준선으로 검증한다. 질문 객체 및 criteria 순서가 모델 입력에 포함되므로 질문 지문에 순서를 반영한다. Python integration/v51.py와 JS DMSG_V51가 같은 profile·policy·질문 binding을 요구한다.

모델 요청 전에 선택을 결합하며 응답 시점에 새 선택으로 재해석하지 않는다. 입력/응답 스키마·필수 head·허용 policy 조합·source hash·generated contract data 불일치는 명시 실패다. v50 raw에서 새 head를 추정하거나 누락 확률을 정상 값으로 채우지 않는다. 실제 release default는 검증된 release_selection에서 읽는다.

기준 정책 평가 후 버전이 명시된 의미 확장 규칙을 적용한다. semantic policy /4는 원래 PAUSE를 보존하며, 현재 민감 요청·송금 이상·명시적 정상 요청·안내/경고의 조건을 순서대로 평가한다. `q_request_specified`만으로 정상화하지 않고 명시적 other_request scope와 간접 주소/페이지 이동 차단을 함께 요구한다. 임계값0.70은 변경하지 않으며 선택 확률은 사기 발생확률이 아니다.

trace에서 조건 충족·계층별 적용 가능성·최종 적용 규칙을 구분한다. profile/question/manifest 지문과 base/semantic 규칙을 남긴다. 순수 현재 턴 평가 뒤 user-review/오프라인 LinkGuard를 한 번 적용하고, 아레나가 과거 위험을 별도로 결합한다. 각 단계의 행동을 분리한다. 사용자 보고와 종료/재개는 자동 위험 해제가 아니다.

근거 표시 enrichment는 판단 행동과 원본 evidence를 바꾸지 않는다. 인용/경고 범위가 모호하면 표시를 보류한다. Python code point와 JS Unicode 위치를 대응시키며 trace에는 offset·유형·표시 상태만 남긴다. 저장 경로에는 입력 원문·인용·URL을 넣지 않는다. 원문 없는 trace는 재추론 입력이 아니다.

Typed는 loopback 전용이고 모델 미연결/오형식은 숨은 fixture로 대체하지 않는다. T=1.52는 제공자 실행 설정, model_attested=false와 domain calibration NOT_ESTABLISHED는 별도 상태다. 공개 생성 Zoro·기기 내 NLP·Typed Zoro-1을 구분한다. 이 문서는 모델 API에 자동 주입되는 프롬프트가 아니다.
