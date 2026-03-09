"""
db/seed_problems.py

12 real problems across 6 skill domains.
Run after migrations: python -m skillos.db.seed_problems

Problems:
  Python Fundamentals (3): Double, FizzBuzz, Palindrome
  Arrays & Strings    (2): Two Sum, Max Subarray
  Hash Maps & Sets    (2): Group Anagrams, First Unique Char
  Recursion           (2): Fibonacci, Power Function
  Sorting & Searching (2): Binary Search, Merge Sorted Arrays
  Graphs & Trees      (1): BFS Level Order
"""

import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import uuid
from skillos.db.database import get_db
from skillos.db.migrations import run_migrations

PROBLEMS = [
    # ── Python Fundamentals ───────────────────────────────────────────────────
    {
        "id": "task-double-001",
        "title": "Double the Number",
        "description": "Read an integer N from stdin. Print N * 2.",
        "difficulty": "easy",
        "skill_id": "skill-python-001",
        "time_limit_ms": 2000, "memory_limit_kb": 131072, "is_published": 1,
        "test_cases": [
            {"input": "5",    "expected_output": "10",   "is_hidden": 0, "ordinal": 1},
            {"input": "0",    "expected_output": "0",    "is_hidden": 0, "ordinal": 2},
            {"input": "-3",   "expected_output": "-6",   "is_hidden": 0, "ordinal": 3},
            {"input": "100",  "expected_output": "200",  "is_hidden": 1, "ordinal": 4},
            {"input": "999",  "expected_output": "1998", "is_hidden": 1, "ordinal": 5},
            {"input": "-1000000000", "expected_output": "-2000000000", "is_hidden": 1, "ordinal": 6},
        ],
    },
    {
        "id": "task-fizzbuzz-002",
        "title": "FizzBuzz",
        "description": (
            "Given N, print numbers 1 to N.\n"
            "For multiples of 3 print Fizz, multiples of 5 print Buzz, "
            "multiples of both print FizzBuzz.\n\n"
            "Input: single integer N.\n"
            "Output: N lines."
        ),
        "difficulty": "easy",
        "skill_id": "skill-python-001",
        "time_limit_ms": 2000, "memory_limit_kb": 131072, "is_published": 1,
        "test_cases": [
            {"input": "5",  "expected_output": "1\n2\nFizz\n4\nBuzz",                    "is_hidden": 0, "ordinal": 1},
            {"input": "15", "expected_output": "1\n2\nFizz\n4\nBuzz\nFizz\n7\n8\nFizz\nBuzz\n11\nFizz\n13\n14\nFizzBuzz", "is_hidden": 0, "ordinal": 2},
            {"input": "1",  "expected_output": "1",                                       "is_hidden": 1, "ordinal": 3},
            {"input": "20", "expected_output": "1\n2\nFizz\n4\nBuzz\nFizz\n7\n8\nFizz\nBuzz\n11\nFizz\n13\n14\nFizzBuzz\n16\n17\nFizz\n19\nBuzz", "is_hidden": 1, "ordinal": 4},
        ],
    },
    {
        "id": "task-palindrome-003",
        "title": "Check Palindrome",
        "description": (
            "Given a string, print YES if it is a palindrome, NO otherwise.\n"
            "Ignore case. Only consider alphanumeric characters.\n\n"
            "Input: single string on one line.\n"
            "Output: YES or NO."
        ),
        "difficulty": "easy",
        "skill_id": "skill-python-001",
        "time_limit_ms": 2000, "memory_limit_kb": 131072, "is_published": 1,
        "test_cases": [
            {"input": "racecar",          "expected_output": "YES", "is_hidden": 0, "ordinal": 1},
            {"input": "hello",            "expected_output": "NO",  "is_hidden": 0, "ordinal": 2},
            {"input": "A man a plan a canal Panama", "expected_output": "YES", "is_hidden": 0, "ordinal": 3},
            {"input": "Was it a car or a cat I saw", "expected_output": "YES", "is_hidden": 1, "ordinal": 4},
            {"input": "Not a palindrome",  "expected_output": "NO",  "is_hidden": 1, "ordinal": 5},
        ],
    },
    # ── Arrays & Strings ──────────────────────────────────────────────────────
    {
        "id": "task-twosum-004",
        "title": "Two Sum",
        "description": (
            "Given an array of integers and a target, return indices (0-based) "
            "of the two numbers that add up to target.\n\n"
            "Input: first line N, second line N space-separated ints, third line target.\n"
            "Output: two space-separated indices, smaller index first."
        ),
        "difficulty": "medium",
        "skill_id": "skill-arrays-001",
        "time_limit_ms": 2000, "memory_limit_kb": 131072, "is_published": 1,
        "test_cases": [
            {"input": "4\n2 7 11 15\n9",  "expected_output": "0 1", "is_hidden": 0, "ordinal": 1},
            {"input": "3\n3 2 4\n6",      "expected_output": "1 2", "is_hidden": 0, "ordinal": 2},
            {"input": "2\n3 3\n6",        "expected_output": "0 1", "is_hidden": 1, "ordinal": 3},
            {"input": "5\n1 4 8 3 2\n5", "expected_output": "0 3", "is_hidden": 1, "ordinal": 4},
        ],
    },
    {
        "id": "task-maxsubarray-005",
        "title": "Maximum Subarray",
        "description": (
            "Given an array of integers, find the contiguous subarray with the largest sum.\n"
            "Print the maximum sum.\n\n"
            "Input: first line N, second line N space-separated integers.\n"
            "Output: single integer — the maximum subarray sum."
        ),
        "difficulty": "medium",
        "skill_id": "skill-arrays-001",
        "time_limit_ms": 2000, "memory_limit_kb": 131072, "is_published": 1,
        "test_cases": [
            {"input": "9\n-2 1 -3 4 -1 2 1 -5 4", "expected_output": "6",  "is_hidden": 0, "ordinal": 1},
            {"input": "1\n1",                       "expected_output": "1",  "is_hidden": 0, "ordinal": 2},
            {"input": "5\n5 4 -1 7 8",             "expected_output": "23", "is_hidden": 0, "ordinal": 3},
            {"input": "4\n-2 -3 -1 -4",            "expected_output": "-1", "is_hidden": 1, "ordinal": 4},
            {"input": "6\n1 2 3 -6 4 5",           "expected_output": "9",  "is_hidden": 1, "ordinal": 5},
        ],
    },
    # ── Hash Maps & Sets ──────────────────────────────────────────────────────
    {
        "id": "task-firstunique-006",
        "title": "First Unique Character",
        "description": (
            "Given a string, find the index of its first non-repeating character.\n"
            "If none exists, return -1.\n\n"
            "Input: single string (lowercase letters only).\n"
            "Output: integer index (0-based)."
        ),
        "difficulty": "easy",
        "skill_id": "skill-hashmaps-001",
        "time_limit_ms": 2000, "memory_limit_kb": 131072, "is_published": 1,
        "test_cases": [
            {"input": "leetcode",  "expected_output": "0",  "is_hidden": 0, "ordinal": 1},
            {"input": "loveleet",  "expected_output": "2",  "is_hidden": 0, "ordinal": 2},
            {"input": "aabb",      "expected_output": "-1", "is_hidden": 0, "ordinal": 3},
            {"input": "z",         "expected_output": "0",  "is_hidden": 1, "ordinal": 4},
            {"input": "aabbccdde","expected_output": "8",  "is_hidden": 1, "ordinal": 5},
        ],
    },
    {
        "id": "task-twostrings-007",
        "title": "Common Characters",
        "description": (
            "Given two strings, print all characters that appear in BOTH strings.\n"
            "Print each character once, sorted alphabetically.\n"
            "If no common characters, print NONE.\n\n"
            "Input: two lines, one string each.\n"
            "Output: sorted common characters joined (no spaces), or NONE."
        ),
        "difficulty": "easy",
        "skill_id": "skill-hashmaps-001",
        "time_limit_ms": 2000, "memory_limit_kb": 131072, "is_published": 1,
        "test_cases": [
            {"input": "hello\nworld",  "expected_output": "lo",   "is_hidden": 0, "ordinal": 1},
            {"input": "abc\nxyz",      "expected_output": "NONE", "is_hidden": 0, "ordinal": 2},
            {"input": "python\njava",  "expected_output": "a",    "is_hidden": 1, "ordinal": 3},
            {"input": "aabbcc\nccbbaa","expected_output": "abc",  "is_hidden": 1, "ordinal": 4},
        ],
    },
    # ── Recursion & Backtracking ───────────────────────────────────────────────
    {
        "id": "task-fibonacci-008",
        "title": "Fibonacci Number",
        "description": (
            "Return the Nth Fibonacci number (0-indexed).\n"
            "F(0)=0, F(1)=1, F(N)=F(N-1)+F(N-2).\n\n"
            "Input: single integer N.\n"
            "Output: F(N)."
        ),
        "difficulty": "easy",
        "skill_id": "skill-recursion-001",
        "time_limit_ms": 3000, "memory_limit_kb": 131072, "is_published": 1,
        "test_cases": [
            {"input": "0",  "expected_output": "0",   "is_hidden": 0, "ordinal": 1},
            {"input": "1",  "expected_output": "1",   "is_hidden": 0, "ordinal": 2},
            {"input": "10", "expected_output": "55",  "is_hidden": 0, "ordinal": 3},
            {"input": "20", "expected_output": "6765","is_hidden": 1, "ordinal": 4},
            {"input": "30", "expected_output": "832040","is_hidden": 1, "ordinal": 5},
        ],
    },
    {
        "id": "task-power-009",
        "title": "Power Function",
        "description": (
            "Implement pow(x, n) — x raised to the power n.\n"
            "n can be negative. Use recursion or fast exponentiation.\n\n"
            "Input: two lines — float x, integer n.\n"
            "Output: result rounded to 5 decimal places."
        ),
        "difficulty": "medium",
        "skill_id": "skill-recursion-001",
        "time_limit_ms": 2000, "memory_limit_kb": 131072, "is_published": 1,
        "test_cases": [
            {"input": "2.0\n10",  "expected_output": "1024.0",   "is_hidden": 0, "ordinal": 1},
            {"input": "2.1\n3",   "expected_output": "9.261",    "is_hidden": 0, "ordinal": 2},
            {"input": "2.0\n-2",  "expected_output": "0.25",     "is_hidden": 0, "ordinal": 3},
            {"input": "1.0\n2147483647", "expected_output": "1.0","is_hidden": 1, "ordinal": 4},
        ],
    },
    # ── Sorting & Searching ───────────────────────────────────────────────────
    {
        "id": "task-binarysearch-010",
        "title": "Binary Search",
        "description": (
            "Given a sorted array and a target, return the index of target.\n"
            "If not found, return -1. Must run in O(log n).\n\n"
            "Input: first line N, second line N sorted integers, third line target.\n"
            "Output: index (0-based) or -1."
        ),
        "difficulty": "easy",
        "skill_id": "skill-sorting-001",
        "time_limit_ms": 2000, "memory_limit_kb": 131072, "is_published": 1,
        "test_cases": [
            {"input": "6\n-1 0 3 5 9 12\n9",  "expected_output": "4",  "is_hidden": 0, "ordinal": 1},
            {"input": "6\n-1 0 3 5 9 12\n2",  "expected_output": "-1", "is_hidden": 0, "ordinal": 2},
            {"input": "1\n5\n5",               "expected_output": "0",  "is_hidden": 1, "ordinal": 3},
            {"input": "5\n1 3 5 7 9\n1",       "expected_output": "0",  "is_hidden": 1, "ordinal": 4},
            {"input": "5\n1 3 5 7 9\n9",       "expected_output": "4",  "is_hidden": 1, "ordinal": 5},
        ],
    },
    {
        "id": "task-mergesorted-011",
        "title": "Merge Two Sorted Arrays",
        "description": (
            "Merge two sorted arrays into one sorted array.\n\n"
            "Input: first line N, second line N sorted ints, "
            "third line M, fourth line M sorted ints.\n"
            "Output: N+M space-separated sorted integers."
        ),
        "difficulty": "medium",
        "skill_id": "skill-sorting-001",
        "time_limit_ms": 2000, "memory_limit_kb": 131072, "is_published": 1,
        "test_cases": [
            {"input": "3\n1 2 3\n3\n2 5 6",   "expected_output": "1 2 2 3 5 6", "is_hidden": 0, "ordinal": 1},
            {"input": "1\n0\n3\n2 5 6",        "expected_output": "0 2 5 6",     "is_hidden": 0, "ordinal": 2},
            {"input": "0\n\n3\n1 2 3",         "expected_output": "1 2 3",       "is_hidden": 1, "ordinal": 3},
            {"input": "4\n1 3 5 7\n4\n2 4 6 8","expected_output": "1 2 3 4 5 6 7 8","is_hidden": 1,"ordinal": 4},
        ],
    },
    # ── Graphs & Trees ────────────────────────────────────────────────────────
    {
        "id": "task-bfslevel-012",
        "title": "BFS Level Order Traversal",
        "description": (
            "Given a binary tree in level-order input format, "
            "print nodes level by level, each level on a new line.\n"
            "Use -1 to represent null nodes.\n\n"
            "Input: space-separated level-order values (use -1 for null).\n"
            "Output: each level's values space-separated, one level per line."
        ),
        "difficulty": "hard",
        "skill_id": "skill-graphs-001",
        "time_limit_ms": 3000, "memory_limit_kb": 131072, "is_published": 1,
        "test_cases": [
            {"input": "3 9 20 -1 -1 15 7", "expected_output": "3\n9 20\n15 7",  "is_hidden": 0, "ordinal": 1},
            {"input": "1",                  "expected_output": "1",               "is_hidden": 0, "ordinal": 2},
            {"input": "1 2 3 4 5",         "expected_output": "1\n2 3\n4 5",     "is_hidden": 1, "ordinal": 3},
            {"input": "1 2 -1 3 -1",       "expected_output": "1\n2\n3",         "is_hidden": 1, "ordinal": 4},
        ],
    },
]


