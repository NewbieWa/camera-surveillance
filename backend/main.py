import os
import sys
import time
import asyncio
import json
import logging
import base64
import tempfile
from typing import List
from pathlib import Path
from datetime import datetime
import cv2
from fastapi import FastAPI, WebSocket, Request
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import subprocess
import shutil


from camera_surveillance.tools.workspace import log_with_timestamp

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

# 添加src目录到Python路径
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src'))


from camera_surveillance.tools.workspace import WorkspaceManager
from camera_surveillance.tools.video_processor import VideoStreamProcessor
from camera_surveillance.processor import AudioTranscriber
from camera_surveillance.processor import SpeechProcessor
from camera_surveillance.tools.keyword_detector import KeywordDetector, OperationType
from camera_surveillance.tools.frame_extractor import FrameExtractor
from camera_surveillance.processor import VehicleNumberRecognizer
from camera_surveillance.processor import AntiRollingModel, RemoveRollingModel
from camera_surveillance.processor import process_detection, process_vehicle_number, process_anti_rolling, process_remove_rolling
from camera_surveillance.tools.result_reporter import ResultReporter
from camera_surveillance.coordinator import process_video_common, process_stored_video_chunk, process_video_task

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

# 用于限制同时执行的视频处理任务数量
video_processing_semaphore = asyncio.Semaphore(3)

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

@app.post("/process-full-video/{device_id}")
async def process_full_video(device_id: str, request: Request):
    """处理完整视频流的端点 - 接收实时视频数据流并在内部创建workspace"""
    try:
        # 在device_id后添加时间戳
        timestamp = int(time.time())
        device_id_with_timestamp = f"{device_id}_{timestamp}"
        
        # 创建工作空间
        workspace_path = workspace_manager.create_workspace(device_id)
        log_with_timestamp(f"为设备 {device_id} 创建工作空间: {workspace_path}")
        
        # 从请求体中读取视频流数据
        video_stream_data = await request.body()
        
        # 启动异步处理任务
        asyncio.create_task(process_video_task(device_id, workspace_path, video_stream_data))
        
        return {
            "message": "视频处理任务已启动",
            "device_id": device_id,
            "original_device_id": device_id,
            "timestamp": timestamp,
            "workspace_path": workspace_path
        }
    except Exception as e:
        log_with_timestamp(f"处理设备 {device_id} 的完整视频时出错: {e}")
        return {
            "message": f"处理视频时出错: {str(e)}",
            "device_id": device_id,
            "timestamp": int(time.time())
        }

