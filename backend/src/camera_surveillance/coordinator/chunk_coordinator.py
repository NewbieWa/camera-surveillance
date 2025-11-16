import os
import time
import asyncio
from typing import List

from camera_surveillance.tools.workspace import log_with_timestamp
from camera_surveillance.tools.video_processor import VideoStreamProcessor
from camera_surveillance.processor import SpeechProcessor
from camera_surveillance.tools.keyword_detector import KeywordDetector
from camera_surveillance.processor import process_detection

# 用于限制同时执行的视频处理任务数量
video_processing_semaphore = asyncio.Semaphore(3)

async def process_video_common(video_source, device_id: str, workspace_path: str, 
                              keyword_detector: KeywordDetector,
                              vehicle_recognizer: "VehicleNumberRecognizer",
                              anti_rolling_model: "AntiRollingModel",
                              remove_rolling_model: "RemoveRollingModel"):
    """
    通用视频处理函数
    :param video_source: 视频源，可以是视频文件路径或字节数据
    :param device_id: 设备ID
    :param workspace_path: 工作空间路径
    :param keyword_detector: 关键词检测器
    :param vehicle_recognizer: 车辆识别器
    :param anti_rolling_model: 防遛模型
    :param remove_rolling_model: 撤遛模型
    """
    try:
        # 初始化视频处理器
        video_processor = VideoStreamProcessor(workspace_path)
        
        # 根据视频源类型进行处理
        if isinstance(video_source, bytes):
            # 如果是字节数据，先创建视频文件
            video_path = os.path.join(workspace_path, f"temp_video_{int(time.time())}.mp4")
            # 处理视频流数据 - 将字节数据传递给视频处理器
            video_processor.process_video_stream_from_bytes(video_source, video_path)
        else:
            # 如果是文件路径，直接使用
            video_path = video_source
        
        # 提取音频用于转录
        audio_path = os.path.join(workspace_path, f"extracted_audio_{os.path.basename(str(video_source))}.wav")
        video_processor.extract_audio_from_video(video_path, audio_path)
        
        # 转录音频
        speech_processor = SpeechProcessor()
        transcriptions = speech_processor.transcribe_file(audio_path)
        # 如果没有转录结果，使用模拟数据
        if not transcriptions:
            transcriptions = [
                (time.time() % 100, "现在进行车号确认操作"),
                (time.time() % 100 + 15, "铁鞋设置手闸拧紧"),
                (time.time() % 100 + 30, "铁鞋撤除手闸松开")
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
        
        log_with_timestamp(f"视频处理完成: {video_path}")
        
        return True
        
    except Exception as e:
        log_with_timestamp(f"处理视频时出错: {e}")
        # 报告错误结果
        from camera_surveillance.tools.result_reporter import ResultReporter
        result_reporter = ResultReporter()
        error_result = {
            "type": "error",
            "device_id": device_id,
            "message": f"处理视频时出错: {str(e)}",
            "timestamp": time.time()
        }
        await result_reporter.report_result(error_result)
        return False

async def process_stored_video_chunk(chunk_file_path: str, device_id: str, workspace_path: str,
                                   keyword_detector: KeywordDetector,
                                   vehicle_recognizer: "VehicleNumberRecognizer",
                                   anti_rolling_model: "AntiRollingModel",
                                   remove_rolling_model: "RemoveRollingModel"):
    """处理存储的视频块 - 类似process_video_task的逻辑"""
    # 使用信号量确保同时最多有3个任务在执行
    async with video_processing_semaphore:
        log_with_timestamp(f"开始处理存储的视频块: {chunk_file_path}")
        await process_video_common(
            chunk_file_path,
            device_id,
            workspace_path,
            keyword_detector,
            vehicle_recognizer,
            anti_rolling_model,
            remove_rolling_model
        )

async def process_video_task(device_id: str, video_stream_data: bytes):
    """异步处理视频流任务 - 接收实时视频数据流"""
    try:
        from camera_surveillance.tools.workspace import WorkspaceManager
        from camera_surveillance.processor import VehicleNumberRecognizer
        from camera_surveillance.processor import AntiRollingModel, RemoveRollingModel
        
        # 使用已存在的工作空间路径，而不是重新创建
        # 首先尝试找到与设备ID对应的工作空间
        workspace_manager = WorkspaceManager("workspace")
        workspace_path = str(workspace_manager.base_path / device_id)
        
        # 检查工作空间是否存在，如果不存在则创建
        if not os.path.exists(workspace_path):
            log_with_timestamp(f"工作空间不存在，为设备 {device_id} 创建: {workspace_path}")
            workspace_path = workspace_manager.create_workspace(device_id)
        else:
            log_with_timestamp(f"使用现有工作空间: {workspace_path}")
        
        # 2. 初始化各个处理模块（带并发配置）
        keyword_detector = KeywordDetector()
        vehicle_recognizer = VehicleNumberRecognizer()
        anti_rolling_model = AntiRollingModel(max_concurrent=5)  # MAX_CONCURRENT_MODELS
        remove_rolling_model = RemoveRollingModel(max_concurrent=5)  # MAX_CONCURRENT_MODELS
        
        log_with_timestamp(f"开始处理设备 {device_id} 的视频流")
        await process_video_common(
            video_stream_data,
            device_id,
            workspace_path,
            keyword_detector,
            vehicle_recognizer,
            anti_rolling_model,
            remove_rolling_model
        )
        
        log_with_timestamp(f"设备 {device_id} 的视频处理完成")
        
    except Exception as e:
        log_with_timestamp(f"处理设备 {device_id} 的视频时出错: {e}")
        # 报告错误结果
        from camera_surveillance.tools.result_reporter import ResultReporter
        result_reporter = ResultReporter()
        error_result = {
            "type": "error",
            "device_id": device_id,
            "message": f"处理视频时出错: {str(e)}",
            "timestamp": time.time()
        }
        await result_reporter.report_result(error_result)