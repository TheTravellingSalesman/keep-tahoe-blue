"""
Image preprocessing utilities for data card processing.
Handles base64 decoding, image enhancement, and preparation for vision models.
"""

import base64
import io
from typing import List, Tuple, Optional
from PIL import Image, ImageEnhance, ImageFilter
import numpy as np
import cv2
import logging

logger = logging.getLogger(__name__)


class ImagePreprocessor:
    """Handles preprocessing of data card images for optimal OCR/vision model performance."""
    
    def __init__(
        self,
        target_size: int = None,
        enhance_contrast: bool = True,
        denoise: bool = True
    ):
        """
        Initialize the preprocessor.
        
        Args:
            target_size: Optional (width, height) to resize images
            enhance_contrast: Whether to enhance image contrast
            denoise: Whether to apply denoising
        """
        self.target_size = target_size
        self.enhance_contrast = enhance_contrast
        self.denoise = denoise
    
    def decode_base64_image(self, base64_string: str) -> Image.Image:
        """
        Decode a base64 encoded image string to PIL Image.
        
        Args:
            base64_string: Base64 encoded image string
            
        Returns:
            PIL Image object
        """
        # Remove data URI prefix if present
        if ',' in base64_string:
            base64_string = base64_string.split(',')[1]
        
        image_data = base64.b64decode(base64_string)
        image = Image.open(io.BytesIO(image_data))
        
        # Convert to RGB if needed
        if image.mode not in ('RGB', 'L'):
            image = image.convert('RGB')
        
        return image
    
    def encode_to_base64(self, image: Image.Image, format: str = "JPEG") -> str:
        """
        Encode PIL Image to base64 string.
        
        Args:
            image: PIL Image object
            format: Image format (JPEG, PNG, etc.)
            
        Returns:
            Base64 encoded string
        """
        buffer = io.BytesIO()
        image.save(buffer, format=format)
        buffer.seek(0)
        return base64.b64encode(buffer.read()).decode('utf-8')
    
    def resize_image_if_needed(self, image: Image.Image, max_size=1296):
        """Resize image if it exceeds max_size on any dimension."""
        width, height = image.size
        
        if width <= max_size and height <= max_size:
            logging.info(f"Image size {width}x{height} is within limits")
            return image
        
        # Calculate new size maintaining aspect ratio
        if width > height:
            new_width = max_size
            new_height = int((max_size / width) * height)
        else:
            new_height = max_size
            new_width = int((max_size / height) * width)
        
        logging.info(f"Resizing image from {width}x{height} to {new_width}x{new_height}")
        image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        return image
    
    def preprocess_image(self, image: Image.Image) -> Image.Image:
        """
        Apply preprocessing steps to enhance image for vision model.
        
        Args:
            image: Input PIL Image
            
        Returns:
            Preprocessed PIL Image
        """
        # Resize if target_size is specified
        if self.target_size:
            image = self.resize_image_if_needed(image, self.target_size)
        else:
            # Use default max_size
            image = self.resize_image_if_needed(image)
        
        # Enhance contrast
        if self.enhance_contrast:
            image = self._enhance_contrast(image)
        
        # Denoise
        if self.denoise:
            image = self._denoise(image)
        
        # Additional enhancements for data cards
        image = self._enhance_for_ocr(image)
        
        return image
    
    def _enhance_contrast(self, image: Image.Image) -> Image.Image:
        """Enhance image contrast - use gentle enhancement."""
        enhancer = ImageEnhance.Contrast(image)
        return enhancer.enhance(1.2)  # Reduced from 1.5
    
    def _denoise(self, image: Image.Image) -> Image.Image:
        """Apply denoising filter."""
        return image.filter(ImageFilter.MedianFilter(size=3))
    
    def _enhance_for_ocr(self, image: Image.Image) -> Image.Image:
        """
        Apply specific enhancements for better OCR on data cards.
        Very light enhancement - PaddleOCR works well with minimal preprocessing.
        """
        # Light sharpening only
        image = image.filter(ImageFilter.SHARPEN)
        
        return image
    
    def auto_rotate(self, image: Image.Image) -> Image.Image:
        """
        Automatically detect and correct image rotation.
        
        Args:
            image: Input PIL Image
            
        Returns:
            Rotated PIL Image
        """
        # Convert to numpy array for OpenCV processing
        img_array = np.array(image)
        
        # Convert to grayscale
        if len(img_array.shape) == 3:
            gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        else:
            gray = img_array
        
        # Detect edges
        edges = cv2.Canny(gray, 50, 150, apertureSize=3)
        
        # Detect lines using Hough transform
        lines = cv2.HoughLines(edges, 1, np.pi / 180, 200)
        
        if lines is not None and len(lines) > 0:
            # Calculate average angle
            angles = []
            for line in lines[:10]:  # Use first 10 lines
                rho, theta = line[0]
                angle = np.degrees(theta) - 90
                angles.append(angle)
            
            avg_angle = np.median(angles)
            
            # Rotate if angle is significant
            if abs(avg_angle) > 1:
                image = image.rotate(avg_angle, expand=True, fillcolor='white')
        
        return image
    
    def process_batch(
        self,
        base64_images: List[str],
        auto_rotate_images: bool = True
    ) -> List[Image.Image]:
        """
        Process a batch of base64 encoded images.
        
        Args:
            base64_images: List of base64 encoded image strings
            auto_rotate_images: Whether to apply automatic rotation correction
            
        Returns:
            List of preprocessed PIL Images
        """
        processed_images = []
        
        for base64_img in base64_images:
            # Decode
            image = self.decode_base64_image(base64_img)
            
            # Auto-rotate if enabled
            if auto_rotate_images:
                image = self.auto_rotate(image)
            
            # Preprocess
            image = self.preprocess_image(image)
            
            processed_images.append(image)
        
        return processed_images
    
    def get_image_info(self, image: Image.Image) -> dict:
        """
        Get information about an image.
        
        Args:
            image: PIL Image
            
        Returns:
            Dictionary with image information
        """
        return {
            'size': image.size,
            'mode': image.mode,
            'format': image.format,
            'width': image.width,
            'height': image.height
        }
