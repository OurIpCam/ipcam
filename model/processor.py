# processor.py
import cv2
import time
import requests
from load_models import YOLOv5Model
from notifier import handle_notifications
from deep_sort_realtime.deepsort_tracker import DeepSort

YOLOV5_DIR = "C:/Users/USER/OneDrive/文件/專題/模組化/models/yolov5"
API_BASE = "http://127.0.0.1:5000"  # 替換成你 API 的位置

class VideoProcessor:
    def __init__(self, project_id):
        self.project_id = project_id
        self.last_config = {}
        self.model = None
        self.tracker = DeepSort(max_age=30)
        self.histories = {"fall": {}, "entrance": {}, "leave": {}}
        self.last_check_time = 0
        self.recheck_interval = 5

    def reload_config(self):
        try:
            response = requests.get(f"{API_BASE}/project/{self.project_id}")
            if response.status_code != 200:
                print("❌ 查無此專案")
                return None
            project = response.json()
            return {
                "model_path": project["model_path"],
                "rtsp_url": project["rtsp_url"],
                "notifications": project["notifications"]
            }
        except Exception as e:
            print(f"❌ API 錯誤: {e}")
            return None

    def has_config_changed(self, new):
        return new != self.last_config

    def process(self):
        cap = None
        while True:
            now = time.time()
            if now - self.last_check_time > self.recheck_interval:
                new_config = self.reload_config()
                if not new_config:
                    continue
                if self.has_config_changed(new_config) or self.model is None:
                    self.model = YOLOv5Model(new_config["model_path"], YOLOV5_DIR).load()
                if cap is None or not cap.isOpened() or self.last_config.get("rtsp_url") != new_config["rtsp_url"]:
                    if cap:
                        cap.release()
                    cap = cv2.VideoCapture(new_config["rtsp_url"])
                self.last_config = new_config
                self.last_check_time = now

            ret, frame = cap.read()
            if not ret:
                print("⚠️ 攝影機錯誤，重連中...")
                cap.release()
                cap = cv2.VideoCapture(self.last_config["rtsp_url"])
                continue

            frame = cv2.resize(frame, (800, 600))
            frame = handle_notifications(frame, self.model, self.last_config, self.histories, self.tracker, self.project_id)
            cv2.imshow("監控畫面", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        cap.release()
        cv2.destroyAllWindows()
