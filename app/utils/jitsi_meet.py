import uuid

def generate_meeting_link(class_id, prefix="class"):
    # prefix = class / exam
    room_name = f"{prefix}-{class_id}-{uuid.uuid4().hex[:6]}"
    
    return f"https://meet.jit.si/{room_name}"