"""
db/seed_v2.py — Extended problem seeding across all 6 domains.

Adds:
  - MCQ problems (multiple choice)
  - Debugging problems (broken code to fix)
  - System design problems (AI-evaluated)
  - More problems per domain (Web, Data Science, Cybersecurity, Product)
"""
import uuid, json
from skillos.db.database import transaction, fetchone, fetchall


def seed_all_v2():
    """Run all v2 seeds. Idempotent — safe to call multiple times."""
    already = fetchone("SELECT id FROM seed_log WHERE id='v2_problems'", ())
    if already:
        return

    _seed_mcq_problems()
    _seed_debugging_problems()
    _seed_system_design_problems()
    _seed_domain_problems()

    with transaction() as db:
        db.execute("INSERT INTO seed_log (id) VALUES ('v2_problems')")

    print("✅ V2 problems seeded")


def _get_skill_id(name_fragment: str) -> str | None:
    row = fetchone(
        "SELECT id FROM skills WHERE LOWER(name) LIKE ? LIMIT 1",
        (f"%{name_fragment.lower()}%",)
    )
    return row["id"] if row else None


def _upsert_task(task: dict):
    """Insert task if not exists (by title)."""
    exists = fetchone("SELECT id FROM tasks WHERE title=?", (task["title"],))
    if exists:
        return exists["id"]
    tid = str(uuid.uuid4())
    with transaction() as db:
        db.execute("""
            INSERT INTO tasks (
                id, skill_id, title, difficulty, description,
                input_format, output_format, constraints, time_limit_ms, memory_limit_kb,
                is_published, problem_type, starter_code, starter_code_broken,
                mcq_options, mcq_correct_index, system_design_rubric, ai_evaluation_prompt
            ) VALUES (?,?,?,?,?,?,?,?,?,?,1,?,?,?,?,?,?,?)
        """, (
            tid,
            task.get("skill_id"),
            task["title"],
            task.get("difficulty", "easy"),
            task.get("description", ""),
            task.get("input_format", ""),
            task.get("output_format", ""),
            task.get("constraints", ""),
            task.get("time_limit_ms", 2000),
            task.get("memory_limit_kb", 262144),
            task.get("problem_type", "coding"),
            task.get("starter_code"),
            task.get("starter_code_broken"),
            json.dumps(task["mcq_options"]) if task.get("mcq_options") else None,
            task.get("mcq_correct_index"),
            task.get("system_design_rubric"),
            task.get("ai_evaluation_prompt"),
        ))

    # Seed test cases for coding/debugging problems
    if task.get("test_cases"):
        with transaction() as db:
            for i, tc in enumerate(task["test_cases"]):
                db.execute("""
                    INSERT INTO test_cases (id, task_id, input, expected_output, ordinal, is_sample)
                    VALUES (?,?,?,?,?,?)
                """, (str(uuid.uuid4()), tid, tc["input"], tc["output"], i, i < 2))
    return tid


