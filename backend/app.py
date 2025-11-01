from fastapi import FastAPI, WebSocket, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import asyncio
import json
import base64
from typing import Dict, List
import time

app = FastAPI()

# 添加CORS中间件以允许前端访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 在生产环境中应该指定具体的域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 存储活跃的WebSocket连接
active_connections: List[WebSocket] = []

# 模拟视频处理结果
async def simulate_video_processing(websocket: WebSocket):
    """模拟视频流处理并发送结果"""
    try:
        for i in range(100):  # 模拟100次处理结果
            # 模拟处理时间
            await asyncio.sleep(1)
            
            # 构造处理结果
            result = {
                "timestamp": time.time(),
                "frame_id": i,
                "detections": [],
                "status": "processing"
            }
            
            # 模拟不同的检测结果
            if i % 10 == 0:
                result["detections"].append({
                    "type": "person",
                    "confidence": 0.85,
                    "bbox": [100, 100, 200, 300]
                })
                
            if i % 25 == 0:
                result["detections"].append({
                    "type": "vehicle",
                    "confidence": 0.92,
                    "bbox": [50, 150, 300, 250]
                })
                
            if i % 50 == 0:
                result["status"] = "alert"
                result["message"] = f"检测到异常行为，置信度: {0.8 + (i % 20) / 100}"
            
            # 发送结果到前端
            await websocket.send_text(json.dumps(result))
            
    except Exception as e:
        print(f"处理视频流时出错: {e}")

@app.get("/")
async def root():
    return {"message": "视频处理后端服务已启动"}

@app.post("/video-stream")
async def receive_video_stream():
    """接收视频流的端点"""
    # 这里应该实现实际的视频流接收逻辑
    return {"message": "视频流接收端点已准备就绪"}

@app.websocket("/ws/results")
async def websocket_results(websocket: WebSocket):
    """WebSocket端点，用于实时发送处理结果"""
    await websocket.accept()
    active_connections.append(websocket)
    
    try:
        # 等待前端发送开始处理的信号
        data = await websocket.receive_text()
        if data == "start_processing":
            await simulate_video_processing(websocket)
    except Exception as e:
        print(f"WebSocket连接错误: {e}")
    finally:
        active_connections.remove(websocket)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)