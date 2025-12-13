# 摄像头监控系统

这是一个全面的摄像头监控系统，提供实时视频分析、物体检测和智能监控功能。

## 项目架构

系统分为两个主要组件：

### 后端 (Backend)
- 使用 Python 和 FastAPI 构建
- 处理视频处理、物体检测和 AI 分析
- 管理摄像头流和视频流
- 为前端提供 RESTful API

### 前端 (Frontend)
- 基于 Web 的界面，使用 HTML、CSS 和 JavaScript 构建
- 实时视频显示和交互
- 用于监控和控制的用户界面

## 系统要求

- Python 3.11+
- Node.js (用于前端开发)
- FFmpeg 用于视频处理
- YOLO 物体检测模型
- uv (Python 包管理器)

## 安装

1. 克隆仓库：
   ```bash
   git clone git@github.com:NewbieWa/camera-surveillance.gi
   cd camera-surveillance
   ```

2. 设置项目：
   ```bash
   # 使用 uv 创建虚拟环境 (可选，项目根目录已有 .venv)
   uv venv .venv
   source .venv/bin/activate  # Windows系统: .venv\Scripts\activate
   # 使用 uv 安装根目录下的 pyproject.toml 中定义的依赖
   uv sync
   ```

3. 设置前端：
   ```bash
   cd frontend
   npm install
   ```

## 运行系统

### 启动整个系统：
```bash
./start_all.sh
```

### 或分别启动组件：

后端：
```bash
cd backend
./start.sh
# 或
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

前端：
```bash
cd frontend
# 使用任何 Web 服务器提供静态文件服务
python -m http.server 8080  # 使用 Python 内置服务器的示例
```

## 功能特性

- 实时视频监控
- 物体检测和跟踪
- 音频转录功能
- 视频分段处理
- AI 驱动的分析