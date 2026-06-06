import firebase_admin
from firebase_admin import credentials

cred = credentials.Certificate(
    "erp-1-e9e9f-firebase-adminsdk-fbsvc-3a66db653c.json"
)

firebase_admin.initialize_app(cred)

print("Firebase Connected")