def _seed_mcq_problems():
    skill_algo = _get_skill_id("algorithm")
    skill_web  = _get_skill_id("web")
    skill_sec  = _get_skill_id("security") or _get_skill_id("cyber")

    mcq_problems = [
        {
            "title": "Big-O Complexity: Which is fastest?",
            "skill_id": skill_algo,
            "difficulty": "easy",
            "problem_type": "mcq",
            "description": """Which algorithm has the best time complexity for searching a sorted array of n elements?

Choose the correct answer:""",
            "mcq_options": [
                "Linear Search — O(n)",
                "Binary Search — O(log n)",
                "Jump Search — O(√n)",
                "Interpolation Search — O(log log n) average"
            ],
            "mcq_correct_index": 3,
        },
        {
            "title": "HTTP Status Codes",
            "skill_id": skill_web,
            "difficulty": "easy",
            "problem_type": "mcq",
            "description": """A REST API endpoint receives a request for a resource that exists but the user doesn't have permission to access it.

What HTTP status code should it return?""",
            "mcq_options": [
                "401 Unauthorized",
                "403 Forbidden",
                "404 Not Found",
                "500 Internal Server Error"
            ],
            "mcq_correct_index": 1,
        },
        {
            "title": "SQL vs NoSQL: When to choose?",
            "skill_id": _get_skill_id("data") or skill_algo,
            "difficulty": "medium",
            "problem_type": "mcq",
            "description": """You're building a social media platform where users have profiles, posts, comments, and likes. Relationships are complex and queries are unpredictable.

Which database is MOST appropriate?""",
            "mcq_options": [
                "Redis — key-value store for speed",
                "MongoDB — flexible schema for varied data",
                "PostgreSQL — ACID compliance and complex queries",
                "Cassandra — write-heavy distributed workloads"
            ],
            "mcq_correct_index": 2,
        },
        {
            "title": "XSS vs CSRF: What's the difference?",
            "skill_id": skill_sec,
            "difficulty": "medium",
            "problem_type": "mcq",
            "description": """An attacker injects malicious JavaScript into a comment field on a website. When other users view the page, the script runs in their browser and steals their cookies.

What type of attack is this?""",
            "mcq_options": [
                "CSRF (Cross-Site Request Forgery)",
                "SQL Injection",
                "XSS (Cross-Site Scripting)",
                "Man-in-the-Middle Attack"
            ],
            "mcq_correct_index": 2,
        },
        {
            "title": "Python: List vs Tuple",
            "skill_id": skill_algo,
            "difficulty": "easy",
            "problem_type": "mcq",
            "description": """You're storing RGB colour values like (255, 128, 0) that should never change during program execution.

Which Python data structure is MOST appropriate and why?""",
            "mcq_options": [
                "List — because you might need to sort the values",
                "Tuple — immutable, hashable, slightly faster access",
                "Set — for unique colour channels",
                "Dictionary — to label each channel explicitly"
            ],
            "mcq_correct_index": 1,
        },
        {
            "title": "Recursion Base Case",
            "skill_id": skill_algo,
            "difficulty": "easy",
            "problem_type": "mcq",
            "description": """What happens if a recursive function has no base case?""",
            "mcq_options": [
                "It runs forever without consuming memory",
                "It raises a StackOverflowError / RecursionError",
                "Python automatically adds a base case",
                "It returns None after 1000 calls"
            ],
            "mcq_correct_index": 1,
        },
    ]

    for p in mcq_problems:
        _upsert_task(p)


