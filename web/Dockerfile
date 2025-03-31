FROM node:14

# 設定工作目錄
WORKDIR /usr/src/app

# 複製你的 Web 源碼
COPY . .

# 安裝依賴
RUN npm install

# 開放端口
EXPOSE 80

# 啟動 Web 服務
CMD ["npm", "start"]
