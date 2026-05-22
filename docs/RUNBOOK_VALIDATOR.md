# Runbook Validator — Documentation Quality Assurance

**Purpose:** Ensure documentation runbooks are accurate, up-to-date, and maintainable  
**Location:** `scripts/validate_runbooks.py`  
**Last Updated:** 2026-05-21

---

## Overview

The Runbook Validator automatically checks documentation for common issues:

- ✅ **File paths exist** — All referenced files and directories actually exist in the repo
- ✅ **Environment variables are documented** — All `.env` vars mentioned in docs are in `.env.example`
- ✅ **Code blocks are balanced** — No unclosed markdown code blocks
- ✅ **Env var references are correct** — Distinguishes between env vars, enums, and HTTP methods

---

## Running Locally

### Validate All Runbooks

```bash
python scripts/validate_runbooks.py
```

**Output:**
```
Validating 7 runbook(s)...

Checking: docs/API_CONTRACT.md
Checking: docs/ARCHITECTURE.md
Checking: docs/FRONTEND_INTEGRATION.md
Checking: docs/HOS_ENGINE.md
Checking: docs/LOCAL_DEVELOPMENT.md
Checking: docs/TESTING.md
Checking: README.md

============================================================
RUNBOOK VALIDATION REPORT
============================================================

✅ All runbooks are valid!

============================================================
```

### Validate Specific Runbook

```bash
python scripts/validate_runbooks.py docs/LOCAL_DEVELOPMENT.md
```

### Check Exit Code

```bash
python scripts/validate_runbooks.py
echo $?  # 0 = success, 1 = errors found
```

---

## Validation Rules

### File Path Validation

**Checks these file extensions:**
- `.md` — Markdown documents
- `.py` — Python source files
- `.txt` — Text files
- `.json` — JSON configuration
- `.yaml` / `.yml` — YAML configuration

**Example references that are checked:**
```markdown
See `docs/ARCHITECTURE.md` for details.
Update `trips/models.py` to add fields.
Reference `.env.example` for variables.
```

**Skipped patterns:**
- `http://` or `https://` URLs
- `$VAR_NAME` or `${VAR_NAME}` (env vars)
- `{{variable}}` (template syntax)
- References within code blocks (directory trees, examples)

### Environment Variable Validation

**Checks for undocumented env vars:**
```markdown
Use `DJANGO_SECRET_KEY=...` in your .env file.
Set `DATABASE_URL=postgresql://...` for production.
Configure `CORS_ALLOWED_ORIGINS` in .env.example.
```

**Exempt variables (no validation required):**
- System vars: `HOME`, `PATH`, `USER`, `PWD`, `SHELL`, `LANG`
- FMCSA enums: `DRIVING`, `OFF_DUTY`, `ON_DUTY_NOT_DRIVING`, `SLEEPER`, `SLEEPER_BERTH`
- HTTP methods: `POST`, `GET`, `PUT`, `DELETE`, `PATCH`
- Framework-specific: `VITE_API_URL`

### Code Block Validation

**Checks:**
- Every ` ``` ` opening has a matching ` ``` ` closing
- Unclosed code blocks cause errors

**Example:** ❌ Invalid
```markdown
Here's how to run tests:

```bash
pytest trips/tests/

Extra text here without closing backticks
```

**Example:** ✅ Valid
```markdown
Here's how to run tests:

```bash
pytest trips/tests/
```

Extra text after the code block.
```

---

## Common Issues & Fixes

### Issue: "File path does not exist: docs/API.md"

**Cause:** The file path is referenced in a runbook but doesn't actually exist.

**Fix:** Either:
1. Create the missing file, OR
2. Update the reference to the correct path, OR
3. Remove the reference if it's no longer needed

**Example:**
```markdown
# ❌ Wrong
See `docs/API.md` for the API contract.

# ✅ Correct
See `docs/API_CONTRACT.md` for the API contract.
```

### Issue: "Environment variable 'CUSTOM_VAR' not documented in .env.example"

**Cause:** A runbook mentions an environment variable that's not in `.env.example`.

**Fix:** Add the variable to `.env.example`:

```bash
# .env.example
DJANGO_SECRET_KEY=your-secret-key-here
CUSTOM_VAR=default-value
```

**Example in docs:**
```markdown
# ❌ Before
Configure `CUSTOM_VAR` in your .env file.

# ✅ After (after adding to .env.example)
Configure `CUSTOM_VAR` in your .env file (see `.env.example`).
```

### Issue: "Unclosed code block (odd number of ``` markers)"

**Cause:** A code block is missing its closing ` ``` `.

**Fix:** Ensure every ` ``` ` has a matching pair:

```markdown
# ❌ Wrong (3 backtick pairs = odd)
```bash
command 1
```

Some text

```bash
command 2

# ✅ Correct (2 backtick pairs = even)
```bash
command 1
```

Some text

