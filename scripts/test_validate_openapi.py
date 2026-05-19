"""
Tests for OpenAPI validation script.
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from validate_openapi import OpenAPIValidator


@pytest.fixture
def valid_spec():
    """Create a valid OpenAPI spec."""
    return {
        "openapi": "3.1.0",
        "info": {
            "title": "Test API",
            "version": "1.0.0",
        },
        "paths": {
            "/api/test/": {
                "post": {
                    "requestBody": {"content": {"application/json": {}}},
                    "responses": {"200": {"description": "Success"}},
                }
            }
        },
        "components": {
            "schemas": {
                "TestRequest": {
                    "type": "object",
                    "required": ["name"],
                    "properties": {"name": {"type": "string"}},
                },
                "TestResponse": {
                    "type": "object",
                    "required": ["id", "name"],
                    "properties": {
                        "id": {"type": "integer"},
                        "name": {"type": "string"},
                    },
                },
            }
        },
    }


@pytest.fixture
def valid_generated():
    """Create a valid generated schema."""
    return {
        "openapi": "3.1.0",
        "info": {
            "title": "Test API",
            "version": "1.0.0",
        },
        "paths": {
            "/api/test/": {
                "post": {
                    "requestBody": {"content": {"application/json": {}}},
                    "responses": {"200": {"description": "Success"}},
                }
            }
        },
        "components": {
            "schemas": {
                "TestRequest": {
                    "type": "object",
                    "required": ["name"],
                    "properties": {"name": {"type": "string"}},
                },
                "TestResponse": {
                    "type": "object",
                    "required": ["id", "name"],
                    "properties": {
                        "id": {"type": "integer"},
                        "name": {"type": "string"},
                    },
                },
            }
        },
    }


def test_validate_endpoints_implemented(valid_spec, valid_generated):
    """Test that missing endpoints are detected."""
    with tempfile.TemporaryDirectory() as tmpdir:
        spec_path = Path(tmpdir) / "spec.yaml"
        generated_path = Path(tmpdir) / "generated.json"

        with open(spec_path, "w") as f:
            yaml.dump(valid_spec, f)
        with open(generated_path, "w") as f:
            json.dump(valid_generated, f)

        validator = OpenAPIValidator(str(spec_path), str(generated_path))
        validator._validate_endpoints_implemented()
        assert len(validator.errors) == 0


def test_validate_endpoints_missing(valid_spec, valid_generated):
    """Test that missing endpoints generate errors."""
    with tempfile.TemporaryDirectory() as tmpdir:
        spec_path = Path(tmpdir) / "spec.yaml"
        generated_path = Path(tmpdir) / "generated.json"

        # Add extra endpoint to spec
        valid_spec["paths"]["/api/missing/"] = {"get": {}}

        with open(spec_path, "w") as f:
            yaml.dump(valid_spec, f)
        with open(generated_path, "w") as f:
            json.dump(valid_generated, f)

        validator = OpenAPIValidator(str(spec_path), str(generated_path))
        validator._validate_endpoints_implemented()
        assert any("Endpoint not implemented" in e for e in validator.errors)


def test_validate_schemas_match(valid_spec, valid_generated):
    """Test that matching schemas pass validation."""
    with tempfile.TemporaryDirectory() as tmpdir:
        spec_path = Path(tmpdir) / "spec.yaml"
        generated_path = Path(tmpdir) / "generated.json"

        with open(spec_path, "w") as f:
            yaml.dump(valid_spec, f)
        with open(generated_path, "w") as f:
            json.dump(valid_generated, f)

        validator = OpenAPIValidator(str(spec_path), str(generated_path))
        validator._validate_schemas_match()
        assert len(validator.errors) == 0


def test_validate_schemas_missing_required_field(valid_spec, valid_generated):
    """Test that missing required fields are detected."""
    with tempfile.TemporaryDirectory() as tmpdir:
        spec_path = Path(tmpdir) / "spec.yaml"
        generated_path = Path(tmpdir) / "generated.json"

        # Remove required field from generated
        del valid_generated["components"]["schemas"]["TestRequest"]["required"]

        with open(spec_path, "w") as f:
            yaml.dump(valid_spec, f)
        with open(generated_path, "w") as f:
            json.dump(valid_generated, f)

        validator = OpenAPIValidator(str(spec_path), str(generated_path))
        validator._validate_schemas_match()
        assert any("missing required fields" in e for e in validator.errors)


def test_validate_required_fields_present(valid_spec):
    """Test that required top-level fields are checked."""
    with tempfile.TemporaryDirectory() as tmpdir:
        spec_path = Path(tmpdir) / "spec.yaml"
        generated_path = Path(tmpdir) / "generated.json"

        with open(spec_path, "w") as f:
            yaml.dump(valid_spec, f)
        with open(generated_path, "w") as f:
            json.dump(valid_spec, f)

        validator = OpenAPIValidator(str(spec_path), str(generated_path))
        validator._validate_required_fields()
        assert len(validator.errors) == 0


def test_validate_required_fields_missing():
    """Test that missing required fields generate errors."""
    with tempfile.TemporaryDirectory() as tmpdir:
        spec_path = Path(tmpdir) / "spec.yaml"
        generated_path = Path(tmpdir) / "generated.json"

        incomplete_spec = {"openapi": "3.1.0"}  # missing info and paths

        with open(spec_path, "w") as f:
            yaml.dump(incomplete_spec, f)
        with open(generated_path, "w") as f:
            json.dump(incomplete_spec, f)

        validator = OpenAPIValidator(str(spec_path), str(generated_path))
        validator._validate_required_fields()
        assert any("Missing required field" in e for e in validator.errors)


def test_full_validation_success(valid_spec, valid_generated):
    """Test that full validation passes with matching specs."""
    with tempfile.TemporaryDirectory() as tmpdir:
        spec_path = Path(tmpdir) / "spec.yaml"
        generated_path = Path(tmpdir) / "generated.json"

        with open(spec_path, "w") as f:
            yaml.dump(valid_spec, f)
        with open(generated_path, "w") as f:
            json.dump(valid_generated, f)

        validator = OpenAPIValidator(str(spec_path), str(generated_path))
        result = validator.validate()
        assert result is True


def test_full_validation_failure(valid_spec, valid_generated):
    """Test that full validation fails with mismatched specs."""
    with tempfile.TemporaryDirectory() as tmpdir:
        spec_path = Path(tmpdir) / "spec.yaml"
        generated_path = Path(tmpdir) / "generated.json"

        # Add missing endpoint to spec
        valid_spec["paths"]["/api/missing/"] = {"get": {}}

        with open(spec_path, "w") as f:
            yaml.dump(valid_spec, f)
        with open(generated_path, "w") as f:
            json.dump(valid_generated, f)

        validator = OpenAPIValidator(str(spec_path), str(generated_path))
        result = validator.validate()
        assert result is False
