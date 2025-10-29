#!/usr/bin/env python3
"""
Test script for DataCardOCR class.

Usage:
    python test_ocr.py <image_path>
    
Example:
    python test_ocr.py ../sample_cards/IMG_5716.jpg
"""

import argparse
import json
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from PIL import Image
from app.ocr import DataCardOCR, OcrFormResult
from pydantic import BaseModel


# =============================================================================
# Mock Schema for Testing
# =============================================================================

class FieldSchemaInput(BaseModel):
    """Schema definition for a single field."""
    name: str


class CategorySchemaInput(BaseModel):
    """Schema definition for a category containing multiple fields."""
    name: str
    fields: list[FieldSchemaInput]


class FormSchemaOutput(BaseModel):
    """Output model for form schema with timestamp."""
    categories: list[CategorySchemaInput]
    updated_at: str = "2025-10-22T00:00:00Z"


# =============================================================================
# Test Schema Based on categories.yaml
# =============================================================================

def create_test_schema() -> FormSchemaOutput:
    """Create a test schema based on the data card format."""
    return FormSchemaOutput(
        categories=[
            CategorySchemaInput(
                name="Plastic Items",
                fields=[
                    FieldSchemaInput(name="Cigarette butts"),
                    FieldSchemaInput(name="Plastic bags"),
                    FieldSchemaInput(name="Plastic bottles"),
                    FieldSchemaInput(name="Plastic bottle caps"),
                    FieldSchemaInput(name="Plastic cups/lids"),
                    FieldSchemaInput(name="Plastic food wrappers"),
                    FieldSchemaInput(name="Plastic sled pieces"),
                    FieldSchemaInput(name="Plastic straws/stirs/straw wrappers"),
                    FieldSchemaInput(name="Plastic takeout containers/plates"),
                    FieldSchemaInput(name="Plastic utensils"),
                    FieldSchemaInput(name="Other plastic pieces"),
                ]
            ),
            CategorySchemaInput(
                name="Styrofoam plastic items",
                fields=[
                    FieldSchemaInput(name="Styrofoam cups"),
                    FieldSchemaInput(name="Styrofoam takeout containers/plates"),
                    FieldSchemaInput(name="Other Styrofoam pieces"),
                ]
            ),
            CategorySchemaInput(
                name="Metal items",
                fields=[
                    FieldSchemaInput(name="Metal cans/pull tabs/metal bottle caps"),
                    FieldSchemaInput(name="Other metal/aluminum pieces"),
                ]
            ),
            CategorySchemaInput(
                name="Paper items",
                fields=[
                    FieldSchemaInput(name="Paper cups/lids"),
                    FieldSchemaInput(name="Paper straws"),
                    FieldSchemaInput(name="Paper takeout containers/plates"),
                    FieldSchemaInput(name="Other paper pieces"),
                ]
            ),
            CategorySchemaInput(
                name="Glass items",
                fields=[
                    FieldSchemaInput(name="Glass bottles"),
                    FieldSchemaInput(name="Other glass pieces"),
                ]
            ),
            CategorySchemaInput(
                name="Personal hygiene",
                fields=[
                    FieldSchemaInput(name="Health/safety items (mask, wipes, gloves)"),
                    FieldSchemaInput(name="Sanitary items (diapers, tampon, toilet paper, band aid, condom)"),
                    FieldSchemaInput(name="Human waste (don't pick up)"),
                    FieldSchemaInput(name="Syringes (don't pick up)"),
                ]
            ),
            CategorySchemaInput(
                name="Animal waste",
                fields=[
                    FieldSchemaInput(name="Dog waste in bag"),
                    FieldSchemaInput(name="Dog waste not in bag (piles)"),
                    FieldSchemaInput(name="Wildlife waste with trash in it (piles)"),
                ]
            ),
        ]
    )


# =============================================================================
# Test Functions
# =============================================================================

