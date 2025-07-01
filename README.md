# PDF Image & Resolution Tools

This repo provides two high-performance Jupyter notebooks for working with PDFs and images, optimized for speed and ease of use.

## Notebooks

### ImageToPDF.ipynb
Convert a folder of images into a single, compact, portrait-oriented PDF.
- Multiprocessing for fast, parallel image processing
- Auto-rotate landscape images to portrait (configurable)
- EXIF orientation correction
- Smart resizing and JPEG quality control
- Progress bars and validation

**Use cases:**
- Photo archiving, albums, sharing, screenshot-to-PDF

### Pdf_Resolution_Conv.ipynb
Downsample and compress an existing PDF to reduce size and resolution.
- Multiprocessing (chunked page processing)
- DPI downsampling and JPEG compression
- Handles large PDFs efficiently
- Progress bars and order preservation

## Quick Start
1. Clone this repo and open a notebook in Jupyter/VS Code.
2. Run the setup cell to install dependencies.
3. Edit the config section at the top of the main cell.
4. Run the main cell to process your files.

**Requirements:** Python 3.8+, Jupyter/VS Code, auto-installs PyMuPDF, Pillow, tqdm.

---
Both notebooks are optimized for large files and use all CPU cores by default. All outputs are compatible with standard PDF viewers.