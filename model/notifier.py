# notifier.py
from notify import FallDown,Entrance,Leave

def handle_notifications(frame, model, config, histories, tracker, project_id):
    notifications = config.get("notifications", [])
    try:
        if "fall_detection" in notifications:
            frame = FallDown(frame, model, histories["fall"], tracker, project_id).detect_fall()
        if "entrance_detection" in notifications:
            frame = Entrance(frame, model, histories["entrance"], tracker, project_id).detect_entrance()
        if "leave_detection" in notifications:
            frame = Leave(frame, model, histories["leave"], tracker, project_id).detect_leave()
    except Exception as e:
        print(f"⚠️ 通知處理錯誤: {e}")
    return frame
