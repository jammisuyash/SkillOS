"""
db/seed_tasks.py — 30 real problems, 6 skills, hidden test cases.
Run: python -m skillos.db.seed_tasks
Idempotent.
"""

import uuid
from skillos.db.database import get_db, transaction
from skillos.db.migrations import run_migrations

TASKS = [

    # ── Python Fundamentals ───────────────────────────────────────────────────
    {
        "id": "task-double-001", "title": "Double the Number", "difficulty": "easy",
        "skill_id": "skill-python-001", "time_limit_ms": 2000, "memory_limit_kb": 131072,
        "description": "Read an integer N from stdin. Print N * 2.\n\nInput: single integer N\nOutput: N * 2",
        "test_cases": [
            {"input": "5",           "expected": "10",          "hidden": 0, "ord": 1},
            {"input": "0",           "expected": "0",           "hidden": 0, "ord": 2},
            {"input": "-3",          "expected": "-6",          "hidden": 1, "ord": 3},
            {"input": "100",         "expected": "200",         "hidden": 1, "ord": 4},
            {"input": "1000000000",  "expected": "2000000000",  "hidden": 1, "ord": 5},
        ],
    },
    {
        "id": "task-fizzbuzz-001", "title": "FizzBuzz", "difficulty": "easy",
        "skill_id": "skill-python-001", "time_limit_ms": 2000, "memory_limit_kb": 131072,
        "description": "Print 1 to N. Multiples of 3: 'Fizz'. Multiples of 5: 'Buzz'. Both: 'FizzBuzz'.\n\nInput: integer N\nOutput: N lines",
        "test_cases": [
            {"input": "5",  "expected": "1\n2\nFizz\n4\nBuzz", "hidden": 0, "ord": 1},
            {"input": "15", "expected": "1\n2\nFizz\n4\nBuzz\nFizz\n7\n8\nFizz\nBuzz\n11\nFizz\n13\n14\nFizzBuzz", "hidden": 0, "ord": 2},
            {"input": "1",  "expected": "1",   "hidden": 1, "ord": 3},
            {"input": "3",  "expected": "1\n2\nFizz", "hidden": 1, "ord": 4},
            {"input": "20", "expected": "1\n2\nFizz\n4\nBuzz\nFizz\n7\n8\nFizz\nBuzz\n11\nFizz\n13\n14\nFizzBuzz\n16\n17\nFizz\n19\nBuzz", "hidden": 1, "ord": 5},
        ],
    },
    {
        "id": "task-palindrome-001", "title": "Palindrome Check", "difficulty": "easy",
        "skill_id": "skill-python-001", "time_limit_ms": 2000, "memory_limit_kb": 131072,
        "description": "Is the string a palindrome?\n\nInput: one string\nOutput: YES or NO",
        "test_cases": [
            {"input": "racecar", "expected": "YES", "hidden": 0, "ord": 1},
            {"input": "hello",   "expected": "NO",  "hidden": 0, "ord": 2},
            {"input": "a",       "expected": "YES", "hidden": 1, "ord": 3},
            {"input": "abba",    "expected": "YES", "hidden": 1, "ord": 4},
            {"input": "abcde",   "expected": "NO",  "hidden": 1, "ord": 5},
        ],
    },
    {
        "id": "task-sumdigits-001", "title": "Sum of Digits", "difficulty": "easy",
        "skill_id": "skill-python-001", "time_limit_ms": 2000, "memory_limit_kb": 131072,
        "description": "Compute the sum of digits of a non-negative integer.\n\nInput: integer N\nOutput: digit sum",
        "test_cases": [
            {"input": "123",        "expected": "6",  "hidden": 0, "ord": 1},
            {"input": "0",          "expected": "0",  "hidden": 0, "ord": 2},
            {"input": "999",        "expected": "27", "hidden": 1, "ord": 3},
            {"input": "1000",       "expected": "1",  "hidden": 1, "ord": 4},
            {"input": "9876543210", "expected": "45", "hidden": 1, "ord": 5},
        ],
    },
    {
        "id": "task-twosum-002", "title": "Two Sum", "difficulty": "medium",
        "skill_id": "skill-python-001", "time_limit_ms": 2000, "memory_limit_kb": 131072,
        "description": "Return indices of two numbers that add up to target.\n\nInput: line1=N, line2=N ints, line3=target\nOutput: two indices, smaller first",
        "test_cases": [
            {"input": "4\n2 7 11 15\n9",      "expected": "0 1", "hidden": 0, "ord": 1},
            {"input": "3\n3 2 4\n6",           "expected": "1 2", "hidden": 0, "ord": 2},
            {"input": "2\n3 3\n6",             "expected": "0 1", "hidden": 1, "ord": 3},
            {"input": "5\n1 4 8 7 3\n11",      "expected": "1 3", "hidden": 1, "ord": 4},
            {"input": "4\n-1 -2 -3 -4\n-7",   "expected": "2 3", "hidden": 1, "ord": 5},
        ],
    },

    # ── Arrays & Strings ──────────────────────────────────────────────────────
    {
        "id": "task-maxsubarray-001", "title": "Maximum Subarray", "difficulty": "medium",
        "skill_id": "skill-arrays-001", "time_limit_ms": 2000, "memory_limit_kb": 131072,
        "description": "Find the contiguous subarray with the largest sum.\n\nInput: line1=N, line2=N ints\nOutput: max sum",
        "test_cases": [
            {"input": "9\n-2 1 -3 4 -1 2 1 -5 4", "expected": "6",  "hidden": 0, "ord": 1},
            {"input": "1\n1",                       "expected": "1",  "hidden": 0, "ord": 2},
            {"input": "4\n5 4 -1 7",               "expected": "15", "hidden": 1, "ord": 3},
            {"input": "3\n-1 -2 -3",               "expected": "-1", "hidden": 1, "ord": 4},
            {"input": "5\n1 2 3 4 5",              "expected": "15", "hidden": 1, "ord": 5},
        ],
    },
    {
        "id": "task-anagram-001", "title": "Valid Anagram", "difficulty": "easy",
        "skill_id": "skill-arrays-001", "time_limit_ms": 2000, "memory_limit_kb": 131072,
        "description": "Is string t an anagram of string s?\n\nInput: line1=s, line2=t\nOutput: true or false",
        "test_cases": [
            {"input": "anagram\nnagaram", "expected": "true",  "hidden": 0, "ord": 1},
            {"input": "rat\ncar",         "expected": "false", "hidden": 0, "ord": 2},
            {"input": "a\na",             "expected": "true",  "hidden": 1, "ord": 3},
            {"input": "ab\nba",           "expected": "true",  "hidden": 1, "ord": 4},
            {"input": "abcd\nabce",       "expected": "false", "hidden": 1, "ord": 5},
        ],
    },
    {
        "id": "task-reversearray-001", "title": "Reverse an Array", "difficulty": "easy",
        "skill_id": "skill-arrays-001", "time_limit_ms": 2000, "memory_limit_kb": 131072,
        "description": "Reverse an array of integers.\n\nInput: line1=N, line2=N ints\nOutput: reversed array space-separated",
        "test_cases": [
            {"input": "5\n1 2 3 4 5",  "expected": "5 4 3 2 1", "hidden": 0, "ord": 1},
            {"input": "1\n42",          "expected": "42",         "hidden": 0, "ord": 2},
            {"input": "3\n7 8 9",       "expected": "9 8 7",      "hidden": 1, "ord": 3},
            {"input": "4\n-1 0 1 2",   "expected": "2 1 0 -1",   "hidden": 1, "ord": 4},
            {"input": "2\n100 200",    "expected": "200 100",     "hidden": 1, "ord": 5},
        ],
    },
    {
        "id": "task-longestword-001", "title": "Longest Word", "difficulty": "easy",
        "skill_id": "skill-arrays-001", "time_limit_ms": 2000, "memory_limit_kb": 131072,
        "description": "Find the longest word in a sentence. On tie, return the first.\n\nInput: one line sentence\nOutput: longest word",
        "test_cases": [
            {"input": "the quick brown fox",   "expected": "quick",       "hidden": 0, "ord": 1},
            {"input": "hello world",            "expected": "hello",       "hidden": 0, "ord": 2},
            {"input": "I love programming",     "expected": "programming", "hidden": 1, "ord": 3},
            {"input": "cat bat rat",            "expected": "cat",         "hidden": 1, "ord": 4},
            {"input": "a bb ccc dddd",          "expected": "dddd",        "hidden": 1, "ord": 5},
        ],
    },
    {
        "id": "task-countvowels-001", "title": "Count Vowels", "difficulty": "easy",
        "skill_id": "skill-arrays-001", "time_limit_ms": 2000, "memory_limit_kb": 131072,
        "description": "Count vowels (a,e,i,o,u) in a string. Case insensitive.\n\nInput: one string\nOutput: count",
        "test_cases": [
            {"input": "Hello World",       "expected": "3", "hidden": 0, "ord": 1},
            {"input": "rhythm",            "expected": "0", "hidden": 0, "ord": 2},
            {"input": "aeiou",             "expected": "5", "hidden": 1, "ord": 3},
            {"input": "AEIOU",             "expected": "5", "hidden": 1, "ord": 4},
            {"input": "The quick brown fox","expected": "5", "hidden": 1, "ord": 5},
        ],
    },

    # ── Sorting & Searching ───────────────────────────────────────────────────
    {
        "id": "task-binarysearch-001", "title": "Binary Search", "difficulty": "easy",
        "skill_id": "skill-sorting-001", "time_limit_ms": 2000, "memory_limit_kb": 131072,
        "description": "Find target in sorted array. Return index or -1.\n\nInput: line1=N, line2=sorted ints, line3=target\nOutput: index or -1",
        "test_cases": [
            {"input": "6\n-1 0 3 5 9 12\n9",  "expected": "4",  "hidden": 0, "ord": 1},
            {"input": "6\n-1 0 3 5 9 12\n2",  "expected": "-1", "hidden": 0, "ord": 2},
            {"input": "1\n5\n5",               "expected": "0",  "hidden": 1, "ord": 3},
            {"input": "5\n1 3 5 7 9\n7",       "expected": "3",  "hidden": 1, "ord": 4},
            {"input": "4\n2 4 6 8\n5",         "expected": "-1", "hidden": 1, "ord": 5},
        ],
    },
    {
        "id": "task-sortarray-001", "title": "Sort an Array", "difficulty": "medium",
        "skill_id": "skill-sorting-001", "time_limit_ms": 3000, "memory_limit_kb": 131072,
        "description": "Sort integers ascending. Implement your own sort — do not use sort() or sorted().\n\nInput: line1=N, line2=N ints\nOutput: sorted array space-separated",
        "test_cases": [
            {"input": "5\n5 2 4 6 1",     "expected": "1 2 4 5 6", "hidden": 0, "ord": 1},
            {"input": "3\n3 1 2",          "expected": "1 2 3",     "hidden": 0, "ord": 2},
            {"input": "1\n42",             "expected": "42",         "hidden": 1, "ord": 3},
            {"input": "4\n-3 1 -1 2",     "expected": "-3 -1 1 2", "hidden": 1, "ord": 4},
            {"input": "5\n1 1 1 1 1",     "expected": "1 1 1 1 1", "hidden": 1, "ord": 5},
        ],
    },
    {
        "id": "task-kthlargest-001", "title": "Kth Largest Element", "difficulty": "medium",
        "skill_id": "skill-sorting-001", "time_limit_ms": 2000, "memory_limit_kb": 131072,
        "description": "Find the kth largest element in an unsorted array.\n\nInput: line1=N, line2=N ints, line3=k\nOutput: kth largest element",
        "test_cases": [
            {"input": "6\n3 2 1 5 6 4\n2", "expected": "5", "hidden": 0, "ord": 1},
            {"input": "5\n3 2 3 1 2\n4",   "expected": "2", "hidden": 0, "ord": 2},
            {"input": "1\n1\n1",            "expected": "1", "hidden": 1, "ord": 3},
            {"input": "3\n5 3 8\n1",        "expected": "8", "hidden": 1, "ord": 4},
            {"input": "4\n7 10 4 3\n3",     "expected": "4", "hidden": 1, "ord": 5},
        ],
    },
    {
        "id": "task-mergesorted-001", "title": "Merge Two Sorted Arrays", "difficulty": "easy",
        "skill_id": "skill-sorting-001", "time_limit_ms": 2000, "memory_limit_kb": 131072,
        "description": "Merge two sorted arrays into one sorted array.\n\nInput: line1=N, line2=N ints, line3=M, line4=M ints\nOutput: merged sorted array",
        "test_cases": [
            {"input": "3\n1 2 3\n3\n2 5 6",  "expected": "1 2 2 3 5 6",  "hidden": 0, "ord": 1},
            {"input": "1\n1\n1\n2",            "expected": "1 2",          "hidden": 0, "ord": 2},
            {"input": "3\n1 3 5\n3\n2 4 6",   "expected": "1 2 3 4 5 6",  "hidden": 1, "ord": 3},
            {"input": "2\n-2 -1\n2\n0 1",     "expected": "-2 -1 0 1",    "hidden": 1, "ord": 4},
            {"input": "3\n1 2 3\n0\n",         "expected": "1 2 3",        "hidden": 1, "ord": 5},
        ],
    },
    {
        "id": "task-findpeak-001", "title": "Find Peak Element", "difficulty": "medium",
        "skill_id": "skill-sorting-001", "time_limit_ms": 2000, "memory_limit_kb": 131072,
        "description": "A peak element is greater than its neighbors. Find any peak and print its index.\n\nInput: line1=N, line2=N distinct ints\nOutput: index of any peak",
        "test_cases": [
            {"input": "3\n1 2 3",    "expected": "2", "hidden": 0, "ord": 1},
            {"input": "5\n1 2 1 3 5","expected": "4", "hidden": 0, "ord": 2},
            {"input": "1\n1",         "expected": "0", "hidden": 1, "ord": 3},
            {"input": "2\n2 1",       "expected": "0", "hidden": 1, "ord": 4},
            {"input": "4\n3 4 3 2",  "expected": "1", "hidden": 1, "ord": 5},
        ],
    },

    # ── Hash Maps & Sets ──────────────────────────────────────────────────────
    {
        "id": "task-wordcount-001", "title": "Word Frequency", "difficulty": "easy",
        "skill_id": "skill-hashmaps-001", "time_limit_ms": 2000, "memory_limit_kb": 131072,
        "description": "Count frequency of each word. Print alphabetically as 'word count'.\n\nInput: one sentence\nOutput: one line per word alphabetically",
        "test_cases": [
            {"input": "the cat sat on the mat", "expected": "cat 1\nmat 1\non 1\nsat 1\nthe 2", "hidden": 0, "ord": 1},
            {"input": "a a a",                  "expected": "a 3",                               "hidden": 0, "ord": 2},
            {"input": "hello world",             "expected": "hello 1\nworld 1",                 "hidden": 1, "ord": 3},
            {"input": "go go go stop go",        "expected": "go 4\nstop 1",                     "hidden": 1, "ord": 4},
            {"input": "one",                     "expected": "one 1",                            "hidden": 1, "ord": 5},
        ],
    },
    {
        "id": "task-firstunique-001", "title": "First Unique Character", "difficulty": "easy",
        "skill_id": "skill-hashmaps-001", "time_limit_ms": 2000, "memory_limit_kb": 131072,
        "description": "Find index of first non-repeating character. Print -1 if none.\n\nInput: one lowercase string\nOutput: index or -1",
        "test_cases": [
            {"input": "leetcode",     "expected": "0",  "hidden": 0, "ord": 1},
            {"input": "loveleetcode", "expected": "2",  "hidden": 0, "ord": 2},
            {"input": "aabb",         "expected": "-1", "hidden": 1, "ord": 3},
            {"input": "z",            "expected": "0",  "hidden": 1, "ord": 4},
            {"input": "aabbc",        "expected": "4",  "hidden": 1, "ord": 5},
        ],
    },
    {
        "id": "task-groupanagrams-001", "title": "Group Anagrams", "difficulty": "medium",
        "skill_id": "skill-hashmaps-001", "time_limit_ms": 2000, "memory_limit_kb": 131072,
        "description": "Group words that are anagrams. Print each group sorted, groups sorted by first word.\n\nInput: line1=N, next N lines=words\nOutput: one group per line",
        "test_cases": [
            {"input": "6\neat\ntea\ntan\nate\nnat\nbat", "expected": "ate eat tea\nbat\nnat tan", "hidden": 0, "ord": 1},
            {"input": "1\na",                             "expected": "a",                        "hidden": 0, "ord": 2},
            {"input": "2\nab\nba",                        "expected": "ab ba",                    "hidden": 1, "ord": 3},
            {"input": "3\nabc\nbca\nfoo",                 "expected": "abc bca\nfoo",              "hidden": 1, "ord": 4},
        ],
    },
    {
        "id": "task-twostrings-001", "title": "Common Characters", "difficulty": "easy",
        "skill_id": "skill-hashmaps-001", "time_limit_ms": 2000, "memory_limit_kb": 131072,
        "description": "Find characters in both strings. Print sorted alphabetically, no duplicates, one per line.\n\nInput: line1=s, line2=t\nOutput: common chars sorted",
        "test_cases": [
            {"input": "hello\nworld",  "expected": "l\no",  "hidden": 0, "ord": 1},
            {"input": "abc\ndef",      "expected": "",       "hidden": 0, "ord": 2},
            {"input": "aab\nab",       "expected": "a\nb",  "hidden": 1, "ord": 3},
            {"input": "python\njava",  "expected": "a",     "hidden": 1, "ord": 4},
            {"input": "zzzz\nz",       "expected": "z",     "hidden": 1, "ord": 5},
        ],
    },
    {
        "id": "task-subarraysum-001", "title": "Subarray Sum Equals K", "difficulty": "hard",
        "skill_id": "skill-hashmaps-001", "time_limit_ms": 2000, "memory_limit_kb": 131072,
        "description": "Count subarrays that sum to exactly K.\n\nInput: line1=N, line2=N ints, line3=K\nOutput: count",
        "test_cases": [
            {"input": "5\n1 1 1 1 1\n2",   "expected": "4", "hidden": 0, "ord": 1},
            {"input": "3\n1 2 3\n3",        "expected": "2", "hidden": 0, "ord": 2},
            {"input": "1\n1\n1",            "expected": "1", "hidden": 1, "ord": 3},
            {"input": "4\n1 -1 1 -1\n0",   "expected": "4", "hidden": 1, "ord": 4},
            {"input": "5\n3 4 7 2 -3\n7",  "expected": "4", "hidden": 1, "ord": 5},
        ],
    },

    # ── Recursion & Backtracking ───────────────────────────────────────────────
    {
        "id": "task-fibonacci-001", "title": "Fibonacci Number", "difficulty": "easy",
        "skill_id": "skill-recursion-001", "time_limit_ms": 2000, "memory_limit_kb": 131072,
        "description": "Return the Nth Fibonacci number. F(0)=0, F(1)=1.\n\nInput: integer N (0-30)\nOutput: F(N)",
        "test_cases": [
            {"input": "0",  "expected": "0",     "hidden": 0, "ord": 1},
            {"input": "1",  "expected": "1",     "hidden": 0, "ord": 2},
            {"input": "10", "expected": "55",    "hidden": 1, "ord": 3},
            {"input": "20", "expected": "6765",  "hidden": 1, "ord": 4},
            {"input": "30", "expected": "832040","hidden": 1, "ord": 5},
        ],
    },
    {
        "id": "task-climbstairs-001", "title": "Climbing Stairs", "difficulty": "easy",
        "skill_id": "skill-recursion-001", "time_limit_ms": 2000, "memory_limit_kb": 131072,
        "description": "Climb 1 or 2 steps at a time. How many distinct ways to reach N steps?\n\nInput: integer N (1-45)\nOutput: number of ways",
        "test_cases": [
            {"input": "2",  "expected": "2",          "hidden": 0, "ord": 1},
            {"input": "3",  "expected": "3",          "hidden": 0, "ord": 2},
            {"input": "1",  "expected": "1",          "hidden": 1, "ord": 3},
            {"input": "5",  "expected": "8",          "hidden": 1, "ord": 4},
            {"input": "10", "expected": "89",         "hidden": 1, "ord": 5},
            {"input": "45", "expected": "1836311903", "hidden": 1, "ord": 6},
        ],
    },
    {
        "id": "task-power-001", "title": "Power Function", "difficulty": "medium",
        "skill_id": "skill-recursion-001", "time_limit_ms": 2000, "memory_limit_kb": 131072,
        "description": "Compute x^n using recursion.\n\nInput: line1=x, line2=n (0 <= n <= 20)\nOutput: x raised to n",
        "test_cases": [
            {"input": "2\n10", "expected": "1024",  "hidden": 0, "ord": 1},
            {"input": "3\n0",  "expected": "1",     "hidden": 0, "ord": 2},
            {"input": "5\n3",  "expected": "125",   "hidden": 1, "ord": 3},
            {"input": "1\n20", "expected": "1",     "hidden": 1, "ord": 4},
            {"input": "10\n4", "expected": "10000", "hidden": 1, "ord": 5},
        ],
    },
    {
        "id": "task-generateparens-001", "title": "Generate Parentheses", "difficulty": "medium",
        "skill_id": "skill-recursion-001", "time_limit_ms": 2000, "memory_limit_kb": 131072,
        "description": "Generate all valid combinations of N pairs of parentheses. Print one per line, sorted.\n\nInput: integer N (1-4)\nOutput: combinations sorted",
        "test_cases": [
            {"input": "1", "expected": "()",                                          "hidden": 0, "ord": 1},
            {"input": "2", "expected": "(())\n()()",                                 "hidden": 0, "ord": 2},
            {"input": "3", "expected": "((()))\n(()())\n(())()\n()(())\n()()()",     "hidden": 1, "ord": 3},
        ],
    },
    {
        "id": "task-subsets-001", "title": "All Subsets", "difficulty": "hard",
        "skill_id": "skill-recursion-001", "time_limit_ms": 2000, "memory_limit_kb": 131072,
        "description": "Generate all subsets of distinct integers. Print each sorted ascending, subsets sorted lexicographically. Empty subset = empty line.\n\nInput: line1=N, line2=N ints\nOutput: all subsets",
        "test_cases": [
            {"input": "2\n1 2",  "expected": "\n1\n1 2\n2",                                    "hidden": 0, "ord": 1},
            {"input": "1\n1",    "expected": "\n1",                                              "hidden": 0, "ord": 2},
            {"input": "3\n1 2 3","expected": "\n1\n1 2\n1 2 3\n1 3\n2\n2 3\n3",               "hidden": 1, "ord": 3},
        ],
    },

    # ── Graphs & Trees ─────────────────────────────────────────────────────────
    {
        "id": "task-bfs-001", "title": "BFS Shortest Path", "difficulty": "medium",
        "skill_id": "skill-graphs-001", "time_limit_ms": 2000, "memory_limit_kb": 131072,
        "description": "Shortest path (edges) from node 0 to node N-1 in undirected graph.\n\nInput: line1=N M, next M lines=edges u v\nOutput: length or -1",
        "test_cases": [
            {"input": "4 4\n0 1\n1 2\n2 3\n0 3",  "expected": "1", "hidden": 0, "ord": 1},
            {"input": "3 1\n0 1",                   "expected": "-1","hidden": 0, "ord": 2},
            {"input": "2 1\n0 1",                  "expected": "1", "hidden": 1, "ord": 3},
            {"input": "5 4\n0 1\n1 2\n2 3\n3 4",  "expected": "4", "hidden": 1, "ord": 4},
            {"input": "4 3\n0 1\n0 2\n2 3",       "expected": "2", "hidden": 1, "ord": 5},
        ],
    },
    {
        "id": "task-connected-001", "title": "Connected Components", "difficulty": "medium",
        "skill_id": "skill-graphs-001", "time_limit_ms": 2000, "memory_limit_kb": 131072,
        "description": "Count connected components in an undirected graph.\n\nInput: line1=N M, next M lines=edges\nOutput: number of components",
        "test_cases": [
            {"input": "5 4\n0 1\n1 2\n3 4\n4 3",  "expected": "2", "hidden": 0, "ord": 1},
            {"input": "5 0",                         "expected": "5", "hidden": 0, "ord": 2},
            {"input": "3 3\n0 1\n1 2\n0 2",        "expected": "1", "hidden": 1, "ord": 3},
            {"input": "4 2\n0 1\n2 3",             "expected": "2", "hidden": 1, "ord": 4},
            {"input": "1 0",                         "expected": "1", "hidden": 1, "ord": 5},
        ],
    },
    {
        "id": "task-treeh-001", "title": "Tree Height", "difficulty": "medium",
        "skill_id": "skill-graphs-001", "time_limit_ms": 2000, "memory_limit_kb": 131072,
        "description": "Find height of binary tree given as parent array (-1=root).\n\nInput: line1=N, line2=parent values\nOutput: height",
        "test_cases": [
            {"input": "5\n-1 0 0 1 1", "expected": "2", "hidden": 0, "ord": 1},
            {"input": "1\n-1",          "expected": "0", "hidden": 0, "ord": 2},
            {"input": "3\n-1 0 1",     "expected": "2", "hidden": 1, "ord": 3},
            {"input": "4\n-1 0 0 2",   "expected": "2", "hidden": 1, "ord": 4},
            {"input": "2\n-1 0",       "expected": "1", "hidden": 1, "ord": 5},
        ],
    },
    {
        "id": "task-cyclicgraph-001", "title": "Detect Cycle in Graph", "difficulty": "hard",
        "skill_id": "skill-graphs-001", "time_limit_ms": 2000, "memory_limit_kb": 131072,
        "description": "Does the undirected graph contain a cycle?\n\nInput: line1=N M, next M lines=edges\nOutput: YES or NO",
        "test_cases": [
            {"input": "3 3\n0 1\n1 2\n2 0",     "expected": "YES", "hidden": 0, "ord": 1},
            {"input": "3 2\n0 1\n1 2",            "expected": "NO",  "hidden": 0, "ord": 2},
            {"input": "1 0",                       "expected": "NO",  "hidden": 1, "ord": 3},
            {"input": "4 4\n0 1\n1 2\n2 3\n3 1", "expected": "YES", "hidden": 1, "ord": 4},
            {"input": "4 3\n0 1\n1 2\n2 3",      "expected": "NO",  "hidden": 1, "ord": 5},
        ],
    },
    {
        "id": "task-levelorder-001", "title": "Level Order Traversal", "difficulty": "hard",
        "skill_id": "skill-graphs-001", "time_limit_ms": 2000, "memory_limit_kb": 131072,
        "description": "Print level-order traversal of binary tree. Each level on new line.\n\nInput: line1=N, line2=level-order array (-1=null)\nOutput: one level per line",
        "test_cases": [
            {"input": "7\n3 9 20 -1 -1 15 7", "expected": "3\n9 20\n15 7", "hidden": 0, "ord": 1},
            {"input": "1\n1",                   "expected": "1",             "hidden": 0, "ord": 2},
            {"input": "3\n1 2 3",              "expected": "1\n2 3",        "hidden": 1, "ord": 3},
            {"input": "5\n1 2 3 4 5",          "expected": "1\n2 3\n4 5",   "hidden": 1, "ord": 4},
        ],
    },
]


