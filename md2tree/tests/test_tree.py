"""
树结构操作测试
"""

import pytest
from md2tree.core.tree import (
    find_node_by_id,
    structure_to_list,
    get_tree_stats,
)


@pytest.fixture
def sample_tree():
    """示例树结构"""
    return [
        {
            'title': 'Title 1',
            'node_id': '1',
            'text': 'Content 1',
            'nodes': [
                {
                    'title': 'Subtitle 1.1',
                    'node_id': '1.1',
                    'text': 'Content 1.1',
                    'nodes': []
                },
                {
                    'title': 'Subtitle 1.2',
                    'node_id': '1.2',
                    'text': 'Content 1.2',
                    'nodes': []
                }
            ]
        },
        {
            'title': 'Title 2',
            'node_id': '2',
            'text': 'Content 2',
            'nodes': []
        }
    ]


class TestFindNodeById:
    """测试节点查找"""
    
    def test_find_existing_node(self, sample_tree):
        """测试查找存在的节点"""
        node = find_node_by_id(sample_tree, '1')
        assert node is not None
        assert node['title'] == 'Title 1'
    
    def test_find_nested_node(self, sample_tree):
        """测试查找嵌套节点"""
        node = find_node_by_id(sample_tree, '1.1')
        assert node is not None
        assert node['title'] == 'Subtitle 1.1'
    
    def test_find_nonexistent_node(self, sample_tree):
        """测试查找不存在的节点"""
        node = find_node_by_id(sample_tree, '999')
        assert node is None


class TestStructureToList:
    """测试树结构展平"""
    
    def test_flatten_tree(self, sample_tree):
        """测试展平树结构"""
        node_list = structure_to_list(sample_tree)
        assert len(node_list) == 4  # 2 个顶级节点 + 2 个子节点
        assert all('node_id' in node for node in node_list)
    
    def test_empty_tree(self):
        """测试空树"""
        node_list = structure_to_list([])
        assert len(node_list) == 0


class TestGetTreeStats:
    """测试树统计"""
    
    def test_basic_stats(self, sample_tree):
        """测试基本统计"""
        stats = get_tree_stats(sample_tree)
        assert stats['total_nodes'] == 4
        assert stats['max_depth'] == 2
        assert stats['leaf_nodes'] == 3  # 1.1, 1.2, 2
        assert stats['internal_nodes'] == 1  # 1
    
    def test_empty_tree_stats(self):
        """测试空树统计"""
        stats = get_tree_stats([])
        assert stats['total_nodes'] == 0
        assert stats['max_depth'] == 0
        assert stats['leaf_nodes'] == 0
        assert stats['internal_nodes'] == 0
