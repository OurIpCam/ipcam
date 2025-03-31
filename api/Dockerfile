# 使用官方 Python 基底映像
FROM python:3.9-slim

# 設定工作目錄
WORKDIR /app

# 複製本地的需求檔案進容器
COPY requirements.txt .

# 安裝 Python 依賴
RUN pip install --no-cache-dir -r requirements.txt

# 複製應用程式碼進容器
COPY . .

# 設定環境變數 (可選, 依據需要)
ENV FLASK_APP=ipcam.py
ENV FLASK_RUN_HOST=0.0.0.0 

# 開放 5000 端口 (Flask 預設端口)
EXPOSE 5000

# 設定容器啟動時執行 Flask 應用
CMD ["python", "ipcam.py"]
