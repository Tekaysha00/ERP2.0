# app/utils/google_meet.py


# === COMMENTS ALL FOR TEMP === 
'''from google.oauth2 import service_account
from googleapiclient.discovery import build
import uuid

SCOPES = ['https://www.googleapis.com/auth/calendar']

creds = service_account.Credentials.from_service_account_file(
    'credentials.json', scopes=SCOPES)

service = build('calendar', 'v3', credentials=creds)


def create_meet_link(summary, start_time, end_time):
    event = {
        'summary': summary,
        'start': {
            'dateTime': start_time,
            'timeZone': 'Asia/Kolkata',
        },
        'end': {
            'dateTime': end_time,
            'timeZone': 'Asia/Kolkata',
        },
        'conferenceData': {
            'createRequest': {
                'requestId': str(uuid.uuid4())
            }
        }
    }

    event = service.events().insert(
        calendarId='primary',
        body=event,
        conferenceDataVersion=1
    ).execute()

    # ✅ SAFE CHECK (IMPORTANT)
    meet_link = None

    if 'conferenceData' in event:
        entry_points = event['conferenceData'].get('entryPoints', [])
        if entry_points:
            meet_link = entry_points[0].get('uri')

    # 🔥 FALLBACK
    if not meet_link:
        meet_link = "MEET_LINK_NOT_GENERATED"

    return meet_link'''