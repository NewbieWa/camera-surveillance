import asyncio
import concurrent.futures
from abc import ABC, abstractmethod
from typing import Optional, List, Tuple
from pathlib import Path
import time
from datetime import datetime
import os
import sys

# 添加项目根目录到Python路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..'))

# 尝试导入必要的库，处理可能的依赖问题
try:
    import cv2
    import torch
    from ultralytics import YOLO
    DEPENDENCIES_AVAILABLE = True
except ImportError as e:
    print(f"警告: 无法导入必要的依赖库: {e}")
    DEPENDENCIES_AVAILABLE = False

def log_with_timestamp(message: str):
    """带时间戳的日志输出函数"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")

class BaseModelInterface(ABC):
    """本地模型接口基类"""
    
    def __init__(self, max_concurrent: int = 5):
        """
        初始化模型基类
        
        Args:
            max_concurrent: 最大并发调用数量
        """
        self.max_concurrent = max_concurrent
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=max_concurrent)
    
    @abstractmethod
    def process_image(self, image_path: str) -> Optional[bool]:
        """
        处理单个图像并返回结果
        
        Args:
            image_path: 图像文件路径
            
        Returns:
            处理结果，True表示成功，False表示失败，None表示无法处理
        """
        pass
    
    async def process_images_parallel(self, image_paths: List[str]) -> List[Tuple[str, Optional[bool]]]:
        """
        并行处理多个图像
        
        Args:
            image_paths: 图像文件路径列表
            
        Returns:
            处理结果列表，每个元素为(图像路径, 处理结果)
        """
        loop = asyncio.get_event_loop()
        tasks = []
        
        # 创建并发任务
        for image_path in image_paths:
            task = loop.run_in_executor(
                self.executor, 
                self._process_image_sync, 
                image_path
            )
            tasks.append(task)
        
        # 等待所有任务完成
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 组合结果
        processed_results = []
        for image_path, result in zip(image_paths, results):
            if isinstance(result, Exception):
                log_with_timestamp(f"处理图像 {image_path} 时出错: {result}")
                processed_results.append((image_path, None))
            else:
                processed_results.append((image_path, result))
        
        return processed_results
    
    def _process_image_sync(self, image_path: str) -> Optional[bool]:
        """
        同步处理单个图像的包装函数
        
        Args:
            image_path: 图像文件路径
            
        Returns:
            处理结果
        """
        try:
            # 记录开始时间
            start_time = time.time()
            result = self.process_image(image_path)
            end_time = time.time()
            
            # 记录处理时间
            processing_time = end_time - start_time
            log_with_timestamp(f"处理图像 {image_path} 耗时: {processing_time:.2f}秒")
            
            return result
        except Exception as e:
            log_with_timestamp(f"处理图像 {image_path} 时出错: {e}")
            return None
    
    def __del__(self):
        """析构函数，关闭线程池"""
        if hasattr(self, 'executor'):
            self.executor.shutdown(wait=True)

class AntiRollingModel(BaseModelInterface):
    """防遛确认模型A"""
    
    def __init__(self, model_path: str = None, conf_threshold: float = 0.8, max_concurrent: int = 5):
        """
        初始化防遛确认模型
        
        Args:
            model_path: 模型文件路径
            conf_threshold: 置信度阈值
            max_concurrent: 最大并发调用数量
        """
        super().__init__(max_concurrent)
        
        print(f"Current working directory: {os.getcwd()}")
        if model_path is None:
            self.model_path = 'src/camera_surveillance/models/det_20250924.pt'
        else:
            self.model_path = model_path
        
        self.conf_threshold = conf_threshold
        self.model = None
        self.device = None
        
        if DEPENDENCIES_AVAILABLE:
            self._load_model()
        else:
            log_with_timestamp("依赖库不可用，防遛确认模型无法加载")
    
    def _load_model(self):
        print(f"Current working directory: {os.getcwd()}")

        """加载模型"""
        try:
            # 根据系统自动判断用mps还是gpu还是cpu
            if torch.backends.mps.is_available():
                self.device = "mps"
            elif torch.cuda.is_available():
                self.device = "cuda"
            else:
                self.device = "cpu"
            
            # 加载模型
            self.model = YOLO(self.model_path)
            log_with_timestamp(f"防遛确认模型加载成功，设备: {self.device}")
        except Exception as e:
            log_with_timestamp(f"加载防遛确认模型失败: {e}")
            raise
    
    def process_image(self, image_path: str) -> Optional[bool]:
        """
        处理图像进行防遛确认
        
        Args:
            image_path: 图像文件路径
            
        Returns:
            True表示防遛设置正确，False表示设置不正确，None表示无法判断
        """
        log_with_timestamp(f"调用防遛确认模型处理图像: {image_path}")
        
        # 检查依赖是否可用
        if not DEPENDENCIES_AVAILABLE:
            log_with_timestamp("依赖库不可用，无法处理图像")
            return None
            
        if self.model is None:
            log_with_timestamp("模型未加载")
            return None
        
        try:
            # 使用模型进行预测
            results = self.model(image_path, conf=self.conf_threshold, device=self.device)
            
            # 检查是否检测到物体
            if len(results[0].boxes) > 0:
                detected_classes = []
                for box in results[0].boxes:
                    class_id = int(box.cls)
                    class_name = self.model.names[class_id]
                    detected_classes.append(class_name)
                
                log_with_timestamp(f"检测到的物体类别: {detected_classes}")
                
                # 根据检测到的物体判断防遛设置是否正确
                # 例如：如果检测到特定类别的物体（如"防遛"相关物体）则返回True
                # 这里可以根据实际需求调整判断逻辑
                # 假设检测到某些特定类别表示设置正确
                # 可以根据业务需求自定义判断逻辑
                # 例如: if 'anti_rolling' in detected_classes: return True
                return self._evaluate_anti_rolling_result(detected_classes)
            else:
                log_with_timestamp("未检测到物体")
                return False
        except Exception as e:
            log_with_timestamp(f"处理图像时出错: {e}")
            return None
    
    def _evaluate_anti_rolling_result(self, detected_classes: List[str]) -> Optional[bool]:
        """
        评估防遛检测结果
        
        Args:
            detected_classes: 检测到的类别列表
            
        Returns:
            True表示防遛设置正确，False表示设置不正确，None表示无法判断
        """
        # 这里可以根据实际业务需求调整判断逻辑
        # 示例：如果检测到特定类别的物体则认为防遛设置正确
        # 例如，如果检测到'person'、'barrier'等类别，根据具体情况判断
        
        # 假设检测到某些类别表示防遛设置正确，这里只是一个示例
        # 在实际应用中应根据具体模型训练的类别和业务需求进行调整
        for class_name in detected_classes:
            # 如果检测到相关物体，可以根据具体逻辑判断是否正确设置
            # 这是一个示例逻辑，实际应根据模型训练的目标进行判断
            if 'person' in class_name.lower() or 'barrier' in class_name.lower():
                # 这里只是示例逻辑，实际应根据具体情况进行调整
                return True
        
        # 如果没有检测到相关物体或无法判断，可以根据业务需求返回False或None
        return False

class RemoveRollingModel(BaseModelInterface):
    """撤遛确认模型B"""
    
    def __init__(self, model_path: str = None, conf_threshold: float = 0.8, max_concurrent: int = 5):
        """
        初始化撤遛确认模型
        
        Args:
            model_path: 模型文件路径
            conf_threshold: 置信度阈值
            max_concurrent: 最大并发调用数量
        """
        super().__init__(max_concurrent)
        
        print(f"Current working directory: {os.getcwd()}")
        if model_path is None:
            self.model_path = "src/camera_surveillance/models/det_20250924.pt"
        else:
            self.model_path = model_path
        
        self.conf_threshold = conf_threshold
        self.model = None
        self.device = None
        
        if DEPENDENCIES_AVAILABLE:
            self._load_model()
        else:
            log_with_timestamp("依赖库不可用，撤遛确认模型无法加载")
    
    def _load_model(self):
        """加载模型"""
        try:
            # 根据系统自动判断用mps还是gpu还是cpu
            if torch.backends.mps.is_available():
                self.device = "mps"
            elif torch.cuda.is_available():
                self.device = "cuda"
            else:
                self.device = "cpu"
            
            # 加载模型
            self.model = YOLO(self.model_path)
            log_with_timestamp(f"撤遛确认模型加载成功，设备: {self.device}")
        except Exception as e:
            log_with_timestamp(f"加载撤遛确认模型失败: {e}")
            raise
    
    def process_image(self, image_path: str) -> Optional[bool]:
        """
        处理图像进行撤遛确认
        
        Args:
            image_path: 图像文件路径
            
        Returns:
            True表示撤遛设置正确，False表示设置不正确，None表示无法判断
        """
        log_with_timestamp(f"调用撤遛确认模型处理图像: {image_path}")
        
        # 检查依赖是否可用
        if not DEPENDENCIES_AVAILABLE:
            log_with_timestamp("依赖库不可用，无法处理图像")
            return None
            
        if self.model is None:
            log_with_timestamp("模型未加载")
            return None
        
        try:
            # 使用模型进行预测
            results = self.model(image_path, conf=self.conf_threshold, device=self.device)
            
            # 检查是否检测到物体
            if len(results[0].boxes) > 0:
                detected_classes = []
                for box in results[0].boxes:
                    class_id = int(box.cls)
                    class_name = self.model.names[class_id]
                    detected_classes.append(class_name)
                
                log_with_timestamp(f"检测到的物体类别: {detected_classes}")
                
                # 根据检测到的物体判断撤遛设置是否正确
                # 例如：如果检测到特定类别的物体（如"撤遛"相关物体）则返回True
                # 这里可以根据实际需求调整判断逻辑
                return self._evaluate_remove_rolling_result(detected_classes)
            else:
                log_with_timestamp("未检测到物体")
                return False
        except Exception as e:
            log_with_timestamp(f"处理图像时出错: {e}")
            return None
    
    def _evaluate_remove_rolling_result(self, detected_classes: List[str]) -> Optional[bool]:
        """
        评估撤遛检测结果
        
        Args:
            detected_classes: 检测到的类别列表
            
        Returns:
            True表示撤遛设置正确，False表示设置不正确，None表示无法判断
        """
        # 这里可以根据实际业务需求调整判断逻辑
        # 示例：如果检测到特定类别的物体则认为撤遛设置正确
        # 例如，如果检测到某些类别表示撤遛操作已完成
        for class_name in detected_classes:
            # 如果检测到相关物体，可以根据具体逻辑判断是否正确设置
            # 这是一个示例逻辑，实际应根据模型训练的目标进行判断
            if 'person' in class_name.lower() or 'barrier' in class_name.lower():
                # 这里只是示例逻辑，实际应根据具体情况进行调整
                return True
        
        # 如果没有检测到相关物体或无法判断，可以根据业务需求返回False或None
        return False