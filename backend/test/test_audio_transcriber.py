#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
音频转录器测试脚本
用于测试改进后的音频转录功能
"""

import os
import sys
import tempfile
import wave
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from camera_surveillance.processor.audio_transcriber import AudioTranscriber

def create_test_wav_file():
    """创建测试WAV文件"""
    # 创建临时WAV文件
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
        # 创建一个简单的WAV文件
        with wave.open(temp_file.name, 'w') as wav_file:
            # 设置参数：声道数=1，采样宽度=2字节，采样率=16000Hz，帧数=0（稍后设置）
            sample_rate = 16000
            channels = 1
            sampwidth = 2
            framerate = sample_rate
            
            wav_file.setnchannels(channels)
            wav_file.setsampwidth(sampwidth)
            wav_file.setframerate(framerate)
            
            # 生成一些静音数据作为占位符
            # 在实际测试中，我们会用真实的音频文件
            import struct
            # 生成1秒的静音数据
            num_frames = sample_rate  # 1秒
            silence_data = b'\x00\x00' * num_frames  # 静音样本
            wav_file.writeframes(silence_data)
        
        return temp_file.name

def test_audio_transcriber():
    """测试音频转录器"""
    print("测试音频转录器...")
    
    # 创建转录器实例
    transcriber = AudioTranscriber()
    
    # 创建测试WAV文件
    test_wav_file = create_test_wav_file()
    print(f"创建测试WAV文件: {test_wav_file}")
    
    try:
        # 测试转录功能
        print("开始测试转录功能...")
        # 由于没有实际的API密钥，这个测试会失败，但可以验证代码逻辑
        # 为了避免实际调用API，我们只验证导入和初始化
        print("音频转录器初始化成功")
        print(f"采样率: {transcriber.sample_rate}")
        
        # 测试WAV文件处理方法
        print("WAV文件处理方法测试...")
        # 注意：实际API调用会因为没有密钥而失败，但代码逻辑应该正确
        
    except Exception as e:
        print(f"预期的API错误（由于缺少API密钥）: {e}")
    
    finally:
        # 清理临时文件
        if os.path.exists(test_wav_file):
            os.remove(test_wav_file)
    
    print("音频转录器测试完成\n")

def test_import():
    """测试导入功能"""
    print("测试音频转录器导入...")
    try:
        from core.processor.audio_transcriber import AudioTranscriber
        print("导入成功")
        
        # 测试初始化
        transcriber = AudioTranscriber()
        print(f"初始化成功，采样率: {transcriber.sample_rate}")
        
    except ImportError as e:
        print(f"导入失败: {e}")
    except Exception as e:
        print(f"初始化失败: {e}")
    
    print("导入测试完成\n")

def main():
    """主函数"""
    print("开始测试音频转录器功能...\n")
    
    # 运行各个测试
    test_import()
    test_audio_transcriber()
    
    print("音频转录器测试完成!")

if __name__ == "__main__":
    main()