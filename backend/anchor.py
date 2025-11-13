"""
锚点文件，用于定位项目中常用的目录位置
"""

import os


def get_images_dir():
    """获取 images 目录的绝对路径"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    images_dir = os.path.join(current_dir, 'images')
    return images_dir


def get_test_dir():
    """获取 test 目录的绝对路径"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    test_dir = os.path.join(current_dir, 'test')
    return test_dir


def get_models_dir():
    """获取 models 目录的绝对路径"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    models_dir = os.path.join(current_dir, 'src', 'camera_surveillance', 'models')
    return models_dir