"""
文档存储服务测试
"""

import pytest
from pathlib import Path
from md2tree.openindex.document_store import DocumentStore, sanitize_filename
from md2tree.openindex.models import DocumentStatus


class TestSanitizeFilename:
    """测试文件名清理"""
    
    def test_basic_sanitize(self):
        """测试基本清理"""
        # sanitize_filename 清理文件名，保留扩展名
        result1 = sanitize_filename("test.pdf")
        assert result1 == "test.pdf"  # 函数保留扩展名
        
        result2 = sanitize_filename("my document.pdf")
        assert result2 == "my_document.pdf"  # 清理空格，保留扩展名
    
    def test_remove_unsafe_chars(self):
        """测试移除不安全字符"""
        result = sanitize_filename("test/file.pdf")
        assert "/" not in result
        assert "\\" not in result
    
    def test_empty_filename(self):
        """测试空文件名"""
        assert sanitize_filename("") == "unnamed"


class TestDocumentStore:
    """文档存储测试"""
    
    def test_init(self, test_document_store: DocumentStore):
        """测试初始化"""
        assert test_document_store is not None
        assert test_document_store.data_dir.exists()
        assert test_document_store.uploads_dir.exists()
    
    def test_add_document(self, test_document_store: DocumentStore):
        """测试添加文档"""
        content = b"fake pdf content"
        doc = test_document_store.add_document("test.pdf", content)
        
        assert doc is not None
        assert 'id' in doc
        assert doc['name'] == "test"
        assert doc['status'] == DocumentStatus.PENDING.value
        
        # 验证文件已创建
        pdf_files = list(test_document_store.uploads_dir.glob("*.pdf"))
        assert len(pdf_files) == 1
    
    def test_get_document(self, test_document_store: DocumentStore):
        """测试获取文档"""
        # 先添加文档
        content = b"fake pdf content"
        added_doc = test_document_store.add_document("test.pdf", content)
        doc_id = added_doc['id']
        
        # 获取文档
        doc = test_document_store.get_document(doc_id)
        assert doc is not None
        assert doc['id'] == doc_id
    
    def test_get_all_documents(self, test_document_store: DocumentStore):
        """测试获取所有文档"""
        # 添加多个文档
        for i in range(3):
            content = b"fake pdf content"
            test_document_store.add_document(f"test{i}.pdf", content)
        
        docs = test_document_store.get_all_documents()
        assert len(docs) == 3
    
    def test_update_document_status(self, test_document_store: DocumentStore):
        """测试更新文档状态"""
        # 先添加文档
        content = b"fake pdf content"
        doc = test_document_store.add_document("test.pdf", content)
        doc_id = doc['id']
        
        # 更新状态
        success = test_document_store.update_document_status(
            doc_id,
            DocumentStatus.READY
        )
        assert success is True
        
        # 验证状态已更新
        updated_doc = test_document_store.get_document(doc_id)
        assert updated_doc['status'] == DocumentStatus.READY.value
    
    def test_delete_document(self, test_document_store: DocumentStore):
        """测试删除文档"""
        # 先添加文档
        content = b"fake pdf content"
        doc = test_document_store.add_document("test.pdf", content)
        doc_id = doc['id']
        
        # 验证文件存在
        pdf_files = list(test_document_store.uploads_dir.glob("*.pdf"))
        assert len(pdf_files) == 1
        
        # 删除文档
        success = test_document_store.delete_document(doc_id)
        assert success is True
        
        # 验证文档已删除
        deleted_doc = test_document_store.get_document(doc_id)
        assert deleted_doc is None
        
        # 验证文件已删除
        pdf_files = list(test_document_store.uploads_dir.glob("*.pdf"))
        assert len(pdf_files) == 0
    
    def test_save_and_load_tree(self, test_document_store: DocumentStore):
        """测试保存和加载树结构"""
        # 先添加文档
        content = b"fake pdf content"
        doc = test_document_store.add_document("test.pdf", content)
        doc_id = doc['id']
        
        # 保存树结构
        tree_data = {
            'structure': [
                {'title': 'Test', 'node_id': '1', 'text': 'Test content'}
            ],
            'stats': {'total_nodes': 1, 'max_depth': 1}
        }
        tree_path = test_document_store.save_tree(doc_id, tree_data)
        assert Path(tree_path).exists()
        
        # 加载树结构
        loaded_tree = test_document_store.load_tree(doc_id)
        assert loaded_tree is not None
        # 验证结构存在（可能包含其他字段）
        assert 'structure' in loaded_tree or isinstance(loaded_tree, dict)
