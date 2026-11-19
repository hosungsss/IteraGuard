# 의심계 v4.9 — v4.8 동일 형식 반영·최종 검증

2026-11-04. 이번 개정은 기존 v4.9의 ZIP 중심 전달을 v4.8처럼 펼쳐진 폴더·앱 배포물·스킬 별칭·통합 문서 형식으로 완성한다. 기존 파일은 Drive ID를 유지해 갱신하고, v4.8 원본은 수정하지 않는다.

## 형식 대응

| v4.8 형식 | 이번 v4.9 |
|---|---|
| apps / dmsg / docs / tools / models / evaluation / linkguard / tests_data / tests_linkguard | 같은 폴더를 실제 Drive 하위 폴더로 펼쳐 저장 |
| internal | 새 합성 실행·빌드·검증 근거만 internal/evidence/v49에 저장. 비공개 수신 원문·실험 DB·자격증명 제외 |
| dmsg.skill / dmsg.zip / dmsg_v4.8.skill / dmsg_v4.8.zip | dmsg.skill / dmsg.zip / dmsg_v4.9.skill / dmsg_v4.9.zip, 현재 내용 동일 |
| IteraGuard_DoubtMeter_v4.8.apk | 갱신된 소스에서 새로 빌드한 IteraGuard_DoubtMeter_v4.9.apk |
| apps/dist의 PWA | 새 IteraGuard_DoubtMeter_v4_9_web_pwa.zip |
| all.md / MASTER_HANDOFF_PROMPT.md / Technical Audit / MANIFEST | v4.9 현재 상태와 검사 결과로 작성 |

과거 v3.9~v4.8의 모든 이름을 v4.9로 바꿔 복제하지 않는다. 이전 버전은 원본 폴더에 보존한다. 새 arena/experiments/integration/tests_v49/vendor는 실제 기능 구현에 필요한 추가 폴더다.

## 요청한 세 가지 반영

1. **로컬 Zoro:** RTX 3060에서 실제 공개 Zoro를 로드해 경고·직접 요청·인용·혼합 절 4건을 최종 서버/proxy로 재실행했다. 결과는 UNCLEAR / DIRECT_REQUEST / UNCLEAR / DIRECT_REQUEST였다. PC 화면용 경로와 SQLite 작업 version 1→2·관측·재조회를 확인했다. 근거: real_zoro_final.json. 이는 Zoro-1 판단 헤드·정확도 검증이 아니다.
2. **문제 수정:** 종료 토큰 248044/248046, 출력 전체 레이블 검증, SQLite 연결 close, Windows 콘솔 인코딩, 입력 편집 후 오래된 결과 폐기·추론 중 입력 잠금, 응답 자료형·중복 JSON·유한 지연·모드 검사, 잘못된 backend 응답의 502 처리, PRD 사본 동기화를 반영했다. 정상 경고문이 UNCLEAR인 의미 판단 한계는 해결됐다고 주장하지 않는다.
3. **최종 통합:** PRD·System Prompting·고정 이름 dmsg 스킬·기존 앱/정책·실행 도구·빌드 도구·검증 기록을 통합했다. PC GPU 모듈을 모바일에 내장했다고 표시하지 않는다.

## 새 APK/PWA 검사

APK versionCode 49 / versionName 4.9를 독립 androguard 파서로 확인했다. apksigtool과 별도 검증 코드에서 APK v2 서명·내용 digest·인증서 공개키 일치를 확인했다. DEX 구조, ZIP CRC, 저장 항목 정렬, 갱신된 웹 자산과 APK 자산 일치를 검사했다. PWA ZIP도 CRC·버전·화면 안내를 확인했다.

APK는 공개 디버그 키를 사용하는 **개발 빌드**이며 INTERNET 권한이 없다. Android 실기기 설치/실행은 NOT_RUN이다. 공개 Zoro는 별도 PC GPU 서버에서 실행하고 앱은 오프라인 분석 및 PC 검증 안내를 제공한다. 새 네이티브 Windows/macOS/iOS 바이너리는 빌드하지 않았다.

## 최종 로컬 결과

- 기존 제품 회귀 325개 PASS, 신규 회귀 42개 PASS.
- Python/JavaScript 정책 일치 24,488개 PASS. 모델 정확도 표본 수가 아니다.
- 실제 공개 Zoro 생성 4건과 PC 서버 연결 PASS_EXECUTION_ONLY.
- 확인 작업 저장·관측·재판단·재조회 PASS. 이 경로의 Typed 모델 미연결은 명시한다.
- 새 PWA 검사 PASS, 새 APK 구조·서명 검사 PASS_DEVICE_NOT_RUN.
- 스킬 별칭 동일성·배포 파일 manifest·전체 ZIP은 배포 생성 후 별도 검사한다.
- Zoro-1 헤드 추론·독립 정확도·Android 실기기 실행은 NOT_RUN.

로컬 최종 상태: internal/evidence/v49/FINAL_VALIDATION.json. 압축 해제 재검증과 Drive 업로드 후 폴더 목록·크기·전체 ZIP 왕복 SHA-256은 별도 DELIVERY_RECEIPT에 기록한다. 클라우드 저장 완료를 로컬 테스트만으로 주장하지 않는다.
