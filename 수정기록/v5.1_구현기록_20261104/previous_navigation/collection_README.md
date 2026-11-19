# IteraGuard 버전 모음 — 현재 작업 기준 v5.0

정리일: 2026-11-04 KST. 최신 제품 소스는 **[[v5.0] IteraGuard_DoubtMeter](%5Bv5.0%5D%20IteraGuard_DoubtMeter/README.md)** 이다. 기존 버전 폴더·Package·Back Data 원문은 보존했다.

**v5는 실행·상태관리·배포 기반을 수정하고 검증한 개발 후보다. 정상 과보류와 일부 필수중단 누락 등 핵심 판단 성능 개선은 미완료다.** 최종 제출본이나 독립 성능 검증 완료본으로 표시하지 않는다.

## 바로 열기

- [현재 상태](%5Bv5.0%5D%20IteraGuard_DoubtMeter/CURRENT_PROJECT_STATE.md) / [미해결 과제](%5Bv5.0%5D%20IteraGuard_DoubtMeter/docs/V50_OPEN_ISSUES.md)
- [전체 이해 문서](%5Bv5.0%5D%20IteraGuard_DoubtMeter/all.md) / [전체 문서 안내](%5Bv5.0%5D%20IteraGuard_DoubtMeter/docs/00_DOCUMENT_MAP.md)
- [상세 변경 원장](%5Bv5.0%5D%20IteraGuard_DoubtMeter/internal/VERSION_LEDGER.md) / [구현·실험 보고](%5Bv5.0%5D%20IteraGuard_DoubtMeter/docs/V50_IMPLEMENTATION_REPORT.md)
- [v5 전체 ZIP](IteraGuard_DoubtMeter_v5_0_FULL_CANDIDATE.zip) / [배포 위치·해시](LATEST_VERSION.json)
- [정리 기록](Back%20Data/v5.0_%EC%A0%95%EB%A6%AC%EA%B8%B0%EB%A1%9D_20261104/ORGANIZATION_REPORT.md)

전체 ZIP은 소스 폴더 바깥에 두었다. 소스 manifest에 FULL 자체가 순환 포함되는 것을 피하기 위한 배치다. v5 폴더 안의 APK/PWA와 dmsg.skill은 해당 v5 배포물이다. 이 모음 루트의 기존 dmsg.skill/dmsg_v4.x.skill은 과거 사본이므로 최신 스킬은 v5 폴더 안에서 선택한다.

## 폴더별 역할

| 위치 | 역할과 현재 읽는 기준 |
|---|---|
| [v5.0] IteraGuard_DoubtMeter | 이후 개발 기준 소스·명세·실험 근거·앱 배포물 |
| v3.x~v4.9 버전 폴더 | 역사 원본. 일부 펼친 트리는 빠진 파일이 있어 완전 릴리스로 단정하지 않음 |
| Package | 별도 실험 키트 v1.x 계보. 제품 v5 버전 번호와 다름 |
| Back Data | 날짜가 있는 준비/계획/검토 기록. 이번 정리 보고를 별도 하위 폴더에 추가 |
| Trida_의심계_학습교재_제1판_20261104 | 당시 v4.9 교육 자료. 영수증상 PDF/HTML/START_HERE/ZIP이 이 로컬 폴더에는 없음 |
| iteraguard / TRILLION_HACKATHON_Team_Guide.md | CallShield/Factory/SRE 별도 프로토타입 계보. 가이드 경로/로컬 모듈 일부가 빠져 완전 실행본으로 표시하지 않음 |

## 버전 흐름

아래는 해당 버전 문서에 기록된 흐름의 요약이다. 이번 정리에서 구버전을 실행하거나 당시 테스트/외부 조건을 재검증한 것은 아니다. 상세 근거는 v5의 internal/history와 internal/organization에 보존했다.

| 버전 | 기록된 주요 범위 |
|---|---|
| v3.1.0 | 합성 문장 4상태 정책, 근거 출처, 세션 중복/버전 보호 |
| v3.4 | all.md 진입점, 최신 턴 ACK, 감사/HTTP 출처 보호 |
| v3.5 | 모델 6문항 Typed 어댑터, X-Ray, 지연 관측 |
| v3.6 | speech/context 충돌 guard, 응답/동의 계약 |
| v4.0 | PAYLOCK HMAC 감사와 현재 사건 결합, ZIP 검증 경계 |
| v4.1 | 재시도 버전/TTL 결합, 전달용 ASCII FULL/CORE |
| v4.2 | 모델 score/echo 계약 및 절 단위 충돌 검사 |
| v4.3 | Python/JS 정책 엔진, 웹/데스크톱/모바일 산출물 |
| v4.4 | Android debug APK와 정적 검증; 실기기와 구분 |
| v4.5 | 기기 내 KoELECTRA NLP, informational/q_evidence 확장 |
| v4.6 | NLP 멀티태스크 학습; 평가셋별 개선/악화 혼재 |
| v4.7 | 보류 분석·DRA 후보, LinkGuard/APK 정적 분석 |
| v4.8 | 도메인 텍스트 위험 검토와 Zoro 실행 게이트 |
| v4.9 | 아레나의 현재 턴/세션/관측 흐름, 명세 형식 정리 |
| v5.0 | 공통 실행 계약·세션 종료/재개·디버깅·실제 Typed 실험; 판단 성능 개선 미완료 |

## 이번 정리의 범위

정리 전 Markdown 360개, 서로 다른 내용 159개를 인벤토리화했다. 파일별 전문/부분/구조 검토 범위는 감사 JSON에 있다. v4.9 FULL의 Markdown 69개 중 펼친 v4.9에서 빠진 30개를 확인했고, 현재 v5에는 69개 경로가 모두 보존돼 있다. v4.9 FULL에도 없는 상세 원장은 추정해 만들지 않았다.

최초 검증 v5 전체 패키지를 검증 후 펼치고, 현행 문서·문서 안내·미완료 목록·원장을 정리했다. 실행 코드·질문·정책·모델·APK/PWA는 이번 작업에서 변경하지 않았다. 이전 workspace 및 최초 v5 ZIP은 남겨 두었다. 현재 브라우저 서버는 이전 workspace에서 계속 실행될 수 있으며 이번 문서 정리로 재시작하지 않았다.

독립 인간 평가, Android 실기기, 세부 팀 합의와 행사 공식 조건 확인은 별도 미완료다. AI 초안·Typed 호출·mock/replay·독립 평가·실기기 검증은 각각 구분해 기록한다.

## v5.1 다음 계획

[v5.1 미해결 문제 개선 계획](<Back%20Data/v5.1_%EA%B0%9C%EC%84%A0%EA%B3%84%ED%9A%8D_20261104/V51_IMPLEMENTATION_PLAN_20261104.md>)을 작성했다. 현재는 계획 단계이며 최신 실행 버전은 v5.0이다.