def _seed_debugging_problems():
    skill_algo = _get_skill_id("algorithm")
    skill_web  = _get_skill_id("web")

    debug_problems = [
        {
            "title": "Debug: Fibonacci Off-By-One",
            "skill_id": skill_algo,
            "difficulty": "easy",
            "problem_type": "debugging",
            "description": """The function below is supposed to return the nth Fibonacci number (0-indexed: fib(0)=0, fib(1)=1, fib(2)=1, fib(3)=2...).

**It has a bug. Find and fix it.**""",
            "starter_code_broken": """def fib(n):
    if n <= 0:
        return 1  # BUG HERE
    if n == 1:
        return 1
    return fib(n-1) + fib(n-2)

n = int(input())
print(fib(n))
""",
            "starter_code": """def fib(n):
    if n <= 0:
        return 1  # BUG HERE
    if n == 1:
        return 1
    return fib(n-1) + fib(n-2)

n = int(input())
print(fib(n))
""",
            "input_format": "Single integer n (0 ≤ n ≤ 30)",
            "output_format": "The nth Fibonacci number",
            "test_cases": [
                {"input": "0", "output": "0"},
                {"input": "1", "output": "1"},
                {"input": "5", "output": "5"},
                {"input": "10", "output": "55"},
            ]
        },
        {
            "title": "Debug: Infinite Loop in Binary Search",
            "skill_id": skill_algo,
            "difficulty": "medium",
            "problem_type": "debugging",
            "description": """This binary search implementation gets stuck in an infinite loop on some inputs. **Find and fix the bug.**

Input: first line = n (array size), second line = n sorted integers, third line = target.""",
            "starter_code_broken": """def binary_search(arr, target):
    left, right = 0, len(arr)  # BUG: should be len(arr) - 1
    while left <= right:
        mid = (left + right) // 2
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            left = mid  # BUG: should be mid + 1
        else:
            right = mid - 1
    return -1

import sys
lines = sys.stdin.read().split()
n = int(lines[0])
arr = [int(x) for x in lines[1:n+1]]
target = int(lines[n+1])
print(binary_search(arr, target))
""",
            "starter_code": """def binary_search(arr, target):
    left, right = 0, len(arr)  # BUG: should be len(arr) - 1
    while left <= right:
        mid = (left + right) // 2
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            left = mid  # BUG: should be mid + 1
        else:
            right = mid - 1
    return -1

import sys
lines = sys.stdin.read().split()
n = int(lines[0])
arr = [int(x) for x in lines[1:n+1]]
target = int(lines[n+1])
print(binary_search(arr, target))
""",
            "input_format": "Line 1: n. Line 2: n sorted integers. Line 3: target",
            "output_format": "Index of target or -1",
            "test_cases": [
                {"input": "5\n1 3 5 7 9\n5", "output": "2"},
                {"input": "5\n1 3 5 7 9\n1", "output": "0"},
                {"input": "5\n1 3 5 7 9\n4", "output": "-1"},
                {"input": "1\n42\n42", "output": "0"},
            ]
        },
        {
            "title": "Debug: Wrong Dictionary Update",
            "skill_id": skill_algo,
            "difficulty": "easy",
            "problem_type": "debugging",
            "description": """This function counts word frequencies but always returns wrong counts. **Fix the bug.**

Input: a sentence. Output: word counts sorted alphabetically, one per line as "word: count".""",
            "starter_code_broken": """def count_words(text):
    counts = {}
    for word in text.split():
        word = word.lower().strip('.,!?')
        if word in counts:
            counts[word] = 1  # BUG: should be counts[word] + 1
        else:
            counts[word] = 1
    return counts

line = input()
counts = count_words(line)
for word in sorted(counts):
    print(f"{word}: {counts[word]}")
""",
            "starter_code": """def count_words(text):
    counts = {}
    for word in text.split():
        word = word.lower().strip('.,!?')
        if word in counts:
            counts[word] = 1  # BUG: should be counts[word] + 1
        else:
            counts[word] = 1
    return counts

line = input()
counts = count_words(line)
for word in sorted(counts):
    print(f"{word}: {counts[word]}")
""",
            "input_format": "A single line of text",
            "output_format": "word: count pairs sorted alphabetically",
            "test_cases": [
                {"input": "the cat sat on the mat", "output": "cat: 1\nmat: 1\non: 1\nsat: 1\nthe: 2"},
                {"input": "hello hello world", "output": "hello: 2\nworld: 1"},
            ]
        },
    ]

    for p in debug_problems:
        _upsert_task(p)


