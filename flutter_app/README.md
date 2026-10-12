# ZIRRO AI — Flutter Android prototype

This directory contains the first Flutter UI scaffold for ZIRRO AI.

## Current status

- [x] Dark, mobile-first chat UI
- [x] Account connection status card
- [x] Official OpenAI setup guide link
- [x] Composer and prototype-mode messages
- [ ] Android platform project files
- [ ] Android-specific local runtime adapter for Sign in with ChatGPT
- [ ] Secure, OS-backed credential storage
- [ ] Verified ChatGPT plan request and streaming response
- [ ] Device testing and release APK

**Important:** This is a UI prototype, not a working ChatGPT client yet. The Connect button does not sign in or request credentials; it explains the current setup state. Messages are not sent to an AI provider.

## Create the Android project on a device or computer with Flutter

Install Flutter and Android SDK, then run:

```bash
flutter create --platforms=android zirro_ai
```

Copy this folder's `lib/main.dart` and `pubspec.yaml` into the generated project, then run:

```bash
cd zirro_ai
flutter pub get
flutter run
```

To build an APK after testing:

```bash
flutter build apk --release
```

## ChatGPT account integration

Read the official OpenAI open-source plan-usage docs first:

- https://developers.openai.com/siwc/token-sharing-open-source
- https://developers.openai.com/siwc/token-sharing-open-source/sign-in
- https://github.com/openai/sign-in-with-chatgpt-devkit

The current official DevKit provides a local Node.js runtime and an Electron example. Flutter does not automatically provide this runtime. Android needs a carefully designed local adapter and OS-backed secure storage. Do not ask users for ChatGPT passwords or cookies, and do not store tokens on a shared server. Keep authentication and plan requests under the user's control and comply with OpenAI's terms.

## Design

ZIRRO uses a dark, glass-inspired visual direction with violet and teal accents. The prototype intentionally shows the disconnected state until a real integration is implemented and tested.
