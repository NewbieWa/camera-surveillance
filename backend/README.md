# 后端 - 摄像头监控系统

这是摄像头监控系统的后端组件，使用 Python 和 FastAPI 构建。它处理视频处理、物体检测、AI 分析，并为前端提供 API。

## 架构

后端结构如下：

- `main.py`: 主应用程序入口点，包含 FastAPI 路由
- `src/camera_surveillance/`: 核心模块
  - `coordinator/`: 协调和管理视频处理任务
  - `models/`: 数据模型和架构定义
  - `processor/`: 视频和音频处理模块
  - `tools/`: 实用函数
- `ffmpeg_tools/`: 使用 FFmpeg 的视频处理工具
- `demo/`: 示例实现和测试脚本
- `doc/`: 文档和示例数据格式
- `test/`: 单元和集成测试

## 功能特性

- 实时视频处理和分析
- 使用 YOLO 模型进行物体检测
- 音频转录功能
- 多摄像头支持
- 视频块处理
- API 端点用于前端通信

## 文档和数据格式

### 1. transcribe_response.json
这是 speech_processor 模块的返回格式示例，包含音频转录的结果及相关信息。

### 2. transcription.json
这是从 transcription_url 下载后的格式，包含转录文本的时间戳和其他元数据。

## 视频处理流程

后端处理视频的完整流程如下：

### 1. 视频接收流程
后端通过 WebSocket 端点 `/ws/live-video/{device_id}` 接收来自前端的视频数据。前端使用 RecordRTC 库将视频流按时间分块（通常是60秒一个块），然后通过 WebSocket 发送到后端。

### 2. 视频合并流程
后端接收视频块并将其存储在临时目录中，当积攒到一定数量的视频块时，使用 FFmpeg 的 concat 协议将多个视频块合并成一个完整的视频文件，合并后的视频转码为 MP4 格式以确保兼容性。

### 3. 视频分析流程
合并完成后，启动子协程处理合并的视频文件：
- 使用 VideoStreamProcessor 提取视频中的音频
- 使用 SpeechProcessor 对音频进行转录
- 使用 KeywordDetector 检测关键词（如"车号确认"、"铁鞋设置"、"铁鞋撤除"等）
- 根据检测到的关键词，调用相应的模型进行识别：
  - VehicleNumberRecognizer：识别车辆编号
  - AntiRollingModel：防遛确认
  - RemoveRollingModel：撤遛确认
- 处理结果通过 WebSocket 发送回前端

### 4. 工作空间管理
为每个设备创建独立的工作空间（workspace/{device_id}_{timestamp}），工作空间包含视频块、提取的音频、处理结果等文件，处理完成后保留工作空间以供后续查看。

整个流程是：前端录制 → 按时间分块 → WebSocket传输 → 后端接收 → 暂存 → FFmpeg合并 → 音频提取 → 语音转录 → 关键词检测 → AI模型分析 → 结果返回前端。

## 运行后端

### 使用启动脚本：
```bash
./start.sh
```

### 使用 uv 运行：
```bash
cd backend
uv run main.py
```

### 使用 uvicorn 直接执行：
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 直接运行主 Python 文件：
```bash
python main.py
```

## 配置

后端可以通过环境变量或主应用程序文件进行配置。主要配置选项包括：
- API 端口和主机设置
- 视频处理参数
- AI 模型路径
- 摄像头源配置