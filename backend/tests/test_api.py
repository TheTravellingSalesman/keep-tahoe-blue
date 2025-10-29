"""
Tests for Keep Tahoe Blue API endpoints and functionality.
"""

import base64
import json
from io import BytesIO
from pathlib import Path
from fastapi.testclient import TestClient
from PIL import Image

from app.main import (
    app,
    convert_image_to_base64,
    FieldStatus,
    KTBFormField,
    KTBFormCategory,
    KTBForm,
    KTBFormResult,
)
from app.ocr import (
    OcrFormResult,
    OcrCategoryResult,
    OcrFieldResult,
)


# =============================================================================
# Test Helper Functions
# =============================================================================

def make_jpeg(img: Image.Image) -> bytes:
    """Convert PIL image to JPEG bytes."""
    buffer = BytesIO()
    img.save(buffer, format='JPEG')
    buffer.seek(0)
    return buffer.read()


def make_png(img: Image.Image) -> bytes:
    """Convert PIL image to PNG bytes."""
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    return buffer.read()


def make_ocr_result(category_data: dict) -> OcrFormResult:
    """
    Helper to create OCR result Pydantic models from dict structure.

    Args:
        category_data: Dict like {"category_name": {"field_name": {"value": x, "confidence": y}}}

    Returns:
        OcrFormResult Pydantic model
    """
    categories = {}
    for cat_name, fields_dict in category_data.items():
        fields = {}
        for field_name, field_data in fields_dict.items():
            fields[field_name] = OcrFieldResult(
                value=field_data["value"],
                confidence=field_data["confidence"]
            )
        categories[cat_name] = OcrCategoryResult(
            name=cat_name,
            fields=fields
        )
    return OcrFormResult(categories=categories)


