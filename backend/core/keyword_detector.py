import re
from typing import List, Tuple, Dict, Optional
from dataclasses import dataclass
from enum import Enum

class OperationType(Enum):
    """操作类型枚举"""
    VEHICLE_NUMBER = "车号确认"
    ANTI_ROLLING = "铁鞋设置手闸拧紧"
    REMOVE_ROLLING = "铁鞋撤除手闸松开"
    UNKNOWN = "未知"

@dataclass
class DetectionResult:
    """检测结果数据类"""
    operation_type: OperationType
    timestamp: float
    confidence: float
    text: str

class KeywordDetector:
    """关键词检测器，用于识别音频中的特定关键词"""
    
    def __init__(self):
        """初始化关键词检测器"""
        # 定义关键词模式
        self.keyword_patterns = {
            OperationType.VEHICLE_NUMBER: [
                r"车号确认",
                r"车号核对",
                r"确认车号",
                r"核对车号"
            ],
            OperationType.ANTI_ROLLING: [
                r"铁鞋设置",
                r"手闸拧紧",
                r"防遛设置",
                r"设置防遛"
            ],
            OperationType.REMOVE_ROLLING: [
                r"铁鞋撤除",
                r"手闸松开",
                r"撤除防遛",
                r"松开手闸"
            ]
        }
    
    def detect_keywords(self, text: str) -> List[DetectionResult]:
        """
        在文本中检测关键词
        
        Args:
            text: 输入文本
            
        Returns:
            检测到的结果列表
        """
        results = []
        
        # 遍历所有操作类型和对应的关键词模式
        for operation_type, patterns in self.keyword_patterns.items():
            for pattern in patterns:
                # 搜索匹配的关键词
                matches = re.finditer(pattern, text, re.IGNORECASE)
                for match in matches:
                    # 计算置信度（基于匹配长度和位置）
                    confidence = min(len(match.group()) / 20.0, 1.0)  # 简单置信度计算
                    
                    result = DetectionResult(
                        operation_type=operation_type,
                        timestamp=0.0,  # 需要根据实际音频时间戳设置
                        confidence=confidence,
                        text=match.group()
                    )
                    results.append(result)
        
        return results
    
    def detect_keywords_with_context(self, texts: List[Tuple[float, str]]) -> List[DetectionResult]:
        """
        在带时间戳的文本列表中检测关键词
        
        Args:
            texts: 带时间戳的文本列表 [(timestamp, text), ...]
            
        Returns:
            检测到的结果列表
        """
        results = []
        
        for timestamp, text in texts:
            detections = self.detect_keywords(text)
            for detection in detections:
                detection.timestamp = timestamp
                results.append(detection)
        
        return results