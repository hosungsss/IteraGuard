# v5.1 AI 합성 개발·검증 자료 주석 기준

작성 목적은 질문·정책 후보의 개발 비교다. 60개 모두 AI 작성이며 인간 독립 평가·실제 사기 정답·실사용 정확도를 대표하지 않는다. 후보 모델의 출력은 작성 및 동결 전에 보지 않았다. development 36개/12 family, validation 24개/8 family를 먼저 배정하고 각 family의 대조 3개를 같은 split에 둔다. 검증셋 내용과 정답은 부모 작업자에게 보고하지 않고 경로·분모·지문만 전달한다.

## 라벨

- `request_presence`: `none`은 현재 화자가 청자에게 수행을 요구하지 않음, `present`는 요구가 존재함, `unclear`는 요구 유무 자체가 현재 문장으로 해결되지 않음. 보호 경고의 부정 지시는 민감 행동 수행 요청으로 세지 않는다. 여기에 해당하는 no-current-request 의미를 speech 및 근거 directness와 함께 읽어야 한다.
- `action`: 기존 폐쇄 라벨 transfer/otp/remote_install/personal_data/link/secrecy/none/unclear에 맞춘 호환 필드다. **none만으로 요청 없음이나 안전을 뜻하지 않는다.**
- `requested_action`: 위 라벨 및 `outside_listed_categories`. 명확한 일반 요청은 이 추가 값을 쓰고 action=none, request_presence=present, action_scope=outside_listed_categories로 구별한다. 제품 기본 질문에 이 값을 이미 추가했다는 의미는 아니다.
- `action_list`: 현재 직접 요구한 모든 지원 민감 행동을 보존한다. 인용·경고·과거 보고에만 등장하는 행동은 제외한다. `additional_requested_actions`는 대표 이외 행동이다. 주행동은 점수 비교용 포인터이며 복수 행동 전체를 대신하지 않는다. 주행동 우선순위는 OTP, 원격 접근, 송금, 개인정보, 링크, 비밀 유지로 정한다. 이는 심각도의 실측 순위가 아니다.
- `speech`: direct_request/reported_or_quoted/negated_or_warning/unclear/informational. 인용이나 경고 뒤 별도의 현재 요구가 있으면 그 현재 요구를 구분하고 근거를 각각 남긴다. 무해한 직접 요청도 direct_request다. 사실 설명과 현재 요청이 섞인 경우 단순한 첫 단어로 전체 화행을 정하지 않는다.
- `risky`: true/false/null은 작성자가 의도한 문맥이며 실제 범죄 진위가 아니다. risk.fraud_truth는 항상 NOT_KNOWN이다. null은 미확정 문맥으로 정상·위험 분모에서 분리한다.
- `allowed_guidance`/`expect`: 동일한 비어 있지 않은 허용 상태 집합. 명확한 무해 정보·행동에는 NO_STRONG_SIGNAL(안전 보증 아님)을 기대한다. 일반 송금·링크는 실제 계좌/발신자/링크를 확인할 수 없으므로 CAUTION 또는 ASK_HUMAN을 허용하고 rationale에 이유를 적는다. 실제 요구 없는 위험 보고, 미해결 대상, 간접 압박은 별도로 주석한다. ASK 허용 사례의 보류를 오답으로 세지 않되 전체 정상 업무 부담은 별도 지표로 남긴다.
- `pause_required`: 명시적 현재 자격증명 전달, 원격 제어, 신분증 등 민감정보 전달 또는 독립 확인 방해·불이익 압박과 결합한 직접 송금 요구에 true를 부여한다. 이 경우 expect는 PAUSE_AND_VERIFY 하나다. 판단 보류와 필수 중단 이행을 같은 성공으로 세지 않는다. 문맥이 모호하면 임의로 true를 넣지 않고 ASK_HUMAN을 허용하며 이유를 쓴다.
- `evidence`: Python Unicode codepoint 기준 start_cp/end_cp, 원문 quote, directness 및 해당 action. 의미를 설명하는 절·대상·행위를 포함하고 요청 어미만을 근거로 쓰지 않는다. 서로 다른 현재 행동은 별도 구간을 둔다. 지시어의 대상이 문장 안에서 해소되면 대상 정의와 요구 부분을 함께 둔다. semantic_verification=false는 AI 주석이 사람 의미 검증 증거가 아님을 뜻한다. offset 일치와 의미 적절성은 서로 다른 검사다.

## family와 분모

family는 특정 업무·관계·사건의 대조 묶음이다. 같은 문장의 어휘 치환을 다른 family로 나누지 않는다. 행동/화행 같은 일반 의미 범주는 양 split에 존재할 수 있으나 같은 시나리오 family나 텍스트는 교차하지 않는다. 기존 98개 본문과 정확 중복·문자 3-gram 유사도를 점검한다. 이 수치는 표절/어휘 중복 보호 장치이며 독립적인 의미 신규성이나 사람 독립성을 증명하지 않는다. 같은 AI 작성자의 문체·설계 편향이 양 split에 남아 있다.

## 사용과 동결

원본 98개·기존 주석·기존 코드·모델은 수정하지 않는다. validation은 이번 개발의 후보 선택 확인용이며 평가 후 수정에 사용하면 그 노출 사실을 기록한다. 이후 인간 독립 잠금 평가를 이 자료로 대체할 수 없다. 모델 실행은 이 작업에 포함하지 않는다. 질문/정책/기기/서빙·후보 수·통과 기준은 실험 담당자가 결과 보기 전에 별도 프로토콜로 고정한다.

데이터 파일과 본 기준, 검사 결과, 생성 스크립트의 SHA를 동결 영수증에 남긴다. 이후 라벨 수정이 필요하면 기존 영수증을 덮어쓰지 말고 이유·변경본·새 지문을 별도 기록한다. 최종 보고는 문장 수, 분리된 family 수, 각 위험/정상/미확정 및 필수중단 분모를 명시하고 허용 정답 일치를 실제 사기 정확도라고 부르지 않는다.
