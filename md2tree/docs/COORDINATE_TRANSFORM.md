# MinerU 坐标转换说明

## 问题背景

MinerU 输出的坐标（`bbox`）基于其内部处理尺寸（约 1000x1000），而不是原始 PDF 的尺寸（例如 612x792）。直接使用这些坐标在 PDF 中定位会不准确。

## 坐标系统

### PDF 坐标系统
- **原点**: 左下角 (0, 0)
- **X 轴**: 从左到右
- **Y 轴**: 从下到上
- **标准尺寸**: Letter (612 x 792 点，1点 = 1/72英寸)

### MinerU 坐标系统
- **原点**: 左下角 (0, 0)
- **内部尺寸**: 约 1000 x 1000
- **输出格式**: `[x1, y1, x2, y2]` 像素坐标

## 坐标转换

### 转换公式

```python
pdf_x1 = (mineru_x1 / mineru_width) * pdf_width
pdf_y1 = (mineru_y1 / mineru_height) * pdf_height
pdf_x2 = (mineru_x2 / mineru_width) * pdf_width
pdf_y2 = (mineru_y2 / mineru_height) * pdf_height
```

### 示例

标题 "AI and Memory Wall" 的坐标转换：

| 坐标系 | bbox | 说明 |
|--------|------|------|
| MinerU | `[321, 64, 674, 97]` | 基于 1000x1000 |
| PDF | `[196.45, 50.69, 412.49, 76.82]` | 转换到 612x792 |

## 使用方法

### 自动坐标转换

在创建 `MinerUParser` 时传入 `pdf_path` 参数，坐标会自动转换：

```python
from mineru_parser import MinerUParser

parser = MinerUParser(
    content_list_path="path/to/content_list.json",
    pdf_path="path/to/original.pdf"  # 关键：传递 PDF 路径
)

# 每个内容块现在包含两种坐标
for block in parser.content_blocks:
    print(f"MinerU bbox: {block.bbox}")
    print(f"PDF bbox: {block.pdf_bbox}")
```

### 输出数据结构

```json
{
  "title": "AI and Memory Wall",
  "page_info": {
    "title_location": {
      "page_idx": 0,
      "bbox": [321, 64, 674, 97],      // MinerU 原始坐标
      "pdf_bbox": [196.45, 50.69, 412.49, 76.82],  // 转换后的 PDF 坐标
      "text": "AI and Memory Wall",
      "type": "title"
    }
  }
}
```

## 使用工作流

```python
from workflow import PDFToTreeWorkflow

workflow = PDFToTreeWorkflow(
    pdf_path="data/pdfs/2403.14123v1_origin.pdf",
    mineru_output_dir="data/pdfs/res/2403.14123v1_origin"
)

tree_data = workflow.run_basic(output_path="results/output.json")
# 坐标会自动转换
```

## 注意事项

1. **Y 轴方向**: PDF 和 MinerU 都使用左下角原点，不需要翻转 Y 轴
2. **DPI 差异**: 如果 PDF 使用非标准 DPI，可能需要调整 `mineru_width/height`
3. **屏幕坐标**: 在 HTML/Canvas 中使用时，需要将 Y 坐标翻转（因为屏幕使用左上角原点）

### 屏幕坐标转换

如果要在 HTML Canvas 中显示，需要翻转 Y 轴：

```python
def pdf_to_screen_coords(pdf_bbox, pdf_height):
    x1, y1, x2, y2 = pdf_bbox
    return [x1, pdf_height - y2, x2, pdf_height - y1]
```

## 验证

运行测试脚本验证坐标转换：

```bash
# 测试坐标转换
python coordinate_transform.py

# 测试完整工作流
python demo.py

# 运行测试套件
python test_mineru_integration.py
```
