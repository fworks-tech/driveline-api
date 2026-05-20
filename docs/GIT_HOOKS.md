# Git Hooks Setup

Automated checks ensure code quality and test coverage before commits and pushes.

## Pre-Commit Hook

**Runs automatically before each commit:**
- Format code with `black`
- Sort imports with `isort`
- Lint with `flake8`

**Setup:**
```bash
cp docs/hooks/pre-commit .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit
```

**What it does:**
1. Formats code with black
2. Sorts imports with isort
3. Lints with flake8 (max line length: 120)
4. Auto-stages formatted files
5. Aborts commit if checks fail

## Pre-Push Hook

**Runs automatically before pushing to remote:**
- Runs all unit and API endpoint tests

**Setup:**
```bash
cp docs/hooks/pre-push .git/hooks/pre-push
chmod +x .git/hooks/pre-push
```

**What it does:**
1. Runs pytest for `test_api_endpoint.py` and `test_hos_engine.py`
2. Aborts push if any tests fail
3. Allows push only if all tests pass

## Installation

Copy all hooks to your local `.git/hooks/` directory:

```bash
# From repo root:
cp docs/hooks/* .git/hooks/
chmod +x .git/hooks/pre-*
```

## Bypassing Hooks (Not Recommended)

If you need to bypass hooks in exceptional cases:

```bash
# Skip pre-commit hook
git commit --no-verify

# Skip pre-push hook
git push --no-verify
```

**⚠️ Note:** Only use `--no-verify` when absolutely necessary. Bypassing checks defeats their purpose.

## Troubleshooting

### Pre-commit hook fails with "black: command not found"
```bash
pip install black isort flake8
```

### Pre-push hook fails because tests are slow
- The hook is designed to prevent untested code from reaching remote
- Optimize tests if they're too slow
- Review test coverage to eliminate unnecessary tests

### Hook permissions denied
```bash
chmod +x .git/hooks/pre-commit
chmod +x .git/hooks/pre-push
```

## CI/CD Integration

These local hooks complement GitHub Actions CI/CD:
- **Local hooks:** Fast feedback during development (pre-commit, pre-push)
- **GitHub Actions:** Final validation on all PRs (comprehensive checks)

## Related Documentation

- [TESTING.md](TESTING.md) — Test running and coverage
- [CLAUDE.md](../CLAUDE.md) — Code quality standards
