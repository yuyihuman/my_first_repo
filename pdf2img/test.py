from pathlib import Path
import fitz  # PyMuPDF
from PIL import Image
from io import BytesIO

# 定义当前文件夹和输出目录
current_dir = Path(".")  # 当前文件夹
output_dir = current_dir / "output_images"
output_dir.mkdir(exist_ok=True)

# 遍历当前文件夹下所有 PDF 文件
pdf_files = list(current_dir.glob("*.pdf"))  # 匹配所有 .pdf 文件
if not pdf_files:
    print("当前文件夹下没有找到 PDF 文件。")
else:
    image_counter = 1  # 用于全局图片计数
    for pdf_path in pdf_files:
        # 打开 PDF 并逐页转换为图片
        pdf_document = fitz.open(pdf_path)
        print(f"正在处理文件：{pdf_path.name}")
        for page_num in range(len(pdf_document)):
            page = pdf_document[page_num]
            pix = page.get_pixmap(dpi=300)  # 设置分辨率为 150 DPI，保证初始质量
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            
            # 使用 BytesIO 临时保存图片以控制大小
            buffer = BytesIO()
            img.save(buffer, format="JPEG", quality=90)  # 初始压缩质量为 90
            buffer_size = buffer.tell()  # 检查文件大小

            # 如果文件大于 3MB，则逐步降低质量
            while buffer_size > 3 * 1024 * 1024:  # 3MB
                buffer = BytesIO()  # 重置缓冲区
                img.save(buffer, format="JPEG", quality=80)  # 降低质量到 80
                buffer_size = buffer.tell()

            # 保存最终图片
            output_file = output_dir / f"{image_counter}.jpg"
            with open(output_file, "wb") as f:
                f.write(buffer.getvalue())
            
            image_counter += 1  # 增加计数
        
        print(f"文件 {pdf_path.name} 已转换完成。")

print(f"所有 PDF 文件已处理完成，图片保存在 {output_dir} 文件夹中。")
