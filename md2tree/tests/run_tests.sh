#!/bin/bash
# 运行测试脚本

set -e

echo "=========================================="
echo "运行 md2tree 测试套件"
echo "=========================================="

# 检查是否安装了 pytest
if ! command -v pytest &> /dev/null; then
    echo "错误: pytest 未安装"
    echo "请运行: pip install pytest pytest-cov pytest-asyncio"
    exit 1
fi

# 运行测试
echo ""
echo "运行单元测试..."
pytest md2tree/tests/ -v --tb=short

echo ""
echo "=========================================="
echo "测试完成"
echo "=========================================="
