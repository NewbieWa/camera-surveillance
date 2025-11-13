import json
import asyncio
from typing import List, Dict, Any
from pathlib import Path
from datetime import datetime

def log_with_timestamp(message: str):
    """带时间戳的日志输出函数"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")

class ResultReporter:
    """结果报告器，用于将处理结果回传给前端"""
    
    def __init__(self):
        """初始化结果报告器"""
        self.websocket_connections = []
    
    def add_websocket_connection(self, websocket):
        """
        添加WebSocket连接
        
        Args:
            websocket: WebSocket连接对象
        """
        if websocket not in self.websocket_connections:
            self.websocket_connections.append(websocket)
    
    def remove_websocket_connection(self, websocket):
        """
        移除WebSocket连接
        
        Args:
            websocket: WebSocket连接对象
        """
        if websocket in self.websocket_connections:
            self.websocket_connections.remove(websocket)
    
    async def report_result(self, result_data: Dict[str, Any]):
        """
        报告处理结果到所有连接的前端
        
        Args:
            result_data: 结果数据
        """
        # 转换为JSON格式
        message = json.dumps(result_data, ensure_ascii=False)
        
        # 发送到所有连接的客户端
        for websocket in self.websocket_connections:
            try:
                await websocket.send_text(message)
            except Exception as e:
                log_with_timestamp(f"发送结果到前端时出错: {e}")
                # 移除失效的连接
                self.remove_websocket_connection(websocket)
    
    def create_vehicle_number_result(self, device_id: str, vehicle_number: str, 
                                   frame_paths: List[str], timestamp: float) -> Dict[str, Any]:
        """
        创建车辆编号识别结果
        
        Args:
            device_id: 设备ID
            vehicle_number: 识别到的车辆编号
            frame_paths: 帧图像路径列表
            timestamp: 时间戳
            
        Returns:
            结果数据字典
        """
        return {
            "type": "vehicle_number",
            "device_id": device_id,
            "result": f"识别车号：{vehicle_number}",
            "vehicle_number": vehicle_number,
            "frames": frame_paths,
            "timestamp": timestamp,
            "status": "success"
        }
    
    def create_vehicle_number_failure(self, device_id: str, frame_paths: List[str], 
                                    timestamp: float) -> Dict[str, Any]:
        """
        创建车辆编号识别失败结果
        
        Args:
            device_id: 设备ID
            frame_paths: 帧图像路径列表
            timestamp: 时间戳
            
        Returns:
            结果数据字典
        """
        return {
            "type": "vehicle_number",
            "device_id": device_id,
            "result": "未识别车号",
            "vehicle_number": None,
            "frames": frame_paths,
            "timestamp": timestamp,
            "status": "failure"
        }
    
    def create_anti_rolling_result(self, device_id: str, is_success: bool, 
                                 frame_paths: List[str], timestamp: float) -> Dict[str, Any]:
        """
        创建防遛确认结果
        
        Args:
            device_id: 设备ID
            is_success: 是否成功
            frame_paths: 帧图像路径列表
            timestamp: 时间戳
            
        Returns:
            结果数据字典
        """
        result_text = "防遛确认" if is_success else "防遛未确认"
        return {
            "type": "anti_rolling",
            "device_id": device_id,
            "result": result_text,
            "success": is_success,
            "frames": frame_paths,
            "timestamp": timestamp,
            "status": "success" if is_success else "failure"
        }
    
    def create_remove_rolling_result(self, device_id: str, is_success: bool, 
                                   frame_paths: List[str], timestamp: float) -> Dict[str, Any]:
        """
        创建撤遛确认结果
        
        Args:
            device_id: 设备ID
            is_success: 是否成功
            frame_paths: 帧图像路径列表
            timestamp: 时间戳
            
        Returns:
            结果数据字典
        """
        result_text = "撤遛确认" if is_success else "撤遛未确认"
        return {
            "type": "remove_rolling",
            "device_id": device_id,
            "result": result_text,
            "success": is_success,
            "frames": frame_paths,
            "timestamp": timestamp,
            "status": "success" if is_success else "failure"
        }