# 🏆 Gold Standard PR Comment Template — IntelliReview

> This document shows a reference "gold standard" PR review comment demonstrating
> all capabilities of the FeedbackGenerator module: severity markers, actionable
> autofixes, evidence mandates, dataflow tracking, nit collapse, and the
> verification walkthrough.

---

# 🔴 IntelliReview AI Audit

> **3** files reviewed | **9** findings | Verdict: **FAIL**

---

## 🔴 Important Findings (Block Merge)

### 🔴 Security: SQL Injection via Unsanitized User Input

**File:** `api/routes/users.py` **Line:** 42

The `user_id` parameter from the HTTP request query string flows directly into
a raw SQL `execute()` call without parameterization. An attacker can inject
arbitrary SQL (e.g., `1; DROP TABLE users--`) to exfiltrate or destroy data.

**Impact:** Complete database compromise — an attacker can read, modify, or
delete any data in the connected database.

**Classification:** CWE-89

**Dataflow:** `request.args["user_id"]` → `cursor.execute(f"SELECT * FROM users WHERE id={user_id}")` (⚠️ unsanitized)

<details>
<summary>🔧 Autofix (click to expand)</summary>

```diff
- cursor.execute(f"SELECT * FROM users WHERE id={user_id}")
+ cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
```

</details>

<details>
<summary>🧪 Evidence: SQL Injection Verification</summary>

**Payload:** `GET /api/users?user_id=1%27%20OR%201%3D1--`

**Expected:** HTTP 400 (invalid input) or parameterized query prevents injection

**Actual:** HTTP 200 with all user records returned (full table dump)

```bash
curl -s "http://localhost:8000/api/users?user_id=1'%20OR%201=1--" | jq '.users | length'
# Returns: 847 (all users in the table)
```

</details>

> 📎 [CWE-89](https://cwe.mitre.org/data/definitions/89.html) | OWASP A03:2021 | [Reference](https://owasp.org/www-community/attacks/SQL_Injection)

---

### 🔴 Security: Hardcoded Database Credentials

**File:** `config/database.py` **Line:** 8

The database connection string contains a plaintext password embedded directly
in the source code. This credential will be committed to version control and
visible to anyone with repository read access.

**Impact:** Credential leakage via Git history — even if removed in a future
commit, the password remains in the repository's commit history indefinitely.

**Classification:** CWE-798

<details>
<summary>🔧 Autofix (click to expand)</summary>

```diff
- DATABASE_URL = "postgresql://admin:s3cret_p@ss@db.example.com:5432/production"
+ DATABASE_URL = os.getenv("DATABASE_URL")
+ if not DATABASE_URL:
+     raise RuntimeError("DATABASE_URL environment variable is required")
```

</details>

<details>
<summary>🧪 Evidence: Hardcoded Secret Verification</summary>

**Payload:** Run: `grep -rn 'password\|api_key\|secret' config/database.py`

**Expected:** Secrets loaded from environment variables or vault

**Actual:** Credentials are committed in plaintext to version control

</details>

> 📎 [CWE-798](https://cwe.mitre.org/data/definitions/798.html) | OWASP A07:2021

---

## 🟡 Nits (Style / Polish)

### 🟡 Style: Variable naming does not follow PEP 8 conventions

**File:** `api/routes/users.py` **Line:** 15

The variable `userData` uses camelCase, which violates PEP 8's recommendation
of `snake_case` for variable names in Python. Inconsistent naming conventions
reduce codebase readability and increase cognitive load during reviews.

<details>
<summary>🔧 Autofix (click to expand)</summary>

```diff
- userData = request.json
+ user_data = request.json
```

</details>

---

### 🟡 Style: Missing type annotations on public function

**File:** `api/routes/users.py` **Line:** 28

The function `get_user_profile` lacks return type annotations, making it harder
for IDE tooling and static analyzers to catch type errors.

<details>
<summary>🔧 Autofix (click to expand)</summary>

```diff
- def get_user_profile(user_id):
+ def get_user_profile(user_id: int) -> dict:
```

</details>

---

<details>
<summary>📦 +3 more nits (collapsed to reduce noise)</summary>

| # | File | Line | Category | Title |
|---|------|------|----------|-------|
| 1 | `api/routes/users.py` | L55 | Style | Trailing whitespace on line |
| 2 | `api/models/user.py` | L12 | Maintainability | Unused import: `datetime` |
| 3 | `api/routes/users.py` | L78 | Style | Line exceeds 120 character limit |

> Collapsed to reduce notification fatigue (>5 nits detected, showing first 5)

</details>

---

## 🟣 Pre-existing (Legacy Debt)

### 🟣 Architecture: Bare except clause swallowing errors

**File:** `api/routes/users.py` **Line:** 92

The `except Exception` block catches all exceptions and silently returns `None`.
This masks runtime errors, making it impossible to diagnose failures in
production. This pattern predates the current PR changes.

<details>
<summary>🔧 Autofix (click to expand)</summary>

```diff
- except Exception:
-     return None
+ except Exception as e:
+     logger.error(f"Failed to fetch user profile: {e}", exc_info=True)
+     raise HTTPException(status_code=500, detail="Internal server error")
```

</details>

> 📎 [CWE-755](https://cwe.mitre.org/data/definitions/755.html)

---

<details>
<summary>📋 Verification Walkthrough</summary>

**Generated:** 2026-04-17 03:45:00 UTC

| Metric | Count |
|--------|-------|
| Total Findings | 9 |
| 🔴 Important | 2 |
| 🟡 Nits | 5 |
| 🟣 Pre-existing | 2 |
| Dataflow Traces Checked | 1 |
| Nits Collapsed | 3 |

**KB Rules Applied:**
- Config override: Custom `.intellireview.yml` rule `ban-console-log` applied

**Finding Verification Details:**

| # | Finding | Method | Summary | Result |
|---|---------|--------|---------|--------|
| 1 | Security: SQL Injection via Unsanitized | `dataflow_trace` | Dataflow traced: request.args["user_id"] → cursor.execute() | ✅ Verified |
| 2 | Security: Hardcoded Database Credentials | `reproduction_step` | Repro step: Hardcoded Secret Verification | ✅ Verified |
| 3 | Style: Variable naming does not follow PEP 8 | `pattern_match` | Nit verified via static pattern matching | ✅ Verified |
| 4 | Style: Missing type annotations on public func | `pattern_match` | Nit verified via static pattern matching | ✅ Verified |
| 5 | Architecture: Bare except clause swallowing | `knowledge_base` | Pre-existing issue identified via historical analysis | ✅ Verified |

---

*This walkthrough was auto-generated by IntelliReview to document how the agent
verified its findings before posting the review.*

</details>