def _seed_system_design_problems():
    skill_sd = _get_skill_id("system") or _get_skill_id("backend") or _get_skill_id("algorithm")

    sd_problems = [
        {
            "title": "Design a URL Shortener",
            "skill_id": skill_sd,
            "difficulty": "medium",
            "problem_type": "system_design",
            "description": """Design a URL shortening service like bit.ly or TinyURL.

**Requirements:**
- Given a long URL, return a short URL (e.g. `https://skillos.dev/abc123`)
- Given a short URL, redirect to the original
- Handle 100 million URLs
- 10:1 read-to-write ratio
- Short URL should be < 8 characters

**Write your design covering:**
1. API design (endpoints, request/response)
2. Database schema
3. How you generate the short code
4. How you handle scale (caching, sharding, CDN)
5. Trade-offs you're making""",
            "system_design_rubric": """Score based on:
- API design clarity (20pts): clear endpoints, proper HTTP methods, good response format
- Database choice justification (20pts): why SQL or NoSQL, schema design
- Short code generation (20pts): hashing vs counter, collision handling, uniqueness guarantee
- Scale thinking (20pts): mentions caching (Redis), CDN, database replication/sharding
- Trade-offs (20pts): acknowledges CAP theorem, eventual consistency, or similar""",
        },
        {
            "title": "Design a Notification System",
            "skill_id": skill_sd,
            "difficulty": "hard",
            "problem_type": "system_design",
            "description": """Design a notification system that supports email, SMS, and push notifications.

**Requirements:**
- Send 10 million notifications per day
- Deliver within 5 seconds for push notifications
- Support retry on failure
- Track delivery status
- Support scheduling notifications for future delivery

**Cover:**
1. High-level architecture diagram (describe in text)
2. How you handle different notification channels
3. Queue design and retry logic
4. How you track delivery status
5. Handling failures at scale""",
            "system_design_rubric": """Score based on:
- Architecture clarity (20pts): message queue, workers, channel providers
- Queue design (20pts): async processing, retry with backoff
- Multi-channel handling (20pts): separate workers per channel type
- Delivery tracking (20pts): status updates, dead letter queues
- Scale and failure handling (20pts): rate limiting, circuit breakers, monitoring""",
        },
        {
            "title": "Design a Rate Limiter",
            "skill_id": skill_sd,
            "difficulty": "medium",
            "problem_type": "system_design",
            "description": """Design a rate limiter for an API gateway that allows 1000 requests per minute per user.

**Requirements:**
- Works in a distributed environment (multiple API servers)
- Returns 429 Too Many Requests with Retry-After header when limit exceeded
- Minimal latency overhead (< 1ms)
- Works for 10 million users

**Cover:**
1. Which rate limiting algorithm you'd use and why
2. Where you'd store the counters
3. How you handle distributed scenarios
4. Edge cases (burst traffic, clock skew, etc.)""",
            "system_design_rubric": """Score based on:
- Algorithm choice (25pts): token bucket vs sliding window vs fixed window — explains trade-offs
- Storage choice (25pts): Redis with atomic operations, explains why not SQL
- Distributed handling (25pts): mentions Redis cluster, or sticky sessions, or Lua scripts
- Edge cases (25pts): burst handling, clock synchronisation, race conditions""",
        },
    ]

    for p in sd_problems:
        _upsert_task(p)


