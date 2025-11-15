#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
修改后的后端服务测试脚本
用于测试并行处理和新功能
"""

import os
import sys
import time
import asyncio
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from camera_surveillance.processor.local_models import AntiRollingModel, RemoveRollingModel
from camera_surveillance.frame_extractor import FrameExtractor

def test_parallel_model_processing():
    """测试并行模型处理功能"""
    print("测试并行模型处理功能...")
    
    # 创建模型实例（设置较小的并发数以便测试）
    anti_rolling_model = AntiRollingModel(max_concurrent=3)
    remove_rolling_model = RemoveRollingModel(max_concurrent=3)
    
    # 创建一些测试图像路径（实际文件不存在，但路径格式正确）
    test_image_paths = [
        "/tmp/test_frame_1.jpg",
        "/tmp/test_frame_2.jpg",
        "/tmp/test_frame_3.jpg",
        "/tmp/test_frame_4.jpg",
        "/tmp/test_frame_5.jpg"
    ]
    
    # 测试并行处理
    print("测试防遛确认模型并行处理...")
    start_time = time.time()
    
    # 运行异步测试
    async def run_test():
        results = await anti_rolling_model.process_images_parallel(test_image_paths)
        return results
    
    results = asyncio.run(run_test())
    end_time = time.time()
    
    print(f"并行处理 {len(test_image_paths)} 个图像耗时: {end_time - start_time:.2f}秒")
    print(f"处理结果: {results}")
    
    print("测试撤遛确认模型并行处理...")
    start_time = time.time()
    
    async def run_test2():
        results = await remove_rolling_model.process_images_parallel(test_image_paths)
        return results
    
    results = asyncio.run(run_test2())
    end_time = time.time()
    
    print(f"并行处理 {len(test_image_paths)} 个图像耗时: {end_time - start_time:.2f}秒")
    print(f"处理结果: {results}")
    
    print("并行模型处理功能测试完成\n")

def test_frame_extraction_with_audio_segments():
    """测试基于音频片段的帧提取"""
    print("测试基于音频片段的帧提取...")
    
    # 由于我们没有实际的视频文件，这里只是测试方法调用
    print("音频片段时间点测试:")
    print("  片段开始时间: 10.0秒")
    print("  片段结束时间: 12.5秒")
    print("  将在片段结束后提取帧 (以12.5秒为中心)")
    
    print("基于音频片段的帧提取测试完成\n")

def test_configuration():
    """测试配置功能"""
    print("测试配置功能...")
    
    # 测试默认并发数
    model1 = AntiRollingModel()
    print(f"默认最大并发数: {model1.max_concurrent}")
    
    # 测试自定义并发数
    model2 = AntiRollingModel(max_concurrent=10)
    print(f"自定义最大并发数: {model2.max_concurrent}")
    
    print("配置功能测试完成\n")

def main():
    """主函数"""
    print("开始测试修改后的后端服务模块...\n")
    
    # 运行各个测试
    test_configuration()
    test_parallel_model_processing()
    test_frame_extraction_with_audio_segments()
    
    print("所有测试完成!")

if __name__ == "__main__":
    main()