# work_assignment.py
import subprocess
import threading
import datetime
import time
import requests

API_BASE = "http://127.0.0.1:5000"
running_processes = {}

def stream_output(pipe, prefix):
    try:
        for line in iter(pipe.readline, ''):
            if not line:
                break
            print(f"{prefix}: {line.strip()}")
    except Exception as e:
        print(f"{prefix} 讀取錯誤: {e}")
    finally:
        pipe.close()

def is_in_time_range(time_ranges):
    now_time = datetime.datetime.now().time()
    today = datetime.datetime.now().strftime("%A")
    for entry in time_ranges:
        if entry.get("day") != today:
            continue
        try:
            start = datetime.datetime.strptime(entry["start"], "%H:%M").time()
            end = datetime.datetime.strptime(entry["end"], "%H:%M").time()
        except:
            continue

        if start <= end:
            if start <= now_time <= end:
                return True
        else:
            if now_time >= start or now_time <= end:
                return True
    return False

def fetch_projects_from_api():
    try:
        res = requests.get(f"{API_BASE}/projects")
        if res.status_code == 200:
            return res.json()
        else:
            print("❌ API 回傳錯誤", res.status_code)
            return []
    except Exception as e:
        print("❌ 無法連線到 API:", e)
        return []

def launch_projects():
    global running_processes
    projects = fetch_projects_from_api()
    current_ids = set()

    for project in projects:
        project_id = project["id"]
        current_ids.add(project_id)
        time_ranges = project["time_ranges"]

        if is_in_time_range(time_ranges):
            if project_id not in running_processes:
                print(f"[啟動] 專案 {project_id}（符合時間 & 星期）")
                process = subprocess.Popen(
                    ["python", "C:/Users/USER/OneDrive/文件/專題/模組化/main.py", "--id", project_id],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    encoding="utf-8",
                    bufsize=1
                )
                threading.Thread(target=stream_output, args=(process.stdout, f"[{project_id} stdout]"), daemon=True).start()
                threading.Thread(target=stream_output, args=(process.stderr, f"[{project_id} stderr]"), daemon=True).start()
                running_processes[project_id] = process
        else:
            if project_id in running_processes:
                print(f"[結束] 專案 {project_id} 超出時間或非今天，終止 process")
                process = running_processes[project_id]
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                del running_processes[project_id]

    for running_id in list(running_processes.keys()):
        if running_id not in current_ids:
            print(f"[終止] 專案 {running_id} 不在資料庫中，終止")
            running_processes[running_id].terminate()
            running_processes[running_id].wait()
            del running_processes[running_id]

if __name__ == '__main__':
    while True:
        try:
            launch_projects()
        except Exception as e:
            print("錯誤:", e)

