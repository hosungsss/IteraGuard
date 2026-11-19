# 의심계 v5.1 Android 개발 APK

현재 debug APK는 `apps/dist/IteraGuard_DoubtMeter_v5_1_android_debug.apk`, 루트 사본은 `IteraGuard_DoubtMeter_v5.1.apk`다. versionCode51/versionName5.1, minSDK24/targetSDK34, permissions[]이며 GPU Zoro 모델을 포함하지 않는다. 기기 내 NLP와 Typed 서버는 별도다.

`python tools/build_distribution_v51.py`는 현재 웹 자산으로 PWA/APK/desktop을 만든다. APK 서명키는 메모리에만 생성하며 신규 개인키 파일을 소스에 저장하지 않는다. 복사본의 기존 debug 키도 배포 소스 밖으로 제외했다. 임시 debug 서명 때문에 빌드마다 바이트와 서명이 바뀔 수 있고 이전 APK 위 업데이트 설치의 서명 호환성을 보장하지 않는다.

현재 APK의 독립 파서·v2 서명·인증서·변조 사본 거부·manifest/DEX·PWA 자산 일치는 PASS다. 이는 Android 설치/실행 증명이 아니며 실기기는 NOT_RUN이다. 최종 FULL/별도 추출 영수증은 [상위 기록](<../../../Back Data/v5.1_구현기록_20261104/IMPLEMENTATION_RECEIPT.json>)을 따른다. 정적 검사 근거는 ../../internal/evidence/v51/apk_validation/apk_independent_verification.json이다.

이전에 포함된 Capacitor/Android Studio 안내와 v4.x 빌드 기록은 [보존 원문](../../internal/history/v50_before_v51_documentation/apps/mobile/BUILD_ANDROID.md)에 있다. 이 문서로 해당 과거 빌드나 Android Studio 실행을 새로 인증하지 않는다.
