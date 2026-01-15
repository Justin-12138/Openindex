"""
Markdown 转换器测试
"""

import pytest
import tempfile
from pathlib import Path
from md2tree.core.converter import md_to_tree, save_tree


@pytest.fixture
def sample_markdown() -> Path:
    """创建示例 Markdown 文件"""
    content = """# Title 1

Content for title 1.

## Subtitle 1.1

Content for subtitle 1.1.

## Subtitle 1.2

Content for subtitle 1.2.

# Title 2

Content for title 2.
"""
    temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False)
    temp_file.write(content)
    temp_file.close()
    return Path(temp_file.name)


class TestMdToTree:
    """Markdown 转树测试"""
    
    def test_basic_conversion(self, sample_markdown: Path):
        """测试基本转换"""
        result = md_to_tree(str(sample_markdown))
        
        assert 'doc_name' in result
        assert 'structure' in result
        assert len(result['structure']) > 0
    
    def test_with_node_id(self, sample_markdown: Path):
        """测试包含节点ID"""
        result = md_to_tree(str(sample_markdown), add_node_id=True)
        
        # 检查第一个节点是否有 node_id
        if result['structure']:
            first_node = result['structure'][0]
            assert 'node_id' in first_node
    
    def test_without_node_id(self, sample_markdown: Path):
        """测试不包含节点ID"""
        result = md_to_tree(str(sample_markdown), add_node_id=False)
        
        # 检查第一个节点是否没有 node_id
        if result['structure']:
            first_node = result['structure'][0]
            assert 'node_id' not in first_node
    
    def test_keep_text(self, sample_markdown: Path):
        """测试保留文本"""
        result = md_to_tree(str(sample_markdown), keep_text=True)
        
        if result['structure']:
            first_node = result['structure'][0]
            assert 'text' in first_node
    
    def test_without_text(self, sample_markdown: Path):
        """测试不保留文本"""
        result = md_to_tree(str(sample_markdown), keep_text=False)
        
        if result['structure']:
            first_node = result['structure'][0]
            assert 'text' not in first_node
    
    def test_nonexistent_file(self):
        """测试不存在的文件"""
        with pytest.raises(FileNotFoundError):
            md_to_tree("nonexistent.md")
    
    def test_save_tree(self, sample_markdown: Path, tmp_path: Path):
        """测试保存树结构"""
        result = md_to_tree(str(sample_markdown))
        output_path = tmp_path / "test_tree.json"
        
        save_tree(result, str(output_path))
        assert output_path.exists()
        
        # 验证文件内容
        import json
        with open(output_path) as f:
            saved_data = json.load(f)
        # 保存的可能是结构本身，或者包含 structure 字段
        assert isinstance(saved_data, (dict, list))
