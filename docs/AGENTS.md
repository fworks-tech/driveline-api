# AGENTS.md — AI Agent Guide for Backend Repository

**Purpose:** Enable AI agents to work effectively on this repository  
**Audience:** Claude Code, GitHub Copilot, and other AI tools  
**Last Updated:** 2026-05-20

---

## 🤖 Agent Capabilities & Limitations

### What Agents Can Do ✅

- **Code Analysis** — Understand API endpoints, database models, business logic
- **Testing** — Write and maintain unit/integration/E2E tests
- **Documentation** — Create/update markdown and code comments
- **Bug Fixes** — Fix issues identified in GitHub issues
- **Database Migrations** — Create safe schema changes with reversibility
- **API Endpoints** — Implement new endpoints following patterns
- **Type Safety** — Add/improve type hints (Python typing)
- **Performance** — Optimize queries, add caching, improve response times

### What Agents Should Avoid ⚠️

- **Major Architecture Changes** — Requires human design approval
- **Breaking API Changes** — Use deprecation patterns instead
- **Data Destructive Migrations** — Without comprehensive testing
- **Dependency Upgrades** — May require environment testing
- **Secrets Management** — Never commit credentials
- **Force Pushes** — Use proper PR workflow
- **Production Deployments** — Wait for human approval
- **Direct Main Pushes** — Use feature branches + PRs

### Confidence Levels

| Task | Confidence | Notes |
|------|-----------|-------|
| Bug fixes from issues | ⭐⭐⭐⭐⭐ | Safe, testable |
| Unit tests | ⭐⭐⭐⭐⭐ | Clear patterns |
| Documentation | ⭐⭐⭐⭐⭐ | No code risks |
| Database migrations | ⭐⭐⭐⭐ | Must be reversible |
| New API endpoints | ⭐⭐⭐⭐ | Verify HOS compliance |
| Performance optimization | ⭐⭐⭐⭐ | Test with real data |
| Major refactoring | ⭐⭐ | Requires human review |
| Architecture changes | ⭐ | Requires human design |

---

## 📋 Safe Operations (Agent-Ready)

### Issue-Based Bug Fixes

**Safe Pattern:**
1. Read GitHub issue description
2. Locate bug in code
3. Create feature branch: `fix/issue-{number}`
4. Write failing test first
5. Implement fix
6. Verify all tests pass
7. Create PR with issue reference
8. **DO NOT MERGE** — Human review required

**Example:**
```bash
# Issue #42: HOS 11-hour rule calculation is off by 1 hour

# Step 1: Analyze
# Find: trips/models.py HOS engine
# Find: tests/test_hos_rules.py

# Step 2: Write failing test
# Add test case showing 12 hours allowed instead of 11

# Step 3: Fix
# Update HOS calculation logic

# Step 4: Create PR
git checkout -b fix/issue-42-hos-11-hour-limit
git add trips/models.py tests/test_hos_rules.py
git commit -m "fix: correct HOS 11-hour driving limit calculation (#42)"
git push origin fix/issue-42-hos-11-hour-limit
```

### Database Migrations

**Safe Pattern:**
1. Create migration file: `python manage.py makemigrations`
2. Review migration SQL
3. Verify migration is reversible
4. Test on local database
5. Test with sample data
6. Create PR with migration
7. Include rollback plan in description

**Safe Migration Types:**
- ✅ Add new columns with defaults
- ✅ Add new tables
- ✅ Add indexes
- ✅ Rename columns (with safe Django migration)
- ✅ Add constraints (not enforced on existing data)

**Unsafe Migration Types:**
- ❌ Delete columns without archive
- ❌ Change column types without compatibility
- ❌ Enforce NOT NULL on populated column
- ❌ Rename tables (confusing for rollback)

### New Tests for Untested Code

**Safe Pattern:**
1. Identify untested function/endpoint
2. Analyze its behavior
3. Create comprehensive tests (unit + integration)
4. Achieve 70%+ coverage on touched code
5. Create PR with test results

**Example:**
```bash
# Add tests for address validation endpoint
# tests/test_address_validation.py
# - Valid address returns coordinates
# - Invalid address returns error
# - Multiple matches returns all options
```

### Documentation Updates

**Safe Pattern:**
1. Read documentation guidelines
2. Update/create markdown files
3. Keep consistent with existing style
4. Link to source of truth (code, issues)
5. Create PR without code changes

**Safe Files to Update:**
- ✅ `*.md` files
- ✅ Docstrings in code
- ✅ Comments explaining complex logic
- ✅ Test descriptions

