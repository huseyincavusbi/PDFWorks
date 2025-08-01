# PDF Resolution & Size Converter (Script Version)
# Convert a PDF to a smaller, lower-resolution version by rendering each page as a JPEG at your chosen DPI and quality.
# Usage: Edit the variables below and run this script with Python 3.

import os
import io
import fitz  # PyMuPDF
from tqdm import tqdm
import multiprocessing
from PIL import Image

def process_chunk_mp(args):
    start, end, pdf_path, dpi, jpeg_quality = args
    doc = fitz.open(pdf_path)
    chunk_results = []
    for page_num in range(start, end):
        page = doc.load_page(page_num)
        downsampled_pix = page.get_pixmap(dpi=dpi)
        img = Image.frombytes("RGB", [downsampled_pix.width, downsampled_pix.height], downsampled_pix.samples)
        img_bytes_io = io.BytesIO()
        img.save(img_bytes_io, format="JPEG", quality=jpeg_quality)
        img_bytes = img_bytes_io.getvalue()
        chunk_results.append((page_num, img_bytes, downsampled_pix.width, downsampled_pix.height))
    doc.close()
    return chunk_results

def main():
    # ---- USER SETTINGS ----
    pdf_path = "path/to/your/input.pdf"  # Input PDF path
    output_pdf_path = os.path.splitext(pdf_path)[0] + "_dwn.pdf"  # Output PDF path
    dpi = 60  # Target DPI (lower for smaller file)
    jpeg_quality = 30  # JPEG quality (lower for smaller file)
    # -----------------------

    original_file_size = os.path.getsize(pdf_path)
    original_doc = fitz.open(pdf_path)
    num_pages = original_doc.page_count
    original_doc.close()

    num_procs = min(multiprocessing.cpu_count() or 1, 8)  # Limit to 8 to avoid memory issues
    print(f"Detected {num_procs} CPU cores for multiprocessing.")
    print(f"Input PDF: {pdf_path}")
    print(f"Total pages to process: {num_pages}")
    print(f"Target DPI for downsampling: {dpi}")
    print(f"JPEG quality: {jpeg_quality}")
    print(f"Output PDF will be saved as: {output_pdf_path}\n")

    chunk_size = (num_pages + num_procs - 1) // num_procs
    chunks = [(i*chunk_size, min((i+1)*chunk_size, num_pages), pdf_path, dpi, jpeg_quality) for i in range(num_procs) if i*chunk_size < num_pages]
    print(f"Splitting {num_pages} pages into {len(chunks)} chunks for multiprocessing.\n")

    with multiprocessing.Pool(processes=num_procs) as pool:
        results = []
        for chunk_result in tqdm(pool.imap_unordered(process_chunk_mp, chunks), total=len(chunks), desc="Process chunks"):
            results.extend(chunk_result)

    results.sort(key=lambda x: x[0])

    print("\nAssembling downsampled pages into new PDF (multiprocessing, JPEG)...")
    new_doc = fitz.open()
    for idx, (page_num, img_bytes, width, height) in enumerate(tqdm(results, desc="Writing pages")):
        img_stream = io.BytesIO(img_bytes)
        new_page_rect = fitz.Rect(0, 0, width, height)
        new_page = new_doc.new_page(width=new_page_rect.width, height=new_page_rect.height)
        new_page.insert_image(new_page_rect, stream=img_stream)
        if (idx+1) % 10 == 0 or (idx+1) == len(results):
            print(f"  Written {idx+1}/{len(results)} pages...")

    new_doc.save(output_pdf_path)
    new_doc.close()

    new_file_size = os.path.getsize(output_pdf_path)
    print("\nPDF processing complete (multiprocessing, JPEG).")
    print(f"Original file size: {original_file_size/1024/1024:.2f} MB")
    print(f"Downsampled file size: {new_file_size/1024/1024:.2f} MB")
    print(f"Downsampled file saved at: {output_pdf_path}")

if __name__ == "__main__":
    main()
