import os
import sys
import time
import asyncio
import json
import logging
from typing import List
from pathlib import Path
from datetime import datetime
import cv2
from fastapi import FastAPI, WebSocket, Request
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

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
        while True:
            # 接收来自前端的数据
            data = await websocket.receive_text()
            frame_data = json.loads(data)
            
            if frame_data["type"] == "stop_detection":
                # 收到停止检测信号，退出循环
                log_with_timestamp(f"收到停止检测信号，设备ID: {device_id}")
                break
            elif frame_data["type"] == "video_frame":
                # 处理实时视频帧
                image_data = frame_data["data"]
                
                # 将base64图像数据保存为临时文件
                import base64
                import tempfile
                from datetime import datetime
                
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
                import base64
                import tempfile
                
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
                            import subprocess
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
                                import shutil
                                output_video_path = os.path.join(workspace_path, f"recorded_video_{int(time.time())}.webm")
                                shutil.copy2(temp_video_path, output_video_path)
                        except:
                            # 如果ffmpeg不可用，直接复制webm文件
                            import shutil
                            output_video_path = os.path.join(workspace_path, f"recorded_video_{int(time.time())}.webm")
                            shutil.copy2(temp_video_path, output_video_path)
                        
                        log_with_timestamp(f"录制的视频已保存到: {output_video_path}")
                        
                    finally:
                        # 清理临时文件
                        try:
                            os.unlink(temp_video_path)
                        except:
                            pass
            elif frame_data["type"] == "detection_video_chunk":
                # 处理实时视频检测的数据块
                video_data_url = frame_data["data"]
                
                # 解析base64数据
                import base64
                import tempfile

                # log_with_timestamp(f"video_data_url: {video_data_url}")
                
                # 移除data URL前缀
                if "," in video_data_url:
                    header, encoded = video_data_url.split(",", 1)
                    video_bytes = base64.b64decode(encoded)
                    
                    # 确保工作空间中的tmp目录存在
                    tmp_dir = os.path.join(workspace_path, "tmp")
                    if not os.path.exists(tmp_dir):
                        os.makedirs(tmp_dir)
                    
                    # 创建临时视频文件在工作空间目录中
                    import time
                    temp_video_path = os.path.join(tmp_dir, f"video_chunk_{int(time.time()*1000000)}_{chunk_counter:06d}.webm")
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
                        
                        # 每10个数据块存储一次
                        if chunk_counter % 10 == 0:
                            # 生成带序号的文件名
                            chunk_file_path = os.path.join(workspace_path, f"detection_video_chunk_{chunk_counter//60:04d}.webm")
                            
                            # 合并所有缓冲区中的视频块
                            try:
                                
                                # 创建一个临时文本文件列出所有要合并的文件
                                import time
                                list_file_path = os.path.join(workspace_path, f"chunk_list_{int(time.time())}.txt")
                                
                                # 添加日志输出
                                log_with_timestamp(f"准备创建列表文件: {list_file_path}")
                                log_with_timestamp(f"workspace_path: {workspace_path}")
                                log_with_timestamp(f"有效视频块数量: {len(chunk_buffer)}")
                                
                                # 过滤掉不存在的文件
                                valid_chunks = [chunk for chunk in chunk_buffer if os.path.exists(chunk)]
                                log_with_timestamp(f"有效存在的视频块数量: {len(valid_chunks)}")
                                
                                if not valid_chunks:
                                    log_with_timestamp("没有有效的视频块可以合并")
                                    # 继续处理下一个循环
                                    continue
                                
                                try:
                                    with open(list_file_path, 'w') as list_file:
                                        for chunk_path in valid_chunks:
                                            # 确保使用绝对路径，防止ffmpeg路径解析问题
                                            absolute_chunk_path = os.path.abspath(chunk_path)
                                            list_file.write(f"file '{absolute_chunk_path}'\n")
                                    log_with_timestamp(f"列表文件已成功创建: {list_file_path}")
                                    
                                    # 读取并输出文件内容以确认文件存在
                                    if os.path.exists(list_file_path):
                                        with open(list_file_path, 'r') as f:
                                            content = f.read()
                                            log_with_timestamp(f"列表文件内容:\n{content}")
                                    else:
                                        log_with_timestamp("错误：列表文件未找到")
                                except Exception as e:
                                    log_with_timestamp(f"创建列表文件失败: {e}")
                                    import traceback
                                    log_with_timestamp(f"详细错误信息: {traceback.format_exc()}")
                                    # 回退到复制第一个有效文件
                                    shutil.copy2(valid_chunks[0], chunk_file_path)
                                    raise
                                
                                # 确保列表文件存在
                                if not os.path.exists(list_file_path):
                                    log_with_timestamp(f"列表文件不存在: {list_file_path}")
                                    # 回退到复制第一个有效文件
                                    shutil.copy2(valid_chunks[0], chunk_file_path)
                                else:
                                    # 检查所有视频块的格式，如果格式不一致则使用重新编码方式
                                    # 使用ffmpeg合并视频
                                    cmd = [
                                        'ffmpeg',
                                        '-f', 'concat',
                                        '-safe', '0',
                                        '-i', list_file_path,
                                        '-c', 'copy',  # 尝试直接复制，不重新编码
                                        chunk_file_path,
                                        '-y'
                                    ]
                                    import subprocess
                                    result = subprocess.run(cmd, capture_output=True, text=True)
                                    
                                    if result.returncode != 0:
                                        log_with_timestamp(f"视频合并失败 (直接复制): {result.stderr}")
                                        log_with_timestamp(f"尝试重新编码，valid_chunks数量: {len(valid_chunks)}")
                                        # 尝试重新编码 - 这可以处理不同格式的视频块
                                        cmd_reencode = [
                                            'ffmpeg',
                                            '-f', 'concat',
                                            '-safe', '0',
                                            '-i', list_file_path,
                                            '-c:v', 'libx264',
                                            '-c:a', 'aac',
                                            '-preset', 'ultrafast',
                                            chunk_file_path,
                                            '-y'
                                        ]
                                        result_reencode = subprocess.run(cmd_reencode, capture_output=True, text=True)
                                        
                                        if result_reencode.returncode != 0:
                                            log_with_timestamp(f"视频重新编码失败: {result_reencode.stderr}")
                                            # 如果合并失败，尝试逐步合并
                                            log_with_timestamp("尝试逐步合并视频块...")
                                            try:
                                                # 从第一个文件开始，逐步合并
                                                temp_output = chunk_file_path + ".temp"
                                                current_file = valid_chunks[0]
                                                
                                                # 先复制第一个文件
                                                shutil.copy2(current_file, temp_output)
                                                
                                                # 依次合并其他文件
                                                for i in range(1, len(valid_chunks)):
                                                    next_file = valid_chunks[i]
                                                    temp_list = os.path.join(workspace_path, f"temp_merge_list_{i}.txt")
                                                    with open(temp_list, 'w') as f:
                                                        f.write(f"file '{os.path.abspath(current_file)}'\n")
                                                        f.write(f"file '{os.path.abspath(next_file)}'\n")
                                                    
                                                    temp_output2 = chunk_file_path + f".temp{i}"
                                                    cmd_merge = [
                                                        'ffmpeg',
                                                        '-f', 'concat',
                                                        '-safe', '0',
                                                        '-i', temp_list,
                                                        '-c', 'copy',
                                                        temp_output2,
                                                        '-y'
                                                    ]
                                                    result_merge = subprocess.run(cmd_merge, capture_output=True, text=True)
                                                    
                                                    if result_merge.returncode != 0:
                                                        log_with_timestamp(f"逐步合并第{i}个文件失败，尝试重新编码: {result_merge.stderr}")
                                                        # 如果直接复制失败，尝试重新编码
                                                        cmd_reencode_step = [
                                                            'ffmpeg',
                                                            '-f', 'concat',
                                                            '-safe', '0',
                                                            '-i', temp_list,
                                                            '-c:v', 'libx264',
                                                            '-c:a', 'aac',
                                                            '-preset', 'ultrafast',
                                                            temp_output2,
                                                            '-y'
                                                        ]
                                                        result_reencode_step = subprocess.run(cmd_reencode_step, capture_output=True, text=True)
                                                        if result_reencode_step.returncode != 0:
                                                            log_with_timestamp(f"逐步合并重新编码也失败: {result_reencode_step.stderr}")
                                                            # 回退到复制第一个文件
                                                            shutil.copy2(valid_chunks[0], chunk_file_path)
                                                            break
                                                    
                                                    # 更新current_file为合并后的文件
                                                    current_file = temp_output2
                                                    shutil.move(temp_output2, temp_output)
                                                    # 清理临时列表文件
                                                    os.unlink(temp_list)
                                                
                                                # 最终结果移动到目标文件
                                                if os.path.exists(temp_output):
                                                    shutil.move(temp_output, chunk_file_path)
                                                    log_with_timestamp(f"逐步合并完成，最终文件大小: {os.path.getsize(chunk_file_path)} 字节")
                                            except Exception as e:
                                                log_with_timestamp(f"逐步合并过程中出现异常: {e}")
                                                # 最后的回退：复制第一个文件
                                                shutil.copy2(valid_chunks[0], chunk_file_path)
                                        else:
                                            log_with_timestamp(f"视频重新编码成功")
                                    else:
                                        log_with_timestamp(f"视频合并成功")
                                    
                                    # 检查生成的文件大小
                                    if os.path.exists(chunk_file_path):
                                        file_size = os.path.getsize(chunk_file_path)
                                        log_with_timestamp(f"检测视频块已合并并保存到: {chunk_file_path}，大小: {file_size} 字节")
                                    else:
                                        log_with_timestamp(f"错误：合并后的文件不存在: {chunk_file_path}")
                                
                                # 启动子协程处理存储的视频文件
                                asyncio.create_task(process_stored_video_chunk(
                                    chunk_file_path, 
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
                                # try:
                                #     if 'list_file_path' in locals() and os.path.exists(list_file_path):
                                #         os.unlink(list_file_path)
                                # except Exception as e:
                                #     log_with_timestamp(f"清理列表文件失败: {e}")
                                i = 1
                            
                            # 清空缓冲区
                            chunk_buffer.clear()
                        
                    finally:
                        # 注意：这里不立即清理temp_video_path，因为它们被存储在chunk_buffer中
                        # 它们将在处理完成后被清理
                        pass
            
            # 发送确认消息
            await websocket.send_text(json.dumps({
                "status": "frame_processed",
                "timestamp": frame_data.get("timestamp", time.time())
            }))
            
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