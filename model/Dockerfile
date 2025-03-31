FROM python:3.8

# 設定工作目錄
WORKDIR /usr/src/app

# 複製你的模型源碼
COPY . .

# 安裝依賴
RUN pip install -r requirements.txt

# 設定容器啟動命令
CMD ["python", "model_server.py"]