```bash
command 2
```
```

---

## CI/CD Integration

### GitHub Actions Workflow

**File:** `.github/workflows/runbook-validation.yml`

**Triggers on:**
- Push to `main` or `develop` branches
- Pull requests to `main` or `develop` branches
- Changes to docs, `.env.example`, or the validation script

**What it does:**
1. Checks out the code
2. Sets up Python 3.11
3. Runs the validator script
4. Reports success or failure

**Failure behavior:**
- If errors are found, the workflow fails
- PR cannot be merged until validation passes
- No manual approval needed (automated check)

### Running Validation Before Push

```bash
# Validate locally before pushing
python scripts/validate_runbooks.py

# If there are errors, fix them first
# Then commit and push
git add docs/...
git commit -m "docs: fix runbook validation issues"
git push
```

---

## Implementation Details

### Validator Architecture

```python
class RunbookValidator:
    def __init__(self, repo_root: Path):
        # Load repo and .env.example
        self.env_vars = load_env_vars()
    
    def validate_file(self, filepath: Path):
        # Check file paths exist
        self._validate_file_paths(content, filepath)
        
        # Check env vars are documented
        self._validate_env_vars(content, filepath)
        
        # Check code blocks are balanced
        self._validate_code_blocks(content, filepath)
    
    def report(self):
        # Print errors and warnings
        # Return exit code (0 = success, 1 = errors)
```

### Key Features

1. **Smart Path Handling**
   - Removes code blocks before path validation (avoids false positives from directory trees)
   - Only validates realistic file extensions
   - Skips URLs and template variables

2. **Environment Variable Detection**
   - Multiple pattern types (`$VAR`, `${VAR}`, `env:VAR`)
   - Exempt list prevents false positives (enums, HTTP methods)
   - Whitelist for framework-specific vars

3. **Error Reporting**
   - Categorizes as ERRORS (must fix) vs WARNINGS (should consider)
   - Groups duplicate errors for readability
   - Summary with counts

---

## Extending the Validator

### Adding New Validation Rules

To add a new validation check:

```python
# In RunbookValidator class
def _validate_new_thing(self, content: str, filepath: Path):
    """Check for new issue."""
    if something_bad_found:
        self.errors.append(f"❌ {filepath.name}: Description of error")
    
    if something_questionable_found:
        self.warnings.append(f"⚠️  {filepath.name}: Description of warning")

# In validate_file()
def validate_file(self, filepath: Path) -> bool:
    # ... existing validation ...
    self._validate_new_thing(content, filepath)
    return len(self.errors) == 0
```

### Adding Files to Validation

Update `find_runbooks()` function:

```python
def find_runbooks(repo_root: Path) -> List[Path]:
    """Find all markdown runbook files in the repo."""
    runbook_patterns = [
        'docs/LOCAL_DEVELOPMENT.md',
        'docs/TESTING.md',
        # Add new file here:
        'docs/MY_NEW_GUIDE.md',
    ]
    # ...
```

---

## Best Practices

### Writing Runbooks That Pass Validation

1. **Use full file paths** in backticks:
   ```markdown
   # ✅ Good
   See `docs/ARCHITECTURE.md`
   
   # ❌ Bad
   See ARCHITECTURE.md
   ```

2. **Document all environment variables** in `.env.example`:
   ```bash
   # .env.example
   DEBUG=False
   CUSTOM_API_KEY=your-key-here
   ```

3. **Balance code blocks** carefully:
   ```markdown
   # ✅ Good
   ```bash
   command
   ```
   
   # ❌ Bad
   ```bash
   command
   More text without closing backticks
   ```

4. **Use exempt env vars** without documenting:
   ```markdown
   # ✅ These don't need .env.example entries
   The `HOME` directory is available.
   Use `POST /api/endpoint/` to create resources.
   Status values: `DRIVING`, `OFF_DUTY`, etc.
   ```

---

## Troubleshooting

### Validator fails with "No runbook files found"

**Cause:** No markdown files found in expected locations.

**Fix:** Ensure files exist in `docs/` and the root directory:
```bash
ls -la docs/*.md
ls -la README.md
```

### False positive: "File path does not exist"

**Cause:** The validator found a path-like string that's not actually a file reference.

**Fix:** Either:
1. Update the reference to use full paths, OR
2. Add context to make it clear it's not a file reference

```markdown
# ❌ Validator sees "conftest.py" as a file reference
Directory structure:
├── __init__.py
├── conftest.py

# ✅ Clearer with path
Directory structure:
├── __init__.py
├── trips/tests/conftest.py
```

### False positive: "Environment variable not documented"

**Cause:** A word that looks like an env var but isn't.

**Fix:** Add to exempt_vars in the validator:

```python
exempt_vars = {
    # ... existing ...
    'MY_NEW_EXEMPT_VAR',
}
```

---

## Related Documentation

- [TESTING.md](TESTING.md) — Test running and coverage
- [LOCAL_DEVELOPMENT.md](LOCAL_DEVELOPMENT.md) — Setup guide (validated by this tool)
- [ARCHITECTURE.md](ARCHITECTURE.md) — System design (validated by this tool)

---

**Tool Status:** ✅ Active  
**Last Updated:** 2026-05-21  
**Maintained by:** Backend team

