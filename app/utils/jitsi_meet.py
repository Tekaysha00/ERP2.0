import uuid

def generate_meeting_link(class_id):
    # unique room name
    room_name = f"class-{class_id}-{uuid.uuid4().hex[:6]}"
    
    return f"https://meet.jit.si/{room_name}"