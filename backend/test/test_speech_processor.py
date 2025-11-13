#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
SpeechProcessor 测试脚本
"""

import os
import sys
import logging
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

def test_speech_processor():
    """测试语音处理器功能"""
    try:
        # 导入模块
        from core.processor.speech_processor import SpeechProcessor
        
        # 创建语音处理器实例
        processor = SpeechProcessor()
        print("SpeechProcessor 实例创建成功")
        
        # 测试从URL转录音频（如果网络可用）
        print("测试从URL转录音频...")
        result = processor.transcribe_url(
            'https://dashscope.oss-cn-beijing.aliyuncs.com/samples/audio/paraformer/hello_world_female2.wav'
        )
        print(f"URL转录结果: {result}")
        
        print("SpeechProcessor 测试完成")
        
    except Exception as e:
        print(f"测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_speech_processor()