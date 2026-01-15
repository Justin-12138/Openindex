"""
Utility functions for md2tree module.

This module contains helper functions for common operations
when working with markdown and tree structures.
"""

from typing import List, Dict, Any, Optional

# Import count_tokens from llm module to avoid duplication
from ..llm.client import count_tokens

# Re-export for backward compatibility
__all__ = [
    'count_tokens',
    'structure_to_list',
    'get_leaf_nodes',
    'find_node_by_id',
    'find_node_by_title',
    'remove_field',
    'get_node_depth',
    'get_tree_stats',
    'validate_tree',
    'sanitize_filename',
    'merge_trees',
    'pretty_print_tree',
]


def structure_to_list(structure: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Flatten a tree structure into a list of all nodes.

    Args:
        structure: Tree structure

    Returns:
        Flat list of all nodes in the tree
    """
    nodes = []

    if isinstance(structure, dict):
        nodes.append(structure)
        if 'nodes' in structure:
            nodes.extend(structure_to_list(structure['nodes']))
    elif isinstance(structure, list):
        for item in structure:
            nodes.extend(structure_to_list(item))

    return nodes


def get_leaf_nodes(structure: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Get all leaf nodes (nodes without children) from the tree.

    Args:
        structure: Tree structure

    Returns:
        List of leaf nodes
    """
    import copy

    leaf_nodes = []

    def _get_leaves(node):
        if isinstance(node, dict):
            if not node.get('nodes'):
                leaf_node = copy.deepcopy(node)
                leaf_node.pop('nodes', None)
                return [leaf_node]
            else:
                leaves = []
                for child in node.get('nodes', []):
                    leaves.extend(_get_leaves(child))
                return leaves
        elif isinstance(node, list):
            leaves = []
            for item in node:
                leaves.extend(_get_leaves(item))
            return leaves
        return []

    for item in structure:
        leaf_nodes.extend(_get_leaves(item))

    return leaf_nodes


def find_node_by_id(structure: List[Dict[str, Any]], node_id: str) -> Optional[Dict[str, Any]]:
    """
    Find a node in the tree by its node_id.

    Args:
        structure: Tree structure
        node_id: The node_id to search for

    Returns:
        The node if found, None otherwise
    """
    def _search(node):
        if isinstance(node, dict):
            if node.get('node_id') == node_id:
                return node
            for key in node.keys():
                if 'nodes' in key:
                    result = _search(node[key])
                    if result:
                        return result
        elif isinstance(node, list):
            for item in node:
                result = _search(item)
                if result:
                    return result
        return None

    for item in structure:
        result = _search(item)
        if result:
            return result
    return None


def find_node_by_title(structure: List[Dict[str, Any]], title: str) -> Optional[Dict[str, Any]]:
    """
    Find a node in the tree by its title.

    Args:
        structure: Tree structure
        title: The title to search for

    Returns:
        The node if found, None otherwise
    """
    def _search(node):
        if isinstance(node, dict):
            if node.get('title') == title:
                return node
            for key in node.keys():
                if 'nodes' in key:
                    result = _search(node[key])
                    if result:
                        return result
        elif isinstance(node, list):
            for item in node:
                result = _search(item)
                if result:
                    return result
        return None

    for item in structure:
        result = _search(item)
        if result:
            return result
    return None


def remove_field(structure: List[Dict[str, Any]], field: str) -> List[Dict[str, Any]]:
    """
    Remove a specific field from all nodes in the tree.

    Args:
        structure: Tree structure
        field: Field name to remove

    Returns:
        Modified tree structure
    """
    if isinstance(structure, dict):
        structure.pop(field, None)
        if 'nodes' in structure:
            remove_field(structure['nodes'], field)
    elif isinstance(structure, list):
        for item in structure:
            remove_field(item, field)

    return structure


def get_node_depth(node: Dict[str, Any]) -> int:
    """
    Get the depth of a node in the tree (root = 0).

    Args:
        node: A tree node

    Returns:
        Depth level of the node
    """
    def _depth(n, current_depth=0):
        if not n.get('nodes'):
            return current_depth
        return max(_depth(child, current_depth + 1) for child in n['nodes'])

    return _depth(node)


def get_tree_stats(structure: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Get statistics about the tree structure.

    Args:
        structure: Tree structure

    Returns:
        Dict with stats: total_nodes, max_depth, leaf_count, etc.
    """
    all_nodes = structure_to_list(structure)
    leaf_nodes = get_leaf_nodes(structure)

    # Calculate max depth
    def _calculate_depth(nodes, current_depth=0):
        if not nodes:
            return current_depth
        return max(_calculate_depth(
            node.get('nodes', []), current_depth + 1
        ) for node in nodes)

    return {
        'total_nodes': len(all_nodes),
        'max_depth': _calculate_depth(structure),
        'leaf_nodes': len(leaf_nodes),
        'internal_nodes': len(all_nodes) - len(leaf_nodes),
    }


def validate_tree(structure: List[Dict[str, Any]]) -> List[str]:
    """
    Validate tree structure and return any issues found.

    Args:
        structure: Tree structure

    Returns:
        List of validation issue messages (empty if valid)
    """
    issues = []

    def _validate(node, path="root"):
        if not isinstance(node, dict):
            issues.append(f"Invalid node at {path}: not a dict")
            return

        if 'title' not in node:
            issues.append(f"Node at {path}: missing 'title' field")

        if 'nodes' in node:
            if not isinstance(node['nodes'], list):
                issues.append(f"Node '{node.get('title', '?')}' at {path}: 'nodes' is not a list")
            else:
                for i, child in enumerate(node['nodes']):
                    child_path = f"{path} -> {node.get('title', '?')}[{i}]"
                    _validate(child, child_path)

    for item in structure:
        _validate(item)

    return issues


def sanitize_filename(filename: str, replacement: str = '-') -> str:
    """
    Sanitize a filename by removing/replacing invalid characters.

    Args:
        filename: The filename to sanitize
        replacement: Character to replace invalid chars with

    Returns:
        Sanitized filename
    """
    # Remove or replace invalid characters
    invalid_chars = ['<', '>', ':', '"', '/', '\\', '|', '?', '*']
    result = filename
    for char in invalid_chars:
        result = result.replace(char, replacement)

    # Remove leading/trailing spaces and dots
    result = result.strip('. ')

    return result or 'untitled'


def merge_trees(trees: List[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    """
    Merge multiple trees into a single tree structure.

    Args:
        trees: List of tree structures to merge

    Returns:
        Merged tree structure
    """
    if not trees:
        return []

    if len(trees) == 1:
        return trees[0]

    # Create a virtual root
    merged_root = {
        'title': 'Merged',
        'nodes': []
    }

    for tree in trees:
        merged_root['nodes'].extend(tree)

    return [merged_root]


def pretty_print_tree(structure: List[Dict[str, Any]], max_text_length: int = 50) -> None:
    """
    Pretty print the tree structure with text preview.

    Args:
        structure: Tree structure
        max_text_length: Maximum length of text to display
    """
    def _print_node(node, indent=0):
        prefix = "  " * indent
        title = node.get('title', 'Untitled')

        print(f"{prefix}- {title}")

        if node.get('node_id'):
            print(f"{prefix}  ID: {node['node_id']}")

        if node.get('text'):
            text = node['text']
            if len(text) > max_text_length:
                text = text[:max_text_length] + "..."
            print(f"{prefix}  Text: {text}")

        if node.get('line_num'):
            print(f"{prefix}  Line: {node['line_num']}")

        if node.get('nodes'):
            for child in node['nodes']:
                _print_node(child, indent + 1)

    for root in structure:
        _print_node(root)
        print()
