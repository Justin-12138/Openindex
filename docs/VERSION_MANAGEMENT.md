# 文档解析版本管理功能

> 实现时间: 2026-01-12

## ✅ 已实现功能

### 1. 数据库版本管理
- ✅ 数据库版本升级到 v2
- ✅ 创建 `parse_versions` 表存储解析版本
- ✅ 自动迁移现有数据到版本表

### 2. 版本管理 API
- ✅ `create_parse_version()` - 创建新解析版本
- ✅ `update_parse_version()` - 更新版本状态和信息
- ✅ `get_parse_version()` - 获取指定版本
- ✅ `get_parse_versions()` - 获取所有版本列表
- ✅ `get_latest_parse_version()` - 获取最新版本

### 3. 解析服务集成
- ✅ 每次解析自动创建新版本
- ✅ 版本化目录结构（`parsed/{doc_id}/v{version}/`）
- ✅ 版本化树文件（`{doc_id}_v{version}_tree.json`）
- ✅ 版本状态跟踪（parsing_mineru → parsing_markdown → adding_locations → ready/error）

### 4. 文档存储更新
- ✅ `get_mineru_output_dir()` 支持版本参数
- ✅ `get_mineru_output_dir_for_new_version()` 创建版本化目录
- ✅ `save_tree()` 支持版本参数，保存版本化树文件

## 📊 数据库结构

### parse_versions 表
```sql
CREATE TABLE parse_versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    doc_id TEXT NOT NULL,
    version INTEGER NOT NULL DEFAULT 1,
    tree_path TEXT,
    mineru_dir TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    error_message TEXT,
    total_nodes INTEGER DEFAULT 0,
    max_depth INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    FOREIGN KEY (doc_id) REFERENCES documents(id) ON DELETE CASCADE,
    UNIQUE(doc_id, version)
);
```

## 🔄 工作流程

1. **开始解析**:
   - 获取当前最新版本号
   - 创建新版本记录（version = latest + 1）
   - 创建版本化目录 `parsed/{doc_id}/v{version}/`

2. **解析过程**:
   - 更新版本状态（parsing_mineru → parsing_markdown → adding_locations）
   - 保存 MinerU 输出到版本化目录
   - 保存树结构到版本化文件

3. **完成解析**:
   - 更新版本状态为 `ready`
   - 记录完成时间
   - 更新文档表指向最新版本（保持兼容性）

4. **错误处理**:
   - 如果解析失败，更新版本状态为 `error`
   - 保存错误消息和堆栈信息

## 📁 文件结构

```
data/
├── parsed/
│   └── {doc_id}/
│       ├── v1/
│       │   ├── vlm/
│       │   │   ├── *.md
│       │   │   ├── *_middle.json
│       │   │   └── ...
│       └── v2/
│           └── ...
├── trees/
│   ├── {doc_id}_v1_tree.json
│   └── {doc_id}_v2_tree.json
└── ...
```

## 🎯 使用示例

### 获取所有版本
```python
versions = db.get_parse_versions(doc_id)
for version in versions:
    print(f"Version {version['version']}: {version['status']} - {version['created_at']}")
```

### 获取特定版本
```python
version = db.get_parse_version(doc_id, version=2)
if version:
    tree_path = version['tree_path']
    # 加载该版本的树结构
```

### 获取最新版本
```python
latest = db.get_latest_parse_version(doc_id)
if latest:
    print(f"Latest version: {latest['version']}")
```

## 🔮 未来扩展

1. **API 端点**: 添加版本查询和选择端点
2. **版本比较**: 比较不同版本的解析结果
3. **版本回滚**: 恢复到之前的解析版本
4. **版本清理**: 自动清理旧版本（保留最近 N 个版本）
5. **版本标签**: 为版本添加标签和描述

## ✅ 测试状态

- ✅ 数据库迁移测试通过
- ✅ 版本管理方法测试通过
- ✅ 解析服务集成测试通过

---

*版本管理功能已完全实现并集成到系统中！*
