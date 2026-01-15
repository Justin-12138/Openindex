"""
Markdown to Tree Converter

A simplified module for converting Markdown files to tree structures.
This module extracts headers and their content from Markdown files and
organizes them into a hierarchical tree structure.
"""

import asyncio
import logging
import re
import json
from pathlib import Path
from typing import List, Dict, Any, Optional

from ..llm.thinning import apply_thinning
from ..llm.summary import generate_summaries_for_structure, generate_doc_description_async
from ..llm.client import LLMConfig

logger = logging.getLogger(__name__)


def extract_headers(markdown_content: str) -> tuple[List[Dict[str, Any]], List[str]]:
    """
    Extract all headers from markdown content.

    Args:
        markdown_content: The markdown text content

    Returns:
        A tuple of (node_list, markdown_lines) where:
        - node_list: List of dicts with 'node_title' and 'line_num'
        - markdown_lines: List of all lines in the markdown
    """
    header_pattern = r'^(#{1,6})\s+(.+)$'
    code_block_pattern = r'^```'
    node_list = []

    lines = markdown_content.split('\n')
    in_code_block = False

    for line_num, line in enumerate(lines, 1):
        stripped_line = line.strip()

        # Check for code block delimiters (triple backticks)
        if re.match(code_block_pattern, stripped_line):
            in_code_block = not in_code_block
            continue

        # Skip empty lines
        if not stripped_line:
            continue

        # Only look for headers when not inside a code block
        if not in_code_block:
            match = re.match(header_pattern, stripped_line)
            if match:
                title = match.group(2).strip()
                node_list.append({'node_title': title, 'line_num': line_num})

    return node_list, lines


def extract_node_content(node_list: List[Dict[str, Any]], markdown_lines: List[str]) -> List[Dict[str, Any]]:
    """
    Extract text content for each node based on header hierarchy.

    Args:
        node_list: List of header nodes from extract_headers
        markdown_lines: List of all markdown lines

    Returns:
        List of nodes with 'title', 'line_num', 'level', and 'text'
    """
    all_nodes = []

    for node in node_list:
        line_content = markdown_lines[node['line_num'] - 1]
        header_match = re.match(r'^(#{1,6})', line_content)

        if header_match is None:
            logger.warning(f"Line {node['line_num']} does not contain a valid header: '{line_content}'")
            continue

        processed_node = {
            'title': node['node_title'],
            'line_num': node['line_num'],
            'level': len(header_match.group(1))
        }
        all_nodes.append(processed_node)

    # Extract text content for each node (from this node to the next node of same/higher level)
    for i, node in enumerate(all_nodes):
        start_line = node['line_num'] - 1
        if i + 1 < len(all_nodes):
            end_line = all_nodes[i + 1]['line_num'] - 1
        else:
            end_line = len(markdown_lines)

        node['text'] = '\n'.join(markdown_lines[start_line:end_line]).strip()

    return all_nodes


def build_tree(node_list: List[Dict[str, Any]], add_node_id: bool = True) -> List[Dict[str, Any]]:
    """
    Build a hierarchical tree structure from a flat list of nodes.

    Args:
        node_list: List of nodes with 'title', 'level', 'text', 'line_num'
        add_node_id: Whether to add sequential node_id to each node

    Returns:
        List of root nodes forming a tree structure
    """
    if not node_list:
        return []

    stack = []
    root_nodes = []
    node_counter = 1

    for node in node_list:
        current_level = node['level']

        tree_node = {
            'title': node['title'],
            'text': node['text'],
            'line_num': node['line_num'],
            'nodes': []
        }

        if add_node_id:
            tree_node['node_id'] = str(node_counter).zfill(4)
            node_counter += 1

        # Pop nodes from stack until we find the parent
        while stack and stack[-1][1] >= current_level:
            stack.pop()

        if not stack:
            root_nodes.append(tree_node)
        else:
            parent_node, _ = stack[-1]
            parent_node['nodes'].append(tree_node)

        stack.append((tree_node, current_level))

    return root_nodes


