"""
db/seed.py — Complete problem library, 12 tasks across 6 skill domains.
Safe to run multiple times (skips existing tasks).
"""

import uuid
from skillos.db.database import get_db, transaction
from skillos.db.migrations import run_migrations


TASKS = [
    # ── PYTHON FUNDAMENTALS (3 tasks) ────────────────────────────────────────
    {
        "id": "task-double-001",
        "title": "Double the Number",
        "description": (
            "Read an integer N from stdin. Print N * 2.\n\n"
            "Input: a single integer N\n"
            "Output: N multiplied by 2"
        ),
        "difficulty": "easy", "skill_id": "skill-python-001",
        "time_limit_ms": 2000, "memory_limit_kb": 131072, "is_published": 1,
        "test_cases": [
            {"input": "5",           "expected_output": "10",          "is_hidden": 0, "ordinal": 1},
            {"input": "0",           "expected_output": "0",           "is_hidden": 0, "ordinal": 2},
            {"input": "-3",          "expected_output": "-6",          "is_hidden": 0, "ordinal": 3},
            {"input": "100",         "expected_output": "200",         "is_hidden": 1, "ordinal": 4},
            {"input": "999999999",   "expected_output": "1999999998",  "is_hidden": 1, "ordinal": 5},
            {"input": "-1000000000", "expected_output": "-2000000000", "is_hidden": 1, "ordinal": 6},
        ],
    },
    {
        "id": "task-fizzbuzz-003",
        "title": "FizzBuzz",
        "description": (
            "Print numbers 1 to N. For multiples of 3 print 'Fizz', for multiples of 5 "
            "print 'Buzz', for multiples of both print 'FizzBuzz'.\n\n"
            "Input: single integer N\n"
            "Output: N lines"
        ),
        "difficulty": "easy", "skill_id": "skill-python-001",
        "time_limit_ms": 2000, "memory_limit_kb": 131072, "is_published": 1,
        "test_cases": [
            {"input": "5",  "expected_output": "1\n2\nFizz\n4\nBuzz", "is_hidden": 0, "ordinal": 1},
            {"input": "3",  "expected_output": "1\n2\nFizz",          "is_hidden": 0, "ordinal": 2},
            {"input": "15", "expected_output": "1\n2\nFizz\n4\nBuzz\nFizz\n7\n8\nFizz\nBuzz\n11\nFizz\n13\n14\nFizzBuzz", "is_hidden": 0, "ordinal": 3},
            {"input": "1",  "expected_output": "1",                   "is_hidden": 1, "ordinal": 4},
            {"input": "20", "expected_output": "1\n2\nFizz\n4\nBuzz\nFizz\n7\n8\nFizz\nBuzz\n11\nFizz\n13\n14\nFizzBuzz\n16\n17\nFizz\n19\nBuzz", "is_hidden": 1, "ordinal": 5},
        ],
    },
    {
        "id": "task-twosum-002",
        "title": "Two Sum",
        "description": (
            "Given an array of integers and a target, return indices of the two numbers "
            "that add up to the target.\n\n"
            "Input: Line 1=N, Line 2=N ints, Line 3=target\n"
            "Output: two space-separated 0-based indices, smaller first"
        ),
        "difficulty": "medium", "skill_id": "skill-python-001",
        "time_limit_ms": 2000, "memory_limit_kb": 131072, "is_published": 1,
        "test_cases": [
            {"input": "4\n2 7 11 15\n9",       "expected_output": "0 1", "is_hidden": 0, "ordinal": 1},
            {"input": "3\n3 2 4\n6",           "expected_output": "1 2", "is_hidden": 0, "ordinal": 2},
            {"input": "2\n3 3\n6",             "expected_output": "0 1", "is_hidden": 0, "ordinal": 3},
            {"input": "5\n1 4 8 7 3\n11",      "expected_output": "1 3", "is_hidden": 1, "ordinal": 4},
            {"input": "6\n0 -1 2 -3 1 4\n-2",  "expected_output": "3 4", "is_hidden": 1, "ordinal": 5},
            {"input": "4\n-1 -2 -3 -4\n-7",   "expected_output": "2 3", "is_hidden": 1, "ordinal": 6},
        ],
    },

    # ── ARRAYS & STRINGS (2 tasks) ────────────────────────────────────────────
    {
        "id": "task-maxsub-004",
        "title": "Maximum Subarray",
        "description": (
            "Find the contiguous subarray with the largest sum. Return its sum.\n\n"
            "Input: Line 1=N, Line 2=N space-separated integers\n"
            "Output: maximum subarray sum"
        ),
        "difficulty": "medium", "skill_id": "skill-arrays-001",
        "time_limit_ms": 2000, "memory_limit_kb": 131072, "is_published": 1,
        "test_cases": [
            {"input": "9\n-2 1 -3 4 -1 2 1 -5 4", "expected_output": "6",  "is_hidden": 0, "ordinal": 1},
            {"input": "1\n1",                       "expected_output": "1",  "is_hidden": 0, "ordinal": 2},
            {"input": "5\n5 4 -1 7 8",              "expected_output": "23", "is_hidden": 0, "ordinal": 3},
            {"input": "4\n-1 -2 -3 -4",            "expected_output": "-1", "is_hidden": 1, "ordinal": 4},
            {"input": "8\n-2 -3 4 -1 -2 1 5 -3",   "expected_output": "7",  "is_hidden": 1, "ordinal": 5},
            {"input": "6\n1 -1 1 -1 1 -1",          "expected_output": "1",  "is_hidden": 1, "ordinal": 6},
        ],
    },
    {
        "id": "task-anagram-005",
        "title": "Valid Anagram",
        "description": (
            "Given two strings, return 'true' if they are anagrams of each other.\n\n"
            "Input: Line 1=s, Line 2=t\n"
            "Output: 'true' or 'false'"
        ),
        "difficulty": "easy", "skill_id": "skill-arrays-001",
        "time_limit_ms": 2000, "memory_limit_kb": 131072, "is_published": 1,
        "test_cases": [
            {"input": "anagram\nnagaram", "expected_output": "true",  "is_hidden": 0, "ordinal": 1},
            {"input": "rat\ncar",         "expected_output": "false", "is_hidden": 0, "ordinal": 2},
            {"input": "a\na",            "expected_output": "true",  "is_hidden": 0, "ordinal": 3},
            {"input": "listen\nsilent",  "expected_output": "true",  "is_hidden": 1, "ordinal": 4},
            {"input": "hello\nworld",    "expected_output": "false", "is_hidden": 1, "ordinal": 5},
            {"input": "ab\nba",          "expected_output": "true",  "is_hidden": 1, "ordinal": 6},
        ],
    },

    # ── HASH MAPS & SETS (1 task) ─────────────────────────────────────────────
    {
        "id": "task-dupcheck-008",
        "title": "Contains Duplicate",
        "description": (
            "Return 'true' if any value appears at least twice; 'false' if all distinct.\n\n"
            "Input: Line 1=N, Line 2=N space-separated integers\n"
            "Output: 'true' or 'false'"
        ),
        "difficulty": "easy", "skill_id": "skill-hashmaps-001",
        "time_limit_ms": 2000, "memory_limit_kb": 131072, "is_published": 1,
        "test_cases": [
            {"input": "4\n1 2 3 1",    "expected_output": "true",  "is_hidden": 0, "ordinal": 1},
            {"input": "4\n1 2 3 4",    "expected_output": "false", "is_hidden": 0, "ordinal": 2},
            {"input": "5\n1 1 1 3 3",  "expected_output": "true",  "is_hidden": 0, "ordinal": 3},
            {"input": "1\n1",          "expected_output": "false", "is_hidden": 1, "ordinal": 4},
            {"input": "3\n-1 -2 -1",   "expected_output": "true",  "is_hidden": 1, "ordinal": 5},
            {"input": "5\n0 1 2 3 4",  "expected_output": "false", "is_hidden": 1, "ordinal": 6},
        ],
    },

    # ── SORTING & SEARCHING (2 tasks) ─────────────────────────────────────────
    {
        "id": "task-bsearch-006",
        "title": "Binary Search",
        "description": (
            "Given a sorted array and a target, return the index or -1.\n"
            "Must be O(log n).\n\n"
            "Input: Line 1=N, Line 2=N sorted ints, Line 3=target\n"
            "Output: 0-based index or -1"
        ),
        "difficulty": "easy", "skill_id": "skill-sorting-001",
        "time_limit_ms": 2000, "memory_limit_kb": 131072, "is_published": 1,
        "test_cases": [
            {"input": "6\n-1 0 3 5 9 12\n9",  "expected_output": "4",  "is_hidden": 0, "ordinal": 1},
            {"input": "6\n-1 0 3 5 9 12\n2",  "expected_output": "-1", "is_hidden": 0, "ordinal": 2},
            {"input": "1\n5\n5",              "expected_output": "0",  "is_hidden": 0, "ordinal": 3},
            {"input": "4\n1 3 5 7\n1",        "expected_output": "0",  "is_hidden": 1, "ordinal": 4},
            {"input": "4\n1 3 5 7\n7",        "expected_output": "3",  "is_hidden": 1, "ordinal": 5},
            {"input": "5\n2 4 6 8 10\n5",     "expected_output": "-1", "is_hidden": 1, "ordinal": 6},
            {"input": "7\n1 2 3 4 5 6 7\n4",  "expected_output": "3",  "is_hidden": 1, "ordinal": 7},
        ],
    },
    {
        "id": "task-kthlargest-007",
        "title": "Kth Largest Element",
        "description": (
            "Return the kth largest element in an array.\n\n"
            "Input: Line 1=N, Line 2=N ints, Line 3=k\n"
            "Output: kth largest value"
        ),
        "difficulty": "medium", "skill_id": "skill-sorting-001",
        "time_limit_ms": 2000, "memory_limit_kb": 131072, "is_published": 1,
        "test_cases": [
            {"input": "6\n3 2 1 5 6 4\n2",       "expected_output": "5",  "is_hidden": 0, "ordinal": 1},
            {"input": "9\n3 2 3 1 2 4 5 5 6\n4",  "expected_output": "4",  "is_hidden": 0, "ordinal": 2},
            {"input": "1\n1\n1",                  "expected_output": "1",  "is_hidden": 0, "ordinal": 3},
            {"input": "5\n5 4 3 2 1\n1",         "expected_output": "5",  "is_hidden": 1, "ordinal": 4},
            {"input": "5\n5 4 3 2 1\n5",         "expected_output": "1",  "is_hidden": 1, "ordinal": 5},
            {"input": "4\n-1 -2 -3 -4\n2",       "expected_output": "-2", "is_hidden": 1, "ordinal": 6},
        ],
    },

    # ── RECURSION & BACKTRACKING (1 task) ─────────────────────────────────────
    {
        "id": "task-climb-009",
        "title": "Climbing Stairs",
        "description": (
            "N steps to reach the top. Each time climb 1 or 2 steps. "
            "How many distinct ways to reach the top?\n\n"
            "Input: single integer N\n"
            "Output: number of distinct ways"
        ),
        "difficulty": "easy", "skill_id": "skill-recursion-001",
        "time_limit_ms": 2000, "memory_limit_kb": 131072, "is_published": 1,
        "test_cases": [
            {"input": "1",  "expected_output": "1",          "is_hidden": 0, "ordinal": 1},
            {"input": "2",  "expected_output": "2",          "is_hidden": 0, "ordinal": 2},
            {"input": "3",  "expected_output": "3",          "is_hidden": 0, "ordinal": 3},
            {"input": "5",  "expected_output": "8",          "is_hidden": 1, "ordinal": 4},
            {"input": "10", "expected_output": "89",         "is_hidden": 1, "ordinal": 5},
            {"input": "20", "expected_output": "10946",      "is_hidden": 1, "ordinal": 6},
            {"input": "45", "expected_output": "1836311903", "is_hidden": 1, "ordinal": 7},
        ],
    },

    # ── GRAPHS & TREES (3 tasks) ──────────────────────────────────────────────
    {
        "id": "task-bfs-010",
        "title": "BFS — Shortest Path",
        "description": (
            "Find shortest path (edge count) from node 0 to node N-1 in an undirected graph.\n\n"
            "Input: Line 1='N M', next M lines='u v'\n"
            "Output: shortest path length or -1"
        ),
        "difficulty": "medium", "skill_id": "skill-graphs-001",
        "time_limit_ms": 2000, "memory_limit_kb": 131072, "is_published": 1,
        "test_cases": [
            {"input": "4 4\n0 1\n1 2\n2 3\n0 3",           "expected_output": "1",  "is_hidden": 0, "ordinal": 1},
            {"input": "3 1\n0 1",                           "expected_output": "-1", "is_hidden": 0, "ordinal": 2},
            {"input": "2 1\n0 1",                           "expected_output": "1",  "is_hidden": 0, "ordinal": 3},
            {"input": "5 4\n0 1\n1 2\n2 3\n3 4",           "expected_output": "4",  "is_hidden": 1, "ordinal": 4},
            {"input": "6 6\n0 1\n0 2\n1 3\n2 3\n3 4\n4 5", "expected_output": "4",  "is_hidden": 1, "ordinal": 5},
            {"input": "4 3\n0 1\n1 2\n0 2",               "expected_output": "-1", "is_hidden": 1, "ordinal": 6},
        ],
    },
    {
        "id": "task-treeh-011",
        "title": "Tree Height",
        "description": (
            "Given a rooted tree as a parent array (-1=root), find its height.\n\n"
            "Input: Line 1=N, Line 2=parent array\n"
            "Output: height (max edges from root to leaf)"
        ),
        "difficulty": "medium", "skill_id": "skill-graphs-001",
        "time_limit_ms": 2000, "memory_limit_kb": 131072, "is_published": 1,
        "test_cases": [
            {"input": "5\n-1 0 0 1 1",     "expected_output": "2", "is_hidden": 0, "ordinal": 1},
            {"input": "1\n-1",             "expected_output": "0", "is_hidden": 0, "ordinal": 2},
            {"input": "4\n-1 0 1 2",       "expected_output": "3", "is_hidden": 0, "ordinal": 3},
            {"input": "3\n-1 0 0",         "expected_output": "1", "is_hidden": 1, "ordinal": 4},
            {"input": "7\n-1 0 0 1 1 2 2", "expected_output": "2", "is_hidden": 1, "ordinal": 5},
            {"input": "6\n-1 0 1 2 3 4",   "expected_output": "5", "is_hidden": 1, "ordinal": 6},
        ],
    },
    {
        "id": "task-numislands-012",
        "title": "Number of Islands",
        "description": (
            "Given an M×N grid of '1's (land) and '0's (water), count the islands.\n"
            "An island is formed by adjacent land cells (horizontal/vertical only).\n\n"
            "Input: Line 1='M N', next M lines=grid rows (space-separated)\n"
            "Output: number of islands"
        ),
        "difficulty": "hard", "skill_id": "skill-graphs-001",
        "time_limit_ms": 3000, "memory_limit_kb": 131072, "is_published": 1,
        "test_cases": [
            {"input": "4 5\n1 1 1 1 0\n1 1 0 1 0\n1 1 0 0 0\n0 0 0 0 0", "expected_output": "1", "is_hidden": 0, "ordinal": 1},
            {"input": "4 5\n1 1 0 0 0\n1 1 0 0 0\n0 0 1 0 0\n0 0 0 1 1", "expected_output": "3", "is_hidden": 0, "ordinal": 2},
            {"input": "1 1\n1",                                             "expected_output": "1", "is_hidden": 0, "ordinal": 3},
            {"input": "1 1\n0",                                             "expected_output": "0", "is_hidden": 1, "ordinal": 4},
            {"input": "3 3\n1 0 1\n0 0 0\n1 0 1",                          "expected_output": "4", "is_hidden": 1, "ordinal": 5},
            {"input": "3 4\n1 1 0 0\n0 1 0 0\n0 0 1 1",                    "expected_output": "2", "is_hidden": 1, "ordinal": 6},
        ],
    },
]


