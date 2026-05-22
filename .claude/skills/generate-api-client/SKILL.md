# 🚀 generate-api-client

**Name:** generate-api-client  
**Type:** Build Automation Skill  
**Prerequisites:** Node.js 16+ with npm, APP repo at `../spotter-eld-logging-app`  
**Source:** `scripts/generate-api-client.sh` + `.claude/skills/generate-api-client/SKILL.md`

---

## What It Does

Automatically regenerates the TypeScript API client from the OpenAPI spec (`docs/openapi.yaml`) using `openapi-typescript-codegen`. The generated client is copied to the APP repo at `src/lib/api-client/`, enabling type-safe API calls in the frontend.

Use this skill after:
- Adding or modifying API endpoints in `trips/views.py`
- Changing request/response serializers
- Updating schema definitions
- Any change to `docs/openapi.yaml`

---

## Usage

### Generate the API Client

```
/generate-api-client
```

Generates a fresh TypeScript client from `docs/openapi.yaml` and copies it to the APP repo. Shows a summary of generated files and next steps for committing in the APP repo.

**Example output:**
```
========================================
Generate TypeScript API Client
========================================

Source:      docs/openapi.yaml
Destination: ../spotter-eld-logging-app/src/lib/api-client
Mode:        generate

✅ Generation complete

📁 Copying generated client to APP repo...

✅ Client copied to: ../spotter-eld-logging-app/src/lib/api-client

📋 Generated Files:
   - core
   - models
   - services
   - index.ts

✨ Next steps:
  1. Review changes: cd ../spotter-eld-logging-app && git diff src/lib/api-client
  2. Test: npm run test
  3. Commit: npm run generate:api-client (verifies no drift) && git add src/lib/api-client
  4. Reference issues #24 (API) and #79 (APP) in your commit message
```

### Check for Drift (CI Mode)

```
/generate-api-client --check
```

Validates that the committed client in the APP repo matches what would be generated from the current OpenAPI spec. Used in CI to detect when the spec and client diverge.

**Exit codes:**
- `0` — No drift (client is in sync)
- `2` — Drift detected (client is out of date; run `/generate-api-client` to fix)

**Example drift detection:**
```
🔍 Checking for drift between generated and committed client...

❌ DRIFT DETECTED: Generated client differs from committed version

Run the following to regenerate the committed client:
  bash scripts/generate-api-client.sh
```

---

## Workflow

### Generate Mode

1. **Run generation script** — `bash scripts/generate-api-client.sh`
   - Validates `npx` and `openapi-typescript-codegen` are available
   - Generates client into temp directory from `docs/openapi.yaml`
   - Copies output to APP repo at `../spotter-eld-logging-app/src/lib/api-client`

2. **Show summary** — Lists generated files (`core/`, `models/`, `services/`, `index.ts`)

3. **Confirm next steps**
   - Ask: "Review the generated client in the APP repo?"
   - If yes: open the APP repo diff for review
   - Remind user to run tests and commit in APP repo referencing both #24 and #79

### Check Mode

1. **Run drift detection** — `bash scripts/generate-api-client.sh --check`
   - Generates a fresh client in temp directory
   - Diffs against the committed client
   - Exits with appropriate code

2. **Report result** — show whether client is in sync or out of date

---

## When to Use

**After changes to the API:**
- You modified an endpoint's request/response schema
- You added a new endpoint to `trips/views.py`
- You updated serializers in `trips/serializers.py`
- You changed `docs/openapi.yaml` manually

**In CI/CD:**
- Use `--check` mode as part of the test suite to detect drift
- Fails the build if committed client doesn't match the spec

**Before APP repo PR:**
- Run `/generate-api-client` and commit the output
- Reference both #24 (API) and #79 (APP) in the commit message
- This unblocks frontend work on #79 (API client integration)

---

## How It Works

The skill calls `bash scripts/generate-api-client.sh`, which:

1. Checks that `npx` is available (Node.js tooling)
2. Runs `npx openapi-typescript-codegen --input docs/openapi.yaml --output <tmpdir>`
3. Compares the generated output to the committed client (in generate mode) or just diffs (in check mode)
4. Prints a summary and next steps

The `openapi-typescript-codegen` tool is automatically installed via `npx` on first run.

---

## Prerequisites & Dependencies

- **Node.js 16+** with `npm` or `npx` available in PATH
- **APP repo** cloned to `../spotter-eld-logging-app` relative to this repo (for generation mode)
- **docs/openapi.yaml** must be valid OpenAPI 3.0.3 spec

---

## Related Issues

- **#24** (API) — Auto-generate TypeScript API client from OpenAPI spec
- **#79** (APP) — Integrate backend API client (openapi)

---

## See Also

- [docs/openapi.yaml](../../docs/openapi.yaml) — API specification
- [docs/API_CONTRACT.md](../../docs/API_CONTRACT.md) — Request/response schemas
- [CLAUDE.md](../../CLAUDE.md) — Branch and commit standards
