#!/bin/bash
# 启动后端服务器

cd "$(dirname "$0")"
source .venv/bin/activate

echo "=========================================="
echo "启动 OpenIndex 后端服务器"
echo "=========================================="
echo ""

# 检查配置
python -c "from md2tree.core.config import get_config_value; print(f'API Host: {get_config_value(\"api\", \"host\", \"0.0.0.0\")}'); print(f'API Port: {get_config_value(\"api\", \"port\", 8090)}')"

echo ""
echo "启动服务器..."
echo "访问地址: http://localhost:8090"
echo "API 文档: http://localhost:8090/docs"
echo ""
echo "按 Ctrl+C 停止服务器"
echo "=========================================="
echo ""

python -m md2tree.openindex.app