def test_ocr_from_file(image_path: str, debug: bool = False):
    """
    Test OCR processing on an image file.
    
    Args:
        image_path: Path to the image file
        debug: Whether to print debug information
    """
    print(f"\n{'='*80}")
    print(f"Testing OCR on: {image_path}")
    print(f"{'='*80}\n")
    
    # Check if file exists
    if not Path(image_path).exists():
        print(f"❌ Error: Image file not found: {image_path}")
        return
    
    # Load image
    print("📸 Loading image...")
    try:
        image = Image.open(image_path)
        print(f"   ✓ Image loaded: {image.size[0]}x{image.size[1]} pixels, mode={image.mode}")
    except Exception as e:
        print(f"   ❌ Error loading image: {e}")
        return
    
    # Initialize OCR
    print("\n🔧 Initializing DataCardOCR...")
    try:
        ocr = DataCardOCR(enhance_contrast=True, denoise=True)
        print("   ✓ OCR initialized successfully")
    except Exception as e:
        print(f"   ❌ Error initializing OCR: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Create test schema
    print("\n📋 Creating test schema...")
    schema = create_test_schema()
    print(f"   ✓ Schema created with {len(schema.categories)} categories")
    
    # Process image
    print("\n🔍 Running OCR processing...")
    try:
        result = ocr.process_image_to_form_result(image, schema)
        print("   ✓ OCR processing completed")
    except Exception as e:
        print(f"   ❌ Error during OCR processing: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Display results
    print(f"\n{'='*80}")
    print("📊 RESULTS")
    print(f"{'='*80}\n")
    
    total_fields_found = 0
    total_categories_found = len(result.categories)
    
    for category_name, category_result in result.categories.items():
        print(f"\n📁 {category_name}")
        print(f"   {'─'*76}")
        
        if not category_result.fields:
            print("   (No fields detected)")
            continue
        
        for field_name, field_result in category_result.fields.items():
            total_fields_found += 1
            
            # Handle None confidence values
            if field_result.confidence is None:
                confidence_percent = 0.0
                status = "✗"
            else:
                confidence_percent = field_result.confidence * 100
                # Color code based on confidence
                if field_result.confidence >= 0.95:
                    status = "✓"
                elif field_result.confidence >= 0.80:
                    status = "⚠"
                else:
                    status = "⚠"
            
            # Handle None values
            value_str = str(field_result.value) if field_result.value is not None else "-"
            
            print(f"   {status} {field_name:50s} = {value_str:>3}  (confidence: {confidence_percent:5.1f}%)")
    
    print(f"\n{'='*80}")
    print(f"Summary:")
    print(f"  • Categories found: {total_categories_found}/{len(schema.categories)}")
    print(f"  • Fields extracted: {total_fields_found}")
    print(f"{'='*80}\n")
    
    # Debug: Show raw OCR results
    if debug:
        print(f"\n{'='*80}")
        print("🔍 DEBUG: Raw OCR Data")
        print(f"{'='*80}\n")
        
        try:
            ocr_data = ocr.process_image_ocr(image)
            print(f"Total OCR text items: {len(ocr_data['ocr_results'])}\n")
            
            for i, item in enumerate(ocr_data['ocr_results'][:50]):  # Show first 50
                conf = item['confidence'] * 100 if item['confidence'] else 0.0
                print(f"{i+1:3d}. [{conf:5.1f}%] {item['text']}")
            
            if len(ocr_data['ocr_results']) > 50:
                print(f"\n... and {len(ocr_data['ocr_results']) - 50} more items")
        except Exception as e:
            print(f"Error getting debug info: {e}")
    
    # Save results to JSON
    output_path = Path(image_path).stem + "_ocr_results.json"
    print(f"\n💾 Saving results to: {output_path}")
    try:
        with open(output_path, 'w') as f:
            json.dump(result.model_dump(), f, indent=2)
        print(f"   ✓ Results saved")
    except Exception as e:
        print(f"   ⚠ Warning: Could not save results: {e}")


# =============================================================================
# Main
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Test DataCardOCR on an image file",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python test_ocr.py ../sample_cards/IMG_5716.jpg
  python test_ocr.py ../sample_cards/IMG_5716.jpg --debug
        """
    )
    parser.add_argument(
        'image_path',
        help='Path to the image file to process'
    )
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Show debug information including raw OCR text'
    )
    
    args = parser.parse_args()
    
    test_ocr_from_file(args.image_path, debug=args.debug)


if __name__ == '__main__':
    main()
