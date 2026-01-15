#!/bin/bash
# 启动前端开发服务器

cd "$(dirname "$0")/md2tree/openindex/frontend"

echo "=========================================="
echo "启动 OpenIndex 前端开发服务器"
echo "=========================================="
echo ""

# 检查 node_modules
if [ ! -d "node_modules" ]; then
    echo "检测到 node_modules 不存在，正在安装依赖..."
    npm install
    echo ""
fi

echo "启动开发服务器..."
echo "访问地址: http://localhost:5173"
echo "后端代理: http://localhost:8090"
echo ""
echo "按 Ctrl+C 停止服务器"
echo "=========================================="
echo ""

npm run dev
