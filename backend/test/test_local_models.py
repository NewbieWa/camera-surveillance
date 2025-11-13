#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
本地模型测试脚本
用于测试 AntiRollingModel 和 RemoveRollingModel 的功能
"""

import os
import sys
import asyncio

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..'))

# 尝试导入模型和anchor，处理可能的依赖问题
from camera_surveillance.processor.local_models import AntiRollingModel, RemoveRollingModel
MODELS_AVAILABLE = True

def test_anti_rolling_model():
    """测试防遛确认模型"""
    if not MODELS_AVAILABLE:
        print("跳过防遛确认模型测试（模型不可用）")
        return
        
    print("测试防遛确认模型...")
    
    try:
        # 创建模型实例
        model = AntiRollingModel()
        print("防遛确认模型创建成功")
        
        # 检查当前目录下是否有测试图像
        test_image_path = 'images/example.jpg'
        # 如果不存在测试图像，可以尝试使用工作空间中的图像
        if not os.path.exists(test_image_path):
            # 查找工作空间中的图像
            workspace_path = "../workspace"
            if os.path.exists(workspace_path):
                for root, dirs, files in os.walk(workspace_path):
                    for file in files:
                        if file.lower().endswith((".jpg", ".jpeg", ".png", ".bmp")):
                            test_image_path = os.path.join(root, file)
                            print(f"找到测试图像: {test_image_path}")
                            break
                    else:
                        continue
                    break
            else:
                # 如果没有找到图像，创建一个简单的示例
                print("未找到测试图像，跳过实际检测测试")
                return
        
        # 测试单个图像处理
        if os.path.exists(test_image_path):
            result = model.process_image(test_image_path)
            print(f"处理图像 {test_image_path} 的结果: {result}")
        else:
            print(f"测试图像不存在: {test_image_path}")
        
        # 测试并行处理多个图像
        image_paths = [test_image_path] * 3  # 使用相同的图像进行测试
        # 过滤掉不存在的图像
        image_paths = [path for path in image_paths if os.path.exists(path)]
        
        if image_paths:
            async def run_parallel_test():
                results = await model.process_images_parallel(image_paths)
                print(f"并行处理结果: {results}")
            
            asyncio.run(run_parallel_test())
        
        print("防遛确认模型测试完成\n")
    except Exception as e:
        print(f"防遛确认模型测试出错: {e}")
        print("可能是由于依赖库版本不兼容（如NumPy 2.x问题）")
        import traceback
        traceback.print_exc()


def test_remove_rolling_model():
    """测试撤遛确认模型"""
    if not MODELS_AVAILABLE:
        print("跳过撤遛确认模型测试（模型不可用）")
        return
        
    print("测试撤遛确认模型...")
    
    try:
        # 创建模型实例
        model = RemoveRollingModel()
        print("撤遛确认模型创建成功")
        
        # 检查当前目录下是否有测试图像
        test_image_path = "images/example.png"
        # 如果不存在测试图像，可以尝试使用工作空间中的图像
        if not os.path.exists(test_image_path):
            # 查找工作空间中的图像
            workspace_path = "../workspace"
            if os.path.exists(workspace_path):
                for root, dirs, files in os.walk(workspace_path):
                    for file in files:
                        if file.lower().endswith((".jpg", ".jpeg", ".png", ".bmp")):
                            test_image_path = os.path.join(root, file)
                            print(f"找到测试图像: {test_image_path}")
                            break
                    else:
                        continue
                    break
            else:
                # 如果没有找到图像，创建一个简单的示例
                print("未找到测试图像，跳过实际检测测试")
                return
        
        # 测试单个图像处理
        if os.path.exists(test_image_path):
            result = model.process_image(test_image_path)
            print(f"处理图像 {test_image_path} 的结果: {result}")
        else:
            print(f"测试图像不存在: {test_image_path}")
        
        # 测试并行处理多个图像
        image_paths = [test_image_path] * 3  # 使用相同的图像进行测试
        # 过滤掉不存在的图像
        image_paths = [path for path in image_paths if os.path.exists(path)]
        
        if image_paths:
            async def run_parallel_test():
                results = await model.process_images_parallel(image_paths)
                print(f"并行处理结果: {results}")
            
            asyncio.run(run_parallel_test())
        
        print("撤遛确认模型测试完成\n")
    except Exception as e:
        print(f"撤遛确认模型测试出错: {e}")
        print("可能是由于依赖库版本不兼容（如NumPy 2.x问题）")
        import traceback
        traceback.print_exc()


def test_model_evaluation_functions():
    """测试模型评估函数"""
    if not MODELS_AVAILABLE:
        print("跳过模型评估函数测试（模型不可用）")
        return
        
    print("测试模型评估函数...")
    
    try:
        # 测试防遛模型评估函数
        anti_model = AntiRollingModel()
        detected_classes = ["person", "barrier", "vehicle"]
        result = anti_model._evaluate_anti_rolling_result(detected_classes)
        print(f"防遛模型评估结果 (输入: {detected_classes}): {result}")
        
        detected_classes = ["background", "sky"]
        result = anti_model._evaluate_anti_rolling_result(detected_classes)
        print(f"防遛模型评估结果 (输入: {detected_classes}): {result}")
        
        # 测试撤遛模型评估函数
        remove_model = RemoveRollingModel()
        detected_classes = ["person", "barrier", "vehicle"]
        result = remove_model._evaluate_remove_rolling_result(detected_classes)
        print(f"撤遛模型评估结果 (输入: {detected_classes}): {result}")
        
        detected_classes = ["background", "sky"]
        result = remove_model._evaluate_remove_rolling_result(detected_classes)
        print(f"撤遛模型评估结果 (输入: {detected_classes}): {result}")
        
        print("模型评估函数测试完成\n")
    except Exception as e:
        print(f"模型评估函数测试出错: {e}")
        import traceback
        traceback.print_exc()


def main():
    """主函数"""
    print("开始测试本地模型模块...\n")
    
    if not MODELS_AVAILABLE:
        print("警告: 模型模块不可用，可能由于依赖库版本不兼容")
        print("请尝试降级 NumPy 到 1.x 版本:")
        print("  pip install 'numpy<2'")
        print()
    
    # 运行各个测试
    test_model_evaluation_functions()
    test_anti_rolling_model()
    test_remove_rolling_model()
    
    print("所有本地模型测试完成!")


if __name__ == "__main__":
    main()