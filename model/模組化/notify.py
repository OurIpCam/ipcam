import cv2
import os
from datetime import datetime, timedelta
import mediapipe as mp
from deep_sort_realtime.deepsort_tracker import DeepSort
import requests

API_URL = "http://127.0.0.1:5000/event/abnormal/create"

JWT_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoxLCJ1c2VyX25hbWUiOiLlt6XlvIDkuKoiLCJsaW5lX2lkIjoieXV1dSIsInBpY3R1cmVfdXJsIjoiIn0.AhfdmNYddUxHZ8q8n34aO5abqgKUnbL3sHb6DPLjTPA"

def upload_abnormal_event(project_id, event_id, picture_url, timestamp):
    try:
        response = requests.post(API_URL, json={
            "token": JWT_TOKEN,
            "project_id": project_id,
            "event_id": event_id,
            "picture_url": picture_url.replace("\\", "/"),
            "occurred_at": timestamp.strftime("%Y-%m-%d %H:%M:%S")
        })
        if response.status_code != 200:
            print("事件上傳失敗：", response.text)
        else:
            print("✅ 事件上傳成功")
    except Exception as e:
        print("事件上傳錯誤：", str(e))

class FallDown:
    def __init__(self, frame, model, fall_history, tracker, project_name):
        self.frame = frame
        self.model = model
        self.fall_history = fall_history
        self.tracker = tracker
        self.project_name = project_name
        self.cooldown = timedelta(seconds=5)

    def detect_fall(self):
        results = self.model(self.frame)
        boxes = results.xyxy[0]
        timestamp = datetime.now()

        if boxes is None or len(boxes) == 0:
            return self.frame

        detections = []
        min_width, min_height = 20, 20
        max_aspect_ratio = 4.0
        min_aspect_ratio = 0.2

        for box in boxes:
            if len(box) < 6:
                continue
            x1, y1, x2, y2, conf, cls = box[:6].tolist()
            width = x2 - x1
            height = y2 - y1
            aspect_ratio = height / width if width > 0 else 0

            if int(cls) == 0 and width > min_width and height > min_height and min_aspect_ratio < aspect_ratio < max_aspect_ratio:
                detections.append(([x1, y1, width, height], conf, 'person'))

        tracks = self.tracker.update_tracks(detections, frame=self.frame)

        for track in tracks:
            if not track.is_confirmed():
                continue

            track_id = str(track.track_id)
            bbox = track.to_ltrb()
            x1, y1, x2, y2 = map(int, bbox)

            height = y2 - y1
            width = x2 - x1
            aspect_ratio = height / width if width > 0 else 0

            cv2.rectangle(self.frame, (x1, y1), (x2, y2), (0, 0, 255), 2)
            label = f"ID: {track_id}"
            cv2.putText(self.frame, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)

            if aspect_ratio < 1.2:
                last_saved_time = self.fall_history.get(track_id)
                if last_saved_time is None or (timestamp - last_saved_time) >= self.cooldown:
                    self.fall_history[track_id] = timestamp
                    save_folder = f"C:/Users/USER/OneDrive/文件/專題/模組化/{self.project_name}/images/fall"
                    os.makedirs(save_folder, exist_ok=True)
                    file_name = os.path.join(save_folder, f'{timestamp.strftime("%Y%m%d-%H%M%S")}-falldown.png')
                    cv2.imwrite(file_name, self.frame)

                    history_folder = f"C:/Users/USER/OneDrive/文件/專題/模組化/{self.project_name}/history"
                    os.makedirs(history_folder, exist_ok=True)
                    with open(os.path.join(history_folder, 'fall_history.txt'), 'a') as f:
                        f.write(f"{timestamp} - {track_id} detected fall\n")

                    upload_abnormal_event(self.project_name, "1", file_name, timestamp)

        return self.frame

