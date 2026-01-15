"""
坐标转换模块

MinerU 输出的坐标基于其内部处理尺寸（约 1000x1000），
需要转换到原始 PDF 的坐标系统（例如 612x792）。
"""

import fitz
from pathlib import Path
from typing import List, Tuple, Dict, Any, Optional
import json


class CoordinateTransform:
    """MinerU 坐标到 PDF 坐标的转换器"""

    def __init__(self, pdf_path: str, mineru_bbox: List[float]):
        """
        初始化转换器

        Args:
            pdf_path: 原始 PDF 文件路径
            mineru_bbox: MinerU 输出的 bbox [x1, y1, x2, y2]
        """
        self.pdf_path = Path(pdf_path)
        self.doc = fitz.open(pdf_path)
        self.page = self.doc[0]

        # PDF 页面尺寸
        self.pdf_width = self.page.rect.width
        self.pdf_height = self.page.rect.height

        # 从 MinerU bbox 反推其内部尺寸
        # 使用 model.json 中的归一化坐标来计算
        # 归一化坐标: [0.323, 0.065, 0.675, 0.098]
        # 绝对坐标: [321, 64, 674, 97]
        self.mineru_width = 1000  # MinerU 内部宽度（约值）
        self.mineru_height = 1000  # MinerU 内部高度（约值）

    def close(self):
        """关闭 PDF 文档"""
        self.doc.close()

    def __enter__(self):
        """支持上下文管理器"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """退出时关闭资源"""
        self.close()
        return False

    def bbox_to_pdf(self, mineru_bbox: List[float], page_idx: int = 0) -> List[float]:
        """
        将 MinerU bbox 转换为 PDF bbox

        Args:
            mineru_bbox: MinerU 输出的 bbox [x1, y1, x2, y2]
            page_idx: 页码

        Returns:
            PDF 坐标系的 bbox [x1, y1, x2, y2]
        """
        x1, y1, x2, y2 = mineru_bbox

        # 线性缩放到 PDF 尺寸
        pdf_x1 = (x1 / self.mineru_width) * self.pdf_width
        pdf_y1 = (y1 / self.mineru_height) * self.pdf_height
        pdf_x2 = (x2 / self.mineru_width) * self.pdf_width
        pdf_y2 = (y2 / self.mineru_height) * self.pdf_height

        return [pdf_x1, pdf_y1, pdf_x2, pdf_y2]

    def bbox_from_normalized(self, normalized_bbox: List[float], page_idx: int = 0) -> List[float]:
        """
        从归一化坐标 (0-1) 转换为 PDF 坐标

        Args:
            normalized_bbox: 归一化 bbox [x1, y1, x2, y2] (0-1)
            page_idx: 页码

        Returns:
            PDF 坐标系的 bbox
        """
        x1, y1, x2, y2 = normalized_bbox

        pdf_x1 = x1 * self.pdf_width
        pdf_y1 = y1 * self.pdf_height
        pdf_x2 = x2 * self.pdf_width
        pdf_y2 = y2 * self.pdf_height

        return [pdf_x1, pdf_y1, pdf_x2, pdf_y2]

    def auto_detect_scale(self, content_list_path: str, model_json_path: str) -> Tuple[float, float]:
        """
        自动检测 MinerU 的坐标缩放比例

        通过对比 content_list.json 和 model.json 来计算 MinerU 的内部尺寸

        Args:
            content_list_path: content_list.json 路径
            model_json_path: model.json 路径

        Returns:
            (mineru_width, mineru_height)
        """
        # 加载 content_list.json（绝对坐标）
        with open(content_list_path, 'r', encoding='utf-8') as f:
            content_data = json.load(f)

        # 加载 model.json（归一化坐标）
        with open(model_json_path, 'r', encoding='utf-8') as f:
            model_data = json.load(f)

        # 找到第一个匹配的项目来计算缩放
        if isinstance(content_data[0], list):
            # v2 格式
            for page_items in content_data:
                for item in page_items:
                    if 'title' in item.get('type', ''):
                        # 找到标题
                        abs_bbox = item.get('bbox')
                        # 在 model.json 中找对应的
                        if model_data and len(model_data) > 0 and len(model_data[0]) > 0:
                            for model_item in model_data[0]:
                                if model_item.get('type') == 'title':
                                    norm_bbox = model_item.get('bbox')
                                    if abs_bbox and norm_bbox:
                                        self.mineru_width = abs_bbox[0] / norm_bbox[0]
                                        self.mineru_height = abs_bbox[1] / norm_bbox[1]
                                        return (self.mineru_width, self.mineru_height)
        else:
            # v1 格式
            for item in content_data:
                if item.get('text_level') == 1:
                    abs_bbox = item.get('bbox')
                    if model_data and len(model_data) > 0 and len(model_data[0]) > 0:
                        for model_item in model_data[0]:
                            if model_item.get('type') == 'title':
                                norm_bbox = model_item.get('bbox')
                                if abs_bbox and norm_bbox:
                                    self.mineru_width = abs_bbox[0] / norm_bbox[0]
                                    self.mineru_height = abs_bbox[1] / norm_bbox[1]
                                    return (self.mineru_width, self.mineru_height)

        # 默认值
        return (1000, 1000)

    def pdf_bbox_to_screen_y(self, pdf_y: float) -> float:
        """
        将 PDF 坐标（左下角原点）转换为屏幕坐标（左上角原点）

        PDF: y=0 在底部
        屏幕: y=0 在顶部

        Args:
            pdf_y: PDF 坐标的 y 值

        Returns:
            屏幕坐标的 y 值
        """
        return self.pdf_height - pdf_y

    def bbox_to_screen_coords(self, pdf_bbox: List[float]) -> List[float]:
        """
        将 PDF bbox 转换为屏幕坐标（用于 HTML Canvas 等）

        Args:
            pdf_bbox: PDF 坐标的 bbox [x1, y1, x2, y2]

        Returns:
            屏幕坐标的 bbox [x1, y1, x2, y2]
        """
        x1, y1, x2, y2 = pdf_bbox

        # PDF 坐标：左下角原点
        # 屏幕坐标：左上角原点，y 需要翻转
        screen_x1 = x1
        screen_y1 = self.pdf_height - y2  # 翻转 y2
        screen_x2 = x2
        screen_y2 = self.pdf_height - y1  # 翻转 y1

        return [screen_x1, screen_y1, screen_x2, screen_y2]

    def verify_bbox(self, mineru_bbox: List[float]) -> Dict[str, Any]:
        """
        验证 bbox 坐标转换

        Args:
            mineru_bbox: MinerU bbox

        Returns:
            验证信息
        """
        pdf_bbox = self.bbox_to_pdf(mineru_bbox)
        screen_bbox = self.bbox_to_screen_coords(pdf_bbox)

        return {
            "mineru_bbox": mineru_bbox,
            "mineru_size": (mineru_bbox[2] - mineru_bbox[0], mineru_bbox[3] - mineru_bbox[1]),
            "pdf_bbox": [round(x, 2) for x in pdf_bbox],
            "pdf_size": (round(pdf_bbox[2] - pdf_bbox[0], 2), round(pdf_bbox[3] - pdf_bbox[1], 2)),
            "screen_bbox": [round(x, 2) for x in screen_bbox],
            "pdf_page_size": (self.pdf_width, self.pdf_height)
        }


def test_coordinate_transform():
    """测试坐标转换"""
    pdf_path = "data/pdfs/2403.14123v1_origin.pdf"
    mineru_bbox = [321, 64, 674, 97]  # "AI and Memory Wall" 标题

    transformer = CoordinateTransform(pdf_path, mineru_bbox)

    print("=" * 60)
    print("坐标转换测试")
    print("=" * 60)
    print(f"\nPDF 页面尺寸: {transformer.pdf_width} x {transformer.pdf_height}")
    print(f"MinerU 内部尺寸: {transformer.mineru_width} x {transformer.mineru_height}")

    # 转换 bbox
    pdf_bbox = transformer.bbox_to_pdf(mineru_bbox)
    print(f"\nMinerU bbox: {mineru_bbox}")
    print(f"PDF bbox: {[round(x, 2) for x in pdf_bbox]}")

    # 屏幕坐标
    screen_bbox = transformer.bbox_to_screen_coords(pdf_bbox)
    print(f"屏幕 bbox: {[round(x, 2) for x in screen_bbox]}")

    # 验证信息
    info = transformer.verify_bbox(mineru_bbox)
    print(f"\n验证信息:")
    print(f"  MinerU 尺寸: {info['mineru_size']}")
    print(f"  PDF 尺寸: {info['pdf_size']}")
    print(f"  PDF 页面: {info['pdf_page_size']}")

    # 测试归一化坐标
    normalized_bbox = [0.323, 0.065, 0.675, 0.098]
    pdf_from_norm = transformer.bbox_from_normalized(normalized_bbox)
    print(f"\n归一化 bbox: {normalized_bbox}")
    print(f"转换为 PDF: {[round(x, 2) for x in pdf_from_norm]}")

    transformer.close()


if __name__ == "__main__":
    test_coordinate_transform()
