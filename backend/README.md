# 后端服务安装和运行说明

## 安装依赖

```bash
pip install -r requirements.txt
```

## 运行服务

```bash
# 使用uvicorn运行
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

## API端点

1. `GET /` - 服务状态检查
2. `POST /video-stream` - 接收视频流
3. `WebSocket /ws/results` - 实时获取处理结果

## WebSocket通信协议

1. 客户端连接到`ws://localhost:8000/ws/results`
2. 客户端发送`start_processing`消息开始处理
3. 服务端通过WebSocket发送JSON格式的处理结果