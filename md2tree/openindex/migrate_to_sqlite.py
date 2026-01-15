"""
迁移脚本：将 JSON 数据迁移到 SQLite

运行方式：
    python -m openindex.migrate_to_sqlite
"""

import json
import sys
from pathlib import Path

# 添加父目录到路径
_current_dir = Path(__file__).parent.parent
if str(_current_dir) not in sys.path:
    sys.path.insert(0, str(_current_dir))

from openindex.database import get_database


def migrate():
    """执行迁移"""
    data_dir = Path(__file__).parent / "data"
    documents_json = data_dir / "documents.json"

    if not documents_json.exists():
        print("No documents.json found, nothing to migrate.")
        return

    print(f"Migrating from {documents_json}...")

    # 读取旧数据
    with open(documents_json, 'r', encoding='utf-8') as f:
        old_data = json.load(f)

    if not old_data:
        print("No documents to migrate.")
        return

    # 获取数据库
    db = get_database(str(data_dir))

    migrated = 0
    skipped = 0

    # 处理字典格式 {doc_id: doc_data} 或列表格式 [doc_data, ...]
    if isinstance(old_data, dict):
        docs_to_migrate = [(doc_id, doc) for doc_id, doc in old_data.items()]
    else:
        docs_to_migrate = [(doc.get('id'), doc) for doc in old_data if doc.get('id')]

    for doc_id, doc in docs_to_migrate:
        if not doc_id:
            continue

        # 检查是否已存在
        existing = db.get_document(doc_id)
        if existing:
            print(f"  Skipping {doc_id} (already exists)")
            skipped += 1
            continue

        # 迁移文档
        try:
            with db.get_connection() as conn:
                cursor = conn.cursor()

                # 提取统计信息
                stats = doc.get('stats', {}) or {}

                # 查找树结构文件路径
                tree_path = None
                trees_dir = data_dir / "trees"
                if trees_dir.exists():
                    tree_file = trees_dir / f"{doc_id}_tree.json"
                    if tree_file.exists():
                        tree_path = str(tree_file)

                cursor.execute("""
                    INSERT INTO documents 
                    (id, name, pdf_path, tree_path, status, total_nodes, max_depth, mineru_dir, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    doc_id,
                    doc.get('name', ''),
                    doc.get('pdf_path', ''),
                    tree_path,
                    doc.get('status', 'pending'),
                    stats.get('total_nodes', 0) if stats else 0,
                    stats.get('max_depth', 0) if stats else 0,
                    doc.get('mineru_dir', ''),
                    doc.get('created_at', '')
                ))

            print(f"  Migrated {doc_id}: {doc.get('name')}")
            migrated += 1

        except Exception as e:
            print(f"  Error migrating {doc_id}: {e}")

    print(f"\nMigration complete!")
    print(f"  Migrated: {migrated}")
    print(f"  Skipped: {skipped}")

    # 重命名旧文件
    backup_path = documents_json.with_suffix('.json.bak')
    documents_json.rename(backup_path)
    print(f"\nBackup created: {backup_path}")


if __name__ == "__main__":
    migrate()
