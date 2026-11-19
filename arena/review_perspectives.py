"""Editorial criteria for existing choice questions, never independent votes."""

# The action question extracts the sender's demand even when its risk is unknown.
ACTION_REVIEW = (
    ' 수신자의 입장에서 누가 누구에게 무엇을 하라는지 쉬운 말로 바꿔 읽으세요. '
    '문자 속 지시와 사용자가 취할 보호 조치를 뒤바꾸지 마세요. '
    '조건 설명과 실제 이행 요구를 구별하고, 잘린 문장이나 모호한 대명사의 뜻을 지어내지 마세요.'
)

# These observations concern the message, not a diagnosis of either person.
SIGNAL_REVIEW = (
    ' 돈·정보·접근 권한이 어디로 가는지, 원래 상대와 다른 곳인지 본문의 근거를 살피세요. '
    '재촉만으로 위험을 정하지 마세요. 사실 확인을 막거나 기억을 부정하고 불이익을 내세워 '
    '행동을 강요하는 표현과 실제 요구가 연결되는지 보세요. 한 문장으로 가스라이팅이나 의도를 단정하지 마세요. '
    '약관·법적 의무를 내세우면 누가 어떤 조건에서 얼마를 요구하는지 살피세요. '
    '발신자의 주장만으로 위법성·채무·환급 권리를 확정하지 마세요. '
    '나이·장애·문체를 위험의 근거로 쓰지 말고, 모호한 정보는 미확인으로 두세요.'
)
