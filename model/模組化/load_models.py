# load_models.py
import torch
import os

class YOLOv5Model:
    def __init__(self, model_path, yolov5_dir):
        self.model_path = model_path
        self.yolov5_dir = yolov5_dir

    def load(self):
        if not os.path.exists(self.model_path):
            print(f"❌ 模型不存在: {self.model_path}")
            return None
        return torch.hub.load(self.yolov5_dir, "custom", path=self.model_path, source="local")
