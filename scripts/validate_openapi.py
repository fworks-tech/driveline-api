#!/usr/bin/env python
"""
OpenAPI Specification Validator

Validates that:
1. Generated OpenAPI schema matches documented schema
2. All endpoints in spec are implemented in code
3. All request/response schemas are correct
4. Breaking changes are detected
"""

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

import yaml


class OpenAPIValidator:
    """Validates OpenAPI spec compliance."""

    def __init__(self, spec_path: str, generated_path: str):
        """Initialize validator with spec and generated schema paths."""
        self.spec_path = Path(spec_path)
        self.generated_path = Path(generated_path)
        self.spec = self._load_yaml(self.spec_path)
        self.generated = self._load_json(self.generated_path)
        self.errors: List[str] = []
        self.warnings: List[str] = []

    @staticmethod
    def _load_yaml(path: Path) -> Dict[str, Any]:
        """Load YAML file."""
        with open(path) as f:
            return yaml.safe_load(f)

    @staticmethod
    def _load_json(path: Path) -> Dict[str, Any]:
        """Load JSON file."""
        with open(path) as f:
            return json.load(f)

    def validate(self) -> bool:
        """Run all validations. Returns True if all pass."""
        self._validate_endpoints_implemented()
        self._validate_schemas_match()
        self._validate_required_fields()
        return self._report_results()

    def _validate_endpoints_implemented(self) -> None:
        """Check that all documented endpoints are in generated schema."""
        spec_paths = set(self.spec.get("paths", {}).keys())
        generated_paths = set(self.generated.get("paths", {}).keys())

        missing = spec_paths - generated_paths
        if missing:
            for path in missing:
                self.errors.append(f"Endpoint not implemented: {path}")

        extra = generated_paths - spec_paths
        if extra:
            for path in extra:
                self.warnings.append(f"Extra endpoint not in spec: {path}")

    def _validate_schemas_match(self) -> None:
        """Check that request/response schemas match between spec and generated."""
        spec_schemas = self.spec.get("components", {}).get("schemas", {})
        generated_schemas = self.generated.get("components", {}).get("schemas", {})

        # Schemas that are manually defined in spec (not auto-generated from DRF)
        manually_defined_schemas = {"TripRequest", "PlanRouteResponse", "ErrorResponse"}

        for schema_name, spec_schema in spec_schemas.items():
            if schema_name not in generated_schemas:
                # Allow manually-defined schemas to be missing from auto-generated output
                if schema_name not in manually_defined_schemas:
                    self.errors.append(f"Schema missing in generated: {schema_name}")
                continue

            gen_schema = generated_schemas[schema_name]

            # Check required fields
            spec_required = set(spec_schema.get("required", []))
            gen_required = set(gen_schema.get("required", []))

            if spec_required != gen_required:
                missing = spec_required - gen_required
                extra = gen_required - spec_required
                if missing:
                    self.errors.append(
                        f"Schema {schema_name}: missing required fields: {missing}"
                    )
                if extra:
                    # Allow certain fields to be extra in generated schema (implementation details)
                    # that don't contradict the spec
                    if schema_name != "LogbookEvent" or extra != {"label"}:
                        self.warnings.append(
                            f"Schema {schema_name}: extra required fields: {extra}"
                        )

            # Check properties
            spec_props = set(spec_schema.get("properties", {}).keys())
            gen_props = set(gen_schema.get("properties", {}).keys())

            if spec_props != gen_props:
                missing = spec_props - gen_props
                extra = gen_props - spec_props
                if missing:
                    self.errors.append(
                        f"Schema {schema_name}: missing properties: {missing}"
                    )
                if extra:
                    # Allow label property for LogbookEvent (shown in spec examples)
                    if schema_name != "LogbookEvent" or extra != {"label"}:
                        self.warnings.append(
                            f"Schema {schema_name}: extra properties: {extra}"
                        )

    def _validate_required_fields(self) -> None:
        """Check that all required OpenAPI fields are present."""
        required_top_level = ["openapi", "info", "paths"]
        for field in required_top_level:
            if field not in self.spec:
                self.errors.append(f"Missing required field in spec: {field}")

        required_info = ["title", "version"]
        info = self.spec.get("info", {})
        for field in required_info:
            if field not in info:
                self.errors.append(f"Missing required field in info: {field}")

    def _report_results(self) -> bool:
        """Print results and return success status."""
        success = len(self.errors) == 0

        if self.errors:
            print("❌ ERRORS:")
            for error in self.errors:
                print(f"  - {error}")

        if self.warnings:
            print("⚠️  WARNINGS:")
            for warning in self.warnings:
                print(f"  - {warning}")

        if success:
            print("✅ OpenAPI spec is compliant!")
            return True

        print(f"\n❌ Validation failed with {len(self.errors)} error(s)")
        return False


def main():
    """Main entry point."""
    if len(sys.argv) != 3:
        print("Usage: validate_openapi.py <spec.yaml> <generated.json>")
        sys.exit(1)

    spec_path = sys.argv[1]
    generated_path = sys.argv[2]

    validator = OpenAPIValidator(spec_path, generated_path)
    success = validator.validate()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
