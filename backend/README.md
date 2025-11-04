# 外勤作业智能分析系统后端服务

## 系统架构

本系统是一个基于FastAPI的后端服务，用于处理实时视频流并进行智能分析。主要功能包括：

1. 接收实时视频流
2. 提取音频并进行语音识别（集成阿里云百炼语音识别服务）
3. 识别特定关键词（车号确认、防遛设置、撤遛设置等）
4. 在关键词识别后提取相关帧图像
5. 使用AI模型进行图像分析
6. 将结果通过WebSocket实时回传给前端

## 目录结构

```
backend/
├── main.py                 # 主服务文件
├── requirements.txt        # 依赖包列表
├── core/                   # 核心模块
│   ├── __init__.py
│   ├── workspace.py        # 工作空间管理
│   ├── video_processor.py  # 视频处理模块
│   ├── audio_transcriber.py # 音频转文字模块
│   ├── keyword_detector.py # 关键词检测模块
│   ├── frame_extractor.py  # 图像帧提取模块
│   ├── vehicle_recognizer.py # 车辆编号识别模块
│   ├── local_models.py     # 本地模型接口
│   └── result_reporter.py  # 结果报告模块
└── demo/                   # 示例代码
    ├── bailianParaformer.py  # 百炼语音识别示例
    └── bailianQwen3vl.py     # 阿里云视觉大模型示例
```

## 安装依赖

```bash
cd backend
pip install -r requirements.txt
```

## 运行服务

```bash
cd backend
python main.py
```

服务将在 `http://localhost:8000` 启动。

## API接口

### WebSocket接口

- `ws://localhost:8000/ws/results` - 用于接收处理结果的WebSocket连接

### HTTP接口

- `POST /video-stream/{device_id}` - 接收指定设备的视频流
- `POST /process-video/{device_id}` - 处理指定设备的视频流
- `GET /` - 服务状态检查

## 环境变量

需要设置以下环境变量：

- `DASHSCOPE_API_KEY` - 阿里云百炼平台的API密钥
- `MAX_CONCURRENT_MODELS` - 最大并发模型调用数（默认为5）

## 处理流程

1. 前端通过WebSocket连接到 `/ws/results` 端点
2. 前端调用 `/video-stream/{device_id}` 创建设备的工作空间
3. 系统开始接收并处理视频流
4. 系统提取音频并使用百炼语音识别服务转文字
5. 系统检测关键词并根据关键词类型执行相应操作：
   - 车号确认：提取相关帧并使用阿里云视觉大模型识别车辆编号
   - 防遛设置：提取相关帧并使用本地模型A判断
   - 撤遛设置：提取相关帧并使用本地模型B判断
6. 系统将处理结果通过WebSocket实时发送给前端

## 改进功能

### 1. 并行模型调用
- 本地模型支持并行处理，提高处理效率
- 可配置最大并发调用数量（通过环境变量`MAX_CONCURRENT_MODELS`）
- 使用线程池实现并发处理，避免阻塞主线程

### 2. 模型调用基类
- 所有本地模型都继承自`BaseModelInterface`基类
- 基类提供统一的并行处理接口
- 自动处理异常和超时情况

### 3. 音频片段时间点处理
- 支持基于音频片段的时间范围提取帧
- 提供专门的方法`extract_frames_for_audio_segment`处理音频片段
- 更准确地定位关键操作时间点

### 4. 阿里云语音识别集成
- 集成阿里云百炼语音识别服务（dashscope）
- 支持实时流式音频转录
- 返回带时间戳的识别结果，便于精确分析
- 支持WAV和PCM格式音频文件处理

## 开发说明

### 添加新的关键词检测

1. 在 `core/keyword_detector.py` 中的 `keyword_patterns` 字典中添加新的关键词模式
2. 在 `core/keyword_detector.py` 中的 `OperationType` 枚举中添加新的操作类型
3. 在 `main.py` 中添加相应的处理函数

### 集成新的AI模型

1. 在 `core/local_models.py` 中创建新的模型类，继承 `BaseModelInterface`
2. 实现 `process_image` 方法
3. 在 `main.py` 中初始化新模型并添加到处理流程中

### 配置并发数量

可以通过设置环境变量来配置最大并发模型调用数：

```bash
export MAX_CONCURRENT_MODELS=10
python main.py
```

或者在启动服务时直接设置：

```bash
MAX_CONCURRENT_MODELS=10 python main.py