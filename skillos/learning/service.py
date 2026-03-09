"""learning/service.py — Learning paths, roadmaps, progress tracking."""
import uuid
from skillos.db.database import get_db, fetchall, fetchone, transaction


def list_paths(domain=None) -> list:
    if domain:
        paths = fetchall("SELECT * FROM learning_paths WHERE is_active=1 AND domain=? ORDER BY ordinal", (domain,))
    else:
        paths = fetchall("SELECT * FROM learning_paths WHERE is_active=1 ORDER BY domain, ordinal")
    result = []
    for p in paths:
        d = dict(p)
        d["total_steps"] = fetchone("SELECT COUNT(*) AS c FROM path_steps WHERE path_id=?", (d["id"],))["c"]
        result.append(d)
    return result


def get_path(path_id: str, user_id: str = None) -> dict | None:
    p = fetchone("SELECT * FROM learning_paths WHERE id=?", (path_id,))
    if not p:
        return None
    result = dict(p)
    steps = fetchall("SELECT ps.*, t.title AS task_title, t.difficulty, t.problem_type FROM path_steps ps LEFT JOIN tasks t ON t.id=ps.task_id WHERE ps.path_id=? ORDER BY ps.ordinal", (path_id,))
    completed_ids = set()
    if user_id:
        done = fetchall("SELECT step_id FROM path_progress WHERE user_id=? AND path_id=?", (user_id, path_id))
        completed_ids = {r["step_id"] for r in done}
    result["steps"] = [{**dict(s), "completed": s["id"] in completed_ids} for s in steps]
    total = len(result["steps"])
    done_count = len(completed_ids)
    result["progress_pct"] = round(done_count / total * 100) if total else 0
    return result


def complete_step(user_id: str, path_id: str, step_id: str) -> dict:
    db = get_db()
    already = db.execute("SELECT 1 FROM path_progress WHERE user_id=? AND path_id=? AND step_id=?", (user_id, path_id, step_id)).fetchone()
    if not already:
        db.execute("INSERT OR IGNORE INTO path_progress (id,user_id,path_id,step_id) VALUES (?,?,?,?)", (str(uuid.uuid4()), user_id, path_id, step_id))
        db.commit()
        try:
            from skillos.reputation.service import award_reputation
            award_reputation(user_id, 10, "path_step_completed")
        except Exception:
            pass
    return get_path(path_id, user_id)


def get_user_paths(user_id: str) -> list:
    paths = list_paths()
    result = []
    for p in paths:
        total = p["total_steps"]
        done = fetchone("SELECT COUNT(*) AS c FROM path_progress WHERE user_id=? AND path_id=?", (user_id, p["id"]))["c"]
        result.append({**p, "progress_pct": round(done / total * 100) if total else 0, "completed_steps": done})
    return result


