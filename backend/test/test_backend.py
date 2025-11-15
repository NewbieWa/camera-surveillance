#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
后端服务测试脚本
用于测试各个模块的功能
"""

import os
import sys
import time
import asyncio
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from camera_surveillance.workspace import WorkspaceManager
from camera_surveillance.keyword_detector import KeywordDetector, OperationType
from camera_surveillance.result_reporter import ResultReporter

def test_workspace_manager():
    """测试工作空间管理器"""
    print("测试工作空间管理器...")
    
    workspace_manager = WorkspaceManager("test_workspace")
    
    # 创建工作空间
    device_id = "test_device_001"
    workspace_path = workspace_manager.create_workspace(device_id)
    print(f"创建工作空间: {workspace_path}")
    
    # 检查目录是否存在
    assert os.path.exists(workspace_path), "工作空间目录未创建成功"
    print("工作空间创建成功")
    
    print("工作空间管理器测试完成\n")

def test_keyword_detector():
    """测试关键词检测器"""
    print("测试关键词检测器...")
    
    detector = KeywordDetector()
    
    # 测试车号确认关键词
    test_text1 = "现在进行车号确认操作，请注意"
    detections1 = detector.detect_keywords(test_text1)
    print(f"检测文本: {test_text1}")
    print(f"检测结果: {detections1}")
    
    # 测试防遛设置关键词
    test_text2 = "铁鞋设置完成，手闸已拧紧"
    detections2 = detector.detect_keywords(test_text2)
    print(f"检测文本: {test_text2}")
    print(f"检测结果: {detections2}")
    
    # 测试撤遛设置关键词
    test_text3 = "铁鞋撤除完毕，手闸已松开"
    detections3 = detector.detect_keywords(test_text3)
    print(f"检测文本: {test_text3}")
    print(f"检测结果: {detections3}")
    
    print("关键词检测器测试完成\n")

def test_result_reporter():
    """测试结果报告器"""
    print("测试结果报告器...")
    
    reporter = ResultReporter()
    
    # 创建车辆编号识别结果
    vehicle_result = reporter.create_vehicle_number_result(
        "test_device_001",
        "ABC12345",
        ["/path/to/frame1.jpg", "/path/to/frame2.jpg"],
        time.time()
    )
    print(f"车辆编号识别结果: {vehicle_result}")
    
    # 创建防遛确认结果
    anti_rolling_result = reporter.create_anti_rolling_result(
        "test_device_001",
        True,
        ["/path/to/frame1.jpg", "/path/to/frame2.jpg"],
        time.time()
    )
    print(f"防遛确认结果: {anti_rolling_result}")
    
    # 创建撤遛确认结果
    remove_rolling_result = reporter.create_remove_rolling_result(
        "test_device_001",
        False,
        ["/path/to/frame1.jpg", "/path/to/frame2.jpg"],
        time.time()
    )
    print(f"撤遛确认结果: {remove_rolling_result}")
    
    print("结果报告器测试完成\n")

async def test_async_functions():
    """测试异步功能"""
    print("测试异步功能...")
    
    reporter = ResultReporter()
    
    # 测试异步报告结果
    test_result = {
        "type": "test",
        "message": "异步测试消息",
        "timestamp": time.time()
    }
    
    await reporter.report_result(test_result)
    print("异步报告结果测试完成")
    
    print("异步功能测试完成\n")

def main():
    """主函数"""
    print("开始测试后端服务模块...\n")
    
    # 运行各个测试
    test_workspace_manager()
    test_keyword_detector()
    test_result_reporter()
    
    # 运行异步测试
    asyncio.run(test_async_functions())
    
    print("所有测试完成!")

if __name__ == "__main__":
    main()