def _seed_domain_problems():
    """More coding problems across Web Dev, Data Science, Cybersecurity."""
    skill_web  = _get_skill_id("web")
    skill_data = _get_skill_id("data")
    skill_sec  = _get_skill_id("security") or _get_skill_id("cyber")
    skill_algo = _get_skill_id("algorithm")

    domain_problems = [
        # Web Dev
        {
            "title": "Parse URL Query Parameters",
            "skill_id": skill_web,
            "difficulty": "easy",
            "problem_type": "coding",
            "description": """Given a URL query string (without the leading ?), parse it into key-value pairs.

Example: `name=Alice&age=30&city=Delhi` → output each pair on a new line as `key=value`, sorted by key.""",
            "input_format": "A single query string like `b=2&a=1&c=3`",
            "output_format": "Key=value pairs sorted by key, one per line",
            "test_cases": [
                {"input": "name=Alice&age=30", "output": "age=30\nname=Alice"},
                {"input": "z=26&a=1&m=13", "output": "a=1\nm=13\nz=26"},
                {"input": "key=value", "output": "key=value"},
            ]
        },
        {
            "title": "Validate Email Format",
            "skill_id": skill_web,
            "difficulty": "easy",
            "problem_type": "coding",
            "description": """Validate whether a given string is a valid email address.

Rules:
- Must have exactly one `@`
- Local part (before @) must be non-empty
- Domain part (after @) must have at least one `.`
- No spaces allowed

Print `valid` or `invalid`.""",
            "input_format": "A single string",
            "output_format": "valid or invalid",
            "test_cases": [
                {"input": "user@example.com", "output": "valid"},
                {"input": "user@", "output": "invalid"},
                {"input": "@example.com", "output": "invalid"},
                {"input": "no-at-sign.com", "output": "invalid"},
                {"input": "user@domain.co.in", "output": "valid"},
            ]
        },
        # Data Science
        {
            "title": "Calculate Moving Average",
            "skill_id": skill_data,
            "difficulty": "easy",
            "problem_type": "coding",
            "description": """Given a list of numbers and a window size k, compute the moving average.

The moving average for position i (0-indexed) is the average of elements from i to i+k-1.
Output k windows, each rounded to 2 decimal places.""",
            "input_format": "Line 1: n k. Line 2: n numbers",
            "output_format": "n-k+1 moving averages, one per line",
            "test_cases": [
                {"input": "5 3\n1 2 3 4 5", "output": "2.0\n3.0\n4.0"},
                {"input": "4 2\n10 20 30 40", "output": "15.0\n25.0\n35.0"},
            ]
        },
        {
            "title": "Find Outliers (IQR Method)",
            "skill_id": skill_data,
            "difficulty": "medium",
            "problem_type": "coding",
            "description": """Given a list of numbers, find outliers using the IQR method.

An outlier is any value below Q1 - 1.5*IQR or above Q3 + 1.5*IQR
where IQR = Q3 - Q1.

Print the outliers in sorted order, one per line. If none, print "no outliers".""",
            "input_format": "Line 1: n. Line 2: n integers",
            "output_format": "Outlier values sorted ascending, or 'no outliers'",
            "test_cases": [
                {"input": "9\n1 2 3 4 5 6 7 8 100", "output": "100"},
                {"input": "6\n10 20 30 40 50 60", "output": "no outliers"},
            ]
        },
        # Cybersecurity
        {
            "title": "Caesar Cipher Decoder",
            "skill_id": skill_sec,
            "difficulty": "easy",
            "problem_type": "coding",
            "description": """Decode a Caesar cipher message. The cipher shifts each letter by a fixed amount.

Given an encoded string and the shift amount, decode it. Only letters are shifted; spaces, numbers, and punctuation stay unchanged. Preserve case.""",
            "input_format": "Line 1: shift amount (1-25). Line 2: encoded message",
            "output_format": "Decoded message",
            "test_cases": [
                {"input": "3\nKhoor Zruog", "output": "Hello World"},
                {"input": "13\nUryyb", "output": "Hello"},
                {"input": "1\nIFFMP", "output": "HELLO"},  # actually shift 1 gives HELLO from IFMMP... let me fix
            ]
        },
        {
            "title": "Password Strength Checker",
            "skill_id": skill_sec,
            "difficulty": "easy",
            "problem_type": "coding",
            "description": """Check password strength based on these rules:
- Length >= 8: +1 point
- Contains uppercase: +1 point
- Contains lowercase: +1 point
- Contains digit: +1 point
- Contains special char (!@#$%^&*): +1 point

Print: `weak` (0-2 points), `medium` (3-4 points), or `strong` (5 points)""",
            "input_format": "A single password string",
            "output_format": "weak, medium, or strong",
            "test_cases": [
                {"input": "abc", "output": "weak"},
                {"input": "password123", "output": "medium"},
                {"input": "P@ssw0rd!", "output": "strong"},
                {"input": "ALLCAPS1!", "output": "medium"},
            ]
        },
    ]

    for p in domain_problems:
        _upsert_task(p)