**Unsafe Files:**
- ❌ requirements.txt (use PR review)
- ❌ settings.py (use PR review)
- ❌ Dockerfile (use PR review)

### Type Safety Improvements

**Safe Pattern:**
1. Add stricter type hints (don't remove existing)
2. Improve `Any` types → concrete types
3. Add type guards
4. Ensure no runtime behavior change
5. Run tests to verify

**Safe Changes:**
```python
# ✅ SAFE: Improving type specificity
def get_route(request_id: Any) -> dict:
    ...

# Improved to:
def get_route(request_id: int) -> Dict[str, Any]:
    ...

# ✅ SAFE: Adding type hints
def validate_hours(hours):  # No hint
    ...

# Improved to:
def validate_hours(hours: int) -> bool:
    ...

# ❌ UNSAFE: Changing behavior
return None  # Changing to return []
```

---

## 🔗 Source of Truth References

### For API Contract
- **File:** `trips/serializers.py`
- **Sections:** All DRF Serializer definitions
- **Use For:** Request/response validation

### For Database Schema
- **File:** `trips/models.py`
- **Sections:** Django Model definitions
- **Use For:** Data structure, relationships

### For HOS Compliance
- **File:** `trips/hos_engine.py`
- **Sections:** All HOS rule calculations
- **Use For:** Business logic requirements

### For Testing Patterns
- **File:** `tests/test_hos_rules.py`
- **Sections:** Test setup, fixtures, patterns
- **Use For:** How to test backend code

### For API Documentation
- **File:** `docs/openapi.yaml`
- **Sections:** All endpoint definitions
- **Use For:** Endpoint contracts

### For Configuration
- **File:** `requirements.txt`
- **Sections:** All dependencies
- **Use For:** Allowed packages, versions

### For Environment Setup
- **File:** `.env.example`
- **Sections:** All required variables
- **Use For:** Configuration requirements

---

## 🚀 Automation Patterns

### Pattern 1: Issue-to-PR Pipeline

```
GitHub Issue (with labels)
    ↓
Agent reads issue + context
    ↓
Agent creates feature branch
    ↓
Agent writes test (test-first)
    ↓
Agent implements fix
    ↓
Agent creates PR with description
    ↓
GitHub Actions runs checks
    ↓
Human review + approval
    ↓
Auto-merge or manual merge
```

### Pattern 2: Automated Tests

```
Code change detected
    ↓
Agent writes tests for change
    ↓
Test coverage analysis
    ↓
If coverage < 70%, flag for review
    ↓
Run full test suite
    ↓
If tests pass, mark as tested
```

### Pattern 3: Migration Safety

```
Schema change needed
    ↓
Agent creates migration with makemigrations
    ↓
Agent tests migration locally
    ↓
Agent creates PR with rollback plan
    ↓
Human reviews migration safety
    ↓
Deployed with rollback ready
```

---

## ⚙️ Configuration for Agents

### Git Configuration
```bash
git config user.email "claude-code@anthropic.com"
git config user.name "Claude Code"
```

### Branching Convention
```
fix/issue-{number}-short-description    # Bug fixes
feat/issue-{number}-short-description   # New features
refactor/area-short-description         # Refactoring
docs/issue-{number}-short-description   # Documentation
test/issue-{number}-short-description   # Tests
```

### Commit Message Format
```
<type>(<scope>): <subject>

<body>

Closes #<issue-number>

Co-Authored-By: Name <email@example.com>
```

---

## 🧪 Testing Commands for Agents

### Run All Tests
```bash
python manage.py test
```

### Run Tests with Coverage
```bash
coverage run --source='.' manage.py test
coverage report
```

### Lint Code
```bash
flake8 .
black --check .
```

### Type Check (if mypy configured)
```bash
mypy .
```

### Local Server
```bash
python manage.py runserver 0.0.0.0:8000
```

### Make Migrations
```bash
python manage.py makemigrations
python manage.py migrate
```

---

## 📊 Metrics Agents Should Track

### Code Quality Metrics
- ✅ Test coverage (target 70%+)
- ✅ Type hint coverage
- ✅ Linting compliance (flake8, black)
- ✅ No hardcoded values

### API Quality Metrics
- ✅ Response time (target <500ms for most endpoints)
- ✅ Error handling (all edge cases covered)
- ✅ Input validation (Serializer level)
- ✅ OpenAPI spec accuracy

### Database Metrics
- ✅ Query efficiency (no N+1 queries)
- ✅ Migration reversibility
- ✅ Index coverage on foreign keys
- ✅ No schema drift

---

## 🚫 Dangerous Operations (No Agent Auto-Merge)

| Operation | Why Dangerous | Agent Action |
|-----------|---------------|-------------|
| **Update requirements.txt** | May break dependencies | Create PR, flag for review |
| **Modify settings.py** | Configuration impact | Create PR, flag for review |
| **Change models.py significantly** | Database impact | Create migration + PR |
| **Delete API endpoints** | Breaking changes | Create deprecation PR |
| **Modify HOS engine** | Compliance impact | Create PR, thorough testing |
| **Force push** | Loses history | Never allow |
| **Commit secrets** | Security risk | Immediately revert |
| **Deploy to production** | Manual approval required | Create deployment PR |

---

## 🔄 Agent Workflow Example

### Scenario: Fix HOS 11-Hour Rule Calculation

```
1. READ ISSUE
   Issue #42: "HOS engine allows 12 hours instead of 11"
   
2. ANALYZE
   File: trips/hos_engine.py
   Current: hours <= 11 (should be < 12)
   Problem: Off-by-one error
   
3. WRITE TEST (TEST-FIRST)
   tests/test_hos_rules.py
   - Add test case: 11.5 hours should FAIL
   - Add test case: 10.9 hours should PASS
   
4. RUN TEST (VERIFY FAILURE)
   python manage.py test tests.test_hos_rules.TestHOS11Hour
   # Test fails (confirming the bug)
   
5. IMPLEMENT FIX
   Update: trips/hos_engine.py
   - Change hours <= 11 to hours < 11
   
6. RUN TEST (VERIFY PASS)
   python manage.py test tests.test_hos_rules.TestHOS11Hour
   # Test passes
   
7. RUN ALL TESTS
   coverage run --source='.' manage.py test
   # All tests pass, coverage 75%+
   
8. COMMIT
   git add trips/hos_engine.py tests/test_hos_rules.py
   git commit -m "fix: correct HOS 11-hour driving limit calculation
   
   The previous logic allowed 12 hours (hours <= 11).
   Fixed to correctly enforce 11-hour limit (hours < 11).
   
   Closes #42
   
   Co-Authored-By: Claude Haiku 4.5 <noreply@anthropic.com>"
   
9. PUSH
   git push origin fix/issue-42-hos-11-hour-limit
   
10. CREATE PR
    gh pr create \
      --title "fix: correct HOS 11-hour driving limit" \
      --body "Fixes off-by-one error in HOS calculation..."
   
11. WAIT
    Wait for human review + approval
    Do not merge (let human do it)
```

---

## 🎯 Agent Confidence Checklist

Before creating a PR, agents should verify:

- [ ] Tests written first (TDD pattern)
- [ ] All tests pass (`python manage.py test`)
- [ ] Code coverage is 70%+ on touched code
- [ ] No hardcoded values
- [ ] Type hints added where possible
- [ ] Follows Django conventions
- [ ] Commit message is clear
- [ ] PR description explains change
- [ ] References related issue (#xxx)
- [ ] No breaking API changes
- [ ] OpenAPI spec updated if needed
- [ ] Migrations are reversible (if needed)

---

## 📞 Escalation Procedure

### When to Escalate to Humans

1. **Unclear Requirements**
   - Issue description is ambiguous
   - Multiple valid interpretations
   - Action: Comment on issue asking for clarification

2. **Design Decision Needed**
   - Multiple implementation approaches
   - Requires architectural change
   - Action: Create issue for discussion

3. **HOS Rule Changes**
   - New or modified FMCSA requirements
   - Affects compliance
   - Action: Flag and wait for legal review

4. **Test Failures**
   - Unexpected test failure
   - Coverage drops below 70%
   - Action: Revert and comment with analysis

5. **Database Changes**
   - Migration fails on test data
   - Rollback needed
   - Action: Diagnose and comment with findings

6. **External Service Changes**
   - Nominatim API changes
   - Django/DRF breaking changes
   - Action: Flag and wait for decision

---

## 🔐 Security Considerations

### Defense-in-Depth Strategy

This project uses **layered security** to protect against common vulnerabilities:

**Layer 1: Input Validation (DRF Serializers)**
- Type checking (rejects non-strings, non-floats)
- Length limits (prevents DoS via massive inputs)
- Range validation (enforces business rules like 0-70 cycle hours)
- Regex patterns (for structured inputs)

**Layer 2: External API Safety**
- Timeouts on all external calls (5-10 seconds max)
- Response validation (verify expected JSON structure)
- No authentication tokens passed to public APIs
- Error handling (graceful degradation on API failure)

**Layer 3: CORS Configuration**
- Development: Allow all origins
- Production: Whitelist only known frontend domains
- Prevents cross-site request attacks from unauthorized origins

**Layer 4: Environment Security**
- All secrets in `.env` file (never committed)
- `.env.example` shows template only (no real values)
- Load via `python-dotenv` at startup
- Never log sensitive data

**Layer 5: Error Handling**
- Never expose stack traces in production responses
- Generic error messages to users ("An error occurred")
- Detailed error logs server-side for debugging
- No PII or internal implementation details in responses

**Layer 6: Future Protections**
- Rate limiting (v1.0.0-beta) — prevent brute force, DoS
- Database encryption (future) — for persisted trip data
- HTTPS enforcement (production only)
- Audit logging (future) — track who accessed what

### Common Attack Vectors & Mitigations

| Attack | Vector | Mitigation | Status |
|--------|--------|-----------|--------|
| **SQL Injection** | User input in queries | Django ORM (parameterized) | ✅ Safe |
| **XSS** | User input in HTML | API returns JSON only | ✅ Safe |
| **CSRF** | Cross-site requests | CORS whitelist | ✅ Safe |
| **DoS** | Massive requests | Input size limits, rate limiting (future) | ⚠️ Partial |
| **Brute Force** | Password guessing | No auth yet, planned JWT | ⚠️ N/A |
| **Man-in-Middle** | Unencrypted traffic | HTTPS required (production) | ⚠️ Partial |
| **Secret Leakage** | Hardcoded credentials | .env + .gitignore | ✅ Safe |

### Best Practices for Agent Code

1. **Always validate input** at the serializer level, never trust user data
2. **Never commit secrets** — if you add an API key, it will be caught by pre-commit hooks
3. **Use Django ORM** for all database operations (parameterized queries)
4. **Add timeouts** to any external API calls (minimum 5 seconds, maximum 30 seconds)
5. **Test error paths** — what happens when Nominatim is down? OSRM times out?
6. **Log securely** — don't log passwords, API keys, or PII
7. **Follow the principle of least privilege** — functions should only have access to data they need

### Security Review Triggers

Agents should ask for human review if:
- Adding authentication or authorization
- Changing CORS configuration
- Adding database access (future)
- Handling passwords or tokens (future)
- Using cryptography
- Any changes to `.env.example` or secrets handling

### Reference

See [ARCHITECTURE.md - Security Considerations](ARCHITECTURE.md#-security-considerations) for detailed security implementation guidance.

---

## 🔐 Security Checklist for Agents

Before merging any code, verify:

- [ ] No hardcoded API keys or secrets
- [ ] No credentials in code or committed files
- [ ] `.env` and `.env.local` are in `.gitignore`
- [ ] Input validation present (Serializer level) for all user inputs
- [ ] SQL injection prevention (use Django ORM, not raw SQL)
- [ ] CORS headers configured correctly for environment
- [ ] All external API calls have timeouts (5-30 seconds)
- [ ] Error responses don't expose internal implementation details
- [ ] No PII (passwords, emails, addresses) in logs
- [ ] Authentication required on protected endpoints (if applicable)
- [ ] Rate limiting considered for high-traffic endpoints
- [ ] Security test cases written (invalid inputs, API failures, etc.)

---

## 📖 Additional Resources

### For Agents
- **COMPLIANCE.md** — HOS compliance requirements
- **Testing patterns** — tests/
- **API documentation** — docs/openapi.yaml
- **Database models** — trips/models.py
- **HOS engine** — trips/hos_engine.py

### For Understanding Context
- **GitHub Issues** — Requirements & context
- **Pull Request History** — Past decisions
- **Commit Messages** — Intent behind changes
- **Tests** — Behavioral specifications

---

## ✅ Agent Health Check

Agents should periodically:

1. **Verify Repository Health**
   - `python manage.py test` passes
   - `coverage report` shows 70%+ coverage
   - No linting errors (`flake8 .`)
   - No TS/type errors (if using mypy)

2. **Update This Document**
   - Check if patterns still accurate
   - Add new safe operations discovered
   - Remove deprecated patterns

3. **Track Metrics**
   - Test coverage trend
   - Type safety trend
   - API response time trend

---

**Agent Approval Status:** ✅ **APPROVED FOR AUTOMATION**  
**Last Reviewed:** 2026-05-20  
**Maintained by:** Backend team  
**Version:** 1.0