class TestFormSchemaEndpoints:
    """Tests for form schema GET/PUT endpoints."""

    def test_get_schema_when_no_schema_exists(self, tmp_path: Path, monkeypatch):
        """Test GET /form-schema returns default schema when none exists."""
        import app.main as main_module
        monkeypatch.setattr(main_module, 'SCHEMA_FILE', tmp_path / "form_schema.json")

        client = TestClient(app)
        response = client.get("/form-schema")

        assert response.status_code == 200
        data = response.json()

        # Verify default schema was created
        assert "categories" in data
        assert "updated_at" in data
        assert len(data["categories"]) == 8  # Default has 8 categories

        # Verify some default categories exist
        category_names = [cat["name"] for cat in data["categories"]]
        assert "Plastic Items" in category_names
        assert "Glass items" in category_names
        assert "Animal waste" in category_names

    def test_put_schema_creates_new_schema(self, tmp_path: Path, monkeypatch):
        """Test PUT /form-schema creates a new schema with timestamp."""
        import app.main as main_module
        monkeypatch.setattr(main_module, 'SCHEMA_FILE', tmp_path / "form_schema.json")

        client = TestClient(app)
        schema = {
            "categories": [
                {
                    "name": "Plastics",
                    "fields": [
                        {"name": "bottles"},
                        {"name": "bags"},
                        {"name": "straws"}
                    ]
                },
                {
                    "name": "Glass",
                    "fields": [
                        {"name": "bottles"},
                        {"name": "jars"}
                    ]
                }
            ]
        }

        response = client.put("/form-schema", json=schema)

        assert response.status_code == 200
        data = response.json()

        # Verify schema structure
        assert "categories" in data
        assert "updated_at" in data
        assert len(data["categories"]) == 2
        assert data["categories"][0]["name"] == "Plastics"

        # Verify timestamp is in ISO format
        assert "T" in data["updated_at"]
        assert data["updated_at"].endswith("Z")

    def test_get_schema_returns_saved_schema(self, tmp_path: Path, monkeypatch):
        """Test GET /form-schema returns the previously saved schema."""
        import app.main as main_module
        monkeypatch.setattr(main_module, 'SCHEMA_FILE', tmp_path / "form_schema.json")

        client = TestClient(app)
        schema = {
            "categories": [
                {
                    "name": "Plastics",
                    "fields": [{"name": "bottles"}, {"name": "bags"}]
                }
            ]
        }

        # First, save a schema
        put_response = client.put("/form-schema", json=schema)
        assert put_response.status_code == 200
        saved_timestamp = put_response.json()["updated_at"]

        # Then retrieve it
        get_response = client.get("/form-schema")
        assert get_response.status_code == 200
        data = get_response.json()

        # Verify the data matches
        assert data["categories"] == schema["categories"]
        assert data["updated_at"] == saved_timestamp

    def test_put_schema_updates_existing_schema(self, tmp_path: Path, monkeypatch):
        """Test PUT /form-schema updates existing schema with new timestamp."""
        import app.main as main_module
        monkeypatch.setattr(main_module, 'SCHEMA_FILE', tmp_path / "form_schema.json")

        client = TestClient(app)
        initial_schema = {
            "categories": [
                {
                    "name": "Plastics",
                    "fields": [{"name": "bottles"}]
                }
            ]
        }

        # Save initial schema
        response1 = client.put("/form-schema", json=initial_schema)
        timestamp1 = response1.json()["updated_at"]

        # Update with modified schema
        modified_schema = {
            "categories": [
                {
                    "name": "Paper",
                    "fields": [{"name": "cardboard"}]
                }
            ]
        }
        response2 = client.put("/form-schema", json=modified_schema)
        timestamp2 = response2.json()["updated_at"]

        # Verify update
        assert response2.status_code == 200
        assert timestamp2 > timestamp1  # New timestamp should be later
        assert response2.json()["categories"][0]["name"] == "Paper"

    def test_schema_persists_to_file(self, tmp_path: Path, monkeypatch):
        """Test that schema is actually written to JSON file."""
        import app.main as main_module
        schema_file = tmp_path / "form_schema.json"
        monkeypatch.setattr(main_module, 'SCHEMA_FILE', schema_file)

        client = TestClient(app)
        schema = {
            "categories": [
                {
                    "name": "Metal",
                    "fields": [{"name": "cans"}, {"name": "foil"}]
                }
            ]
        }

        client.put("/form-schema", json=schema)

        # Verify file exists and contains correct data
        assert schema_file.exists()
        file_data = json.loads(schema_file.read_text())

        assert "categories" in file_data
        assert "updated_at" in file_data
        assert file_data["categories"] == schema["categories"]


class TestImageProcessing:
    """Tests for image/PDF processing functionality."""

    def test_process_jpg_image_to_base64(self):
        """Test JPG image is converted to base64 PNG."""
        img = Image.new('RGB', (100, 100), color='red')
        jpg_bytes = make_jpeg(img)

        result = convert_image_to_base64(jpg_bytes)

        # Verify it's a valid base64 string
        assert isinstance(result, str)
        decoded = base64.b64decode(result)

        # Verify it's a valid PNG image
        img = Image.open(BytesIO(decoded))
        assert img.format == 'PNG'
        assert img.mode == 'RGB'
        assert img.size == (100, 100)

    def test_process_png_image_to_base64(self):
        """Test PNG image is converted to base64 PNG."""
        img = Image.new('RGB', (100, 100), color='blue')
        png_bytes = make_png(img)

        result = convert_image_to_base64(png_bytes)

        # Verify it's a valid base64 string
        assert isinstance(result, str)
        decoded = base64.b64decode(result)

        # Verify it's a valid PNG image
        img = Image.open(BytesIO(decoded))
        assert img.format == 'PNG'
        assert img.mode == 'RGB'

    def test_process_rgba_image_converts_to_rgb(self):
        """Test RGBA image is converted to RGB before encoding."""
        img = Image.new('RGBA', (100, 100), color=(0, 255, 0, 128))
        rgba_bytes = make_png(img)

        result = convert_image_to_base64(rgba_bytes)

        decoded = base64.b64decode(result)
        img = Image.open(BytesIO(decoded))

        # Verify conversion to RGB
        assert img.mode == 'RGB'
        assert img.format == 'PNG'

    def test_process_image_standardizes_format(self):
        """Test that all images are standardized to the same format."""
        jpg_img = Image.new('RGB', (50, 50), color='red')
        jpg_bytes = make_jpeg(jpg_img)

        png_img = Image.new('RGB', (50, 50), color='blue')
        png_bytes = make_png(png_img)

        jpg_result = convert_image_to_base64(jpg_bytes)
        png_result = convert_image_to_base64(png_bytes)

        # Both should decode to PNG format
        jpg_decoded = Image.open(BytesIO(base64.b64decode(jpg_result)))
        png_decoded = Image.open(BytesIO(base64.b64decode(png_result)))

        assert jpg_decoded.format == 'PNG'
        assert png_decoded.format == 'PNG'