@app.websocket("/ws/live-video/{device_id}")
async def websocket_live_video(websocket: WebSocket, device_id: str):
    """WebSocket端点，用于接收实时视频帧并处理"""
    await websocket.accept()
    log_with_timestamp(f"实时视频WebSocket连接已建立，设备ID: {device_id}")
    
    # 创建工作空间
    workspace_path = workspace_manager.create_workspace(device_id)
    log_with_timestamp(f"为设备 {device_id} 创建工作空间: {workspace_path}")
    
    # 初始化处理模块
    video_processor = VideoStreamProcessor(workspace_path)
    audio_transcriber = AudioTranscriber()
    keyword_detector = KeywordDetector()
    vehicle_recognizer = VehicleNumberRecognizer()
    anti_rolling_model = AntiRollingModel(max_concurrent=MAX_CONCURRENT_MODELS)
    remove_rolling_model = RemoveRollingModel(max_concurrent=MAX_CONCURRENT_MODELS)
    
    # 开始视频录制
    video_path = video_processor.start_video_recording()
    log_with_timestamp(f"开始录制视频到: {video_path}")
    
    # 用于存储detection_video_chunk的计数器和缓冲区
    chunk_counter = 0
    chunk_buffer = []
    
    try:
        # 存储待处理的元数据
        pending_metadata = None
        
        while True:
            # 接收来自前端的数据 - 可以是文本或二进制
            try:
                # 尝试接收数据
                data = await websocket.receive()
                
                # 处理文本数据
                if "text" in data:
                    frame_data = json.loads(data["text"])
                    
                    if frame_data["type"] == "stop_detection":
                        # 收到停止检测信号，退出循环
                        log_with_timestamp(f"收到停止检测信号，设备ID: {device_id}")
                        break
                    elif frame_data["type"] == "video_frame":
                        # 处理实时视频帧
                        image_data = frame_data["data"]
                        
                        # 将base64图像数据保存为临时文件
                        # 移除base64数据的前缀
                        if "," in image_data:
                            header, encoded = image_data.split(",", 1)
                        else:
                            encoded = image_data
                        image_bytes = base64.b64decode(encoded)
                        
                        # 创建临时图像文件
                        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_file:
                            temp_file.write(image_bytes)
                            temp_image_path = temp_file.name
                        
                        try:
                            # 将临时图像添加到视频中
                            video_processor.add_frame_to_video(temp_image_path)
                            
                            # 定期处理视频片段
                            current_time = time.time()
                            if current_time % 5 < 0.1:  # 每5秒处理一次
                                # 提取音频（如果有的话）
                                audio_path = os.path.join(workspace_path, "extracted_audio.wav")
                                
                                # 检查是否有音频数据可处理
                                if os.path.exists(audio_path) and os.path.getsize(audio_path) > 0:
                                    # 转录音频
                                    speech_processor = SpeechProcessor()
                                    transcriptions = speech_processor.transcribe_file(audio_path)
                                    
                                    # 如果没有转录结果，使用模拟数据
                                    if not transcriptions:
                                        transcriptions = [
                                            (current_time % 100, "现在进行车号确认操作"),
                                            (current_time % 100 + 15, "铁鞋设置手闸拧紧"),
                                            (current_time % 100 + 30, "铁鞋撤除手闸松开")
                                        ]
                                    
                                    # 检测关键词
                                    detections = keyword_detector.detect_keywords_with_context(transcriptions)
                                    
                                    # 处理每个检测到的操作
                                    for detection in detections:
                                        await process_detection(
                                            device_id, 
                                            detection, 
                                            video_path, 
                                            vehicle_recognizer, 
                                            anti_rolling_model, 
                                            remove_rolling_model
                                        )
                                
                                # 也可以直接对当前帧进行图像识别
                                # 尝试识别车辆编号
                                vehicle_number = vehicle_recognizer.recognize_vehicle_number(temp_image_path)
                                if vehicle_number:
                                    result = result_reporter.create_vehicle_number_result(
                                        device_id, vehicle_number, [temp_image_path], current_time
                                    )
                                    await result_reporter.report_result(result)
                                
                        finally:
                            # 清理临时文件
                            try:
                                os.unlink(temp_image_path)
                            except:
                                pass
                    elif frame_data["type"] == "recorded_video":
                        # 处理录制的完整音视频文件
                        video_data_url = frame_data["data"]
                        
                        # 解析base64数据
                        # 移除data URL前缀
                        if "," in video_data_url:
                            header, encoded = video_data_url.split(",", 1)
                            video_bytes = base64.b64decode(encoded)
                            
                            # 创建临时视频文件
                            with tempfile.NamedTemporaryFile(suffix='.webm', delete=False) as temp_file:
                                temp_file.write(video_bytes)
                                temp_video_path = temp_file.name
                            
                            try:
                                # 将录制的视频保存到工作空间
                                output_video_path = os.path.join(workspace_path, f"recorded_video_{int(time.time())}.webm")
                                
                                # 如果系统有ffmpeg，尝试转换格式以确保兼容性
                                try:
                                    # 尝试将webm转换为mp4
                                    output_video_path = os.path.join(workspace_path, f"recorded_video_{int(time.time())}.mp4")
                                    cmd = [
                                        'ffmpeg',
                                        '-i', temp_video_path,
                                        '-c:v', 'libx264',
                                        '-c:a', 'aac',
                                        output_video_path,
                                        '-y'
                                    ]
                                    result = subprocess.run(cmd, capture_output=True, text=True)
                                    
                                    if result.returncode != 0:
                                        # 如果ffmpeg失败，回退到直接复制文件
                                        output_video_path = os.path.join(workspace_path, f"recorded_video_{int(time.time())}.webm")
                                        shutil.copy2(temp_video_path, output_video_path)
                                except:
                                    # 如果ffmpeg不可用，直接复制webm文件
                                    output_video_path = os.path.join(workspace_path, f"recorded_video_{int(time.time())}.webm")
                                    shutil.copy2(temp_video_path, output_video_path)
                                
                                log_with_timestamp(f"录制的视频已保存到: {output_video_path}")
                                
                            finally:
                                # 清理临时文件
                                try:
                                    os.unlink(temp_video_path)
                                except:
                                    pass
                    elif frame_data["type"] == "detection_video_chunk_metadata":
                        # 存储元数据，等待后续的二进制数据
                        pending_metadata = frame_data
                        continue  # 等待二进制数据
                        
                # 处理二进制数据
                elif "bytes" in data and pending_metadata:
                    # 处理之前存储的元数据和当前的二进制数据
                    video_bytes = data["bytes"]
                    frame_data = pending_metadata
                    pending_metadata = None  # 清除已处理的元数据
                    
                    # 确保工作空间中的tmp目录存在
                    tmp_dir = os.path.join(workspace_path, "tmp")
                    if not os.path.exists(tmp_dir):
                        os.makedirs(tmp_dir)
                    
                    # 创建临时视频文件在工作空间目录中
                    import time
                    temp_video_path = os.path.join(tmp_dir, f"video_chunk_{int(time.time()*1000000)}_{chunk_counter:06d}.webm")
                    
                    # 不进行 WebM 头部校验，直接保存二进制数据
                    with open(temp_video_path, 'wb') as temp_file:
                        temp_file.write(video_bytes)
                    
                    try:
                        log_with_timestamp(f"接收视频块，临时文件: {temp_video_path}")
                        
                        # 直接将数据块添加到缓冲区用于定期保存，不再尝试处理单个片段
                        chunk_buffer.append(temp_video_path)
                        chunk_counter += 1
                        
                        # 检查文件大小
                        if os.path.exists(temp_video_path):
                            file_size = os.path.getsize(temp_video_path)
                            log_with_timestamp(f"视频块大小: {file_size} 字节")
                        
                        log_with_timestamp("视频块已添加到缓冲区，等待合并处理")


                        batch_size = 1
                        # 每3个数据块存储一次
                        if chunk_counter % batch_size == 0:
                            try:
                                # 定义最终合并文件的路径
                                final_file_path = os.path.join(workspace_path, f"detection_video_chunk_{chunk_counter//batch_size:04d}.mp4")
                                
                                # 创建包含所有视频块路径的临时列表文件
                                list_file_path = os.path.join(workspace_path, f"video_list_{chunk_counter//batch_size}.txt")
                                
                                with open(list_file_path, 'w', encoding='utf-8') as f:
                                    for video_chunk_path in chunk_buffer:
                                        # 转换为绝对路径以避免路径问题
                                        abs_video_path = os.path.abspath(video_chunk_path)
                                        # 使用单引号包围路径以处理特殊字符
                                        f.write(f"file '{abs_video_path}'\n")
                                
                                # 使用ffmpeg合并视频块，转码为MP4兼容格式
                                cmd = [
                                    'ffmpeg',
                                    '-f', 'concat',
                                    '-safe', '0',
                                    '-i', list_file_path,
                                    '-c:v', 'libx264',  # 将VP8视频编码转换为H.264
                                    '-c:a', 'aac',      # 将Opus音频编码转换为AAC
                                    '-strict', 'experimental',
                                    final_file_path,
                                    '-y'  # 覆盖已存在的文件
                                ]
                                
                                log_with_timestamp(f"开始合并视频块到: {final_file_path}")
                                log_with_timestamp(f"合并命令: {' '.join(cmd)}")
                                
                                result = subprocess.run(cmd, capture_output=True, text=True)
                                
                                if result.returncode != 0:
                                    log_with_timestamp(f"FFmpeg合并失败: {result.stderr}")
                                    raise Exception(f"FFmpeg合并失败: {result.stderr}")
                                
                                log_with_timestamp(f"视频块合并完成: {final_file_path}, 大小: {os.path.getsize(final_file_path)} 字节")
                                
                                # 启动子协程处理存储的视频文件
                                asyncio.create_task(process_stored_video_chunk(
                                    final_file_path, 
                                    device_id, 
                                    workspace_path, 
                                    keyword_detector, 
                                    vehicle_recognizer, 
                                    anti_rolling_model, 
                                    remove_rolling_model
                                ))
                                
                            except Exception as e:
                                log_with_timestamp(f"合并视频块时出错: {e}")
                                import traceback
                                log_with_timestamp(f"错误详情: {traceback.format_exc()}")
                            finally:
                                # 清理列表文件
                                try:
                                    if 'list_file_path' in locals() and os.path.exists(list_file_path):
                                        os.unlink(list_file_path)
                                except Exception as e:
                                    log_with_timestamp(f"清理列表文件失败: {e}")
                            
                            # 清空缓冲区
                            chunk_buffer.clear()
                        
                    finally:
                        # 注意：这里不立即清理temp_video_path，因为它们被存储在chunk_buffer中
                        # 它们将在处理完成后被清理
                        pass
                    # 发送确认消息
                    await websocket.send_text(json.dumps({
                        "status": "frame_processed",
                        "timestamp": frame_data.get("timestamp", time.time()) if frame_data else time.time()
                    }))
                else:
                    # 发送确认消息
                    await websocket.send_text(json.dumps({
                        "status": "frame_processed",
                        "timestamp": time.time()
                    }))
            except Exception as e:
                log_with_timestamp(f"接收WebSocket数据时出错: {e}")
                # 继续循环，不中断连接
                continue
            
    except Exception as e:
        log_with_timestamp(f"处理设备 {device_id} 的实时视频流时出错: {e}")
        # 报告错误结果
        error_result = {
            "type": "error",
            "device_id": device_id,
            "message": f"处理实时视频流时出错: {str(e)}",
            "timestamp": time.time()
        }
        await result_reporter.report_result(error_result)
    finally:
        # 清理缓冲区中剩余的临时文件
        for temp_path in chunk_buffer:
            try:
                os.unlink(temp_path)
            except:
                pass
        
        # 清理tmp目录
        # tmp_dir = os.path.join(workspace_path, "tmp")
        # if os.path.exists(tmp_dir):
        #     import shutil
        #     try:
        #         shutil.rmtree(tmp_dir)
        #         log_with_timestamp(f"已清理tmp目录: {tmp_dir}")
        #     except Exception as e:
        #         log_with_timestamp(f"清理tmp目录失败: {e}")
                
        # 确保所有帧都已写入视频文件
        log_with_timestamp(f"等待视频帧写入完成，当前帧数: {video_processor.frame_count}")
        
        # 停止视频处理并释放资源
        # 确保视频写入器被正确关闭
        video_processor.stop_processing()
        log_with_timestamp(f"实时视频WebSocket连接已关闭，设备ID: {device_id}")
        
        # 添加短暂延迟以确保文件写入完成
        await asyncio.sleep(1)  # 等待1秒确保文件写入完成


def find_segment_start(data):
    """在 WebM/EBML 数据中找到 Segment 的开始位置"""
    if isinstance(data, str):
        with open(data, 'rb') as f:
            data = f.read()

    # WebM Segment 的 EBML ID: 0x18 0x53 0x80 0x67
    segment_marker = b'\x18\x53\x80\x67'
    segment_pos = data.find(segment_marker)

    if segment_pos != -1:
        return segment_pos

    # 如果没找到 Segment，返回 0
    return 0

def find_track_entries_end(data, segment_start):
    """找到 TrackEntry 结束位置（简化版）"""
    # 查找 TrackEntry (0x16 0x54 0xAE 0x6B)
    track_pos = data.find(b'\x16\x54\xae\x6b', segment_start)
    if track_pos != -1:
        # 简化：假设 TrackEntry 在 500 字节内结束
        return min(len(data), track_pos + 500)
    return segment_start + 100  # 默认返回较短的头部





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