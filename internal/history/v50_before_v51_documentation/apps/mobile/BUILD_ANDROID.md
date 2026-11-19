# 의심계 v4.4 — Android 앱 빌드

이 묶음은 **컴파일되지 않은 Android Studio 프로젝트**입니다. 개발 환경에서 Android SDK와 Google Maven 저장소에 접근할 수 없어 APK를 만들거나 기기에서 실행해 보지 못했습니다.

## 필요한 것
- Node.js 20 이상, Android Studio (SDK Platform 35, JDK 21 포함)

## 빌드
```bash
npm ci                 # Capacitor 플러그인 (android/ 프로젝트가 node_modules를 참조합니다)
npx cap sync android   # www/ 웹 앱을 android/app/src/main/assets 로 복사
npx cap open android   # Android Studio에서 열기 → Run ▶ 또는 Build > Build APK(s)
```
명령줄: `cd android && ./gradlew assembleDebug` → `android/app/build/outputs/apk/debug/app-debug.apk`

## 설치하지 않고 바로 쓰기 (PWA)
웹 묶음(`IteraGuard_DoubtMeter_v4_4_web_pwa.zip`)을 HTTPS로 호스팅하거나 공유 링크로 연 뒤 Chrome 메뉴 → **앱 설치**를 누르면 홈 화면 앱으로 설치됩니다. 오프라인에서도 동작합니다.

모바일 앱은 모델 서버 연결을 지원하지 않습니다(로컬 판단 엔진만 사용).


## v4.8 개발 빌드

`python tools/build_apk.py --out apps/dist/IteraGuard_DoubtMeter_v4_8_android_debug.apk` (사전에 `apps/dist/web` 현재 자산 빌드 필요). 공개 디버그 키 서명, 인터넷 권한 없음. APK v2 서명과 콘텐츠 해시는 `python tools/verify_apk_v48.py <APK 경로>`로 확인하되, 설치·실행·스토어 승인 증거를 의미하지 않음.


## v4.9 개발 빌드

versionCode 49/versionName 4.9. 갱신된 웹 소스에서 새 디버그 APK를 생성하고 독립 파서·APK v2 서명·자산 일치를 검사한다. 실기기 설치는 별도다. APK는 INTERNET 권한이 없으며 Zoro GPU는 별도 PC에서 실행한다.
