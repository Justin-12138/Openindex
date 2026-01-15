#!/bin/bash
# 同时启动前后端服务器

cd "$(dirname "$0")"

echo "=========================================="
echo "启动 OpenIndex 前后端服务"
echo "=========================================="
echo ""

# 检查虚拟环境
if [ ! -d ".venv" ]; then
    echo "错误: 虚拟环境不存在 (.venv)"
    exit 1
fi

# 检查前端依赖
if [ ! -d "md2tree/openindex/frontend/node_modules" ]; then
    echo "检测到前端依赖未安装，正在安装..."
    cd md2tree/openindex/frontend
    npm install
    cd ../../..
    echo ""
fi

echo "启动后端服务器 (端口 8090)..."
source .venv/bin/activate
python -m md2tree.openindex.app &
BACKEND_PID=$!

echo "等待后端启动..."
sleep 3

echo "启动前端开发服务器 (端口 5173)..."
cd md2tree/openindex/frontend
npm run dev &
FRONTEND_PID=$!

echo ""
echo "=========================================="
echo "服务已启动"
echo "=========================================="
echo "后端 API: http://localhost:8090"
echo "API 文档: http://localhost:8090/docs"
echo "前端应用: http://localhost:5173"
echo ""
echo "后端 PID: $BACKEND_PID"
echo "前端 PID: $FRONTEND_PID"
echo ""
echo "按 Ctrl+C 停止所有服务"
echo "=========================================="

# 等待用户中断
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT TERM
wait
