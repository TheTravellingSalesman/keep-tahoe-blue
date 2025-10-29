"""
OCR Module for processing images and extracting form data.

This module provides an interface for OCR processing using PaddleOCR to extract
card count data from data collection form images.
"""

import logging
from pathlib import Path
import re
import tempfile
from typing import Any, Optional

from paddleocr import PaddleOCR
from PIL import Image
from pydantic import BaseModel

from utils.preprocessor import ImagePreprocessor

# Import types from main to avoid circular dependency issues
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .main import FormSchemaOutput

logger = logging.getLogger(__name__)


# =============================================================================
# OCR Result Models
# =============================================================================


class OcrFieldResult(BaseModel):
    """Raw OCR result for a single field (before validation)."""

    value: Optional[Any]
    confidence: Optional[float]


class OcrCategoryResult(BaseModel):
    """Raw OCR results for a category."""

    name: str
    fields: dict[str, OcrFieldResult]  # field_name -> result


class OcrFormResult(BaseModel):
    """Raw OCR results for an entire form."""

    categories: dict[str, OcrCategoryResult]  # category_name -> result


# =============================================================================
# DataCardOCR Class
# =============================================================================


class DataCardOCR:
    """
    Converts data card images to card count data using PaddleOCR.
    
    This class handles OCR processing of data collection form images,
    extracting text with coordinates and confidence scores, then parsing
    the text to extract field counts using pattern matching.
    """
    
    def __init__(self, enhance_contrast: bool = False, denoise: bool = False):
        """
        Initialize PaddleOCR with optimized settings for data cards.
        
        Args:
            enhance_contrast: Whether to enhance image contrast during preprocessing
            denoise: Whether to apply denoising during preprocessing
        """
        self.ocr = PaddleOCR(
            lang='en',
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=False
        )
        
        # Initialize image preprocessor with minimal processing
        # PaddleOCR works better with less aggressive preprocessing
        self.preprocessor = ImagePreprocessor(
            target_size=None,  # Let resize_image_if_needed handle max size
            enhance_contrast=enhance_contrast,
            denoise=denoise
        )
    
    def process_image_ocr(self, image: Image.Image) -> dict[str, Any]:
        """
        Run OCR on an image and extract text with coordinates and confidence.
        
        Args:
            image: PIL Image to process
            
        Returns:
            Dictionary containing OCR results with text, coordinates, and confidence
        """
        # Always resize to max size - this is required for PaddleOCR
        image = self.preprocessor.resize_image_if_needed(image, max_size=1296)
        
        # Save to temporary file for PaddleOCR
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp_file:
            tmp_path = tmp_file.name
            image.save(tmp_path, format='JPEG', quality=95)
        
        try:
            # Run OCR using predict_iter (same as working implementation)
            result_iter = self.ocr.predict_iter(tmp_path)
            
            # Process results from iterator
            ocr_results = []
            
            idx = 0
            for res in result_iter:
                idx += 1
                
                # Extract data from result object (same as working implementation)
                result_data = None
                if hasattr(res, 'json') and isinstance(res.json, dict):
                    result_data = res.json
                elif hasattr(res, 'json') and callable(res.json):
                    result_data = res.json()
                elif hasattr(res, 'to_dict'):
                    result_data = res.to_dict()
                elif hasattr(res, '__dict__'):
                    result_data = {k: str(v) for k, v in res.__dict__.items() if not k.startswith('_')}
                else:
                    continue
                
                # Extract text, boxes, and scores from the result
                if 'res' in result_data:
                    res_data = result_data['res']
                    texts = res_data.get('rec_texts', [])
                    scores = res_data.get('rec_scores', [])
                    boxes = res_data.get('rec_boxes', [])
                    
                    for i, (text, score, box) in enumerate(zip(texts, scores, boxes)):
                        ocr_results.append({
                            'text': text,
                            'confidence': score,
                            'box': box  # [x_min, y_min, x_max, y_max]
                        })
            
            return {
                'ocr_results': ocr_results,
                'text_lines': [item['text'] for item in ocr_results]
            }
        
        finally:
            # Clean up temporary file
            Path(tmp_path).unlink(missing_ok=True)
    
    def extract_field_counts(
        self, 
        ocr_results: list[dict[str, Any]], 
        schema: "FormSchemaOutput"
    ) -> dict[str, dict[str, OcrFieldResult]]:
        """
        Extract field counts from OCR results based on schema.
        
        Uses sophisticated spatial matching to find count values (e.g., "=5", "=12")
        associated with field labels, following the pattern matching strategy.
        
        Args:
            ocr_results: List of OCR results with text, confidence, and coordinates
            schema: Form schema defining categories and fields
            
        Returns:
            Dictionary mapping category names to field results
        """
        # Build a flat list of all field names for cross-checking
        all_field_names = []
        field_to_category = {}
        
        for category in schema.categories:
            for field in category.fields:
                all_field_names.append(field.name)
                field_to_category[field.name] = category.name
        
        # Sort OCR results by position (y, then x) for spatial analysis
        sorted_results = sorted(ocr_results, key=lambda x: (x['box'][1], x['box'][0]))
        
        # Initialize all categories in the result structure
        category_results = {}
        for category in schema.categories:
            category_results[category.name] = {}
        
        # Extract counts for each field
        for field_name in all_field_names:
            count, confidence = self._find_item_count(
                field_name, 
                sorted_results, 
                all_field_names
            )
            
            category_name = field_to_category[field_name]
            
            # Always store the field, even if not found (with None values)
            if count > 0 or confidence > 0:
                category_results[category_name][field_name] = OcrFieldResult(
                    value=count,
                    confidence=confidence
                )
            else:
                # Field not found - return with None value and confidence
                category_results[category_name][field_name] = OcrFieldResult(
                    value=None,
                    confidence=None
                )
        
        return category_results
    
    def _find_item_count(
        self,
        item_name: str,
        ocr_items: list[dict[str, Any]],
        all_items: list[str]
    ) -> tuple[int, float]:
        """
        Find the count for a specific item using schema-driven spatial matching.
        
        Strategy:
        1. Find OCR fragments that match the item name from schema
        2. Check if =NUMBER is embedded in the same OCR fragment (after item name)
        3. Otherwise, find the nearest =NUMBER pattern to the right on the same line
        4. Ensure the count doesn't belong to another schema item
        
        Args:
            item_name: The item to search for (e.g., "Cigarette butts")
            ocr_items: List of OCR result dicts with text, confidence, and box coordinates
            all_items: All schema items (to avoid matching counts from other items)
        
        Returns:
            Tuple of (count, confidence)
        """
        # Normalize item name for fuzzy matching
        item_lower = item_name.lower()
        item_words = item_lower.split()
        
        # Get key words (longer words are more distinctive)
        key_words = [w for w in item_words if len(w) > 3]
        if not key_words:
            key_words = item_words
        
        # Find OCR fragments that match this schema item
        item_matches = []
        for item in ocr_items:
            text = item['text']
            text_lower = text.lower()
            x, y = item['box'][0], item['box'][1]
            conf = item['confidence']
            
            # Count how many key words match (fuzzy - allow OCR errors)
            match_count = 0
            for word in key_words:
                # Exact match or prefix match (for OCR errors)
                if word in text_lower or (len(word) >= 4 and text_lower.find(word[:4]) >= 0):
                    match_count += 1
            
            match_quality = match_count / len(key_words) if key_words else 0
            
            # Check if words appear in correct order (bonus for correct ordering)
            in_order = True
            last_pos = -1
            for word in key_words:
                pos = text_lower.find(word)
                if pos < 0 and len(word) >= 4:
                    pos = text_lower.find(word[:4])
                if pos >= 0:
                    if pos <= last_pos:
                        in_order = False
                        break
                    last_pos = pos
            
            # Boost match quality if words are in correct order
            if in_order and match_quality > 0:
                match_quality += 0.5
            
            # More lenient matching: at least 50% of key words
            if match_quality >= 0.5:
                item_matches.append((text, x, y, conf, match_quality))
        
        if not item_matches:
            return 0, 0.0
        
        # Sort by match quality (best first)
        item_matches.sort(key=lambda m: m[4], reverse=True)
        
        # For the best match, check if the count is IN THE SAME OCR fragment
        item_text, item_x, item_y, item_conf, match_quality = item_matches[0]
        
        # FIRST: Check if the item text itself contains =NUMBER (combined in same OCR block)
        embedded_match = re.search(r'=\s*(\d+)', item_text)
        if embedded_match:
            # Verify the =NUMBER appears after the item name keywords in the text
            item_text_lower = item_text.lower()
            last_keyword_pos = -1
            for word in key_words:
                pos = item_text_lower.rfind(word)
                if pos > last_keyword_pos:
                    last_keyword_pos = pos
            
            # Check if =NUMBER appears after the last keyword
            count_pos = embedded_match.start()
            if count_pos > last_keyword_pos:
                count = int(embedded_match.group(1))
                return count, item_conf
        
        # SECOND: Find =NUMBER patterns on the same line to the right
        best_count = None
        best_confidence = None
        best_distance = float('inf')
        
        for item in ocr_items:
            text = item['text']
            x, y = item['box'][0], item['box'][1]
            conf = item['confidence']
            
            match = re.search(r'=\s*(\d+)', text)
            if match:
                count = int(match.group(1))
                
                # Calculate spatial distance
                dx = x - item_x
                dy = abs(y - item_y)
                
                # Must be on the SAME LINE:
                # - To the right (dx > 0)
                # - Within 18 pixels vertically (tight tolerance)
                # - Within 400 pixels horizontally
                if dx > 0 and dx < 400 and dy < 18:
                    # Check if there's another schema item between this item and the count
                    blocked = False
                    for other_item in all_items:
                        if other_item == item_name:
                            continue
                        
                        other_lower = other_item.lower()
                        other_words = [w for w in other_lower.split() if len(w) > 3]
                        if not other_words:
                            other_words = other_lower.split()
                        
                        for check_item in ocr_items:
                            check_text_lower = check_item['text'].lower()
                            check_x = check_item['box'][0]
                            check_y = check_item['box'][1]
                            
                            other_match_count = sum(1 for word in other_words if word in check_text_lower)
                            other_match_quality = other_match_count / len(other_words) if other_words else 0
                            
                            if other_match_quality >= 0.7:
                                # This other item is present - is it between our item and count?
                                if item_x + 30 < check_x < x - 30 and abs(check_y - item_y) < 15:
                                    blocked = True
                                    break
                        
                        if blocked:
                            break
                    
                    if not blocked:
                        distance = dx
                        
                        if distance < best_distance:
                            best_distance = distance
                            best_count = count
                            best_confidence = conf
        
        if best_count is not None:
            return best_count, best_confidence
        
        # Not found - return 0 with confidence 0.0
        return 0, 0.0
    
    def process_image_to_form_result(
        self, 
        image: Image.Image | str,
        schema: "FormSchemaOutput"
    ) -> OcrFormResult:
        """
        Process an image and extract form data based on schema.
        
        Args:
            image: PIL Image or base64-encoded image string
            schema: Form schema defining expected categories and fields
            
        Returns:
            OcrFormResult with extracted field values and confidence scores
        """
        # Decode if base64 string
        if isinstance(image, str):
            image = self.preprocessor.decode_base64_image(image)
        
        # Run OCR
        ocr_data = self.process_image_ocr(image)
        
        # Extract field counts
        category_results = self.extract_field_counts(ocr_data['ocr_results'], schema)
        
        # Build OcrFormResult
        categories = {}
        for category_name, fields in category_results.items():
            categories[category_name] = OcrCategoryResult(
                name=category_name,
                fields=fields
            )
        
        return OcrFormResult(categories=categories)


# =============================================================================
# Public API
# =============================================================================

# Global OCR instance (lazy initialization)
_ocr_instance = None


def get_ocr_instance() -> DataCardOCR:
    """Get or create the global OCR instance."""
    global _ocr_instance
    if _ocr_instance is None:
        _ocr_instance = DataCardOCR()
    return _ocr_instance


def process_image(
    image: str,  # base64-encoded image
    schema: "FormSchemaOutput",  # Pydantic model
) -> OcrFormResult:
    """
    Process a single image using OCR to extract form data.

    Args:
        image: Base64-encoded image
        schema: Form schema Pydantic model defining expected categories and fields

    Returns:
        OcrFormResult Pydantic model containing raw OCR values and confidence scores
        (before validation)
    """
    ocr = get_ocr_instance()

    try:
        return ocr.process_image_to_form_result(image, schema)
    except Exception:
        # On error, return empty result
        logger.exception("Error processing image")
        return OcrFormResult(categories={})
