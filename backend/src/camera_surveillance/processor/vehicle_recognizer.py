import os
from typing import Optional, Dict, Any
from pathlib import Path
from datetime import datetime

def log_with_timestamp(message: str):
    """带时间戳的日志输出函数"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")

class VehicleNumberRecognizer:
    """车辆编号识别器，使用阿里云视觉大模型"""
    
    def __init__(self):
        """初始化车辆编号识别器"""
        # 导入阿里云dashscope SDK
        try:
            from dashscope import MultiModalConversation
            self.MultiModalConversation = MultiModalConversation
        except ImportError:
            log_with_timestamp("警告: 未安装dashscope库，请先安装: pip install dashscope")
            raise
    
    def recognize_vehicle_number(self, image_path: str) -> Optional[str]:
        """
        识别图像中的车辆编号
        
        Args:
            image_path: 图像文件路径
            
        Returns:
            识别到的车辆编号，如果未识别到则返回None
        """
        try:
            # 构建图像路径
            abs_image_path = Path(image_path).resolve()
            image_url = f"file://{abs_image_path}"
            
            # 构建消息
            messages = [
                {
                    'role': 'user',
                    'content': [
                        {'image': image_url},
                        {'text': '请识别图中的车辆编号或车牌号码，只返回识别到的数字字母组合，如果无法识别则返回"未识别"。'}
                    ]
                }
            ]
            
            # 调用阿里云视觉大模型
            response = self.MultiModalConversation.call(
                # 从环境变量获取API KEY
                api_key=os.getenv('DASHSCOPE_API_KEY'),
                model='qwen3-vl-8b-instruct',  # 使用适当的视觉模型
                messages=messages
            )

            log_with_timestamp(f"vehicle response: {response}")
            
            # 解析响应
            if response and "output" in response and "choices" in response["output"]:
                content = response["output"]["choices"][0]["message"]["content"]
                if isinstance(content, list) and len(content) > 0:
                    text_result = content[0]["text"].strip()
                    # 如果模型返回"未识别"，则返回None
                    if text_result == "未识别" or "未识别" in text_result or not text_result:
                        return None
                    return text_result
            
            return None
        except Exception as e:
            log_with_timestamp(f"识别车辆编号时出错: {e}")
            return None