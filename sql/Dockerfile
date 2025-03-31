
FROM mysql:8.0

# 設定 MySQL 環境變數
ENV MYSQL_ROOT_PASSWORD=00000000
ENV MYSQL_DATABASE=ipcam

# 複製 SQL 初始化檔案
COPY ./init_db.sql /docker-entrypoint-initdb.d/
