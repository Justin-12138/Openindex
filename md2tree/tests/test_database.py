"""
数据库模块测试
"""

import pytest
from md2tree.openindex.database import Database
from md2tree.openindex.models import DocumentStatus


class TestDatabase:
    """数据库测试"""
    
    def test_init_database(self, test_database: Database):
        """测试数据库初始化"""
        assert test_database is not None
        assert test_database.db_path.exists()
    
    def test_add_document(self, test_database: Database):
        """测试添加文档"""
        doc = test_database.add_document(
            doc_id="test1234",
            name="Test Document",
            original_filename="test.pdf",
            pdf_path="/path/to/test.pdf",
            file_size=1024
        )
        assert doc is not None
        assert doc['id'] == "test1234"
        assert doc['name'] == "Test Document"
    
    def test_get_document(self, test_database: Database):
        """测试获取文档"""
        # 先添加文档
        test_database.add_document(
            doc_id="test1234",
            name="Test Document",
            original_filename="test.pdf",
            pdf_path="/path/to/test.pdf",
            file_size=1024
        )
        
        # 获取文档
        doc = test_database.get_document("test1234")
        assert doc is not None
        assert doc['id'] == "test1234"
    
    def test_get_nonexistent_document(self, test_database: Database):
        """测试获取不存在的文档"""
        doc = test_database.get_document("nonexistent")
        assert doc is None
    
    def test_update_document_status(self, test_database: Database):
        """测试更新文档状态"""
        # 先添加文档
        test_database.add_document(
            doc_id="test1234",
            name="Test Document",
            original_filename="test.pdf",
            pdf_path="/path/to/test.pdf",
            file_size=1024
        )
        
        # 更新状态
        success = test_database.update_document_status(
            "test1234",
            status=DocumentStatus.READY.value
        )
        assert success is True
        
        # 验证状态已更新
        doc = test_database.get_document("test1234")
        assert doc['status'] == DocumentStatus.READY.value
    
    def test_delete_document(self, test_database: Database):
        """测试删除文档"""
        # 先添加文档
        test_database.add_document(
            doc_id="test1234",
            name="Test Document",
            original_filename="test.pdf",
            pdf_path="/path/to/test.pdf",
            file_size=1024
        )
        
        # 删除文档
        success = test_database.delete_document("test1234")
        assert success is True
        
        # 验证文档已删除
        doc = test_database.get_document("test1234")
        assert doc is None
    
    def test_create_library(self, test_database: Database):
        """测试创建库"""
        lib = test_database.create_library(
            name="Test Library",
            description="Test description",
            color="#ff0000",
            icon="📚"
        )
        assert lib is not None
        assert lib['name'] == "Test Library"
        assert 'id' in lib
    
    def test_get_stats(self, test_database: Database):
        """测试获取统计信息"""
        stats = test_database.get_stats()
        assert 'total_documents' in stats
        assert 'ready_documents' in stats
        assert 'total_conversations' in stats
        assert 'total_messages' in stats
        assert stats['total_documents'] == 0  # 初始状态
    
    def test_create_conversation(self, test_database: Database):
        """测试创建对话"""
        # 先添加文档
        test_database.add_document(
            doc_id="test1234",
            name="Test Document",
            original_filename="test.pdf",
            pdf_path="/path/to/test.pdf",
            file_size=1024
        )
        
        # 创建对话
        conv = test_database.create_conversation("test1234", "Test Conversation")
        assert conv is not None
        assert conv['doc_id'] == "test1234"
        assert conv['title'] == "Test Conversation"
        assert 'id' in conv
    
    def test_get_conversation(self, test_database: Database):
        """测试获取对话"""
        # 先添加文档和对话
        test_database.add_document(
            doc_id="test1234",
            name="Test Document",
            original_filename="test.pdf",
            pdf_path="/path/to/test.pdf",
            file_size=1024
        )
        created_conv = test_database.create_conversation("test1234", "Test Conversation")
        conv_id = created_conv['id']
        
        # 获取对话
        conv = test_database.get_conversation(conv_id)
        assert conv is not None
        assert conv['id'] == conv_id
        assert 'messages' in conv
    
    def test_add_message(self, test_database: Database):
        """测试添加消息"""
        # 先添加文档和对话
        test_database.add_document(
            doc_id="test1234",
            name="Test Document",
            original_filename="test.pdf",
            pdf_path="/path/to/test.pdf",
            file_size=1024
        )
        conv = test_database.create_conversation("test1234", "Test Conversation")
        conv_id = conv['id']
        
        # 添加消息
        msg = test_database.add_message(
            conversation_id=conv_id,
            role="user",
            content="Test message"
        )
        assert msg is not None
        assert msg['role'] == "user"
        assert msg['content'] == "Test message"
        assert 'id' in msg
    
    def test_get_messages(self, test_database: Database):
        """测试获取消息列表"""
        # 先添加文档和对话
        test_database.add_document(
            doc_id="test1234",
            name="Test Document",
            original_filename="test.pdf",
            pdf_path="/path/to/test.pdf",
            file_size=1024
        )
        conv = test_database.create_conversation("test1234", "Test Conversation")
        conv_id = conv['id']
        
        # 添加多条消息
        test_database.add_message(conv_id, "user", "Message 1")
        test_database.add_message(conv_id, "assistant", "Message 2")
        
        # 获取消息
        messages = test_database.get_messages(conv_id)
        assert len(messages) == 2
        assert messages[0]['content'] == "Message 1"
        assert messages[1]['content'] == "Message 2"
    
    def test_delete_conversation(self, test_database: Database):
        """测试删除对话"""
        # 先添加文档和对话
        test_database.add_document(
            doc_id="test1234",
            name="Test Document",
            original_filename="test.pdf",
            pdf_path="/path/to/test.pdf",
            file_size=1024
        )
        conv = test_database.create_conversation("test1234", "Test Conversation")
        conv_id = conv['id']
        
        # 删除对话（软删除）
        success = test_database.delete_conversation(conv_id, hard=False)
        assert success is True
        
        # 验证对话已软删除（不包含在查询结果中）
        conversations = test_database.get_conversations_by_doc("test1234", include_deleted=False)
        assert len(conversations) == 0
        
        # 包含已删除的对话
        conversations_all = test_database.get_conversations_by_doc("test1234", include_deleted=True)
        assert len(conversations_all) == 1
