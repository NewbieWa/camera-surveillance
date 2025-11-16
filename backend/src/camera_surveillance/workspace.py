import os
import time
from typing import Optional
from pathlib import Path

class WorkspaceManager:
    """工作空间管理器，用于创建和管理任务的临时工作目录"""
    
    def __init__(self, base_path: str = "workspace"):
        """
        初始化工作空间管理器
        
        Args:
            base_path: 工作空间基础路径
        """
        self.base_path = Path(base_path)
        self.base_path.mkdir(exist_ok=True)
    
    def create_workspace(self, device_id: str) -> str:
        """
        为指定设备创建工作空间
        
        Args:
            device_id: 设备编码
            
        Returns:
            工作空间路径
        """
        # 如果设备ID已经包含时间戳格式（如camera_1234567890），则不重复添加时间戳
        if device_id.startswith("camera_") and "_" in device_id and device_id.split("_")[-1].isdigit():
            workspace_name = device_id
        else:
            timestamp = int(time.time())
            workspace_name = f"{device_id}_{timestamp}"
            
        workspace_path = self.base_path / workspace_name
        workspace_path.mkdir(exist_ok=True)
        return str(workspace_path)
    
    def cleanup_workspace(self, workspace_path: str, max_age_hours: int = 24):
        """
        清理过期的工作空间
        
        Args:
            workspace_path: 工作空间路径
            max_age_hours: 最大保留小时数
        """
        workspace = Path(workspace_path)
        if workspace.exists() and workspace.is_dir():
            # 检查是否过期
            age_seconds = time.time() - workspace.stat().st_ctime
            if age_seconds > max_age_hours * 3600:
                import shutil
                shutil.rmtree(workspace)