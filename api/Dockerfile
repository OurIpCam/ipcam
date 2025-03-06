# 使用 Python 3.9 作為基礎映像檔
FROM python:3.9-slim

# 設定工作目錄
WORKDIR /app

# 複製程式碼到容器內
COPY . .

# 安裝指定版本的 Flask
RUN pip install flask==2.0.2

# 開放 Flask 需要的端口
EXPOSE 5000

# 設定環境變數
ENV FLASK_APP=api.py
ENV FLASK_RUN_HOST=0.0.0.0

# 啟動 Flask 應用
CMD ["flask", "run"]