def seed_learning_paths():
    """Seed 10 learning paths across all 5 domains. Idempotent."""
    existing = fetchone("SELECT id FROM learning_paths LIMIT 1")
    if existing:
        return

    paths = [
        # ── ALGORITHMS ──────────────────────────────────────────────────────
        {
            "id": "path-algo-beginner",
            "title": "Algorithms Fundamentals",
            "description": "Master core data structures and algorithms from scratch. Ideal starting point for interview prep.",
            "domain": "algorithms", "difficulty": "beginner", "ordinal": 1,
            "steps": [
                {"title": "Two Sum", "task_id": "arr-001", "skill_id": "sk-arrays", "step_type": "problem", "ordinal": 1},
                {"title": "Valid Anagram", "task_id": "str-001", "skill_id": "sk-strings", "step_type": "problem", "ordinal": 2},
                {"title": "Valid Parentheses", "task_id": "str-005", "skill_id": "sk-stacks", "step_type": "problem", "ordinal": 3},
                {"title": "Best Time to Buy and Sell Stock", "task_id": "arr-002", "skill_id": "sk-arrays", "step_type": "problem", "ordinal": 4},
                {"title": "Linked List Cycle", "task_id": "ll-001", "skill_id": "sk-linkedlist", "step_type": "problem", "ordinal": 5},
                {"title": "Binary Search", "task_id": "bs-001", "skill_id": "sk-binary", "step_type": "problem", "ordinal": 6},
                {"title": "Climbing Stairs", "task_id": "dp-001", "skill_id": "sk-dp", "step_type": "problem", "ordinal": 7},
                {"title": "Tree Inorder Traversal", "task_id": "tr-001", "skill_id": "sk-trees", "step_type": "problem", "ordinal": 8},
            ],
        },
        {
            "id": "path-algo-advanced",
            "title": "Advanced Algorithms",
            "description": "Dynamic programming, graphs, and hard-level problems for FAANG-level preparation.",
            "domain": "algorithms", "difficulty": "advanced", "ordinal": 2,
            "steps": [
                {"title": "Longest Increasing Subsequence", "task_id": "dp-004", "skill_id": "sk-dp", "step_type": "problem", "ordinal": 1},
                {"title": "Number of Islands", "task_id": "gr-001", "skill_id": "sk-graphs", "step_type": "problem", "ordinal": 2},
                {"title": "Course Schedule (Topo Sort)", "task_id": "gr-004", "skill_id": "sk-graphs", "step_type": "problem", "ordinal": 3},
                {"title": "Trapping Rain Water", "task_id": "arr-011", "skill_id": "sk-arrays", "step_type": "problem", "ordinal": 4},
                {"title": "Merge K Sorted Lists", "task_id": "hp-001", "skill_id": "sk-heap", "step_type": "problem", "ordinal": 5},
                {"title": "Word Search II (Trie+Backtrack)", "task_id": "trie-001", "skill_id": "sk-trie", "step_type": "problem", "ordinal": 6},
                {"title": "Alien Dictionary", "task_id": "gr-009", "skill_id": "sk-graphs", "step_type": "problem", "ordinal": 7},
                {"title": "Edit Distance", "task_id": "dp-007", "skill_id": "sk-dp", "step_type": "problem", "ordinal": 8},
            ],
        },
        # ── WEB DEV ─────────────────────────────────────────────────────────
        {
            "id": "path-webdev-fundamentals",
            "title": "Web Dev Fundamentals",
            "description": "JavaScript, REST APIs, async patterns, and HTTP — everything for a modern web developer.",
            "domain": "web_dev", "difficulty": "beginner", "ordinal": 3,
            "steps": [
                {"title": "REST API Design MCQ", "task_id": "api-mcq-001", "skill_id": "sk-restapi", "step_type": "problem", "ordinal": 1},
                {"title": "HTTP Methods & Status Codes", "task_id": "api-mcq-002", "skill_id": "sk-restapi", "step_type": "problem", "ordinal": 2},
                {"title": "JavaScript Closures", "task_id": "js-001", "skill_id": "sk-jscore", "step_type": "problem", "ordinal": 3},
                {"title": "Promise Chaining", "task_id": "api-mcq-005", "skill_id": "sk-async", "step_type": "problem", "ordinal": 4},
                {"title": "Authentication Concepts", "task_id": "api-mcq-007", "skill_id": "sk-auth", "step_type": "problem", "ordinal": 5},
                {"title": "RESTful API Design", "task_id": "api-mcq-010", "skill_id": "sk-restapi", "step_type": "problem", "ordinal": 6},
            ],
        },
        {
            "id": "path-webdev-backend",
            "title": "Backend Engineering",
            "description": "Server-side development: Node.js, databases, auth, caching, and production-ready APIs.",
            "domain": "web_dev", "difficulty": "intermediate", "ordinal": 4,
            "steps": [
                {"title": "Node.js Event Loop", "task_id": "api-mcq-003", "skill_id": "sk-nodejs", "step_type": "problem", "ordinal": 1},
                {"title": "JWT Authentication", "task_id": "api-mcq-007", "skill_id": "sk-auth", "step_type": "problem", "ordinal": 2},
                {"title": "Rate Limiting Design", "task_id": "api-mcq-009", "skill_id": "sk-restapi", "step_type": "problem", "ordinal": 3},
                {"title": "SQL Query Optimisation", "task_id": "sql-003", "skill_id": "sk-sql", "step_type": "problem", "ordinal": 4},
                {"title": "OAuth 2.0 Flow", "task_id": "api-mcq-011", "skill_id": "sk-auth", "step_type": "problem", "ordinal": 5},
                {"title": "API Versioning Strategies", "task_id": "api-mcq-013", "skill_id": "sk-restapi", "step_type": "problem", "ordinal": 6},
            ],
        },
        # ── DATA SCIENCE ─────────────────────────────────────────────────────
        {
            "id": "path-data-sql",
            "title": "SQL & Databases",
            "description": "Master SQL from basic queries to window functions, CTEs, and query optimisation.",
            "domain": "data_science", "difficulty": "beginner", "ordinal": 5,
            "steps": [
                {"title": "Basic SELECT Queries", "task_id": "sql-001", "skill_id": "sk-sql", "step_type": "problem", "ordinal": 1},
                {"title": "JOINs and Aggregation", "task_id": "sql-002", "skill_id": "sk-sql", "step_type": "problem", "ordinal": 2},
                {"title": "Complex JOINs", "task_id": "sql-003", "skill_id": "sk-sql", "step_type": "problem", "ordinal": 3},
                {"title": "Subqueries & CTEs", "task_id": "sql-004", "skill_id": "sk-sql", "step_type": "problem", "ordinal": 4},
                {"title": "Window Functions", "task_id": "sql-005", "skill_id": "sk-sql", "step_type": "problem", "ordinal": 5},
                {"title": "Query Optimisation", "task_id": "sql-006", "skill_id": "sk-sql", "step_type": "problem", "ordinal": 6},
            ],
        },
        {
            "id": "path-data-ml",
            "title": "Machine Learning Path",
            "description": "From data wrangling with pandas to building and evaluating ML models.",
            "domain": "data_science", "difficulty": "intermediate", "ordinal": 6,
            "steps": [
                {"title": "Pandas DataFrame Ops", "task_id": "ds-001", "skill_id": "sk-pandas", "step_type": "problem", "ordinal": 1},
                {"title": "Data Cleaning", "task_id": "ds-002", "skill_id": "sk-pandas", "step_type": "problem", "ordinal": 2},
                {"title": "Statistical Concepts MCQ", "task_id": "ds-003", "skill_id": "sk-stats", "step_type": "problem", "ordinal": 3},
                {"title": "Linear Regression", "task_id": "ds-004", "skill_id": "sk-ml", "step_type": "problem", "ordinal": 4},
                {"title": "Model Evaluation", "task_id": "ds-005", "skill_id": "sk-ml", "step_type": "problem", "ordinal": 5},
                {"title": "Feature Engineering", "task_id": "ds-006", "skill_id": "sk-ml", "step_type": "problem", "ordinal": 6},
            ],
        },
        # ── CYBERSECURITY ──────────────────────────────────────────────────
        {
            "id": "path-security-fundamentals",
            "title": "Security Fundamentals",
            "description": "Cryptography, common web vulnerabilities (OWASP Top 10), and secure coding practices.",
            "domain": "cybersecurity", "difficulty": "beginner", "ordinal": 7,
            "steps": [
                {"title": "Cryptography Basics", "task_id": "sec-mcq-001", "skill_id": "sk-crypto", "step_type": "problem", "ordinal": 1},
                {"title": "SQL Injection", "task_id": "sec-mcq-002", "skill_id": "sk-vulns", "step_type": "problem", "ordinal": 2},
                {"title": "XSS & CSRF Attacks", "task_id": "sec-mcq-003", "skill_id": "sk-vulns", "step_type": "problem", "ordinal": 3},
                {"title": "HTTPS & TLS", "task_id": "sec-mcq-004", "skill_id": "sk-network", "step_type": "problem", "ordinal": 4},
                {"title": "Password Hashing", "task_id": "sec-mcq-005", "skill_id": "sk-crypto", "step_type": "problem", "ordinal": 5},
                {"title": "OAuth & Token Security", "task_id": "sec-mcq-007", "skill_id": "sk-vulns", "step_type": "problem", "ordinal": 6},
                {"title": "Network Scanning Concepts", "task_id": "sec-mcq-009", "skill_id": "sk-network", "step_type": "problem", "ordinal": 7},
            ],
        },
        {
            "id": "path-security-advanced",
            "title": "Advanced Security & Pentesting",
            "description": "Advanced attack vectors, secure design patterns, and defensive programming.",
            "domain": "cybersecurity", "difficulty": "advanced", "ordinal": 8,
            "steps": [
                {"title": "Memory Safety Vulnerabilities", "task_id": "sec-mcq-010", "skill_id": "sk-vulns", "step_type": "problem", "ordinal": 1},
                {"title": "Cryptographic Protocols", "task_id": "sec-mcq-011", "skill_id": "sk-crypto", "step_type": "problem", "ordinal": 2},
                {"title": "Reverse Engineering Basics", "task_id": "sec-mcq-012", "skill_id": "sk-forensics", "step_type": "problem", "ordinal": 3},
                {"title": "Network Forensics", "task_id": "sec-mcq-013", "skill_id": "sk-forensics", "step_type": "problem", "ordinal": 4},
                {"title": "Zero-Day Concepts", "task_id": "sec-mcq-014", "skill_id": "sk-vulns", "step_type": "problem", "ordinal": 5},
            ],
        },
        # ── SYSTEM DESIGN ─────────────────────────────────────────────────
        {
            "id": "path-sysdesign-fundamentals",
            "title": "System Design Fundamentals",
            "description": "Load balancing, caching, databases, CAP theorem, and distributed systems basics.",
            "domain": "system_design", "difficulty": "intermediate", "ordinal": 9,
            "steps": [
                {"title": "Scalability Concepts", "task_id": "sd-mcq-001", "skill_id": "sk-scale", "step_type": "problem", "ordinal": 1},
                {"title": "Database Sharding", "task_id": "sd-mcq-002", "skill_id": "sk-databases", "step_type": "problem", "ordinal": 2},
                {"title": "Caching Strategies", "task_id": "sd-mcq-003", "skill_id": "sk-sysarch", "step_type": "problem", "ordinal": 3},
                {"title": "Load Balancing", "task_id": "sd-mcq-004", "skill_id": "sk-scale", "step_type": "problem", "ordinal": 4},
                {"title": "CAP Theorem", "task_id": "sd-mcq-005", "skill_id": "sk-scale", "step_type": "problem", "ordinal": 5},
                {"title": "Microservices Design", "task_id": "sd-mcq-007", "skill_id": "sk-microservices", "step_type": "problem", "ordinal": 6},
                {"title": "Design a URL Shortener", "task_id": "sd-mcq-009", "skill_id": "sk-sysarch", "step_type": "problem", "ordinal": 7},
                {"title": "Design a Rate Limiter", "task_id": "sd-mcq-010", "skill_id": "sk-sysarch", "step_type": "problem", "ordinal": 8},
            ],
        },
        {
            "id": "path-fullstack",
            "title": "Full Stack Developer",
            "description": "End-to-end path: frontend, backend, databases, DevOps — become a complete developer.",
            "domain": "full_stack", "difficulty": "intermediate", "ordinal": 10,
            "steps": [
                {"title": "JavaScript Fundamentals", "task_id": "js-001", "skill_id": "sk-jscore", "step_type": "problem", "ordinal": 1},
                {"title": "REST API Design", "task_id": "api-mcq-001", "skill_id": "sk-restapi", "step_type": "problem", "ordinal": 2},
                {"title": "SQL Fundamentals", "task_id": "sql-001", "skill_id": "sk-sql", "step_type": "problem", "ordinal": 3},
                {"title": "Authentication & JWT", "task_id": "api-mcq-007", "skill_id": "sk-auth", "step_type": "problem", "ordinal": 4},
                {"title": "Debug: Broken API Endpoint", "task_id": "fs-debug-001", "skill_id": "sk-fullstack", "step_type": "problem", "ordinal": 5},
                {"title": "System Design: Choose Your DB", "task_id": "sd-mcq-002", "skill_id": "sk-databases", "step_type": "problem", "ordinal": 6},
                {"title": "Two Sum (Algorithms Refresher)", "task_id": "arr-001", "skill_id": "sk-arrays", "step_type": "problem", "ordinal": 7},
                {"title": "Security: XSS & CSRF", "task_id": "sec-mcq-003", "skill_id": "sk-vulns", "step_type": "problem", "ordinal": 8},
                {"title": "CI/CD Concepts", "task_id": "fs-debug-004", "skill_id": "sk-devops", "step_type": "problem", "ordinal": 9},
            ],
        },
    ]

    with transaction() as db:
        for p_data in paths:
            steps = p_data.pop("steps")
            db.execute(
                "INSERT OR IGNORE INTO learning_paths (id,title,description,domain,difficulty,ordinal,is_active) VALUES (?,?,?,?,?,?,1)",
                (p_data["id"], p_data["title"], p_data["description"], p_data["domain"], p_data["difficulty"], p_data["ordinal"])
            )
            for s in steps:
                db.execute(
                    "INSERT OR IGNORE INTO path_steps (id,path_id,title,task_id,skill_id,step_type,ordinal,is_required) VALUES (?,?,?,?,?,?,?,1)",
                    (str(uuid.uuid4()), p_data["id"], s["title"], s.get("task_id"), s.get("skill_id"), s["step_type"], s["ordinal"])
                )