def seed():
    run_migrations()
    db = get_db()
    seeded = skipped = 0

    for task in list(TASKS):
        if db.execute("SELECT id FROM tasks WHERE id = ?", (task["id"],)).fetchone():
            print(f"  skip  {task['id']}")
            skipped += 1
            continue

        test_cases = task.pop("test_cases")
        tc = dict(task)

        with transaction(db):
            db.execute(
                "INSERT INTO tasks (id,title,description,difficulty,skill_id,time_limit_ms,memory_limit_kb,is_published) VALUES (?,?,?,?,?,?,?,?)",
                (tc["id"], tc["title"], tc["description"], tc["difficulty"], tc["skill_id"], tc["time_limit_ms"], tc["memory_limit_kb"], tc["is_published"]),
            )
            for row in test_cases:
                db.execute(
                    "INSERT INTO test_cases (id,task_id,input,expected_output,is_hidden,comparison_mode,ordinal) VALUES (?,?,?,?,?,'exact',?)",
                    (str(uuid.uuid4()), tc["id"], row["input"], row["expected_output"], row["is_hidden"], row["ordinal"]),
                )

        print(f"  seeded {tc['id']} — {tc['title']} ({len(test_cases)} test cases)")
        task["test_cases"] = test_cases
        seeded += 1

    print(f"\n  Total: {seeded} seeded, {skipped} skipped")


if __name__ == "__main__":
    print("Seeding problems...")
    seed()
    print("Done.")
