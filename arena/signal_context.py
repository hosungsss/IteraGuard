"""Bounded display guard for signal-only responses; never rewrites model scores.

This is not a general Korean parser. Unknown clauses prevent risk relaxation.
Existing Arena policy and its shadow observer are not modified.
"""
import re
from copy import deepcopy

VERSION = 'signal-context/1'
# Full-clause grammars, not keyword presence. Every clause must be accounted for.
WARNING = [
    r'(?:은행|금융기관|보안팀)은 (?:원격제어 앱 설치나 접속 코드 전달|원격제어 앱 설치|인증번호 전달|비밀번호 전달)을? ?요구하지 않습니다',
    r'(?:누구에게도 )?(?:문자 인증번호나 비밀번호|인증번호|비밀번호|OTP)를? ?알려주지 마세요',
    r'(?:원격제어 앱을 설치|접속 코드를 전달)하지 마세요',
    r'(?:이런|이러한) 요청을 받으면 거절하세요',
]
REPORT = [
    r'(?:어제|지난주) (?:사기범|상대방)이 (?:문자 인증번호|비밀번호)를 알려달라고 했지만 거절했습니다',
    r'(?:이미 )?신고를 마쳤습니다',
    r'(?:이미 )?신고했습니다',
]
INTRO = [r'보안 안내입니다', r'예방 안내입니다']

def full_any(clause, patterns):
    return any(re.fullmatch(pattern, clause) for pattern in patterns)

def scope_of(text):
    # Quoted instructional wrappers and any unrecognized clause retain the model result.
    clauses = [s.strip() for s in re.split(r'[.!?。\n]+', text) if s.strip()]
    if not clauses:
        return 'unresolved'
    warning = report = False
    for clause in clauses:
        if full_any(clause, WARNING): warning = True
        elif full_any(clause, REPORT): report = True
        elif not full_any(clause, INTRO): return 'unresolved'
    if warning and not report: return 'protective_warning'
    if report and not warning: return 'past_report'
    return 'unresolved'

def reconcile(text, result):
    result = deepcopy(result)
    original = {'grade': result['grade'], 'requested_action': deepcopy(result['requested_action'])}
    scope = scope_of(text)
    reasons = []
    if scope in ('protective_warning', 'past_report'):
        result['requested_action'] = {'id': 'no_request', 'label': '현재 민감 행동 요구 없음'}
        # A grammar match cannot certify safety. Conflicting risk becomes uncertainty, not green.
        if result['grade'] != 'green': result['grade'] = 'gray'
        reasons.append('BOUNDED_' + scope.upper())
    elif result['requested_action']['id'] == 'unknown' and result['grade'] == 'green':
        result['grade'] = 'gray'
        reasons.append('UNKNOWN_ACTION_NOT_NORMAL')
    elif result['grade'] == 'green' and result['requested_action']['id'] in {
        'share_auth_secret', 'grant_remote_access', 'pay_to_changed_account', 'pay_unlock_fee'
    }:
        result['grade'] = 'gray'
        reasons.append('SENSITIVE_ACTION_GREEN_CONFLICT')
    result['context_review'] = {
        'version': VERSION, 'scope': scope, 'reasons': reasons,
        'adjusted': original != {'grade': result['grade'], 'requested_action': result['requested_action']},
        'original': original, 'scores_source': 'ORIGINAL_MODEL_NOT_FINAL_GRADE',
        'safety_verified': False,
    }
    result['explanation'] = (
        '예방·금지 안내로 확인된 문장입니다. 위험 행동을 실행하라는 현재 요구와 구분했습니다. 신원이나 안전이 확인된 것은 아닙니다.' if scope == 'protective_warning' else
        '과거 요구를 거절하고 신고했다는 보고입니다. 과거에 언급된 행동을 현재 요구로 표시하지 않습니다. 신고 사실은 별도 확인이 필요합니다.' if scope == 'past_report' else
        '요청 행동이 불명확해 정상으로 확정하지 않습니다. 구체적인 요청 내용과 발신자를 확인하세요.' if 'UNKNOWN_ACTION_NOT_NORMAL' in reasons else
        '위험 신호 등급과 민감 행동 추정이 일치하지 않습니다. 행동 추정은 미확정이며 요청의 진위를 별도로 확인해야 합니다.' if reasons else
        '본문 기반 모델 판단입니다. 발신자 신원과 실제 안전 여부는 확인되지 않았습니다.'
    )
    return result
