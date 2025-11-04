#!/bin/bash

# 启动后端服务的脚本

# 检查是否在正确的目录
if [ ! -f "main.py" ]; then
    echo "错误: 请在backend目录中运行此脚本"
    exit 1
fi

# 检查Python环境
if ! command -v python3 &> /dev/null; then
    echo "错误: 未找到Python3"
    exit 1
fi

# 检查依赖
if [ ! -f "requirements.txt" ]; then
    echo "警告: 未找到requirements.txt文件"
else
    echo "检查并安装依赖..."
    pip install -r requirements.txt
fi

# 启动服务
echo "启动后端服务..."
echo "服务将在 http://localhost:8000 上运行"
echo "按 Ctrl+C 停止服务"

python3 main.py