# DiveOps Staff Chat - Android App

A native Android app for DiveOps staff to receive push notifications and respond to customer chat messages.

## Features

- Staff authentication via email/password
- Real-time conversation list
- Chat messaging with customers
- Push notifications with sound for new messages
- Message status indicators (sent/delivered/read)

## Setup Instructions

### 1. Firebase Setup

1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Create a new project or select existing project
3. Add an Android app with package name: `com.diveops.chat`
4. Download `google-services.json` and place it in `app/` directory
5. Enable Firebase Cloud Messaging in the Firebase Console

### 2. Server Configuration

On the Django server, you need to configure Firebase Admin SDK:

1. In Firebase Console, go to Project Settings > Service Accounts
2. Click "Generate new private key" to download the credentials JSON file
3. Set the environment variable on your server:
   ```bash
   export GOOGLE_APPLICATION_CREDENTIALS="/path/to/firebase-credentials.json"
   ```

### 3. Build Configuration

For production builds, update the `BASE_URL` in `app/build.gradle.kts`:

```kotlin
buildConfigField("String", "BASE_URL", "\"https://your-domain.com\"")
```

### 4. Build the App

```bash
# Debug build (connects to localhost:8000 via Android emulator)
./gradlew assembleDebug

# Release build
./gradlew assembleRelease
```

### 5. Install on Device

```bash
# Install debug build
adb install app/build/outputs/apk/debug/app-debug.apk

# Install release build
adb install app/build/outputs/apk/release/app-release.apk
```

## Project Structure

```
app/src/main/java/com/diveops/chat/
├── DiveOpsApp.kt              # Application class
├── MainActivity.kt            # Main entry point with navigation
├── api/
│   ├── ApiClient.kt          # Retrofit client setup
│   └── ApiService.kt         # API endpoint definitions
├── data/
│   ├── AuthRepository.kt     # Authentication & token management
│   └── ChatRepository.kt     # Chat data operations
├── fcm/
│   └── ChatFirebaseMessagingService.kt  # Push notification handling
└── ui/
    ├── theme/
    │   └── Theme.kt          # Material 3 theme
    ├── LoginScreen.kt        # Login UI
    ├── ConversationsScreen.kt # Conversation list UI
    └── ChatScreen.kt         # Chat thread UI
```

## API Endpoints Used

- `POST /api/mobile/login/` - Staff authentication
- `POST /api/mobile/fcm/register/` - Register FCM device token
- `POST /api/mobile/fcm/unregister/` - Unregister FCM device token
- `GET /api/mobile/conversations/` - List all conversations
- `GET /api/mobile/conversations/{id}/messages/` - Get messages for conversation
- `POST /api/mobile/conversations/{id}/send/` - Send a message

## Requirements

- Android Studio Hedgehog (2023.1.1) or later
- Android SDK 34
- Kotlin 1.9.20
- Minimum Android version: 8.0 (API 26)

## Notes

- Debug builds connect to `http://10.0.2.2:8000` (Android emulator localhost)
- Release builds connect to production server URL
- FCM tokens are automatically registered on login and unregistered on logout
- Push notifications include sound and vibration
