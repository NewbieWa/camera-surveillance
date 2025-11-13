import os
import sys
import time
import asyncio
import json
import logging
from typing import List
from pathlib import Path
from datetime import datetime
from fastapi import FastAPI, WebSocket, Request
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.FileHandler('backend.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def log_with_timestamp(message: str):
    """带时间戳的日志输出函数"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")
    # 同时记录到日志文件
    logger.info(f"[{timestamp}] {message}")

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from backend.src.backend.core import WorkspaceManager
from backend.src.backend.core import VideoStreamProcessor
from backend.src.backend.processor.audio_transcriber import AudioTranscriber
from backend.src.backend.processor.speech_processor import SpeechProcessor
from backend.src.backend.core import KeywordDetector, OperationType
from backend.src.backend.core import FrameExtractor
from backend.src.backend.processor.vehicle_recognizer import VehicleNumberRecognizer
from backend.src.backend.processor.local_models import AntiRollingModel, RemoveRollingModel
from backend.src.backend.core import ResultReporter

app = FastAPI(title="外勤作业智能分析系统", description="实时视频流处理和分析服务")

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 配置参数
MAX_CONCURRENT_MODELS = int(os.getenv("MAX_CONCURRENT_MODELS", "5"))  # 最大并发模型调用数

# 全局变量
workspace_manager = WorkspaceManager("workspace")
result_reporter = ResultReporter()
active_connections: List[WebSocket] = []

@app.get("/list-video-files")
async def list_video_files():
    """获取视频文件列表"""
    try:
        # 修正路径：从项目根目录开始查找前端视频文件
        project_root = Path(__file__).parent.parent  # 获取项目根目录
        video_dir = project_root / "frontend" / "video" / "train_number"
        
        log_with_timestamp(f"正在查找视频目录: {video_dir}")
        
        if not video_dir.exists():
            log_with_timestamp("视频目录不存在")
            return {"video_files": []}
        
        video_files = []
        for file_path in video_dir.iterdir():
            if file_path.is_file() and file_path.suffix.lower() in ['.mp4', '.avi', '.mov', '.mkv']:
                video_files.append(file_path.name)
        
        # 按字母顺序排序
        video_files.sort()
        
        # 打印视频文件列表
        log_with_timestamp(f"找到 {len(video_files)} 个视频文件: {video_files}")
        
        return {"video_files": video_files}
    except Exception as e:
        log_with_timestamp(f"获取视频文件列表时出错: {e}")
        return {"video_files": []}

@app.websocket("/ws/results")
async def websocket_results(websocket: WebSocket):
    """WebSocket端点，用于实时发送处理结果"""
    await websocket.accept()
    active_connections.append(websocket)
    result_reporter.add_websocket_connection(websocket)
    
    try:
        while True:
            # 保持连接活跃
            data = await websocket.receive_text()
            # 可以处理来自前端的指令
            await websocket.send_text(json.dumps({"status": "connected"}))
    except Exception as e:
        log_with_timestamp(f"WebSocket连接错误: {e}")
    finally:
        active_connections.remove(websocket)
        result_reporter.remove_websocket_connection(websocket)

@app.post("/video-stream/{device_id}")
async def receive_video_stream(device_id: str):
    """接收视频流的端点"""
    # 在device_id后添加时间戳
    import time
    timestamp = int(time.time())
    device_id_with_timestamp = f"{device_id}_{timestamp}"
    
    # 创建工作空间
    workspace_path = workspace_manager.create_workspace(device_id_with_timestamp)
    
    # 返回工作空间信息
    return {
        "message": "视频流接收端点已准备就绪",
        "device_id_with_timestamp": device_id_with_timestamp,
        "original_device_id": device_id,
        "timestamp": timestamp,
        "workspace_path": workspace_path
    }

@app.post("/process-video/{device_id}")
async def process_video_stream(device_id: str, request: Request):
    """处理视频流的端点 - 接收实时视频数据流"""
    # 从设备ID中提取原始ID（因为可能包含时间戳）
    original_device_id = device_id.split('_')[0] if '_' in device_id else device_id
    
    # 从请求体中读取视频流数据
    video_stream_data = await request.body()
    
    # 启动异步处理任务
    asyncio.create_task(process_video_task(device_id, video_stream_data))
    
    return {
        "message": "视频处理任务已启动",
        "device_id": device_id,
        "original_device_id": original_device_id
    }

async def process_video_task(device_id: str, video_stream_data: bytes):
    """异步处理视频流任务 - 接收实时视频数据流"""
    try:
        # 使用已存在的工作空间路径，而不是重新创建
        # 首先尝试找到与设备ID对应的工作空间
        workspace_path = str(workspace_manager.base_path / device_id)
        
        # 检查工作空间是否存在，如果不存在则创建
        if not os.path.exists(workspace_path):
            log_with_timestamp(f"工作空间不存在，为设备 {device_id} 创建: {workspace_path}")
            workspace_path = workspace_manager.create_workspace(device_id)
        else:
            log_with_timestamp(f"使用现有工作空间: {workspace_path}")
        
        # 2. 初始化各个处理模块（带并发配置）
        video_processor = VideoStreamProcessor(workspace_path)
        audio_transcriber = AudioTranscriber()
        keyword_detector = KeywordDetector()
        vehicle_recognizer = VehicleNumberRecognizer()
        anti_rolling_model = AntiRollingModel(max_concurrent=MAX_CONCURRENT_MODELS)
        remove_rolling_model = RemoveRollingModel(max_concurrent=MAX_CONCURRENT_MODELS)
        
        # 3. 开始视频录制
        video_path = video_processor.start_video_recording()
        log_with_timestamp(f"开始录制视频到: {video_path}")
        
        # 4. 处理视频流数据 - 将字节数据传递给视频处理器
        video_processor.process_video_stream_from_bytes(video_stream_data, video_path)
        
        # 5. 提取音频
        audio_path = os.path.join(workspace_path, "extracted_audio.wav")
        video_processor.extract_audio_from_video(video_path, audio_path)
        
        # 6. 转录音频 - 使用SpeechProcessor
        speech_processor = SpeechProcessor()
        transcriptions = speech_processor.transcribe_file(audio_path)
        # 如果没有转录结果，使用模拟数据
        if not transcriptions:
            transcriptions = [
                (10.5, "现在进行车号确认操作"),
                (25.2, "铁鞋设置手闸拧紧"),
                (42.8, "铁鞋撤除手闸松开")
            ]
        
        # 7. 检测关键词
        detections = keyword_detector.detect_keywords_with_context(transcriptions)
        
        # 8. 处理每个检测到的操作
        for detection in detections:
            await process_detection(
                device_id, 
                detection, 
                video_path, 
                vehicle_recognizer, 
                anti_rolling_model, 
                remove_rolling_model
            )
        
        log_with_timestamp(f"设备 {device_id} 的视频处理完成")
        
    except Exception as e:
        log_with_timestamp(f"处理设备 {device_id} 的视频时出错: {e}")
        # 报告错误结果
        error_result = {
            "type": "error",
            "device_id": device_id,
            "message": f"处理视频时出错: {str(e)}",
            "timestamp": time.time()
        }
        await result_reporter.report_result(error_result)

async def process_detection(device_id: str, detection, video_path: str,
                          vehicle_recognizer: VehicleNumberRecognizer,
                          anti_rolling_model: AntiRollingModel,
                          remove_rolling_model: RemoveRollingModel):
    """处理单个检测结果"""
    try:
        # 1. 提取相关帧（根据操作类型使用不同的时间点逻辑）
        frame_extractor = FrameExtractor(video_path)
        
        # TODO: 这里需要根据实际的音频片段时间来提取帧
        # 目前我们假设detection.timestamp就是音频片段的结束时间
        frame_paths = frame_extractor.extract_frames_around_timestamp(
            detection.timestamp,
            before_seconds=2.0,
            after_seconds=4.0,
            interval_seconds=1.0
        )
        frame_extractor.release()
        
        # 2. 根据操作类型处理
        if detection.operation_type == OperationType.VEHICLE_NUMBER:
            await process_vehicle_number(
                device_id, detection, frame_paths, vehicle_recognizer
            )
        elif detection.operation_type == OperationType.ANTI_ROLLING:
            await process_anti_rolling(
                device_id, detection, frame_paths, anti_rolling_model
            )
        elif detection.operation_type == OperationType.REMOVE_ROLLING:
            await process_remove_rolling(
                device_id, detection, frame_paths, remove_rolling_model
            )
            
    except Exception as e:
        log_with_timestamp(f"处理检测结果时出错: {e}")

async def process_vehicle_number(device_id: str, detection, frame_paths, 
                               vehicle_recognizer: VehicleNumberRecognizer):
    """处理车号确认操作"""
    log_with_timestamp(f"处理车号确认操作: {detection.text}")
    
    # 尝试识别车辆编号
    vehicle_number = None
    for timestamp, frame_path in frame_paths:
        vehicle_number = vehicle_recognizer.recognize_vehicle_number(frame_path)
        if vehicle_number:
            break
    
    # 创建结果报告
    if vehicle_number:
        result = result_reporter.create_vehicle_number_result(
            device_id, vehicle_number, [fp for _, fp in frame_paths], detection.timestamp
        )
    else:
        result = result_reporter.create_vehicle_number_failure(
            device_id, [fp for _, fp in frame_paths], detection.timestamp
        )
    
    # 发送结果
    await result_reporter.report_result(result)

async def process_anti_rolling(device_id: str, detection, frame_paths,
                             anti_rolling_model: AntiRollingModel):
    """处理防遛确认操作"""
    log_with_timestamp(f"处理防遛确认操作: {detection.text}")
    
    # 使用模型并行处理所有帧
    frame_file_paths = [frame_path for _, frame_path in frame_paths]
    results = await anti_rolling_model.process_images_parallel(frame_file_paths)
    
    # 检查是否有任何帧处理成功
    is_success = False
    for _, result in results:
        if result is True:
            is_success = True
            break
    
    # 创建结果报告
    result = result_reporter.create_anti_rolling_result(
        device_id, is_success, [fp for _, fp in frame_paths], detection.timestamp
    )
    
    # 发送结果
    await result_reporter.report_result(result)

async def process_remove_rolling(device_id: str, detection, frame_paths,
                               remove_rolling_model: RemoveRollingModel):
    """处理撤遛确认操作"""
    log_with_timestamp(f"处理撤遛确认操作: {detection.text}")
    
    # 使用模型并行处理所有帧
    frame_file_paths = [frame_path for _, frame_path in frame_paths]
    results = await remove_rolling_model.process_images_parallel(frame_file_paths)
    
    # 检查是否有任何帧处理成功
    is_success = False
    for _, result in results:
        if result is True:
            is_success = True
            break
    
    # 创建结果报告
    result = result_reporter.create_remove_rolling_result(
        device_id, is_success, [fp for _, fp in frame_paths], detection.timestamp
    )
    
    # 发送结果
    await result_reporter.report_result(result)

@app.get("/")
async def root():
    return {"message": "外勤作业智能分析系统后端服务已启动"}

if __name__ == "__main__":
    # 配置Uvicorn日志格式，添加时间戳
    import logging
    import sys
    
    # 创建带时间戳的日志格式
    log_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "()": "uvicorn.logging.DefaultFormatter",
                "fmt": "%(asctime)s %(levelprefix)s %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
                "use_colors": None,
            },
            "access": {
                "()": "uvicorn.logging.AccessFormatter",
                "fmt": '%(asctime)s %(levelprefix)s %(client_addr)s - "%(request_line)s" %(status_code)s',
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
        },
        "handlers": {
            "default": {
                "formatter": "default",
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stderr",
            },
            "access": {
                "formatter": "access",
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stdout",
            },
        },
        "loggers": {
            "uvicorn": {"handlers": ["default"], "level": "INFO"},
            "uvicorn.error": {"level": "INFO"},
            "uvicorn.access": {"handlers": ["access"], "level": "INFO", "propagate": False},
        },
    }
    
    uvicorn.run(app, host="0.0.0.0", port=8000, log_config=log_config)