#!/usr/bin/env bash
set -e

# Configuration
INPUT_FILE="docs/openapi.yaml"
OUTPUT_DIR="../spotter-eld-logging-app/src/lib/api-client"
TMPDIR=$(mktemp -d)
trap "rm -rf $TMPDIR" EXIT

# Mode: --check for drift detection, default for generation
MODE="generate"
if [ "$1" = "--check" ]; then
  MODE="check"
fi

# Banner
echo "========================================"
echo "Generate TypeScript API Client"
echo "========================================"
echo ""
echo "Source:      $INPUT_FILE"
echo "Destination: $OUTPUT_DIR"
echo "Mode:        $MODE"
echo ""

# Check prerequisites
if ! command -v npx &> /dev/null; then
  echo "❌ ERROR: npx not found. Please install Node.js 16+ with npm."
  exit 1
fi

echo "📦 Generating TypeScript client from OpenAPI spec..."
echo ""

# Generate client
if ! npx --yes openapi-typescript-codegen@latest --input "$INPUT_FILE" --output "$TMPDIR"; then
  echo "❌ ERROR: Failed to generate TypeScript client."
  echo "Please ensure docs/openapi.yaml is valid."
  exit 1
fi

echo ""
echo "✅ Generation complete"
echo ""

# Mode: drift check
if [ "$MODE" = "check" ]; then
  echo "🔍 Checking for drift between generated and committed client..."
  echo ""

  if [ ! -d "$OUTPUT_DIR" ]; then
    echo "⚠️  No committed client found at $OUTPUT_DIR"
    echo "This is expected on first run. Drift check skipped."
    exit 0
  fi

  if ! diff -r "$OUTPUT_DIR" "$TMPDIR" >/dev/null 2>&1; then
    echo "❌ DRIFT DETECTED: Generated client differs from committed version"
    echo ""
    echo "Run the following to regenerate the committed client:"
    echo "  bash scripts/generate-api-client.sh"
    echo ""
    exit 2
  else
    echo "✅ Generated client matches committed version (no drift)"
    exit 0
  fi
fi

# Mode: generate and copy
echo "📁 Copying generated client to APP repo..."
echo ""

if [ ! -d "$(dirname "$OUTPUT_DIR")" ]; then
  echo "⚠️  APP repo directory not found at $(dirname "$OUTPUT_DIR")"
  echo "Skipping copy. Generated files available in: $TMPDIR"
  echo ""
  echo "To use the generated client:"
  echo "  1. Copy: cp -r $TMPDIR/* $OUTPUT_DIR/"
  echo "  2. Or run this script from within the API repo next to the APP repo"
  exit 1
fi

# Remove old client and copy new one
if [ -d "$OUTPUT_DIR" ]; then
  rm -rf "$OUTPUT_DIR"
fi

mkdir -p "$(dirname "$OUTPUT_DIR")"
cp -r "$TMPDIR" "$OUTPUT_DIR"

echo "✅ Client copied to: $OUTPUT_DIR"
echo ""

# Summary
echo "📋 Generated Files:"
ls -1 "$OUTPUT_DIR" | sed 's/^/   - /'
echo ""

echo "✨ Next steps:"
echo "  1. Review changes: cd ../spotter-eld-logging-app && git diff src/lib/api-client"
echo "  2. Test: npm run test"
echo "  3. Commit: npm run generate:api-client (verifies no drift) && git add src/lib/api-client"
echo "  4. Reference issues #24 (API) and #79 (APP) in your commit message"
echo ""
