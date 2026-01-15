# 测试说明

本目录包含项目的单元测试和集成测试。

## 验证测试文件

在运行测试之前，可以先验证测试文件的语法：

```bash
# 验证所有测试文件的语法
python3 md2tree/tests/validate_tests.py
```

这会检查所有测试文件的语法正确性，并统计测试数量。

## 运行测试

### 运行所有测试

```bash
# 使用 pytest
pytest md2tree/tests/ -v

# 运行特定测试文件
pytest md2tree/tests/test_utils.py -v

# 运行特定测试类
pytest md2tree/tests/test_utils.py::TestSanitizeString -v

# 运行特定测试方法
pytest md2tree/tests/test_utils.py::TestSanitizeString::test_basic_sanitize -v
```

### 运行测试并查看覆盖率

```bash
# 需要先安装 pytest-cov
pip install pytest-cov

# 运行测试并生成覆盖率报告
pytest md2tree/tests/ --cov=md2tree --cov-report=html

# 查看覆盖率报告
# 打开 htmlcov/index.html
```

## 测试文件说明

### 单元测试
- `conftest.py`: pytest 配置和共享 fixtures
- `test_utils.py`: 工具函数测试（验证、格式化、清理等）
- `test_database.py`: 数据库模块测试（CRUD、对话、消息等）
- `test_document_store.py`: 文档存储服务测试（文件操作、树结构等）
- `test_config.py`: 配置管理测试
- `test_converter.py`: Markdown 转换器测试
- `test_tree.py`: 树结构操作测试（查找、展平、统计等）

### 集成测试
- `test_api_integration.py`: FastAPI 端点集成测试

### 功能测试（保留）
- `test.py`: 原有的功能测试脚本
- `test_retrieval.py`: 检索功能测试
- `test_mineru_integration.py`: MinerU 集成测试
- `test_query_to_block.py`: 查询到块转换测试
- `test_concurrency.py`: 并发控制测试

## 测试原则

1. **独立性**: 每个测试应该独立运行，不依赖其他测试
2. **可重复性**: 测试结果应该可重复
3. **快速执行**: 单元测试应该快速执行
4. **清晰命名**: 测试名称应该清晰描述测试内容
5. **使用 fixtures**: 使用 pytest fixtures 共享测试数据
6. **隔离性**: 使用临时目录和数据库，不影响实际数据
7. **覆盖关键路径**: 优先测试核心功能和边界情况

## 测试覆盖率

当前测试覆盖：
- ✅ 工具函数（验证、格式化、清理）
- ✅ 数据库操作（CRUD、状态管理、对话、消息）
- ✅ 文档存储（文件操作、树结构管理）
- ✅ 配置管理（加载、验证、访问）
- ✅ Markdown转换（基本转换功能）
- ✅ 树结构操作（查找、展平、统计）
- ✅ API端点（健康检查、指标、缓存管理）

## 添加新测试

1. 创建新的测试文件，命名格式：`test_*.py`
2. 导入必要的模块和 fixtures
3. 编写测试类和测试方法
4. 使用 `pytest` 运行测试

## 注意事项

- 测试使用临时目录，不会影响实际数据
- 某些测试可能需要外部依赖（如 LLM API），这些测试会被标记为集成测试
- 数据库测试使用 SQLite 内存数据库或临时文件
