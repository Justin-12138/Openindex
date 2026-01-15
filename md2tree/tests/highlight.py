import fitz  # PyMuPDF

pdf_path = "/home/lz/repo/PageIndex/md2tree/data/pdfs/2403.14123v1_origin.pdf"
output_path = "/home/lz/repo/PageIndex/md2tree/data/pdfs/2403.14123v1_highlight.pdf"

page_idx = 0
bbox = [197, 51, 413, 77]  # x0, y0, x1, y1

# 打开 PDF
doc = fitz.open(pdf_path)
page = doc[page_idx]

# 创建矩形区域
rect = fitz.Rect(bbox)

# 添加高亮注释
highlight = page.add_highlight_annot(rect)

# （可选）设置高亮颜色（默认是黄色）
highlight.set_colors(stroke=(1, 1, 0))  # RGB, 黄色
highlight.update()

# 保存新文件
doc.save(output_path)
doc.close()

print(f"高亮完成，输出文件：{output_path}")