def seed_problems():
    run_migrations()
    db = get_db()

    seeded = 0
    skipped = 0

    for problem in PROBLEMS:
        existing = db.execute(
            "SELECT id FROM tasks WHERE id = ?", (problem["id"],)
        ).fetchone()

        if existing:
            skipped += 1
            print(f"  skip  {problem['id']} ({problem['title']})")
            continue

        test_cases = problem.pop("test_cases")

        db.execute("""
            INSERT INTO tasks
                (id, title, description, difficulty, skill_id,
                 time_limit_ms, memory_limit_kb, is_published)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            problem["id"], problem["title"], problem["description"],
            problem["difficulty"], problem["skill_id"],
            problem["time_limit_ms"], problem["memory_limit_kb"],
            problem["is_published"],
        ))

        for tc in test_cases:
            db.execute("""
                INSERT INTO test_cases
                    (id, task_id, input, expected_output, is_hidden, ordinal)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                str(uuid.uuid4()),
                problem["id"],
                tc["input"],
                tc["expected_output"],
                tc["is_hidden"],
                tc["ordinal"],
            ))

        problem["test_cases"] = test_cases
        seeded += 1
        print(f"  seed  {problem['id']} ({problem['title']}) — {len(test_cases)} test cases")

    db.commit()
    print(f"\nDone. Seeded: {seeded}  Skipped: {skipped}")


if __name__ == "__main__":
    seed_problems()
