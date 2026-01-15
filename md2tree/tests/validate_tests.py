#!/usr/bin/env python3
"""
测试验证脚本

验证测试文件的语法和基本结构，不运行实际测试。
"""

import ast
import sys
from pathlib import Path


def validate_python_file(file_path: Path) -> tuple[bool, str]:
    """
    验证 Python 文件的语法
    
    Returns:
        (is_valid, message)
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            source = f.read()
        
        # 尝试解析 AST
        ast.parse(source, filename=str(file_path))
        return True, "✓ 语法正确"
    except SyntaxError as e:
        return False, f"✗ 语法错误: {e}"
    except Exception as e:
        return False, f"✗ 错误: {e}"


def check_test_structure(file_path: Path) -> list[str]:
    """
    检查测试文件的结构
    
    Returns:
        发现的问题列表
    """
    issues = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            source = f.read()
        
        tree = ast.parse(source, filename=str(file_path))
        
        # 检查是否有测试类
        has_test_class = False
        has_test_function = False
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                if node.name.startswith('Test'):
                    has_test_class = True
            elif isinstance(node, ast.FunctionDef):
                if node.name.startswith('test_'):
                    has_test_function = True
        
        if not has_test_class and not has_test_function:
            issues.append("⚠ 未找到测试类或测试函数")
        
    except Exception as e:
        issues.append(f"✗ 无法分析结构: {e}")
    
    return issues


def main():
    """主函数"""
    tests_dir = Path(__file__).parent
    test_files = list(tests_dir.glob("test_*.py"))
    
    print("=" * 60)
    print("测试文件验证")
    print("=" * 60)
    print()
    
    total = len(test_files)
    passed = 0
    failed = 0
    
    for test_file in sorted(test_files):
        print(f"检查: {test_file.name}")
        
        # 验证语法
        is_valid, message = validate_python_file(test_file)
        print(f"  {message}")
        
        if is_valid:
            passed += 1
            # 检查结构
            issues = check_test_structure(test_file)
            if issues:
                for issue in issues:
                    print(f"  {issue}")
        else:
            failed += 1
        
        print()
    
    print("=" * 60)
    print(f"总计: {total} 个文件")
    print(f"通过: {passed} 个")
    print(f"失败: {failed} 个")
    print("=" * 60)
    
    # 检查 conftest.py
    conftest = tests_dir / "conftest.py"
    if conftest.exists():
        print()
        print(f"检查: {conftest.name}")
        is_valid, message = validate_python_file(conftest)
        print(f"  {message}")
    
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
