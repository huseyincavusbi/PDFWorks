import os
import io
from PIL import Image
from tqdm import tqdm
import multiprocessing
import fitz  # PyMuPDF

# Optimized image processing function with smart rotation
def process_image_final(args):
    idx, img_path, max_width, max_height, jpeg_quality, force_portrait, rotation_angle = args
    
    try:
        with Image.open(img_path) as img:
            # Convert to RGB if needed
            if img.mode != "RGB":
                img = img.convert("RGB")
            
            # Handle EXIF orientation data to fix camera rotation issues
            exif_corrected = False
            try:
                from PIL.ExifTags import ORIENTATION
                if hasattr(img, 'getexif'):
                    exif_dict = img.getexif()
                    if exif_dict and ORIENTATION in exif_dict:
                        orientation = exif_dict[ORIENTATION]
                        
                        if orientation == 3:
                            img = img.transpose(Image.ROTATE_180)
                            exif_corrected = True
                        elif orientation == 6:
                            img = img.transpose(Image.ROTATE_270)
                            exif_corrected = True  
                        elif orientation == 8:
                            img = img.transpose(Image.ROTATE_90)
                            exif_corrected = True
            except Exception:
                pass # Ignore if EXIF data is missing or invalid
            
            # Force portrait orientation if requested
            rotated = False
            applied_rotation_angle = 0
            if force_portrait and img.width > img.height:
                # Use the user-specified rotation angle
                img = img.rotate(rotation_angle, expand=True)
                applied_rotation_angle = rotation_angle
                rotated = True
            
            # Calculate new size while maintaining aspect ratio (ONLY DOWNSCALE)
            original_width, original_height = img.size
            aspect_ratio = original_width / original_height
            
            # Only resize if the image is larger than our max dimensions
            resized = False
            if original_width > max_width or original_height > max_height:
                if aspect_ratio > 1:  # Landscape (shouldn't happen after rotation if force_portrait is true)
                    new_width = min(max_width, original_width)
                    new_height = int(new_width / aspect_ratio)
                else:  # Portrait
                    new_height = min(max_height, original_height)
                    new_width = int(new_height * aspect_ratio)
                
                # Only resize if we're making it smaller (never upscale)
                if new_width < original_width or new_height < original_height:
                    img = img.resize((new_width, new_height), Image.LANCZOS)
                    resized = True
            
            # Save as JPEG to bytes
            img_bytes_io = io.BytesIO()
            img.save(img_bytes_io, format="JPEG", quality=jpeg_quality)
            img_bytes = img_bytes_io.getvalue()
            width, height = img.size
            
            return (idx, img_bytes, width, height, rotated, resized, applied_rotation_angle, exif_corrected)
            
    except Exception as e:
        print(f"⚠️  Error processing {os.path.basename(img_path)}: {e}")
        return None