def seed():
    run_migrations()
    db = get_db()
    seeded = skipped = 0

    for task in TASKS:
        existing = db.execute("SELECT id FROM tasks WHERE id = ?", (task["id"],)).fetchone()
        if existing:
            skipped += 1
            continue

        test_cases = task.pop("test_cases")
        with transaction(db):
            db.execute(
                "INSERT INTO tasks (id, title, description, difficulty, skill_id, time_limit_ms, memory_limit_kb, is_published) VALUES (?,?,?,?,?,?,?,1)",
                (task["id"], task["title"], task["description"], task["difficulty"],
                 task["skill_id"], task["time_limit_ms"], task["memory_limit_kb"]),
            )
            for tc in test_cases:
                db.execute(
                    "INSERT INTO test_cases (id, task_id, input, expected_output, is_hidden, comparison_mode, ordinal) VALUES (?,?,?,?,?,'exact',?)",
                    (str(uuid.uuid4()), task["id"], tc["input"], tc["expected"], tc["hidden"], tc["ord"]),
                )
        print(f"  seeded  {task['title']:35} ({len(test_cases)} tests)")
        seeded += 1

    print(f"\n  {seeded} tasks seeded, {skipped} already existed.")


if __name__ == "__main__":
    print("Seeding task library...")
    seed()
    print("Done.")

# Alias for main.py compatibility
seed_tasks = seed

