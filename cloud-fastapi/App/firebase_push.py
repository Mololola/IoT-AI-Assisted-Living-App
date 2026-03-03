import firebase_admin
from firebase_admin import credentials, messaging
import os


def init_firebase():
    if not firebase_admin._apps:
        project_id = os.getenv("FIREBASE_PROJECT_ID")
        private_key = os.getenv("FIREBASE_PRIVATE_KEY")
        client_email = os.getenv("FIREBASE_CLIENT_EMAIL")

        if not all([project_id, private_key, client_email]):
            raise RuntimeError("Firebase environment variables not set")

        firebase_credentials = {
            "type": "service_account",
            "project_id": project_id,
            "private_key": private_key.replace("\\n", "\n"),
            "client_email": client_email,
            "token_uri": "https://oauth2.googleapis.com/token",
        }

        cred = credentials.Certificate(firebase_credentials)
        firebase_admin.initialize_app(cred)


def send_alert_notification(doc):
    try:
        message = messaging.Message(
            notification=messaging.Notification(
                title=f"{doc['severity'].upper()} Alert",
                body=doc["message"],
            ),
            data={
                "alert_id": str(doc["alert_id"]),
                "severity": doc["severity"],
                "rule_type": doc["rule_type"],
            },
            topic="alerts",
        )

        response = messaging.send(message)
        print("FCM sent:", response)

    except Exception as e:
        print("FCM error:", str(e))