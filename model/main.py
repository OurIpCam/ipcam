# main.py
import argparse
from processor import VideoProcessor


parser = argparse.ArgumentParser()
parser.add_argument("--id", required=True, help="專案 ID")
args = parser.parse_args()

project_id = int(args.id[1:]) if args.id.startswith("P") else int(args.id)
print(f"🎬 啟動分析：專案 {project_id}")

processor = VideoProcessor(project_id)
processor.process()