def format_structure(structure: List[Dict[str, Any]], order: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """
    Format tree structure by reordering fields and removing empty nodes lists.

    Args:
        structure: Tree structure
        order: Ordered list of fields to keep

    Returns:
        Formatted tree structure
    """
    if order is None:
        order = ['title', 'node_id', 'text', 'line_num', 'nodes']

    if isinstance(structure, dict):
        if 'nodes' in structure:
            structure['nodes'] = format_structure(structure['nodes'], order)
        # Remove empty nodes
        if not structure.get('nodes'):
            structure.pop('nodes', None)
        # Reorder fields
        return {k: structure[k] for k in order if k in structure}
    elif isinstance(structure, list):
        return [format_structure(item, order) for item in structure]

    return structure


def md_to_tree(
    md_path: str,
    add_node_id: bool = True,
    keep_text: bool = True,
    keep_fields: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Basic function to convert a Markdown file to a tree structure (without LLM).

    Args:
        md_path: Path to the markdown file
        add_node_id: Whether to add sequential node_id to each node
        keep_text: Whether to include the 'text' field in output
        keep_fields: Ordered list of fields to keep (None = keep all present fields)

    Returns:
        Dict with 'doc_name' and 'structure' keys
        
    Raises:
        FileNotFoundError: If the markdown file does not exist
        IOError: If there's an error reading the file
    """
    md_file = Path(md_path)
    if not md_file.exists():
        raise FileNotFoundError(f"Markdown file not found: {md_path}")
    
    try:
        with open(md_file, 'r', encoding='utf-8') as f:
            markdown_content = f.read()
    except (IOError, OSError) as e:
        logger.error(f"Failed to read markdown file {md_path}: {e}")
        raise IOError(f"Failed to read markdown file: {e}") from e

    logger.info("Extracting nodes from markdown...")
    node_list, markdown_lines = extract_headers(markdown_content)

    logger.info("Extracting text content from nodes...")
    nodes_with_content = extract_node_content(node_list, markdown_lines)

    logger.info("Building tree from nodes...")
    tree_structure = build_tree(nodes_with_content, add_node_id=add_node_id)

    # Determine which fields to keep
    if keep_fields is None:
        keep_fields = ['title', 'node_id', 'text', 'line_num', 'nodes']
        if not keep_text:
            keep_fields = ['title', 'node_id', 'line_num', 'nodes']

    logger.info("Formatting tree structure...")
    tree_structure = format_structure(tree_structure, order=keep_fields)

    return {
        'doc_name': Path(md_path).stem,
        'structure': tree_structure,
    }


async def md_to_tree_async(
    md_path: str,
    config: Optional[LLMConfig] = None,
    add_node_id: bool = True,
    keep_text: bool = True,
    enable_thinning: bool = False,
    thinning_threshold: int = 5000,
    enable_summary: bool = False,
    summary_token_threshold: int = 200,
    enable_doc_description: bool = False,
) -> Dict[str, Any]:
    """
    Advanced async function to convert Markdown to tree with LLM features.

    Args:
        md_path: Path to the markdown file
        config: LLM configuration
        add_node_id: Whether to add node_id
        keep_text: Whether to keep text field in final output
        enable_thinning: Whether to apply tree thinning
        thinning_threshold: Minimum token threshold for thinning
        enable_summary: Whether to generate summaries
        summary_token_threshold: Token threshold for using original text
        enable_doc_description: Whether to generate document description

    Returns:
        Dict with 'doc_name', optionally 'doc_description', and 'structure'
        
    Raises:
        FileNotFoundError: If the markdown file does not exist
        IOError: If there's an error reading the file
    """
    if config is None:
        config = LLMConfig()

    md_file = Path(md_path)
    if not md_file.exists():
        raise FileNotFoundError(f"Markdown file not found: {md_path}")
    
    try:
        with open(md_file, 'r', encoding='utf-8') as f:
            markdown_content = f.read()
    except (IOError, OSError) as e:
        logger.error(f"Failed to read markdown file {md_path}: {e}")
        raise IOError(f"Failed to read markdown file: {e}") from e

    logger.info("Extracting nodes from markdown...")
    node_list, markdown_lines = extract_headers(markdown_content)

    logger.info("Extracting text content from nodes...")
    nodes_with_content = extract_node_content(node_list, markdown_lines)

    # Apply thinning if requested
    if enable_thinning:
        logger.info(f"Applying tree thinning (threshold: {thinning_threshold} tokens)...")
        nodes_with_content = apply_thinning(
            nodes_with_content,
            min_token_threshold=thinning_threshold,
            model=config.model
        )

    logger.info("Building tree from nodes...")
    tree_structure = build_tree(nodes_with_content, add_node_id=add_node_id)

    # Add summaries if requested
    if enable_summary:
        # Format with text for summary generation
        tree_structure = format_structure(
            tree_structure,
            order=['title', 'node_id', 'summary', 'prefix_summary', 'text', 'line_num', 'nodes']
        )

        logger.info("Generating summaries...")
        tree_structure = await generate_summaries_for_structure(
            tree_structure,
            summary_token_threshold=summary_token_threshold,
            config=config
        )

        # Remove text if not requested
        if not keep_text:
            tree_structure = format_structure(
                tree_structure,
                order=['title', 'node_id', 'summary', 'prefix_summary', 'line_num', 'nodes']
            )
    else:
        # No summaries, format based on text preference
        if keep_text:
            tree_structure = format_structure(
                tree_structure,
                order=['title', 'node_id', 'text', 'line_num', 'nodes']
            )
        else:
            tree_structure = format_structure(
                tree_structure,
                order=['title', 'node_id', 'line_num', 'nodes']
            )

    result = {
        'doc_name': Path(md_path).stem,
        'structure': tree_structure,
    }

    # Add document description if requested
    if enable_doc_description:
        logger.info("Generating document description...")
        doc_description = await generate_doc_description_async(tree_structure, config)
        result['doc_description'] = doc_description

    return result


def save_tree(tree_data: Dict[str, Any], output_path: str) -> None:
    """
    Save tree structure to a JSON file.

    Args:
        tree_data: Tree structure from md_to_tree
        output_path: Path to save the JSON file
        
    Raises:
        IOError: If there's an error writing the file
    """
    output_file = Path(output_path)
    try:
        output_file.parent.mkdir(parents=True, exist_ok=True)
    except (IOError, OSError) as e:
        logger.error(f"Failed to create directory {output_file.parent}: {e}")
        raise IOError(f"Failed to create output directory: {e}") from e

    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(tree_data, f, indent=2, ensure_ascii=False)
        logger.info(f'Tree structure saved to: {output_file}')
    except (IOError, OSError) as e:
        logger.error(f"Failed to save tree structure to {output_file}: {e}")
        raise IOError(f"Failed to save tree structure: {e}") from e


def print_toc(tree: List[Dict[str, Any]], indent: int = 0) -> None:
    """
    Print a table of contents from the tree structure.

    Args:
        tree: Tree structure
        indent: Current indentation level
    """
    for node in tree:
        print('  ' * indent + node['title'])
        if node.get('nodes'):
            print_toc(node['nodes'], indent + 1)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Convert Markdown file to tree structure')
    parser.add_argument('md_path', type=str, help='Path to the Markdown file')
    parser.add_argument('--output', '-o', type=str, default=None,
                        help='Output JSON file path (default: ./results/<doc_name>_structure.json)')
    parser.add_argument('--no-node-id', action='store_true',
                        help='Do not add node_id to each node')
    parser.add_argument('--no-text', action='store_true',
                        help='Do not include text content in output')
    parser.add_argument('--thinning', action='store_true',
                        help='Apply tree thinning (merge small nodes)')
    parser.add_argument('--thinning-threshold', type=int, default=5000,
                        help='Minimum token threshold for thinning (default: 5000)')
    parser.add_argument('--summary', action='store_true',
                        help='Generate node summaries using LLM')
    parser.add_argument('--summary-threshold', type=int, default=200,
                        help='Token threshold for using original text as summary (default: 200)')
    parser.add_argument('--doc-description', action='store_true',
                        help='Generate document description using LLM')
    parser.add_argument('--model', type=str, default=None,
                        help='LLM model name (default: from .env or glm-4.7)')

    args = parser.parse_args()

    # Determine if we need async (LLM features)
    needs_async = args.thinning or args.summary or args.doc_description

    if needs_async:
        # Async version with LLM features
        config = LLMConfig(model=args.model)
        tree_data = asyncio.run(md_to_tree_async(
            md_path=args.md_path,
            config=config,
            add_node_id=not args.no_node_id,
            keep_text=not args.no_text,
            enable_thinning=args.thinning,
            thinning_threshold=args.thinning_threshold,
            enable_summary=args.summary,
            summary_token_threshold=args.summary_threshold,
            enable_doc_description=args.doc_description,
        ))
    else:
        # Basic version without LLM
        tree_data = md_to_tree(
            md_path=args.md_path,
            add_node_id=not args.no_node_id,
            keep_text=not args.no_text
        )

    # Determine output path
    if args.output:
        output_path = args.output
    else:
        output_path = f'./results/{tree_data["doc_name"]}_structure.json'

    # Save to file
    save_tree(tree_data, output_path)

    # Print table of contents
    print('\n' + '=' * 60)
    print('TABLE OF CONTENTS')
    print('=' * 60)
    print_toc(tree_data['structure'])

    if tree_data.get('doc_description'):
        print('\n' + '=' * 60)
        print('DOCUMENT DESCRIPTION')
        print('=' * 60)
        print(tree_data['doc_description'])