def main():
    print("Image Folder to PDF Converter)")
    print("=" * 60)

    # --- USER INPUT SECTION ---
    image_folder = "path/to/your/image/folder"  # Change this to your image folder path
    output_pdf_path = "path/to/your/output.pdf"  # Change this to your desired output PDF path

    # Optimized settings for portrait PDFs
    max_width = 1200   # Maximum width in pixels (portrait orientation)
    max_height = 1600  # Maximum height in pixels (taller for portrait)
    jpeg_quality = 85  # JPEG quality (0-100)
    force_portrait = True  # Force all images to portrait orientation

    # Rotation settings (if images are upside down, try different values)
    rotation_angle = -90  # Degrees to rotate landscape images (-90, 90, 180, 270)
                          # -90 = counter-clockwise, 90 = clockwise
                          # Try 90 if images are upside down with -90
    # --- END USER INPUT SECTION ---

    print(f"Source folder: {image_folder}")
    print(f"Output PDF: {output_pdf_path}")
    print(f"Portrait mode: {'Enabled' if force_portrait else 'Disabled'}")
    if force_portrait:
        print(f"🔄 Rotation angle: {rotation_angle}° ({'Counter-clockwise' if rotation_angle < 0 else 'Clockwise'})")
    print()

    # Get sorted list of image files
    image_files = sorted([
        os.path.join(image_folder, f)
        for f in os.listdir(image_folder)
        if f.lower().endswith((".jpg", ".jpeg", ".png", ".bmp", ".tiff"))
    ])

    if not image_files:
        print("❌ No image files found in the specified folder!")
        return # Use return instead of exit() in a function

    print(f"🔍 Found {len(image_files)} images")

    # CPU configuration
    num_procs = os.cpu_count() or 1
    print(f"🚀 Using {num_procs} CPU cores for multiprocessing")
    print()

    # Prepare arguments for multiprocessing
    args_list = [(i, img_path, max_width, max_height, jpeg_quality, force_portrait, rotation_angle) 
                 for i, img_path in enumerate(image_files)]

    print("🔄 Processing images...")
    results = []
    rotation_count = 0
    resize_count = 0
    exif_correction_count = 0
    rotation_angles = []

    with multiprocessing.Pool(processes=num_procs) as pool:
        for result in tqdm(pool.imap_unordered(process_image_final, args_list), 
                          total=len(args_list), desc="Processing"):
            if result:
                results.append(result)
                if len(result) >= 7 and result[4]:  # rotated (handle both old and new format)
                    rotation_count += 1
                    if len(result) >= 7:
                        rotation_angles.append(result[6])  # rotation angle
                if len(result) >= 6 and result[5]:  # resized
                    resize_count += 1
                if len(result) >= 8 and result[7]:  # exif corrected
                    exif_correction_count += 1

    # Sort results by original order
    results.sort(key=lambda x: x[0])

    print(f"✅ Processed {len(results)} images successfully")
    print(f"🔧 Applied EXIF orientation correction to {exif_correction_count} images")
    print(f"🔄 Rotated {rotation_count} landscape images to portrait")
    if rotation_angles:
        print(f"   └─ Rotation angles used: {set(rotation_angles)} degrees")
    print(f"📏 Resized {resize_count} images for optimization")
    print()

    if not results:
        print("❌ No images were processed successfully!")
        return # Use return instead of exit() in a function

    # Create PDF
    print("📚 Assembling PDF...")
    new_doc = fitz.open()

    for idx, result in enumerate(tqdm(results, desc="Writing pages")):
        try:
            # Handle both old and new result formats
            if len(result) >= 8:
                i, img_bytes, width, height, rotated, resized, rotation_angle, exif_corrected = result
            elif len(result) >= 7:
                i, img_bytes, width, height, rotated, resized, rotation_angle = result
            else:
                i, img_bytes, width, height, rotated, resized = result
            
            img_stream = io.BytesIO(img_bytes)
            new_page_rect = fitz.Rect(0, 0, width, height)
            new_page = new_doc.new_page(width=width, height=height)
            new_page.insert_image(new_page_rect, stream=img_stream)
            
            # Progress update every 50 pages
            if (idx + 1) % 50 == 0 or (idx + 1) == len(results):
                print(f"  📄 Written {idx + 1}/{len(results)} pages...")
                
        except Exception as e:
            print(f"⚠️  Error adding page {idx + 1}: {e}")

    # Save PDF
    try:
        new_doc.save(output_pdf_path)
        new_doc.close()
        print(f"PDF saved successfully!")
    except Exception as e:
        print(f"❌ Error saving PDF: {e}")
        return # Use return instead of exit() in a function

    # Final validation and statistics
    print()
    print("🔍 Final validation...")

    try:
        # Validate PDF
        doc_final = fitz.open(output_pdf_path)
        page_count = doc_final.page_count
        
        # Check orientations
        portrait_pages = 0
        landscape_pages = 0
        for i in range(page_count):
            page = doc_final[i]
            if page.rect.height > page.rect.width:
                portrait_pages += 1
            else:
                landscape_pages += 1
        
        # Get file size
        file_size_mb = os.path.getsize(output_pdf_path) / (1024 * 1024)
        avg_size_per_page = file_size_mb / page_count if page_count > 0 else 0
        
        doc_final.close()
        
        # Success report
        print("=" * 60)
        print("SUCCESS! PDF Created Successfully")
        print("=" * 60)
        print(f"Output file: {output_pdf_path}")
        print(f"Total pages: {page_count}")
        print(f"Portrait pages: {portrait_pages} ({portrait_pages/page_count*100:.1f}%)")
        print(f"Landscape pages: {landscape_pages} ({landscape_pages/page_count*100:.1f}%)")
        print(f"File size: {file_size_mb:.1f} MB")
        print(f"Average per page: {avg_size_per_page:.2f} MB")
        print()
        
        if force_portrait and portrait_pages == page_count:
            print("🎉 Perfect! All images are now in portrait orientation!")
            print("🔧 Applied smart rotation with EXIF orientation correction")
        elif force_portrait:
            print(f"⚠️  Note: {landscape_pages} images remained in landscape orientation")
        
    except Exception as e:
        print(f"⚠️  Validation error (but PDF was created): {e}")
        print(f"📄 Check the file manually: {output_pdf_path}")

    print("🏁 Process completed!")

# This is the crucial part: ensures main() runs only when the script is executed directly
if __name__ == '__main__':
    main()
