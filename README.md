# 🏠 IoT & AI Assisted Living App

A cross-platform mobile application (Android & iOS) built with Flutter as part of a university 
group project. The app connects to an IoT sensor network deployed in an assisted living 
environment, providing caregivers with real-time monitoring, smart alerting, and remote 
actuator control.

---

## 📱 Features

- **Live Sensor Dashboard** — real-time sensor readings grouped by room
- **Custom History Charts** — hand-drawn charts visualising historical sensor data
- **Push Notifications** — Firebase Cloud Messaging for severity-based alerts
- **Alert Cards** — colour-coded by severity with one-tap acknowledgement
- **Actuator Control** — remote control of lights, blinds, and door locks
- **Routines & Exceptions** — caregivers schedule alert-suppression windows; 
  the Raspberry Pi polls the cloud every 15s and suppresses alerts automatically

---

## 🏗️ Architecture
```
Flutter App (Android/iOS)
        │
        ▼
REST API (14 endpoints — GET/POST/PUT/DELETE)
        │
        ▼
FastAPI Backend + MongoDB
        │
        ▼
Raspberry Pi (IoT sensor polling & actuator control)
```

**Flutter stack:**
- Riverpod — state management
- GoRouter — navigation with auth guard
- Repository pattern — clean separation of data and UI
- Optimistic UI updates
- Firebase Cloud Messaging — push notifications

---

## 🌿 Branches

| Branch | Description |
|---|---|
| `main` | Flutter mobile application |
| `FAST-API-Backend` | FastAPI + MongoDB backend server |
| `ML` | Machine learning components |

---

## 🚀 Getting Started

### Prerequisites
- Flutter SDK (>=3.0.0)
- Dart
- Android Studio or Xcode
- Firebase project configured

### Run the app
```bash
# Clone the repo
git clone https://github.com/Mololola/IoT-AI-Assisted-Living-App.git

# Install dependencies
flutter pub get

# Run on connected device or emulator
flutter run
```

### Backend (FAST-API-Backend branch)
```bash
git checkout FAST-API-Backend
pip install -r requirements.txt
uvicorn main:app --reload
```

---

## 👥 My Contribution

This was a group project. My responsibilities included:

- Full Flutter mobile app development (Android & iOS)
- REST API integration across all 14 endpoints
- Routines/exceptions scheduling feature
- Firebase push notification setup
- Resolving live integration issues during bench inspection
- Presented the working system at the Dragons' Den final pitch

---

## 🛠️ Tech Stack

`Flutter` `Dart` `Firebase` `Riverpod` `GoRouter` `FastAPI` `MongoDB` `Python` `Raspberry Pi`