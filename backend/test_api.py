#!/usr/bin/env python3
"""
Test script for the Keep Tahoe Blue API.

Tests the /upload endpoint with sample images.
"""

import base64
import json
import sys
from pathlib import Path
from uuid import uuid4

import requests


def test_health():
    """Test the health endpoint."""
    print("\n" + "="*80)
    print("Testing Health Endpoint")
    print("="*80)
    
    response = requests.get("http://localhost:8000/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    
    assert response.status_code == 200, "Health check failed"
    print("✓ Health check passed")


def test_get_schema():
    """Test getting the form schema."""
    print("\n" + "="*80)
    print("Testing Get Schema Endpoint")
    print("="*80)
    
    response = requests.get("http://localhost:8000/form-schema")
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        schema = response.json()
        print(f"Categories: {len(schema['categories'])}")
        for cat in schema['categories']:
            print(f"  - {cat['name']}: {len(cat['fields'])} fields")
        print("✓ Schema retrieved successfully")
        return schema
    else:
        print(f"✗ Failed to get schema: {response.text}")
        return None


def test_upload_single_image(image_path: str):
    """Test uploading a single image."""
    print("\n" + "="*80)
    print(f"Testing Upload Endpoint: {image_path}")
    print("="*80)
    
    if not Path(image_path).exists():
        print(f"✗ Image not found: {image_path}")
        return
    
    # Read image file
    with open(image_path, 'rb') as f:
        image_data = f.read()
    
    # Create metadata
    file_uuid = str(uuid4())
    metadata = [
        {
            "uuid": file_uuid,
            "metadata": {
                "filename": Path(image_path).name,
                "source": "test_script"
            }
        }
    ]
    
    # Prepare multipart form data
    files = {
        'files': (Path(image_path).name, image_data, 'image/jpeg')
    }
    
    data = {
        'metadata': json.dumps(metadata)
    }
    
    print(f"Uploading image with UUID: {file_uuid}")
    print("Sending request...")
    
    response = requests.post(
        "http://localhost:8000/upload",
        files=files,
        data=data
    )
    
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print("\n✓ Upload successful!")
        print(f"\nResults for {len(result['results'])} image(s):")
        
        for idx, form_result in enumerate(result['results'], 1):
            print(f"\n--- Image {idx} (UUID: {form_result['uuid']}) ---")
            
            total_fields = 0
            confident_fields = 0
            needs_validation = 0
            errors = 0
            
            for category in form_result['form']['categories']:
                print(f"\n  {category['name']}:")
                for field in category['fields']:
                    total_fields += 1
                    status = field['status']
                    value = field['value']
                    
                    if status == 'confident':
                        confident_fields += 1
                        marker = "✓"
                    elif status == 'needs-validation':
                        needs_validation += 1
                        marker = "⚠"
                    else:
                        errors += 1
                        marker = "✗"
                    
                    print(f"    {marker} {field['name']:40s} = {value:>4s}  [{status}]")
            
            print(f"\n  Summary:")
            print(f"    Total fields:      {total_fields}")
            print(f"    Confident:         {confident_fields}")
            print(f"    Needs validation:  {needs_validation}")
            print(f"    Errors:            {errors}")
    else:
        print(f"✗ Upload failed")
        print(f"Response: {response.text}")


def test_upload_multiple_images(image_paths: list[str]):
    """Test uploading multiple images."""
    print("\n" + "="*80)
    print(f"Testing Multiple Upload: {len(image_paths)} images")
    print("="*80)
    
    # Prepare files and metadata
    files = []
    metadata = []
    
    for image_path in image_paths:
        if not Path(image_path).exists():
            print(f"✗ Image not found: {image_path}")
            continue
        
        with open(image_path, 'rb') as f:
            image_data = f.read()
        
        file_uuid = str(uuid4())
        files.append(('files', (Path(image_path).name, image_data, 'image/jpeg')))
        metadata.append({
            "uuid": file_uuid,
            "metadata": {
                "filename": Path(image_path).name,
                "source": "test_script"
            }
        })
    
    data = {
        'metadata': json.dumps(metadata)
    }
    
    print(f"Uploading {len(files)} images...")
    
    response = requests.post(
        "http://localhost:8000/upload",
        files=files,
        data=data
    )
    
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"\n✓ Upload successful! Processed {len(result['results'])} images")
        
        for idx, form_result in enumerate(result['results'], 1):
            total_fields = sum(len(cat['fields']) for cat in form_result['form']['categories'])
            issues = sum(
                1 for cat in form_result['form']['categories']
                for field in cat['fields']
                if field['status'] in ['needs-validation', 'error']
            )
            print(f"  {idx}. UUID: {form_result['uuid'][:8]}... - {total_fields} fields, {issues} issues")
    else:
        print(f"✗ Upload failed: {response.text}")


def main():
    """Run API tests."""
    print("\n" + "="*80)
    print("Keep Tahoe Blue API Test Suite")
    print("="*80)
    print("\nMake sure the API server is running:")
    print("  cd backend")
    print("  uv run uvicorn app.main:app --reload")
    print()
    
    try:
        # Test health endpoint
        test_health()
        
        # Test schema endpoint
        schema = test_get_schema()
        
        # Test single image upload
        sample_images = [
            "./sample_cards/IMG_5715.jpg",
            "./sample_cards/IMG_5716.jpg",
            "../sample_cards/IMG_5715.jpg",
            "../sample_cards/IMG_5716.jpg",
        ]
        
        # Find first existing image
        test_image = None
        for img in sample_images:
            if Path(img).exists():
                test_image = img
                break
        
        if test_image:
            test_upload_single_image(test_image)
        else:
            print("\n⚠ No sample images found for testing")
        
        # Test multiple images if available
        existing_images = [img for img in sample_images if Path(img).exists()]
        if len(existing_images) >= 2:
            test_upload_multiple_images(existing_images[:2])
        
        print("\n" + "="*80)
        print("✓ All tests completed!")
        print("="*80 + "\n")
        
    except requests.exceptions.ConnectionError:
        print("\n✗ Error: Could not connect to API server")
        print("Make sure the server is running on http://localhost:8000")
        print("\nStart the server with:")
        print("  cd backend")
        print("  uv run uvicorn app.main:app --reload")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