class TestValidationLogic:
    """Tests for field validation and status determination."""

    def test_integer_with_high_confidence_is_confident(self):
        """Test integer with confidence >= 0.95 gets 'confident' status."""
        field = KTBFormField.from_ocr_field("test", OcrFieldResult(value=5, confidence=0.95))
        assert field.value == "5"
        assert field.status == FieldStatus.CONFIDENT

        field = KTBFormField.from_ocr_field("test", OcrFieldResult(value=10, confidence=0.99))
        assert field.value == "10"
        assert field.status == FieldStatus.CONFIDENT

        field = KTBFormField.from_ocr_field("test", OcrFieldResult(value=0, confidence=1.0))
        assert field.value == "0"
        assert field.status == FieldStatus.CONFIDENT

    def test_integer_with_low_confidence_needs_validation(self):
        """Test integer with confidence < 0.95 gets 'needs-validation' status."""
        field = KTBFormField.from_ocr_field("test", OcrFieldResult(value=5, confidence=0.94))
        assert field.value == "5"
        assert field.status == FieldStatus.NEEDS_VALIDATION

        field = KTBFormField.from_ocr_field("test", OcrFieldResult(value=10, confidence=0.5))
        assert field.value == "10"
        assert field.status == FieldStatus.NEEDS_VALIDATION

        field = KTBFormField.from_ocr_field("test", OcrFieldResult(value=3, confidence=0.0))
        assert field.value == "3"
        assert field.status == FieldStatus.NEEDS_VALIDATION

    def test_non_integer_value_gets_error_status(self):
        """Test non-integer values get 'error' status regardless of confidence."""
        field = KTBFormField.from_ocr_field("test", OcrFieldResult(value="abc", confidence=0.99))
        assert field.value == "abc"
        assert field.status == FieldStatus.ERROR

        field = KTBFormField.from_ocr_field("test", OcrFieldResult(value="12.5", confidence=1.0))
        assert field.value == "12.5"
        assert field.status == FieldStatus.ERROR

        field = KTBFormField.from_ocr_field("test", OcrFieldResult(value="text123", confidence=0.95))
        assert field.value == "text123"
        assert field.status == FieldStatus.ERROR

    def test_none_value_converted_to_zero(self):
        """Test None values are converted to '0'."""
        # None with high confidence
        field = KTBFormField.from_ocr_field("test", OcrFieldResult(value=None, confidence=0.99))
        assert field.value == "0"
        assert field.status == FieldStatus.CONFIDENT

        # None with low confidence
        field = KTBFormField.from_ocr_field("test", OcrFieldResult(value=None, confidence=0.80))
        assert field.value == "0"
        assert field.status == FieldStatus.NEEDS_VALIDATION


