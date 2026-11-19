# 의심계 v4.4 — iPhone·iPad 앱 빌드

이 묶음은 **컴파일되지 않은 Xcode 프로젝트**입니다. iOS 앱은 macOS의 Xcode와 Apple 서명으로만 빌드·설치할 수 있어, 개발 환경(Linux)에서 빌드하거나 기기에서 실행해 보지 못했습니다.

## 필요한 것
- macOS, Xcode 16 이상, CocoaPods(`sudo gem install cocoapods`), Node.js 20 이상
- 실제 기기 설치: Apple ID(무료 계정은 7일 서명), 배포: Apple Developer Program

## 빌드
```bash
npm ci
npx cap sync ios       # www/ 복사 + pod install
npx cap open ios       # Xcode → Signing & Capabilities 에서 Team 선택 → Run ▶
```

## 설치하지 않고 바로 쓰기 (PWA)
Safari에서 웹 앱 링크를 열고 공유 → **홈 화면에 추가**를 누르면 전체 화면 앱처럼 실행됩니다. 오프라인에서도 동작합니다.

모바일 앱은 모델 서버 연결을 지원하지 않습니다(로컬 판단 엔진만 사용).
