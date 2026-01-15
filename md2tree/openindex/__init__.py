"""
OpenIndex - AI 论文阅读应用

一个基于 md2tree 的 AI 论文阅读和检索应用。

核心流程:
1. PDF → MinerU → Markdown + 坐标
2. Markdown → 树结构
3. Query + 树结构 → LLM → 选择节点
4. Query + 节点原文 → LLM → 答案
5. 答案 + 坐标 → PDF 定位
"""

__version__ = "0.1.0"
