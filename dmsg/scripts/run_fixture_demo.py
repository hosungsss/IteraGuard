"""A clearly-labeled synthetic fixture demonstration. No real model inference."""
import json
from policy import Action, EvidenceKind, EvidenceSpan, Mode, ModelStatus, Observation, evaluate


def make_sample(text, search=None, kind=None, unavailable=False):
    spans = ()
    if search is not None:
        start = text.index(search)
        spans = (EvidenceSpan(kind, start, start + len(search), search),)
    return Observation(text, spans=spans, mode=Mode.FIXTURE,
                       model_status=(ModelStatus.UNAVAILABLE if unavailable else ModelStatus.OK))


def main():
    cases = [
        make_sample("예금 만기일 안내입니다. 지점에 방문하세요."),
        make_sample("수사관입니다. 범죄 연루 계좌를 조사합니다."),
        make_sample("지금 바로 이 계좌로 송금하세요.", "송금하세요", EvidenceKind.MONEY_TRANSFER),
        make_sample("지금 이 원격제어 앱을 설치하세요.", "원격제어 앱을 설치", EvidenceKind.REMOTE_ACCESS),
        make_sample("문자 링크를 클릭해 조회하세요.", "링크를 클릭", EvidenceKind.UNVERIFIED_LINK),
        make_sample("정보가 부족합니다.", unavailable=True),
    ]
    for i, obs in enumerate(cases, 1):
        decision = evaluate(obs)
        assert decision.engine_mode is Mode.FIXTURE
        print(json.dumps({"scenario": i, "engine_mode": "FIXTURE / NOT LIVE ZORO",
                          "action": decision.action.value,
                          "reason_code": decision.reason_code,
                          "explanation": decision.template_ko}, ensure_ascii=False))

if __name__ == "__main__":
    main()
