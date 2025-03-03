import asyncio
import cv2

#RTSP流的協程
async def process_rtsp_stream(rtsp_url, window_name):
    cap = cv2.VideoCapture(rtsp_url)
    if not cap.isOpened():
        print(f"無法打開監視器 {window_name}")
        return
    
    while True:
        ret, frame = cap.read()
        if not ret:
            print(f"從 {window_name} 讀取影像失敗")
            break
        resized_frame = cv2.resize(frame, None, fx=0.2, fy=0.2)
        # 顯示每台監視器的影像
        cv2.imshow(window_name, resized_frame)
        
        # 按下q鍵退出
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    
    cap.release()



# 協程
async def main():
    rtsp_urls = [
        "rtsp://admin:644181@192.168.137.238/live/profile.1"
    ]
    tasks = []
    for i, rtsp_url in enumerate(rtsp_urls):
        task = asyncio.create_task(process_rtsp_stream(rtsp_url, f"監視器 {i+1}"))
        tasks.append(task)
    await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.run(main())
    cv2.destroyAllWindows()
