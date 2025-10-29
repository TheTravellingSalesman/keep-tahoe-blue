#!/usr/bin/env python3
"""
Quick test script for DataCardOCR - minimal dependencies version.

This script tests the OCR with a simplified schema.

Usage:
    cd backend
    python test_ocr_simple.py
"""

import sys
from pathlib import Path

# Add paths
sys.path.insert(0, str(Path(__file__).parent))

from PIL import Image
from app.ocr import DataCardOCR


def main():
    """Run a simple OCR test."""
    
    # Find a sample image
    sample_images = [
        "../sample_cards/IMG_5716.jpg",
        "../sample_cards/IMG_5715.jpg",
        "sample_cards/IMG_5716.jpg",
        "sample_cards/IMG_5715.jpg",
    ]
    
    image_path = None
    for path in sample_images:
        if Path(path).exists():
            image_path = path
            break
    
    if not image_path:
        print("❌ No sample images found. Please provide an image path:")
        print("   python test_ocr_simple.py <path_to_image>")
        return
    
    if len(sys.argv) > 1:
        image_path = sys.argv[1]
    
    print(f"\n{'='*80}")
    print(f"Testing DataCardOCR")
    print(f"{'='*80}\n")
    print(f"Image: {image_path}\n")
    
    # Load image
    print("📸 Loading image...")
    image = Image.open(image_path)
    print(f"   ✓ Loaded: {image.size[0]}x{image.size[1]} pixels\n")
    
    # Initialize OCR
    print("🔧 Initializing OCR (this may take a moment)...")
    ocr = DataCardOCR(enhance_contrast=True, denoise=True)
    print("   ✓ OCR ready\n")
    
    # Run OCR to get raw text
    print("🔍 Running OCR...")
    ocr_data = ocr.process_image_ocr(image)
    print(f"   ✓ Detected {len(ocr_data['ocr_results'])} text items\n")
    
    # Display results
    print(f"{'='*80}")
    print("Detected Text (first 100 items):")
    print(f"{'='*80}\n")
    
    for i, item in enumerate(ocr_data['ocr_results'][:100]):
        conf = item['confidence'] * 100
        text = item['text']
        box = item['box']
        
        # Highlight count patterns
        if text.startswith('=') and text[1:].strip().isdigit():
            marker = "🔢"
        else:
            marker = "  "
        
        print(f"{marker} [{conf:5.1f}%] {text:40s} @ y={box[1]:4d}")
    
    if len(ocr_data['ocr_results']) > 100:
        print(f"\n... and {len(ocr_data['ocr_results']) - 100} more items")
    
    print(f"\n{'='*80}")
    print("✓ Test completed successfully!")
    print(f"{'='*80}\n")


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
