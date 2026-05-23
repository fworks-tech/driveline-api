# Pull Request Automation Rules

**Document Purpose:** Define automated PR configuration rules  
**Last Updated:** 2026-05-21

This document describes the automated rules that are applied to every pull request when it's opened.

---

## Automated Configuration

### 1. Labels (Auto-Applied)

Labels are automatically determined based on the PR title prefix:

| Title Pattern | Labels Applied |
|---|---|
| `feat(` or `feature` | `type/feature` |
| `fix(` or `bugfix` | `type/bug` |
| `docs(` | `type/docs` |
| `infra(` or `chore(` | `type/infra` |
| `test(` | `type/test` |

**Priority Labels** (auto-detected from body):
- `priority/high` - if PR body contains "HIGH PRIORITY" or "URGENT"
- `priority/medium` - default if not specified

**Example:**
```
PR Title: feat(#10): add url-based api versioning
↓
Auto-applied: type/feature, priority/medium
```

### 2. Assignee

**Rule**: PR is automatically assigned to the creator (person who opened the PR)

**Purpose**: Ensures accountability - the person who creates the PR is responsible for addressing review feedback

### 3. Milestone

**Detection**: Automatically extracted from PR body or issue reference

| Reference | Milestone |
|---|---|
| `#10` (issue in title) | Based on issue's milestone |
| `v.1.1.0` in body | `v.1.1.0` |
| `v.1.0.0` in body | `v.1.0.0` |

**Available Milestones**:
- `v.1.1.0` - Production-ready API with HOS compliance, Docker deployment, and Redis caching
- `v.1.0.0` - Core API implementation

### 4. Project Board Status

**Rule**: PR is prepared for project board assignment with status "In Progress"

**How to use**:
1. When PR opens, automation adds it to the project board
2. Status is set to "In Progress" automatically
3. Move to "In Review" when requesting reviews
4. Move to "Done" when merged

---

## Automation Workflow Behavior

### When a PR Opens:

1. **GitHub Actions Trigger** (`on: pull_request.types: [opened]`)
2. **Extract Issue Reference** from PR title or body
3. **Apply Labels** based on type and priority
4. **Assign PR** to creator
5. **Add to Project Board** and set "In Progress"
6. **Set Milestone** if applicable
7. **Post Automation Comment** with checklist

### Automation Comment

A comment is automatically posted with:
- Summary of applied configuration
- Pre-merge checklist
- Link to project standards

---

## Manual Overrides

You can always manually override automated settings:

```bash
# Override labels
gh pr edit 37 --add-label "priority/high" --remove-label "priority/medium"

# Override assignee
gh pr edit 37 --add-assignee "@another-user"

# Override milestone
gh pr edit 37 --milestone "v.1.0.0"
```

---

## CI/CD Integration

### Required Checks Before Merge:

1. ✅ **Backend Tests** - All tests pass with 70%+ coverage
2. ✅ **Type Check** - mypy/type checking passes
3. ✅ **Lint** - black, isort, flake8 pass
4. ✅ **OpenAPI Validation** - Spec matches implementation
5. ✅ **Code Review** - At least one approval

### Automatic Failure Handling:

If any check fails:
1. PR is marked with ❌ status indicator
2. Details are available in GitHub Actions tab
3. Fix the issue and push a new commit
4. Checks re-run automatically

---

## Commit Message Standards

All commits must follow **Conventional Commits**:

```
feat(#10): add url-based api versioning
fix(#9): correct jwt token validation
docs: update authentication guide
infra(docker): add production dockerfile
chore: update dependencies
```

Format: `<type>(<scope>): <subject>`

**Types**:
- `feat` - New feature
- `fix` - Bug fix
- `docs` - Documentation
- `style` - Code style (formatting)
- `refactor` - Code refactoring
- `perf` - Performance improvement
- `test` - Test changes
- `chore` - Tooling, dependencies
- `infra` - Infrastructure/CI

---

## Examples

### Example 1: New Feature PR

```bash
# User creates PR with title: "feat(#10): add api versioning"
# Automation applies:
- Labels: type/feature, priority/medium
- Assignee: @creator-username
- Milestone: v.1.1.0 (from issue #10)
- Project Status: In Progress
```

### Example 2: Bug Fix PR

```bash
# User creates PR with title: "fix(#9): correct jwt validation"
# Automation applies:
- Labels: type/bug, priority/medium
- Assignee: @creator-username
- Milestone: v.1.1.0
- Project Status: In Progress
```

### Example 3: High Priority Fix

```bash
# User creates PR body containing "HIGH PRIORITY"
# Automation applies:
- Labels: type/feature, priority/high  ← high priority detected
- Assignee: @creator-username
- Milestone: extracted from issue
- Project Status: In Progress
```

---

## Troubleshooting

### Labels Not Applied

**Issue**: PR opened but no labels added

**Solution**:
1. Check PR title follows conventional commit pattern
2. Re-run automation: close and reopen PR
3. Manually add labels: `gh pr edit <number> --add-label "type/feature"`

### Assignee Not Set

**Issue**: PR is not assigned to creator

**Solution**:
1. Check repository permissions
2. Manually assign: `gh pr edit <number> --add-assignee "@me"`

### Milestone Not Found

**Issue**: PR created but milestone not set

**Solution**:
1. Ensure issue reference is in PR title (e.g., `#10`)
2. Check issue has a milestone assigned
3. Manually set: `gh pr edit <number> --milestone "v.1.1.0"`

---

## Related Documents

- [CLAUDE.md](../CLAUDE.md) - Project workflow standards
- [GitHub Actions Workflows](.github/workflows/) - Workflow definitions
- [Conventional Commits](https://www.conventionalcommits.org/) - Commit standard spec

