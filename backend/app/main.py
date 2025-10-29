"""
Keep Tahoe Blue API - OCR Form Processing Backend
"""

import base64
import csv
import json
from datetime import datetime, timezone
from enum import Enum
from io import BytesIO, StringIO
from pathlib import Path
from threading import Lock
from typing import Any
from uuid import UUID

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from PIL import Image
from pydantic import BaseModel, Field

from .ocr import OcrCategoryResult, OcrFieldResult, OcrFormResult, process_image

SCHEMA_FILE = Path(__file__).parent / "data" / "form_schema.json"
DEFAULT_SCHEMA_FILE = Path(__file__).parent / "data" / "default-schema.json"
SCHEMA_LOCK = Lock()

app = FastAPI(
    title="Keep Tahoe Blue API",
    description="Backend API for OCR form processing",
    version="0.1.0",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Update this in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class FieldStatus(str, Enum):
    """Status of a field after OCR processing."""

    CONFIDENT = "confident"
    NEEDS_VALIDATION = "needs-validation"
    ERROR = "error"


class FieldSchemaInput(BaseModel):
    """Schema definition for a single field."""

    name: str


class CategorySchemaInput(BaseModel):
    """Schema definition for a category containing multiple fields."""

    name: str
    fields: list[FieldSchemaInput]


class FormSchemaInput(BaseModel):
    """Input model for form schema."""

    categories: list[CategorySchemaInput]


class FormSchemaOutput(BaseModel):
    """Output model for form schema with timestamp."""

    categories: list[CategorySchemaInput]
    updated_at: str  # ISO format datetime


class FilePayload(BaseModel):
    """Input model for a single file in the upload payload."""
    uuid: str
    name: str
    type: str
    size: int
    base64: str


class UploadPayload(BaseModel):
    """Input model for the /upload endpoint."""
    files: list[FilePayload]
    metadata: str


class KTBFormField(BaseModel):
    """A field in the form with validated OCR results."""

    name: str
    value: str
    status: FieldStatus

    @classmethod
    def from_ocr_field(cls, name: str, ocr_field: OcrFieldResult) -> "KTBFormField":
        """
        Create a KTBFormField from an OCR field result.

        Args:
            name: Field name
            ocr_field: Raw OCR result for this field

        Returns:
            KTBFormField with validated value and status

        Validation Rules:
            - If value is None, convert to "0"
            - If value cannot be converted to integer, status is "error"
            - If confidence < 0.95, status is "needs-validation"
            - Otherwise, status is "confident"
        """
        value = ocr_field.value
        confidence = ocr_field.confidence

        # Handle None values -> convert to "0"
        if value is None:
            value = 0

        # Handle None confidence -> treat as needs validation
        if confidence is None:
            confidence = 0.0

        # Try to convert to integer
        try:
            int_value = int(value)
            value_str = str(int_value)
        except (ValueError, TypeError):
            # Cannot convert to integer - return error status
            return cls(name=name, value=str(value), status=FieldStatus.ERROR)

        # Check confidence threshold
        if confidence < 0.95:
            return cls(name=name, value=value_str, status=FieldStatus.NEEDS_VALIDATION)

        return cls(name=name, value=value_str, status=FieldStatus.CONFIDENT)


class KTBFormCategory(BaseModel):
    """A category in the form."""

    name: str
    fields: list[KTBFormField]

    @classmethod
    def from_ocr_category(
        cls, category_schema: CategorySchemaInput, ocr_category: OcrCategoryResult
    ) -> "KTBFormCategory":
        """
        Create a KTBFormCategory from schema and OCR results.

        Args:
            category_schema: Schema definition for this category
            ocr_category: Raw OCR results for this category

        Returns:
            KTBFormCategory with validated fields
        """
        fields = []
        for field_schema in category_schema.fields:
            ocr_field = ocr_category.fields.get(
                field_schema.name, OcrFieldResult(value=None, confidence=1.0)
            )
            fields.append(KTBFormField.from_ocr_field(field_schema.name, ocr_field))
        return cls(name=category_schema.name, fields=fields)


class KTBForm(BaseModel):
    """Complete validated form."""

    categories: list[KTBFormCategory]

    @classmethod
    def from_ocr_form(
        cls, schema: FormSchemaOutput, ocr_form: OcrFormResult
    ) -> "KTBForm":
        """
        Create a KTBForm from schema and OCR results.

        Args:
            schema: Form schema defining expected categories and fields
            ocr_form: Raw OCR results for the entire form

        Returns:
            KTBForm with validated categories and fields
        """
        categories = []
        for category_schema in schema.categories:
            ocr_category = ocr_form.categories.get(category_schema.name)
            if ocr_category:
                categories.append(
                    KTBFormCategory.from_ocr_category(category_schema, ocr_category)
                )
        return cls(categories=categories)


class KTBFormResult(BaseModel):
    """Result for a single processed form image."""

    uuid: str
    image: str  # base64 encoded
    form: KTBForm


class UploadResponse(BaseModel):
    """Response containing all processed form results."""

    results: list[KTBFormResult]


class UploadMetadata(BaseModel):
    """Metadata for an uploaded file."""

    uuid: UUID
    metadata: dict[str, Any] = Field(default_factory=dict)


class CsvMetadataField(BaseModel):
    """A metadata field for CSV generation."""

    name: str
    value: str


class CsvFormField(BaseModel):
    """A field in the CSV form data."""

    name: str
    value: int


class CsvFormCategory(BaseModel):
    """A category in the CSV form data."""

    category: str
    fields: list[CsvFormField]


class CsvGenerationRequest(BaseModel):
    """Request body for CSV generation endpoint."""

    model_config = {"populate_by_name": True}

    metadata: list[CsvMetadataField]
    cleanup_data: list[CsvFormCategory] = Field(alias="clean-up-data")


def get_default_schema() -> FormSchemaInput:
    """
    Get the default form schema from the default-schema.json file.

    Returns:
        Default form schema with all expected categories and fields

    Raises:
        FileNotFoundError: If default-schema.json is missing
        ValueError: If default-schema.json is invalid
    """
    if not DEFAULT_SCHEMA_FILE.exists():
        raise FileNotFoundError(
            f"Default schema file not found at {DEFAULT_SCHEMA_FILE}"
        )

    data = json.loads(DEFAULT_SCHEMA_FILE.read_text())
    return FormSchemaInput(**data)


def get_schema() -> FormSchemaOutput:
    """
    Retrieve the current form schema from JSON file.
    If no schema exists, creates and returns the default schema.

    Returns:
        FormSchemaOutput with current or default schema
    """
    if not SCHEMA_FILE.exists():
        # Create default schema
        default_schema = get_default_schema()
        return save_schema(default_schema)

    with SCHEMA_LOCK:
        data = json.loads(SCHEMA_FILE.read_text())
        return FormSchemaOutput(**data)


def save_schema(schema: FormSchemaInput) -> FormSchemaOutput:
    """
    Save form schema to JSON file with timestamp.

    Args:
        schema: The form schema to save

    Returns:
        FormSchemaOutput with updated timestamp
    """
    # Ensure data directory exists
    SCHEMA_FILE.parent.mkdir(parents=True, exist_ok=True)

    with SCHEMA_LOCK:
        data = {
            "categories": [cat.model_dump() for cat in schema.categories],
            "updated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        }
        SCHEMA_FILE.write_text(json.dumps(data, indent=2))
        return FormSchemaOutput(**data)


def convert_image_to_base64(image_bytes: bytes) -> str:
    """
    Convert image bytes to standardized base64-encoded PNG.

    Args:
        image_bytes: Raw image file bytes

    Returns:
        Base64-encoded PNG image string
    """
    # Open image and convert to RGB (standardize format)
    img = Image.open(BytesIO(image_bytes))

    # Convert to RGB if necessary (e.g., RGBA, grayscale)
    if img.mode != "RGB":
        img = img.convert("RGB")

    # Save as PNG to BytesIO
    output = BytesIO()
    img.save(output, format="PNG")
    output.seek(0)

    # Encode to base64
    return base64.b64encode(output.read()).decode("utf-8")


def count_issues(result: KTBFormResult) -> int:
    """
    Count the number of fields with issues in a result.

    Args:
        result: Form result to analyze

    Returns:
        Number of fields with status "needs-validation" or "error"
    """
    count = 0
    for category in result.form.categories:
        for field in category.fields:
            if field.status in (FieldStatus.NEEDS_VALIDATION, FieldStatus.ERROR):
                count += 1
    return count


# =============================================================================
# API Endpoints
# =============================================================================


@app.get("/health")
async def health_check():
    """
    Health check endpoint.

    Returns:
        Simple health status response
    """
    return {"status": "healthy"}


@app.get("/form-schema", response_model=FormSchemaOutput)
async def get_form_schema():
    """
    Retrieve the currently configured form schema.

    If no schema has been configured yet, automatically creates and returns
    the default schema.

    Returns:
        Current form schema with categories, fields, and last update timestamp
    """
    return get_schema()


@app.put("/form-schema", response_model=FormSchemaOutput)
async def update_form_schema(schema: FormSchemaInput):
    """
    Update the form schema for the application.

    The form schema governs which fields we expect to find in an image, and
    are the only fields we will return values for.

    Args:
        schema: New form schema definition

    Returns:
        Updated schema with new timestamp
    """
    return save_schema(schema)


@app.post("/upload", response_model=UploadResponse)
async def upload_images(payload: UploadPayload):
    """
    Upload and process images for OCR form extraction from a JSON payload.

    Args:
        payload: JSON body containing a list of base64-encoded files and metadata.

    Returns:
        Processed results sorted by number of issues (most issues first)

    Raises:
        HTTPException: 400 if validation fails or more than 100 images provided
    """
    # Validate image count
    if len(payload.files) > 100:
        raise HTTPException(
            status_code=400,
            detail=f"Too many images. Maximum 100 allowed, received {len(payload.files)}",
        )

    # Get current schema (will create default if none exists)
    current_schema = get_schema()

    # Process images with OCR
    form_results = []
    for file_data in payload.files:
        try:
            # Decode the base64 string to get image bytes
            content = base64.b64decode(file_data.base64)
        except (ValueError, TypeError):
            raise HTTPException(
                status_code=400, detail=f"Invalid base64 string for file {file_data.name}"
            )

        # Convert to standardized base64 PNG
        b64_image = convert_image_to_base64(content)

        # Process with OCR
        ocr_result = process_image(b64_image, current_schema)

        # Create form result
        form = KTBForm.from_ocr_form(current_schema, ocr_result)
        form_results.append(
            KTBFormResult(uuid=file_data.uuid, image=b64_image, form=form)
        )

    # Sort by number of issues (descending - most issues first)
    form_results.sort(key=count_issues, reverse=True)

    return UploadResponse(results=form_results)


@app.post("/generate-csv")
async def generate_csv(request: CsvGenerationRequest):
    """
    Generate a CSV file from corrected form data and metadata.

    Each row in the CSV represents a single field with its value, category,
    and all metadata fields duplicated across all rows.

    Args:
        request: CSV generation request with metadata and cleanup data

    Returns:
        StreamingResponse with CSV file content

    CSV Format:
        - field_name: Name of the field
        - value: Field value (integer)
        - category_name: Category the field belongs to
        - [metadata columns]: One column for each metadata field (duplicated per row)

    Example:
        If metadata has [{"name": "date", "value": "2024-01-01"}]
        and cleanup_data has one category "Plastics" with field "bottles" = 5,
        the CSV will have columns: field_name, value, category_name, date
        and one row: bottles, 5, Plastics, 2024-01-01
    """
    # Build CSV in memory
    output = StringIO()

    # Create metadata column names and values dict
    metadata_columns = [field.name for field in request.metadata]
    metadata_values = {field.name: field.value for field in request.metadata}

    # Define CSV columns: field_name, value, category_name, then all metadata columns
    fieldnames = ["field_name", "value", "category_name"] + metadata_columns

    writer = csv.DictWriter(output, fieldnames=fieldnames, lineterminator='\n')
    writer.writeheader()

    # Write a row for each field in each category
    for category in request.cleanup_data:
        for field in category.fields:
            row = {
                "field_name": field.name,
                "value": field.value,
                "category_name": category.category,
                **metadata_values  # Spread all metadata values
            }
            writer.writerow(row)

    # Prepare CSV content for streaming
    output.seek(0)
    csv_content = output.getvalue()

    # Generate filename with timestamp
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"cleanup_data_{timestamp}.csv"

    # Return as streaming response with appropriate headers
    return StreamingResponse(
        iter([csv_content]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )
