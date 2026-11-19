# 실측 없는 수치의 발표를 차단하는 평가 명세

## 데이터 계약

JSONL에서 줄마다 다음 필드를 모두 제공한다. `case_id`, `scenario_family`, `split`, `gold_risky`, `predicted_action`, `source_mode`. 각 `case_id`는 전역 유일하며 `scenario_family`는 development/calibration/locked 중 하나의 split에서만 등장한다. `gold_risky`는 사람이 정의한 정답 bool이다. source_mode는 FIXTURE/MOCK/MODEL_RESPONSE_UNATTESTED/CHECKPOINT_VERIFIED 중 하나다. 마지막 모드는 사용자가 명시했다고 실제 체크포인트가 증명되는 게 아니므로 실행 로그 별도 검증을 요구한다.

## 원칙

- 단위는 동일 프로젝트에서 공통으로 정의한 발화/대화 단위여야 하며 섞으면 지표 해석이 불가능하다.
- 사기 경고 누락: 위험 gold에서 `NO_STRONG_SIGNAL`을 낸 비율. 이 지표만으로 실제 피해 미탐률을 주장하지 않는다.
- 정상 업무 중단: 정상 gold에서 `PAUSE_AND_VERIFY`를 낸 비율. `CAUTION`과 `ASK_HUMAN`도 업무부담이 될 수 있으므로 따로 보고한다.
- 보류율: 전체에서 `ASK_HUMAN` 비율. 독립 정답률과 혼합하지 않는다.
- 표본 수가 0인 분모는 `null`로 표시하며 0%라고 꾸미지 않는다.
- Wilson 95% 구간은 단순 이항 근사이며 샘플 대표성이나 독립성을 보증하지 않는다.
- 예제·개발셋으로 정한 임계값과 화면 데모로 선택한 카드는 잠금셋의 일부가 될 수 없다.

## 실행

`python dmsg/scripts/evaluate_annotations.py /path/to/independently_annotated.jsonl`

파일이 없으면 NOT_RUN 상태다. 이 코드가 출력하는 수치는 제공한 주석 파일의 계산값일 뿐, 한국어 사기 실세계 정확도나 모델의 진품 인증이 아니다. 불확실성 평가(Brier/ECE), 텍스트 정답·선택확률 측정, Zoro-1 실제 실행은 별도 프로토콜이 필요하다.
