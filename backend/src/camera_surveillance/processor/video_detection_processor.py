import os
import time
from typing import List

from camera_surveillance.tools.result_reporter import ResultReporter
from camera_surveillance.tools.frame_extractor import FrameExtractor
from camera_surveillance.tools.keyword_detector import KeywordDetector, OperationType
from camera_surveillance.processor.vehicle_recognizer import VehicleNumberRecognizer
from camera_surveillance.processor.local_models import AntiRollingModel, RemoveRollingModel

result_reporter = ResultReporter()

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
        from camera_surveillance.tools.workspace import log_with_timestamp
        log_with_timestamp(f"处理检测结果时出错: {e}")

async def process_vehicle_number(device_id: str, detection, frame_paths, 
                               vehicle_recognizer: VehicleNumberRecognizer):
    """处理车号确认操作"""
    from camera_surveillance.tools.workspace import log_with_timestamp
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
    from camera_surveillance.tools.workspace import log_with_timestamp
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
    from camera_surveillance.tools.workspace import log_with_timestamp
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