class TestUploadEndpoint:
    """Tests for the /upload endpoint."""

    def test_upload_over_100_images_raises_validation_error(self, tmp_path: Path, monkeypatch):
        """Test uploading > 100 images returns 400 validation error."""
        import app.main as main_module
        monkeypatch.setattr(main_module, 'SCHEMA_FILE', tmp_path / "form_schema.json")

        client = TestClient(app)
        schema = {
            "categories": [
                {
                    "name": "Plastics",
                    "fields": [{"name": "bottles"}]
                }
            ]
        }

        # Setup schema
        client.put("/form-schema", json=schema)

        # Create a sample image
        image_bytes = make_jpeg(Image.new('RGB', (50, 50), color='red'))

        # Create 101 files
        files = [
            ("files", (f"image_{i}.jpg", BytesIO(image_bytes), "image/jpeg"))
            for i in range(101)
        ]

        metadata = json.dumps([
            {"uuid": f"test-uuid-{i}", "metadata": {}}
            for i in range(101)
        ])

        response = client.post(
            "/upload",
            files=files,
            data={"metadata": metadata}
        )

        assert response.status_code == 400
        assert "Too many images" in response.json()["detail"]
        assert "100" in response.json()["detail"]

    def test_upload_with_mismatched_metadata_count_raises_error(self, tmp_path: Path, monkeypatch):
        """Test uploading files with mismatched metadata count returns 400 error."""
        import app.main as main_module
        monkeypatch.setattr(main_module, 'SCHEMA_FILE', tmp_path / "form_schema.json")

        client = TestClient(app)
        schema = {
            "categories": [
                {
                    "name": "Plastics",
                    "fields": [{"name": "bottles"}]
                }
            ]
        }

        # Setup schema
        client.put("/form-schema", json=schema)

        # Create a sample image
        image_bytes = make_jpeg(Image.new('RGB', (50, 50), color='red'))

        # Create 3 files but only 2 metadata entries
        files = [
            ("files", (f"image_{i}.jpg", BytesIO(image_bytes), "image/jpeg"))
            for i in range(3)
        ]

        metadata = json.dumps([
            {"uuid": "test-uuid-0", "metadata": {}},
            {"uuid": "test-uuid-1", "metadata": {}}
        ])

        response = client.post(
            "/upload",
            files=files,
            data={"metadata": metadata}
        )

        assert response.status_code == 400
        assert "Metadata count" in response.json()["detail"]
        assert "must match file count" in response.json()["detail"]

    def test_upload_exactly_100_images_succeeds(self, tmp_path: Path, monkeypatch, mocker):
        """Test uploading exactly 100 images succeeds."""
        import app.main as main_module
        monkeypatch.setattr(main_module, 'SCHEMA_FILE', tmp_path / "form_schema.json")

        client = TestClient(app)
        schema = {
            "categories": [
                {
                    "name": "Plastics",
                    "fields": [
                        {"name": "bottles"},
                        {"name": "bags"},
                        {"name": "straws"}
                    ]
                },
                {
                    "name": "Glass",
                    "fields": [
                        {"name": "bottles"},
                        {"name": "jars"}
                    ]
                }
            ]
        }

        # Setup schema
        client.put("/form-schema", json=schema)

        # Mock OCR to avoid processing overhead
        mock_ocr = mocker.patch('app.main.process_image')
        mock_ocr.return_value = make_ocr_result({
            "Plastics": {
                "bottles": {"value": 5, "confidence": 0.99},
                "bags": {"value": 3, "confidence": 0.99},
                "straws": {"value": 2, "confidence": 0.99}
            },
            "Glass": {
                "bottles": {"value": 1, "confidence": 0.99},
                "jars": {"value": 0, "confidence": 0.99}
            }
        })

        # Create a sample image
        image_bytes = make_jpeg(Image.new('RGB', (50, 50), color='red'))

        # Create 100 files
        files = [
            ("files", (f"image_{i}.jpg", BytesIO(image_bytes), "image/jpeg"))
            for i in range(100)
        ]

        metadata = json.dumps([
            {"uuid": f"test-uuid-{i}", "metadata": {}}
            for i in range(100)
        ])

        response = client.post(
            "/upload",
            files=files,
            data={"metadata": metadata}
        )

        assert response.status_code == 200
        assert len(response.json()["results"]) == 100

    def test_upload_without_schema_uses_default(self, tmp_path: Path, monkeypatch, mocker):
        """Test upload uses default schema if no schema is configured."""
        import app.main as main_module
        monkeypatch.setattr(main_module, 'SCHEMA_FILE', tmp_path / "form_schema.json")

        client = TestClient(app)

        # Mock OCR to return results for default schema
        mock_ocr = mocker.patch('app.main.process_image')
        mock_ocr.return_value = make_ocr_result({
            "Plastic Items": {
                "Cigarette butts": {"value": 5, "confidence": 0.99},
                "Plastic bags": {"value": 3, "confidence": 0.99},
                "Plastic bottles": {"value": None, "confidence": 0.99},
                "Plastic bottle caps": {"value": None, "confidence": 0.99},
                "Plastic cups/lids": {"value": None, "confidence": 0.99},
                "Plastic food wrappers": {"value": None, "confidence": 0.99},
                "Plastic sled pieces": {"value": None, "confidence": 0.99},
                "Plastic straws/stirs/straw wrappers": {"value": None, "confidence": 0.99},
                "Plastic takeout containers/plates": {"value": None, "confidence": 0.99},
                "Plastic utensils": {"value": None, "confidence": 0.99},
                "Other plastic pieces": {"value": None, "confidence": 0.99},
            }
            # Would need all 8 categories, but this is sufficient for the test
        })

        # Create a sample image
        image_bytes = make_jpeg(Image.new('RGB', (50, 50), color='red'))

        files = [("files", ("image.jpg", BytesIO(image_bytes), "image/jpeg"))]
        metadata = json.dumps([{"uuid": "test-uuid", "metadata": {}}])

        response = client.post(
            "/upload",
            files=files,
            data={"metadata": metadata}
        )

        # Should succeed with default schema
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert len(data["results"]) == 1

    def test_upload_processes_and_returns_correct_structure(self, tmp_path: Path, monkeypatch, mocker):
        """Test upload returns correctly structured response."""
        import app.main as main_module
        monkeypatch.setattr(main_module, 'SCHEMA_FILE', tmp_path / "form_schema.json")

        client = TestClient(app)
        schema = {
            "categories": [
                {
                    "name": "Plastics",
                    "fields": [
                        {"name": "bottles"},
                        {"name": "bags"},
                        {"name": "straws"}
                    ]
                },
                {
                    "name": "Glass",
                    "fields": [
                        {"name": "bottles"},
                        {"name": "jars"}
                    ]
                }
            ]
        }

        # Setup schema
        client.put("/form-schema", json=schema)

        # Mock OCR
        mock_ocr = mocker.patch('app.main.process_image')
        mock_ocr.return_value = make_ocr_result({
            "Plastics": {
                "bottles": {"value": 5, "confidence": 0.99},
                "bags": {"value": 3, "confidence": 0.90},  # Low confidence
                "straws": {"value": "invalid", "confidence": 0.99}  # Non-integer
            },
            "Glass": {
                "bottles": {"value": None, "confidence": 0.99},  # None -> 0
                "jars": {"value": 2, "confidence": 0.95}
            }
        })

        # Create a sample image
        image_bytes = make_jpeg(Image.new('RGB', (50, 50), color='blue'))

        files = [("files", ("image.jpg", BytesIO(image_bytes), "image/jpeg"))]
        metadata = json.dumps([{"uuid": "test-uuid-1", "metadata": {"location": "beach"}}])

        response = client.post(
            "/upload",
            files=files,
            data={"metadata": metadata}
        )

        assert response.status_code == 200
        data = response.json()

        # Verify structure
        assert "results" in data
        assert len(data["results"]) == 1

        result = data["results"][0]
        assert result["uuid"] == "test-uuid-1"
        assert "image" in result  # Base64 image
        assert "form" in result

        # Verify form structure
        form = result["form"]
        assert len(form["categories"]) == 2

        # Check Plastics category
        plastics = form["categories"][0]
        assert plastics["name"] == "Plastics"
        assert len(plastics["fields"]) == 3

        # Verify field statuses
        bottles_field = next(f for f in plastics["fields"] if f["name"] == "bottles")
        assert bottles_field["value"] == "5"
        assert bottles_field["status"] == "confident"

        bags_field = next(f for f in plastics["fields"] if f["name"] == "bags")
        assert bags_field["value"] == "3"
        assert bags_field["status"] == "needs-validation"

        straws_field = next(f for f in plastics["fields"] if f["name"] == "straws")
        assert straws_field["value"] == "invalid"
        assert straws_field["status"] == "error"

        # Check Glass category
        glass = form["categories"][1]
        glass_bottles = next(f for f in glass["fields"] if f["name"] == "bottles")
        assert glass_bottles["value"] == "0"  # None converted to 0
        assert glass_bottles["status"] == "confident"

    def test_upload_results_sorted_by_issues(self, tmp_path: Path, monkeypatch, mocker):
        """Test upload results are sorted by number of issues (most first)."""
        import app.main as main_module
        monkeypatch.setattr(main_module, 'SCHEMA_FILE', tmp_path / "form_schema.json")

        client = TestClient(app)
        schema = {
            "categories": [
                {
                    "name": "Plastics",
                    "fields": [
                        {"name": "bottles"},
                        {"name": "bags"},
                        {"name": "straws"}
                    ]
                },
                {
                    "name": "Glass",
                    "fields": [
                        {"name": "bottles"},
                        {"name": "jars"}
                    ]
                }
            ]
        }

        # Setup schema
        client.put("/form-schema", json=schema)

        # Mock OCR with varying issues - use side_effect for multiple calls
        mock_ocr = mocker.patch('app.main.process_image')
        mock_ocr.side_effect = [
            make_ocr_result({  # image-1: 2 issues
                "Plastics": {
                    "bottles": {"value": 5, "confidence": 0.99},  # confident
                    "bags": {"value": 3, "confidence": 0.90},  # needs-validation
                    "straws": {"value": "bad", "confidence": 0.99}  # error
                },
                "Glass": {
                    "bottles": {"value": 1, "confidence": 0.99},  # confident
                    "jars": {"value": 2, "confidence": 0.99}  # confident
                }
            }),
            make_ocr_result({  # image-2: 0 issues (all confident)
                "Plastics": {
                    "bottles": {"value": 10, "confidence": 0.99},
                    "bags": {"value": 5, "confidence": 0.99},
                    "straws": {"value": 3, "confidence": 0.99}
                },
                "Glass": {
                    "bottles": {"value": 2, "confidence": 0.99},
                    "jars": {"value": 1, "confidence": 0.99}
                }
            }),
            make_ocr_result({  # image-3: 4 issues
                "Plastics": {
                    "bottles": {"value": 5, "confidence": 0.80},  # needs-validation
                    "bags": {"value": "x", "confidence": 0.99},  # error
                    "straws": {"value": 2, "confidence": 0.90}  # needs-validation
                },
                "Glass": {
                    "bottles": {"value": 1, "confidence": 0.99},  # confident
                    "jars": {"value": 2, "confidence": 0.85}  # needs-validation
                }
            })
        ]

        # Create a sample image
        image_bytes = make_jpeg(Image.new('RGB', (50, 50), color='green'))

        files = [
            ("files", (f"image-{i}.jpg", BytesIO(image_bytes), "image/jpeg"))
            for i in range(1, 4)
        ]
        metadata = json.dumps([
            {"uuid": f"image-{i}", "metadata": {}}
            for i in range(1, 4)
        ])

        response = client.post(
            "/upload",
            files=files,
            data={"metadata": metadata}
        )

        assert response.status_code == 200
        results = response.json()["results"]

        # Verify sorting: image-3 (4 issues), image-1 (2 issues), image-2 (0 issues)
        assert results[0]["uuid"] == "image-3"
        assert results[1]["uuid"] == "image-1"
        assert results[2]["uuid"] == "image-2"

        # Verify issue counts by counting non-confident statuses
        def count_issues(result):
            count = 0
            for category in result["form"]["categories"]:
                for field in category["fields"]:
                    if field["status"] in ["needs-validation", "error"]:
                        count += 1
            return count

        assert count_issues(results[0]) == 4
        assert count_issues(results[1]) == 2
        assert count_issues(results[2]) == 0