class Entrance:
    def __init__(self, frame, model, entrance_history, tracker, project_name):
        self.frame = frame
        self.model = model
        self.entrance_history = entrance_history
        self.tracker = tracker
        self.project_name = project_name

    def detect_entrance(self):
        results = self.model(self.frame)
        boxes = results.xyxy[0]
        timestamp = datetime.now()
        detections = []

        min_width, min_height = 30, 30
        max_aspect_ratio = 3.0
        min_aspect_ratio = 0.3

        for box in boxes:
            if len(box) < 6:
                continue
            x1, y1, x2, y2, conf, cls = box[:6].tolist()
            width = x2 - x1
            height = y2 - y1
            aspect_ratio = height / width if width > 0 else 0

            if int(cls) == 0 and width > min_width and height > min_height and min_aspect_ratio < aspect_ratio < max_aspect_ratio:
                detections.append(([x1, y1, width, height], conf, 'person'))

        tracks = self.tracker.update_tracks(detections, frame=self.frame)

        for track in tracks:
            if not track.is_confirmed():
                continue

            track_id = str(track.track_id)
            bbox = track.to_ltrb()
            x1, y1, x2, y2 = map(int, bbox)

            cv2.rectangle(self.frame, (x1, y1), (x2, y2), (255, 0, 0), 2)
            label = f"ID: {track_id}"
            cv2.putText(self.frame, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)

            if track_id not in self.entrance_history:
                self.entrance_history[track_id] = True

                save_folder = f"C:/Users/USER/OneDrive/文件/專題/模組化/{self.project_name}/images/person_entrance"
                os.makedirs(save_folder, exist_ok=True)
                filename = os.path.join(save_folder, f'{timestamp.strftime("%Y%m%d-%H%M%S")}-entrance.png')
                cv2.imwrite(filename, self.frame)

                history_folder = f"C:/Users/USER/OneDrive/文件/專題/模組化/{self.project_name}/history"
                os.makedirs(history_folder, exist_ok=True)
                with open(os.path.join(history_folder, 'entrance_history.txt'), 'a') as f:
                    f.write(f"{timestamp} - person {track_id} entered\n")

                upload_abnormal_event(self.project_name, "2", filename, timestamp)

        return self.frame

class Leave:
    def __init__(self, frame, model, leave_history, tracker, project_name):
        self.frame = frame
        self.model = model
        self.leave_history = leave_history
        self.tracker = tracker
        self.leave_confirm_time = timedelta(seconds=3)
        self.project_name = project_name
        self.left_ids = set()

    def detect_leave(self):
        results = self.model(self.frame)
        boxes = results.xyxy[0]
        timestamp = datetime.now()
        detections = []

        min_width, min_height = 30, 30
        max_aspect_ratio = 3.0
        min_aspect_ratio = 0.3

        for box in boxes:
            if len(box) < 6:
                continue
            x1, y1, x2, y2, conf, cls = box[:6].tolist()
            width = x2 - x1
            height = y2 - y1
            aspect_ratio = height / width if width > 0 else 0

            if int(cls) == 0 and width > min_width and height > min_height and min_aspect_ratio < aspect_ratio < max_aspect_ratio:
                detections.append(([x1, y1, width, height], conf, 'person'))

        tracks = self.tracker.update_tracks(detections, frame=self.frame)
        current_ids = set()

        for track in tracks:
            if not track.is_confirmed():
                continue

            track_id = str(track.track_id)
            bbox = track.to_ltrb()
            x1, y1, x2, y2 = map(int, bbox)

            current_ids.add(track_id)
            cv2.rectangle(self.frame, (x1, y1), (x2, y2), (255, 0, 0), 2)
            label = f"ID: {track_id}"
            cv2.putText(self.frame, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)

        for track_id in current_ids:
            self.leave_history[track_id] = timestamp

        disappeared_ids = [track_id for track_id, last_seen in self.leave_history.items()
                           if track_id not in current_ids and (timestamp - last_seen) > self.leave_confirm_time]

        for track_id in disappeared_ids:
            if track_id not in self.left_ids:
                history_folder = f"C:/Users/USER/OneDrive/文件/專題/模組化/{self.project_name}/history"
                os.makedirs(history_folder, exist_ok=True)
                with open(os.path.join(history_folder, 'leave_history.txt'), 'a') as f:
                    f.write(f"{timestamp} - person {track_id} left\n")

                self.left_ids.add(track_id)
                # 建立一張離開時的快照圖
                leave_folder = f"C:/Users/USER/OneDrive/文件/專題/模組化/{self.project_name}/images/person_leave"
                os.makedirs(leave_folder, exist_ok=True)
                filename = os.path.join(leave_folder, f'{timestamp.strftime("%Y%m%d-%H%M%S")}-leave.png')
                cv2.imwrite(filename, self.frame)

                upload_abnormal_event(self.project_name, "3", filename, timestamp)

            del self.leave_history[track_id]

        return self.frame
