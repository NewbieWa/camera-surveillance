#!/bin/bash

# 启动前后端服务的脚本

# 定义颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 定义端口
BACKEND_PORT=8000
FRONTEND_PORT=8080

echo -e "${GREEN}=================================${NC}"
echo -e "${GREEN}  启动外勤作业智能分析系统${NC}"
echo -e "${GREEN}=================================${NC}"

# 检查是否有进程占用端口
check_port() {
    local port=$1
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        echo -e "${YELLOW}端口 $port 已被占用${NC}"
        return 0
    else
        return 1
    fi
}

# 杀死占用端口的进程
kill_port_process() {
    local port=$1
    local pid=$(lsof -Pi :$port -sTCP:LISTEN -t 2>/dev/null)
    if [ ! -z "$pid" ]; then
        echo -e "${YELLOW}正在终止占用端口 $port 的进程 (PID: $pid)${NC}"
        kill -9 $pid 2>/dev/null
        sleep 2
    fi
}

# 检查并清理端口
echo -e "${YELLOW}检查端口占用情况...${NC}"
if check_port $BACKEND_PORT; then
    kill_port_process $BACKEND_PORT
fi

if check_port $FRONTEND_PORT; then
    kill_port_process $FRONTEND_PORT
fi

# 启动后端服务
echo -e "${GREEN}启动后端服务...${NC}"
cd /Users/wanglei/workStore/code/workSource/camera-surveillance/backend
python3 main.py > backend.log 2>&1 &
BACKEND_PID=$!

# 等待后端服务启动
sleep 3

# 检查后端服务是否启动成功
# 增加重试机制以应对启动延迟
sleep 2  # 额外等待确保服务已完全启动
for i in {1..10}; do
    if curl -s http://localhost:$BACKEND_PORT/ > /dev/null; then
        echo -e "${GREEN}✓ 后端服务启动成功 (PID: $BACKEND_PID)${NC}"
        break
    else
        if [ $i -eq 10 ]; then
            echo -e "${RED}✗ 后端服务启动失败${NC}"
            if [ -f backend.log ]; then
                cat backend.log
            fi
            exit 1
        fi
        sleep 1
    fi
done

# 启动前端服务
echo -e "${GREEN}启动前端服务...${NC}"
cd /Users/wanglei/workStore/code/workSource/camera-surveillance/frontend
python3 -m http.server $FRONTEND_PORT > frontend.log 2>&1 &
FRONTEND_PID=$!

# 等待前端服务启动
sleep 2

# 检查前端服务是否启动成功
if curl -s http://localhost:$FRONTEND_PORT/ > /dev/null; then
    echo -e "${GREEN}✓ 前端服务启动成功 (PID: $FRONTEND_PID)${NC}"
else
    echo -e "${RED}✗ 前端服务启动失败${NC}"
    cat frontend.log
    # 终止后端服务
    kill $BACKEND_PID 2>/dev/null
    exit 1
fi

echo -e "${GREEN}=================================${NC}"
echo -e "${GREEN}系统启动完成！${NC}"
echo -e "${GREEN}=================================${NC}"
echo -e "后端服务地址: http://localhost:$BACKEND_PORT"
echo -e "前端服务地址: http://localhost:$FRONTEND_PORT"
echo -e "${YELLOW}按 Ctrl+C 停止所有服务${NC}"

# 等待用户中断信号
trap 'echo -e "${YELLOW}正在停止服务...${NC}"; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit' INT

# 保持脚本运行
while true; do
    sleep 1
done