class TestCsvGenerationEndpoint:
    """Tests for the /generate-csv endpoint."""

    def test_generate_csv_with_single_category(self):
        """Test CSV generation with single category and metadata fields."""
        client = TestClient(app)

        request_data = {
            "metadata": [
                {"name": "date", "value": "2024-01-15"},
                {"name": "location", "value": "Lake Tahoe"}
            ],
            "clean-up-data": [
                {
                    "category": "Plastics",
                    "fields": [
                        {"name": "bottles", "value": 5},
                        {"name": "bags", "value": 3}
                    ]
                }
            ]
        }

        response = client.post("/generate-csv", json=request_data)

        assert response.status_code == 200
        assert response.headers["content-type"] == "text/csv; charset=utf-8"
        assert "attachment" in response.headers["content-disposition"]
        assert "cleanup_data_" in response.headers["content-disposition"]
        assert ".csv" in response.headers["content-disposition"]

        # Parse CSV content
        csv_content = response.text
        lines = csv_content.strip().split('\n')

        # Verify header
        assert lines[0] == "field_name,value,category_name,date,location"

        # Verify data rows
        assert lines[1] == "bottles,5,Plastics,2024-01-15,Lake Tahoe"
        assert lines[2] == "bags,3,Plastics,2024-01-15,Lake Tahoe"

    def test_generate_csv_with_multiple_categories(self):
        """Test CSV generation with multiple categories."""
        client = TestClient(app)

        request_data = {
            "metadata": [
                {"name": "volunteer", "value": "John Doe"}
            ],
            "clean-up-data": [
                {
                    "category": "Plastics",
                    "fields": [
                        {"name": "bottles", "value": 10}
                    ]
                },
                {
                    "category": "Glass",
                    "fields": [
                        {"name": "bottles", "value": 2},
                        {"name": "jars", "value": 1}
                    ]
                }
            ]
        }

        response = client.post("/generate-csv", json=request_data)

        assert response.status_code == 200

        # Parse CSV content
        csv_content = response.text
        lines = csv_content.strip().split('\n')

        # Should have header + 3 data rows
        assert len(lines) == 4
        assert lines[0] == "field_name,value,category_name,volunteer"
        assert lines[1] == "bottles,10,Plastics,John Doe"
        assert lines[2] == "bottles,2,Glass,John Doe"
        assert lines[3] == "jars,1,Glass,John Doe"

    def test_generate_csv_with_no_metadata(self):
        """Test CSV generation with no metadata fields."""
        client = TestClient(app)

        request_data = {
            "metadata": [],
            "clean-up-data": [
                {
                    "category": "Metal",
                    "fields": [
                        {"name": "cans", "value": 15}
                    ]
                }
            ]
        }

        response = client.post("/generate-csv", json=request_data)

        assert response.status_code == 200

        # Parse CSV content
        csv_content = response.text
        lines = csv_content.strip().split('\n')

        # Should have only the core columns (no metadata columns)
        assert lines[0] == "field_name,value,category_name"
        assert lines[1] == "cans,15,Metal"

    def test_generate_csv_with_zero_values(self):
        """Test CSV generation handles zero values correctly."""
        client = TestClient(app)

        request_data = {
            "metadata": [{"name": "session", "value": "morning"}],
            "clean-up-data": [
                {
                    "category": "Plastics",
                    "fields": [
                        {"name": "bottles", "value": 0},
                        {"name": "bags", "value": 5}
                    ]
                }
            ]
        }

        response = client.post("/generate-csv", json=request_data)

        assert response.status_code == 200

        # Parse CSV content
        csv_content = response.text
        lines = csv_content.strip().split('\n')

        # Verify zero is properly written
        assert lines[1] == "bottles,0,Plastics,morning"
        assert lines[2] == "bags,5,Plastics,morning"


class TestHealthEndpoint:
    """Tests for health check endpoint."""

    def test_health_check(self):
        """Test health endpoint returns healthy status."""
        client = TestClient(app)
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}
