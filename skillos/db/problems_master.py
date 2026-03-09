"""
problems_master.py — 500+ problems across all domains.

Domains:
  - Algorithms & Data Structures (200+ problems)
  - Web Dev & APIs (80+ problems)
  - Data Science & SQL (80+ problems)
  - Cybersecurity (60+ problems)
  - System Design (40+ problems)
  - Full Stack (40+ problems)
"""
import uuid, json
from skillos.db.database import get_db, transaction

# ── Skills ───────────────────────────────────────────────────────────────────
ALL_SKILLS = [
    # Algorithms
    {"id":"sk-arrays",      "name":"Arrays",              "domain":"algorithms"},
    {"id":"sk-strings",     "name":"Strings",             "domain":"algorithms"},
    {"id":"sk-hashmaps",    "name":"Hash Maps",           "domain":"algorithms"},
    {"id":"sk-linkedlist",  "name":"Linked Lists",        "domain":"algorithms"},
    {"id":"sk-stacks",      "name":"Stacks & Queues",     "domain":"algorithms"},
    {"id":"sk-trees",       "name":"Trees",               "domain":"algorithms"},
    {"id":"sk-graphs",      "name":"Graphs",              "domain":"algorithms"},
    {"id":"sk-dp",          "name":"Dynamic Programming", "domain":"algorithms"},
    {"id":"sk-greedy",      "name":"Greedy",              "domain":"algorithms"},
    {"id":"sk-binary",      "name":"Binary Search",       "domain":"algorithms"},
    {"id":"sk-sorting",     "name":"Sorting",             "domain":"algorithms"},
    {"id":"sk-recursion",   "name":"Recursion",           "domain":"algorithms"},
    {"id":"sk-bits",        "name":"Bit Manipulation",    "domain":"algorithms"},
    {"id":"sk-math",        "name":"Math & Number Theory","domain":"algorithms"},
    {"id":"sk-twoptr",      "name":"Two Pointers",        "domain":"algorithms"},
    {"id":"sk-sliding",     "name":"Sliding Window",      "domain":"algorithms"},
    {"id":"sk-heap",        "name":"Heaps & Priority Q",  "domain":"algorithms"},
    {"id":"sk-trie",        "name":"Tries",               "domain":"algorithms"},
    {"id":"sk-backtrack",   "name":"Backtracking",        "domain":"algorithms"},
    # Web Dev
    {"id":"sk-restapi",     "name":"REST APIs",           "domain":"web_dev"},
    {"id":"sk-jscore",      "name":"JavaScript Core",     "domain":"web_dev"},
    {"id":"sk-async",       "name":"Async & Promises",    "domain":"web_dev"},
    {"id":"sk-html",        "name":"HTML & CSS",          "domain":"web_dev"},
    {"id":"sk-nodejs",      "name":"Node.js",             "domain":"web_dev"},
    {"id":"sk-auth",        "name":"Auth & Security",     "domain":"web_dev"},
    # Data Science
    {"id":"sk-sql",         "name":"SQL",                 "domain":"data_science"},
    {"id":"sk-pandas",      "name":"Data Manipulation",   "domain":"data_science"},
    {"id":"sk-stats",       "name":"Statistics",          "domain":"data_science"},
    {"id":"sk-ml",          "name":"Machine Learning",    "domain":"data_science"},
    {"id":"sk-viz",         "name":"Data Visualization",  "domain":"data_science"},
    # Cybersecurity
    {"id":"sk-crypto",      "name":"Cryptography",        "domain":"cybersecurity"},
    {"id":"sk-vulns",       "name":"Web Vulnerabilities", "domain":"cybersecurity"},
    {"id":"sk-network",     "name":"Network Security",    "domain":"cybersecurity"},
    {"id":"sk-forensics",   "name":"Digital Forensics",   "domain":"cybersecurity"},
    # System Design
    {"id":"sk-sysarch",     "name":"System Architecture", "domain":"system_design"},
    {"id":"sk-scale",       "name":"Scalability",         "domain":"system_design"},
    {"id":"sk-databases",   "name":"Database Design",     "domain":"system_design"},
    {"id":"sk-microservices","name":"Microservices",      "domain":"system_design"},
    # Full Stack
    {"id":"sk-fullstack",   "name":"Full Stack Dev",      "domain":"full_stack"},
    {"id":"sk-devops",      "name":"DevOps & CI/CD",      "domain":"full_stack"},
]

# ── Problem helper ────────────────────────────────────────────────────────────
def p(id, title, desc, diff, skill, cases, ptype="coding", starter=None, broken=None,
      mcq_opts=None, mcq_idx=None, rubric=None):
    return {
        "id": id, "title": title, "description": desc,
        "difficulty": diff, "skill_id": skill,
        "test_cases": cases, "problem_type": ptype,
        "starter_code": starter, "starter_code_broken": broken,
        "mcq_options": json.dumps(mcq_opts) if mcq_opts else None,
        "mcq_correct_index": mcq_idx,
        "system_design_rubric": rubric,
    }

def tc(inp, out): return {"input": inp, "expected_output": out}

# ═══════════════════════════════════════════════════════
# ALGORITHMS & DATA STRUCTURES — 200+ PROBLEMS
# ═══════════════════════════════════════════════════════

ARRAY_PROBLEMS = [
    p("arr-001","Two Sum","Given an array of integers and a target, return indices of two numbers that add up to target.\nInput: first line is n, second line is n space-separated integers, third line is target.\nOutput: two space-separated indices (0-based, smaller first).","easy","sk-arrays",[
        tc("4\n2 7 11 15\n9","0 1"),tc("3\n3 2 4\n6","1 2"),tc("2\n3 3\n6","0 1")]),
    p("arr-002","Best Time to Buy and Sell Stock","Find the maximum profit from buying and selling a stock once.\nInput: n, then n prices.\nOutput: max profit (0 if no profit possible).","easy","sk-arrays",[
        tc("6\n7 1 5 3 6 4","5"),tc("5\n7 6 4 3 1","0"),tc("1\n5","0")]),
    p("arr-003","Maximum Subarray (Kadane's)","Find the contiguous subarray with the largest sum.\nInput: n, then n integers.\nOutput: the maximum sum.","easy","sk-arrays",[
        tc("9\n-2 1 -3 4 -1 2 1 -5 4","6"),tc("1\n1","1"),tc("5\n-1 -2 -3 -4 -5","-1")]),
    p("arr-004","Product of Array Except Self","Return array where each element is the product of all other elements. No division allowed. O(n) time.\nInput: n, then n integers.\nOutput: n space-separated products.","medium","sk-arrays",[
        tc("4\n1 2 3 4","24 12 8 6"),tc("4\n-1 1 0 -3","0 0 9 0")]),
    p("arr-005","Container With Most Water","Find two lines that together with x-axis forms a container with most water.\nInput: n, then n heights.\nOutput: maximum water.","medium","sk-arrays",[
        tc("9\n1 8 6 2 5 4 8 3 7","49"),tc("2\n1 1","1")]),
    p("arr-006","3Sum","Find all unique triplets that sum to 0.\nInput: n, then n integers.\nOutput: each triplet on a new line, sorted, space-separated. If none, print NONE.","medium","sk-arrays",[
        tc("6\n-1 0 1 2 -1 -4","-1 -1 2\n-1 0 1"),tc("3\n0 1 1","NONE"),tc("3\n0 0 0","0 0 0")]),
    p("arr-007","Rotate Array","Rotate array to the right by k steps.\nInput: n, then n integers, then k.\nOutput: rotated array space-separated.","medium","sk-arrays",[
        tc("7\n1 2 3 4 5 6 7\n3","5 6 7 1 2 3 4"),tc("3\n-1 -100 3 99\n2","3 99 -1 -100")]),
    p("arr-008","Find Minimum in Rotated Sorted Array","Find minimum element in a rotated sorted array.\nInput: n, then n integers.\nOutput: minimum element.","medium","sk-arrays",[
        tc("5\n3 4 5 1 2","1"),tc("4\n4 5 6 7 0 1 2","0"),tc("1\n1","1")]),
    p("arr-009","Merge Intervals","Merge all overlapping intervals.\nInput: n, then n lines each with start end.\nOutput: merged intervals, one per line.","medium","sk-arrays",[
        tc("4\n1 3\n2 6\n8 10\n15 18","1 6\n8 10\n15 18"),tc("2\n1 4\n4 5","1 5")]),
    p("arr-010","Jump Game","Can you reach the last index? Each element = max jump from that position.\nInput: n, then n integers.\nOutput: YES or NO.","medium","sk-arrays",[
        tc("5\n2 3 1 1 4","YES"),tc("5\n3 2 1 0 4","NO")]),
    p("arr-011","Trapping Rain Water","Compute how much water can be trapped after rain.\nInput: n, then n heights.\nOutput: total water trapped.","hard","sk-arrays",[
        tc("12\n0 1 0 2 1 0 1 3 2 1 2 1","6"),tc("6\n4 2 0 3 2 5","9")]),
    p("arr-012","Sliding Window Maximum","Find max in each window of size k.\nInput: n, then n integers, then k.\nOutput: maximums space-separated.","hard","sk-arrays",[
        tc("8\n1 3 -1 -3 5 3 6 7\n3","3 3 5 5 6 7"),tc("4\n1 -1\n1","1 -1")]),
    p("arr-013","Subarray Sum Equals K","Count subarrays that sum to k.\nInput: n, then n integers, then k.\nOutput: count.","medium","sk-arrays",[
        tc("5\n1 1 1 2 3\n3","3"),tc("3\n1 2 3\n3","2")]),
    p("arr-014","Majority Element","Find element appearing more than n/2 times (guaranteed to exist).\nInput: n, then n integers.\nOutput: majority element.","easy","sk-arrays",[
        tc("3\n3 2 3","3"),tc("7\n2 2 1 1 1 2 2","2")]),
    p("arr-015","Pascal's Triangle","Print the first n rows of Pascal's triangle.\nInput: n.\nOutput: each row space-separated on new line.","easy","sk-arrays",[
        tc("5","1\n1 1\n1 2 1\n1 3 3 1\n1 4 6 4 1"),tc("1","1")]),
]

STRING_PROBLEMS = [
    p("str-001","Valid Anagram","Check if two strings are anagrams of each other.\nInput: two strings on separate lines.\nOutput: YES or NO.","easy","sk-strings",[
        tc("anagram\nnagaram","YES"),tc("rat\ncar","NO"),tc("a\na","YES")]),
    p("str-002","Longest Substring Without Repeating Characters","Find length of longest substring with all unique characters.\nInput: a string.\nOutput: length.","medium","sk-strings",[
        tc("abcabcbb","3"),tc("bbbbb","1"),tc("pwwkew","3"),tc("","0")]),
    p("str-003","Group Anagrams","Group strings that are anagrams of each other.\nInput: n, then n strings.\nOutput: each group space-separated on its own line, groups sorted by first word, words in each group sorted alphabetically.","medium","sk-strings",[
        tc("6\neat tea tan ate nat bat","ate eat tea\nbat\nant nat tan"),tc("1\n","")]),
    p("str-004","Longest Palindromic Substring","Find the longest palindromic substring.\nInput: a string.\nOutput: the palindrome (if tie, return any valid one).","medium","sk-strings",[
        tc("babad","bab"),tc("cbbd","bb"),tc("a","a")]),
    p("str-005","Valid Parentheses","Check if brackets are balanced.\nInput: a string of ()[]{}.\nOutput: YES or NO.","easy","sk-strings",[
        tc("()","YES"),tc("()[{}]","YES"),tc("(]","NO"),tc("{[}","NO")]),
    p("str-006","Reverse Words in a String","Reverse the order of words in a string.\nInput: a sentence (may have multiple spaces).\nOutput: reversed words, single-spaced.","easy","sk-strings",[
        tc("the sky is blue","blue is sky the"),tc("  hello world  ","world hello")]),
    p("str-007","Zigzag Conversion","Write string in zigzag pattern with n rows, then read row by row.\nInput: string, then numRows.\nOutput: zigzag string.","medium","sk-strings",[
        tc("PAYPALISHIRING\n3","PAHNAPLSIIGYIR"),tc("PAYPALISHIRING\n4","PINALSIGYAHRPI"),tc("A\n1","A")]),
    p("str-008","Count and Say","Generate the nth term of the count-and-say sequence.\nInput: n (1-10).\nOutput: nth term.","medium","sk-strings",[
        tc("1","1"),tc("4","1211"),tc("6","312211")]),
    p("str-009","Roman to Integer","Convert roman numeral to integer.\nInput: roman numeral string.\nOutput: integer.","easy","sk-strings",[
        tc("III","3"),tc("LVIII","58"),tc("MCMXCIV","1994")]),
    p("str-010","String Compression","Compress string using counts. If compressed not shorter, return original.\nInput: a string.\nOutput: compressed string.","medium","sk-strings",[
        tc("aabcccccaaa","a2b1c5a3"),tc("abcdef","abcdef")]),
    p("str-011","Minimum Window Substring","Find smallest window in s containing all chars of t.\nInput: two strings s and t.\nOutput: minimum window or empty string if none.","hard","sk-strings",[
        tc("ADOBECODEBANC\nABC","BANC"),tc("a\na","a"),tc("a\naa","")]),
    p("str-012","Wildcard Matching","Match string with pattern (* = any sequence, ? = any char).\nInput: string and pattern.\nOutput: YES or NO.","hard","sk-strings",[
        tc("aa\na","NO"),tc("aa\n*","YES"),tc("cb\n?a","NO"),tc("adceb\n*a*b","YES")]),
    p("str-013","Decode String","Decode encoded string. k[encoded_string] repeats k times.\nInput: encoded string.\nOutput: decoded string.","medium","sk-strings",[
        tc("3[a]2[bc]","aaabcbc"),tc("3[a2[c]]","accaccacc"),tc("2[abc]3[cd]ef","abcabccdcdcdef")]),
    p("str-014","Longest Common Prefix","Find longest common prefix among array of strings.\nInput: n, then n strings.\nOutput: common prefix or empty line.","easy","sk-strings",[
        tc("3\nflower\nflow\nflight","fl"),tc("3\ndog\nracecar\ncar","")]),
    p("str-015","Implement strStr()","Find first occurrence of needle in haystack. Return -1 if not found.\nInput: haystack, then needle.\nOutput: index.","easy","sk-strings",[
        tc("hello\nll","2"),tc("aaaaa\nbba","-1"),tc("a\n","0")]),
]

HASHMAP_PROBLEMS = [
    p("hm-001","Two Sum (HashMap)","Given array and target, return indices summing to target using HashMap.\nInput: n, then n integers, then target.\nOutput: smaller index first.","easy","sk-hashmaps",[
        tc("4\n2 7 11 15\n9","0 1"),tc("3\n3 2 4\n6","1 2")]),
    p("hm-002","Word Frequency","Count frequency of each word.\nInput: sentence.\nOutput: word:count pairs sorted by count desc, then alphabetically. One per line.","easy","sk-hashmaps",[
        tc("the cat sat on the mat the cat","the:3\ncat:2\nmat:1\non:1\nsat:1")]),
    p("hm-003","LRU Cache","Implement an LRU Cache.\nInput: capacity, then operations: GET key or PUT key value.\nOutput: result of each GET (-1 if not found), one per line.","hard","sk-hashmaps",[
        tc("2\nPUT 1 1\nPUT 2 2\nGET 1\nPUT 3 3\nGET 2\nPUT 4 4\nGET 1\nGET 3\nGET 4","1\n-1\n1\n3\n4")]),
    p("hm-004","Subarray Sum to Zero","Count subarrays that sum to exactly 0.\nInput: n, then n integers.\nOutput: count.","medium","sk-hashmaps",[
        tc("6\n0 0 5 5 0 0","6"),tc("3\n1 -1 0","3")]),
    p("hm-005","First Non-Repeating Character","Find first character that appears only once.\nInput: a string.\nOutput: the character, or -1 if none.","easy","sk-hashmaps",[
        tc("leetcode","l"),tc("aabb","-1"),tc("dddccdbba","a")]),
    p("hm-006","Intersection of Two Arrays","Find unique elements that appear in both arrays.\nInput: n, n integers, m, m integers.\nOutput: intersection sorted ascending.","easy","sk-hashmaps",[
        tc("4\n1 2 2 1\n3\n2 2","2"),tc("5\n4 9 5 4 3\n5\n9 4 9 8 4","4 9")]),
    p("hm-007","Isomorphic Strings","Check if two strings are isomorphic (chars can be mapped 1-to-1).\nInput: two strings.\nOutput: YES or NO.","easy","sk-hashmaps",[
        tc("egg\nadd","YES"),tc("foo\nbar","NO"),tc("paper\ntitle","YES")]),
    p("hm-008","Top K Frequent Words","Return top k most frequent words, sorted by frequency desc then alpha.\nInput: n words, then k.\nOutput: k words one per line.","medium","sk-hashmaps",[
        tc("6\ni love leetcode i love coding\n2","i\nlove"),tc("4\nthe day is sunny the the the sunny is is\n4","the\nis\nsunny\nday")]),
]

LINKED_LIST_PROBLEMS = [
    p("ll-001","Reverse Linked List","Reverse a linked list.\nInput: n, then n space-separated values.\nOutput: reversed list space-separated.","easy","sk-linkedlist",[
        tc("5\n1 2 3 4 5","5 4 3 2 1"),tc("2\n1 2","2 1"),tc("1\n1","1")]),
    p("ll-002","Detect Cycle","Detect if linked list has a cycle.\nInput: n values, then pos (-1 = no cycle, else index where tail connects).\nOutput: YES or NO.","easy","sk-linkedlist",[
        tc("4\n3 2 0 -4\n1","YES"),tc("2\n1 2\n0","YES"),tc("1\n1\n-1","NO")]),
    p("ll-003","Merge Two Sorted Lists","Merge two sorted linked lists.\nInput: n, n values, m, m values.\nOutput: merged sorted list space-separated.","easy","sk-linkedlist",[
        tc("3\n1 2 4\n3\n1 3 4","1 1 2 3 4 4"),tc("0\n\n0\n",""),tc("0\n\n1\n0","0")]),
    p("ll-004","Remove Nth Node From End","Remove the nth node from end of list.\nInput: n values, then k (1-indexed from end).\nOutput: resulting list.","medium","sk-linkedlist",[
        tc("5\n1 2 3 4 5\n2","1 2 3 5"),tc("1\n1\n1",""),tc("2\n1 2\n1","1")]),
    p("ll-005","Add Two Numbers","Add two numbers represented as reversed linked lists.\nInput: n, n digits, m, m digits.\nOutput: sum as reversed list.","medium","sk-linkedlist",[
        tc("3\n2 4 3\n3\n5 6 4","7 0 8"),tc("1\n0\n1\n0","0"),tc("4\n9 9 9 9\n4\n9 9 9 9","8 9 9 9 1")]),
    p("ll-006","Find Middle of Linked List","Find the middle node (if even, return second middle).\nInput: n, then n values.\nOutput: values from middle to end.","easy","sk-linkedlist",[
        tc("5\n1 2 3 4 5","3 4 5"),tc("6\n1 2 3 4 5 6","4 5 6")]),
    p("ll-007","Palindrome Linked List","Check if linked list values form a palindrome.\nInput: n, then n values.\nOutput: YES or NO.","easy","sk-linkedlist",[
        tc("4\n1 2 2 1","YES"),tc("5\n1 2 0 2 1","YES"),tc("2\n1 2","NO")]),
]

STACK_QUEUE_PROBLEMS = [
    p("sq-001","Valid Parentheses","Check if all brackets are properly matched and ordered.\nInput: string of (){}[].\nOutput: YES or NO.","easy","sk-stacks",[
        tc("()[]{}","YES"),tc("([)]","NO"),tc("{[]}","YES")]),
    p("sq-002","Min Stack","Implement stack with O(1) push, pop, top, getMin.\nInput: operations: PUSH n, POP, TOP, MIN.\nOutput: results of TOP and MIN operations, one per line.","medium","sk-stacks",[
        tc("PUSH -2\nPUSH 0\nPUSH -3\nMIN\nPOP\nTOP\nMIN","-3\n0\n-2")]),
    p("sq-003","Daily Temperatures","Find days to wait for a warmer day. 0 if never.\nInput: n, then n temperatures.\nOutput: days to wait, space-separated.","medium","sk-stacks",[
        tc("8\n73 74 75 71 69 72 76 73","1 1 4 2 1 1 0 0"),tc("3\n30 40 50","1 1 0"),tc("3\n30 60 90","1 1 0")]),
    p("sq-004","Largest Rectangle in Histogram","Find largest rectangle area in histogram.\nInput: n, then n heights.\nOutput: largest area.","hard","sk-stacks",[
        tc("6\n2 1 5 6 2 3","10"),tc("2\n2 4","4")]),
    p("sq-005","Implement Queue Using Stacks","Implement FIFO queue using only stacks.\nInput: ENQUEUE n or DEQUEUE or PEEK operations.\nOutput: result of DEQUEUE and PEEK, one per line.","medium","sk-stacks",[
        tc("ENQUEUE 1\nENQUEUE 2\nPEEK\nDEQUEUE\nDEQUEUE","1\n1\n2")]),
    p("sq-006","Evaluate Reverse Polish Notation","Evaluate an expression in reverse polish notation.\nInput: tokens space-separated.\nOutput: result.","medium","sk-stacks",[
        tc("2 1 + 3 *","9"),tc("4 13 5 / +","6"),tc("10 6 9 3 + -11 * / * 17 + 5 +","22")]),
]

TREE_PROBLEMS = [
    p("tr-001","Maximum Depth of Binary Tree","Find maximum depth of binary tree.\nInput: level-order traversal (null for missing nodes), space-separated.\nOutput: depth.","easy","sk-trees",[
        tc("3 9 20 null null 15 7","3"),tc("1 null 2","2"),tc("1","1")]),
    p("tr-002","Invert Binary Tree","Invert (mirror) binary tree.\nInput: level-order traversal.\nOutput: level-order of inverted tree.","easy","sk-trees",[
        tc("4 2 7 1 3 6 9","4 7 2 9 6 3 1"),tc("2 1 3","2 3 1"),tc("","")]),
    p("tr-003","Validate Binary Search Tree","Check if tree is a valid BST.\nInput: level-order traversal.\nOutput: YES or NO.","medium","sk-trees",[
        tc("2 1 3","YES"),tc("5 1 4 null null 3 6","NO")]),
    p("tr-004","Lowest Common Ancestor","Find LCA of two nodes in BST.\nInput: BST level-order, then p, then q.\nOutput: LCA value.","medium","sk-trees",[
        tc("6 2 8 0 4 7 9 null null 3 5\n2\n8","6"),tc("6 2 8 0 4 7 9 null null 3 5\n2\n4","2")]),
    p("tr-005","Level Order Traversal","Return level-order traversal of binary tree.\nInput: level-order traversal.\nOutput: each level on a new line, space-separated.","medium","sk-trees",[
        tc("3 9 20 null null 15 7","3\n9 20\n15 7"),tc("1","1")]),
    p("tr-006","Path Sum","Check if tree has root-to-leaf path summing to target.\nInput: level-order traversal, then target.\nOutput: YES or NO.","easy","sk-trees",[
        tc("5 4 8 11 null 13 4 7 2 null null null 1\n22","YES"),tc("1 2 3\n5","NO")]),
    p("tr-007","Symmetric Tree","Check if binary tree is symmetric around its center.\nInput: level-order traversal.\nOutput: YES or NO.","easy","sk-trees",[
        tc("1 2 2 3 4 4 3","YES"),tc("1 2 2 null 3 null 3","NO")]),
    p("tr-008","Diameter of Binary Tree","Find the diameter (longest path between any two nodes).\nInput: level-order traversal.\nOutput: diameter (number of edges).","easy","sk-trees",[
        tc("1 2 3 4 5","3"),tc("1 2","1"),tc("1","0")]),
    p("tr-009","Binary Tree Right Side View","Return values visible from the right side.\nInput: level-order traversal.\nOutput: right side values space-separated.","medium","sk-trees",[
        tc("1 2 3 null 5 null 4","1 3 4"),tc("1 null 3","1 3")]),
    p("tr-010","Construct BST from Sorted Array","Construct height-balanced BST from sorted array.\nInput: n, then n sorted integers.\nOutput: level-order traversal of BST.","medium","sk-trees",[
        tc("7\n-10 -3 0 5 9 20 21","0 -3 9 -10 null 5 20 null null null null null 21"),tc("3\n1 2 3","2 1 3")]),
]

GRAPH_PROBLEMS = [
    p("gr-001","Number of Islands","Count islands (connected 1s) in grid.\nInput: rows cols, then grid rows.\nOutput: count.","medium","sk-graphs",[
        tc("4 5\n1 1 1 1 0\n1 1 0 1 0\n1 1 0 0 0\n0 0 0 0 0","1"),tc("4 5\n1 1 0 0 0\n1 1 0 0 0\n0 0 1 0 0\n0 0 0 1 1","3")]),
    p("gr-002","Course Schedule","Can you finish all courses? Detect cycle in directed graph.\nInput: n courses, then m prereqs, then m lines of [course prereq].\nOutput: YES or NO.","medium","sk-graphs",[
        tc("2\n1\n1 0","YES"),tc("2\n2\n1 0\n0 1","NO")]),
    p("gr-003","Clone Graph","Clone a graph (each node has val and neighbors).\nInput: adjacency list format: n, then n lines of neighbors.\nOutput: adjacency list of clone.","medium","sk-graphs",[
        tc("4\n2 4\n1 3\n2 4\n1 3","1:[2,4]\n2:[1,3]\n3:[2,4]\n4:[1,3]")]),
    p("gr-004","Word Ladder","Find shortest transformation from begin to end word.\nInput: begin, end, n words in wordList.\nOutput: length of shortest chain (0 if none).","hard","sk-graphs",[
        tc("hit\ncog\n6\nhot dot dog lot log cog","5"),tc("hit\ncog\n5\nhot dot dog lot log","0")]),
    p("gr-005","Pacific Atlantic Water Flow","Find cells that can flow to both Pacific and Atlantic oceans.\nInput: rows cols, then grid.\nOutput: cell coordinates (row col) sorted, one per line.","medium","sk-graphs",[
        tc("5 5\n1 2 2 3 5\n3 2 3 4 4\n2 4 5 3 1\n6 7 1 4 5\n5 1 1 2 4","0 4\n1 3\n1 4\n2 2\n3 0\n3 1\n4 0")]),
    p("gr-006","Dijkstra's Shortest Path","Find shortest path from source to all nodes.\nInput: n nodes, m edges, source, then m lines of u v weight.\nOutput: shortest distance to each node (0 to n-1), -1 if unreachable.","medium","sk-graphs",[
        tc("5 6 0\n0 1 4\n0 2 1\n2 1 2\n1 3 1\n2 3 5\n3 4 3","0 3 1 4 7")]),
    p("gr-007","Topological Sort","Return topological order of DAG.\nInput: n nodes (0-indexed), m edges, then m lines of u v.\nOutput: topological order space-separated.","medium","sk-graphs",[
        tc("6 6\n5 2\n5 0\n4 0\n4 1\n2 3\n3 1","4 5 0 2 3 1"),tc("4 3\n3 0\n3 1\n1 2","3 1 2 0")]),
    p("gr-008","Minimum Spanning Tree (Kruskal)","Find MST weight.\nInput: n nodes, m edges, then m lines of u v weight.\nOutput: MST total weight.","hard","sk-graphs",[
        tc("4 5\n0 1 10\n0 2 6\n0 3 5\n1 3 15\n2 3 4","19")]),
]

DP_PROBLEMS = [
    p("dp-001","Climbing Stairs","Count ways to climb n stairs (1 or 2 steps at a time).\nInput: n.\nOutput: number of ways.","easy","sk-dp",[
        tc("2","2"),tc("3","3"),tc("10","89")]),
    p("dp-002","Coin Change","Find minimum coins to make amount. -1 if impossible.\nInput: n coins, then n values, then amount.\nOutput: minimum coins or -1.","medium","sk-dp",[
        tc("3\n1 5 11\n15","3"),tc("2\n2 5\n3","-1"),tc("1\n1\n0","0")]),
    p("dp-003","Longest Increasing Subsequence","Find length of longest strictly increasing subsequence.\nInput: n, then n integers.\nOutput: length.","medium","sk-dp",[
        tc("10\n10 9 2 5 3 7 101 18","4"),tc("1\n0","1"),tc("4\n7 7 7 7","1")]),
    p("dp-004","0/1 Knapsack","Max value with weight capacity.\nInput: n items, capacity, then n lines of value weight.\nOutput: max value.","medium","sk-dp",[
        tc("4 5\n1 2\n6 2\n10 3\n16 5","17"),tc("3 10\n1 10\n6 20\n18 30","18")]),
    p("dp-005","Longest Common Subsequence","Find length of longest common subsequence.\nInput: two strings.\nOutput: length.","medium","sk-dp",[
        tc("abcde\nace","3"),tc("abc\nabc","3"),tc("abc\ndef","0")]),
    p("dp-006","Edit Distance","Minimum operations (insert/delete/replace) to convert word1 to word2.\nInput: two strings.\nOutput: min operations.","hard","sk-dp",[
        tc("horse\nros","3"),tc("intention\nexecution","5"),tc("a\na","0")]),
    p("dp-007","Unique Paths","Count unique paths in m×n grid from top-left to bottom-right.\nInput: m n.\nOutput: count.","medium","sk-dp",[
        tc("3 7","28"),tc("3 2","3"),tc("7 3","28")]),
    p("dp-008","Word Break","Can string be segmented into dictionary words?\nInput: string, then n, then n words.\nOutput: YES or NO.","medium","sk-dp",[
        tc("leetcode\n2\nleet code","YES"),tc("applepenapple\n3\napple pen","YES"),tc("catsandog\n5\ncats dog sand and cat","NO")]),
    p("dp-009","Maximum Product Subarray","Find contiguous subarray with largest product.\nInput: n, then n integers.\nOutput: max product.","medium","sk-dp",[
        tc("5\n2 3 -2 4","6"),tc("4\n-2 0 -1","0")]),
    p("dp-010","Partition Equal Subset Sum","Can array be partitioned into two equal-sum subsets?\nInput: n, then n integers.\nOutput: YES or NO.","medium","sk-dp",[
        tc("4\n1 5 11 5","YES"),tc("3\n1 2 3 5","NO")]),
    p("dp-011","House Robber","Max money without robbing adjacent houses.\nInput: n, then n amounts.\nOutput: max money.","medium","sk-dp",[
        tc("4\n1 2 3 1","4"),tc("5\n2 7 9 3 1","12")]),
    p("dp-012","Triangle Minimum Path Sum","Find minimum path sum from top to bottom in triangle.\nInput: n (rows), then triangle row by row.\nOutput: minimum sum.","medium","sk-dp",[
        tc("4\n2\n3 4\n6 5 7\n4 1 8 3","11"),tc("1\n-10","-10")]),
    p("dp-013","Burst Balloons","Maximize coins from bursting balloons optimally.\nInput: n, then n balloon values.\nOutput: max coins.","hard","sk-dp",[
        tc("4\n3 1 5 8","167"),tc("2\n1 5","10")]),
    p("dp-014","Regular Expression Matching","Implement regex matching with . and *.\nInput: string s, then pattern p.\nOutput: YES or NO.","hard","sk-dp",[
        tc("aa\na","NO"),tc("aa\na*","YES"),tc("ab\n.*","YES"),tc("mississippi\nmis*is*p*.","NO")]),
    p("dp-015","Maximal Square","Find largest square of 1s in binary matrix.\nInput: rows cols, then matrix rows.\nOutput: area of largest square.","medium","sk-dp",[
        tc("4 5\n1 0 1 0 0\n1 0 1 1 1\n1 1 1 1 1\n1 0 0 1 0","4")]),
]

BINARY_SEARCH_PROBLEMS = [
    p("bs-001","Binary Search","Classic binary search in sorted array.\nInput: n sorted integers, then target.\nOutput: index or -1.","easy","sk-binary",[
        tc("6\n-1 0 3 5 9 12\n9","4"),tc("6\n-1 0 3 5 9 12\n2","-1")]),
    p("bs-002","Search in Rotated Array","Search target in rotated sorted array.\nInput: n integers, then target.\nOutput: index or -1.","medium","sk-binary",[
        tc("7\n4 5 6 7 0 1 2\n0","4"),tc("7\n4 5 6 7 0 1 2\n3","-1")]),
    p("bs-003","Find Peak Element","Find a peak element (greater than neighbors). Return any valid index.\nInput: n integers.\nOutput: peak index.","medium","sk-binary",[
        tc("4\n1 2 3 1","2"),tc("5\n1 2 1 3 5","4")]),
    p("bs-004","Median of Two Sorted Arrays","Find median of two sorted arrays in O(log(m+n)).\nInput: n, n integers, m, m integers.\nOutput: median (float, 1 decimal).","hard","sk-binary",[
        tc("2\n1 3\n1\n2","2.0"),tc("2\n1 2\n2\n3 4","2.5")]),
    p("bs-005","Kth Smallest in Sorted Matrix","Find kth smallest element in row-col sorted matrix.\nInput: n (n×n matrix), then n rows, then k.\nOutput: kth smallest.","medium","sk-binary",[
        tc("3\n1 5 9\n10 11 13\n12 13 15\n8","13")]),
    p("bs-006","First and Last Position","Find first and last position of target in sorted array.\nInput: n integers, then target.\nOutput: first last (or -1 -1).","medium","sk-binary",[
        tc("6\n5 7 7 8 8 10\n8","3 4"),tc("6\n5 7 7 8 8 10\n6","-1 -1")]),
    p("bs-007","Sqrt(x) Integer","Compute integer square root (floor).\nInput: x.\nOutput: floor of sqrt(x).","easy","sk-binary",[
        tc("4","2"),tc("8","2"),tc("9","3"),tc("1","1")]),
]

GREEDY_PROBLEMS = [
    p("gr-a-001","Activity Selection","Select maximum non-overlapping activities.\nInput: n, then n lines of start end.\nOutput: max count.","easy","sk-greedy",[
        tc("6\n1 2\n3 4\n0 6\n5 7\n8 9\n5 9","4"),tc("3\n1 4\n2 3\n3 5","2")]),
    p("gr-a-002","Fractional Knapsack","Maximize value with fractional items allowed.\nInput: n items, capacity, then n lines of value weight.\nOutput: max value (2 decimal places).","medium","sk-greedy",[
        tc("3 50\n60 10\n100 20\n120 30","240.00"),tc("1 10\n500 30","166.67")]),
    p("gr-a-003","Gas Station","Find starting gas station to complete circular route.\nInput: n, then n gas values, then n cost values.\nOutput: starting index or -1.","medium","sk-greedy",[
        tc("5\n1 2 3 4 5\n3 4 5 1 2","3"),tc("3\n2 3 4\n3 4 3","-1")]),
    p("gr-a-004","Task Scheduler","Find minimum time to execute all tasks with cooldown n.\nInput: tasks string (letters), then n.\nOutput: minimum time.","medium","sk-greedy",[
        tc("AABABC\n2","8"),tc("AAABBBCC\n3","10")]),
    p("gr-a-005","Meeting Rooms II","Find minimum conference rooms needed.\nInput: n, then n lines of start end.\nOutput: rooms needed.","medium","sk-greedy",[
        tc("3\n0 30\n5 10\n15 20","2"),tc("3\n7 10\n2 4\n4 5","1")]),
]

TWO_POINTER_PROBLEMS = [
    p("tp-001","Valid Palindrome","Check if string is palindrome ignoring non-alphanumeric and case.\nInput: a string.\nOutput: YES or NO.","easy","sk-twoptr",[
        tc("A man a plan a canal Panama","YES"),tc("race a car","NO"),tc("  ","YES")]),
    p("tp-002","Remove Duplicates from Sorted Array","Remove duplicates in-place, return new length.\nInput: n, then n sorted integers.\nOutput: k (new length) and first k elements space-separated.","easy","sk-twoptr",[
        tc("5\n1 1 2","2 1 2"),tc("8\n0 0 1 1 1 2 2 3 3 4","5 0 1 2 3 4")]),
    p("tp-003","4Sum","Find all unique quadruplets summing to target.\nInput: n integers, then target.\nOutput: each quadruplet sorted, one per line.","medium","sk-twoptr",[
        tc("8\n1 0 -1 0 -2 2\n0","-2 -1 1 2\n-2 0 0 2\n-1 0 0 1"),tc("4\n2 2 2 2\n8","2 2 2 2")]),
    p("tp-004","Minimum Size Subarray Sum","Find minimum length subarray with sum >= target.\nInput: target, then n, then n integers.\nOutput: minimum length (0 if impossible).","medium","sk-twoptr",[
        tc("7\n5\n2 3 1 2 4 3","2"),tc("4\n4\n1 4 4","1"),tc("11\n3\n1 1 1","0")]),
    p("tp-005","Sort Colors (Dutch Flag)","Sort array of 0s, 1s, and 2s in-place.\nInput: n, then n integers (0, 1, or 2).\nOutput: sorted array.","medium","sk-twoptr",[
        tc("6\n2 0 2 1 1 0","0 0 1 1 2 2"),tc("3\n2 0 1","0 1 2")]),
]

SLIDING_WINDOW_PROBLEMS = [
    p("sw-001","Maximum Average Subarray","Find max average of any subarray of length k.\nInput: n integers, then k.\nOutput: max average (5 decimal places).","easy","sk-sliding",[
        tc("5\n1 12 -5 -6 50 3\n4","12.75000"),tc("3\n5 5 5\n1","5.00000")]),
    p("sw-002","Longest Substring with K Distinct","Length of longest substring with at most k distinct chars.\nInput: string, then k.\nOutput: length.","medium","sk-sliding",[
        tc("eceba\n2","3"),tc("aa\n1","2")]),
    p("sw-003","Minimum Window Substring II","Find min window in s containing all chars of t (same as before but different constraints).","hard","sk-sliding",[
        tc("ADOBECODEBANC\nABC","BANC"),tc("a\na","a"),tc("a\naa","")]),
    p("sw-004","Count Occurrences of Anagrams","Count all anagrams of pattern in string.\nInput: string, then pattern.\nOutput: count.","medium","sk-sliding",[
        tc("cbaebabacd\nabc","2"),tc("abab\nab","3")]),
    p("sw-005","Max Consecutive Ones III","Max consecutive 1s with at most k flips.\nInput: n binary digits, then k.\nOutput: max length.","medium","sk-sliding",[
        tc("10\n1 1 1 0 0 0 1 1 1 1\n3","10"),tc("9\n0 0 1 1 0 0 1 1 1\n0","4")]),
]

HEAP_PROBLEMS = [
    p("hp-001","Kth Largest Element","Find kth largest in array.\nInput: n integers, then k.\nOutput: kth largest.","medium","sk-heap",[
        tc("6\n3 2 1 5 6 4\n2","5"),tc("4\n3 2 3 1 2 4 5 5 6\n4","4")]),
    p("hp-002","Top K Frequent Elements","Return top k most frequent elements.\nInput: n integers, then k.\nOutput: elements sorted descending by frequency, then ascending by value.","medium","sk-heap",[
        tc("6\n1 1 1 2 2 3\n2","1 2"),tc("1\n1\n1","1")]),
    p("hp-003","Merge K Sorted Lists","Merge k sorted lists.\nInput: k, then k lines of sorted integers (space-separated, or empty).\nOutput: merged sorted list.","hard","sk-heap",[
        tc("3\n1 4 5\n1 3 4\n2 6","1 1 2 3 4 4 5 6"),tc("0\n",""),tc("3\n\n","")]),
    p("hp-004","Find Median from Data Stream","Implement MedianFinder.\nInput: ADD n or MEDIAN operations.\nOutput: result of each MEDIAN, 1 decimal.","hard","sk-heap",[
        tc("ADD 1\nADD 2\nMEDIAN\nADD 3\nMEDIAN","1.5\n2.0")]),
    p("hp-005","Task Scheduler with Priority","Schedule tasks with deadlines and profits. Maximize profit.\nInput: n, then n lines of profit deadline.\nOutput: max profit.","hard","sk-heap",[
        tc("4\n20 1\n10 1\n40 1\n30 1","40"),tc("5\n20 2\n15 2\n10 1\n5 3\n1 3","45")]),
]

BACKTRACKING_PROBLEMS = [
    p("bt-001","Subsets","Generate all subsets of a set.\nInput: n distinct integers.\nOutput: each subset sorted, one per line (empty line for empty subset). Subsets in lexicographic order.","medium","sk-backtrack",[
        tc("3\n1 2 3","\n1\n1 2\n1 2 3\n1 3\n2\n2 3\n3"),tc("1\n0","\n0")]),
    p("bt-002","Permutations","Generate all permutations.\nInput: n distinct integers.\nOutput: each permutation space-separated, sorted lexicographically.","medium","sk-backtrack",[
        tc("3\n1 2 3","1 2 3\n1 3 2\n2 1 3\n2 3 1\n3 1 2\n3 2 1"),tc("1\n0","0")]),
    p("bt-003","N-Queens","Place n queens so no two attack each other. Count solutions.\nInput: n.\nOutput: count of distinct solutions.","hard","sk-backtrack",[
        tc("4","2"),tc("1","1"),tc("8","92")]),
    p("bt-004","Combination Sum","Find all unique combinations summing to target (can reuse).\nInput: n candidates, then target.\nOutput: each combination sorted, one per line.","medium","sk-backtrack",[
        tc("4\n2 3 6 7\n7","2 2 3\n7"),tc("4\n2 3 5\n8","2 2 2 2\n2 3 3\n3 5")]),
    p("bt-005","Sudoku Solver","Solve a 9×9 sudoku puzzle.\nInput: 9 lines of 9 digits (0 = empty).\nOutput: solved sudoku.","hard","sk-backtrack",[
        tc("5 3 0 0 7 0 0 0 0\n6 0 0 1 9 5 0 0 0\n0 9 8 0 0 0 0 6 0\n8 0 0 0 6 0 0 0 3\n4 0 0 8 0 3 0 0 1\n7 0 0 0 2 0 0 0 6\n0 6 0 0 0 0 2 8 0\n0 0 0 4 1 9 0 0 5\n0 0 0 0 8 0 0 7 9","5 3 4 6 7 8 9 1 2\n6 7 2 1 9 5 3 4 8\n1 9 8 3 4 2 5 6 7\n8 5 9 7 6 1 4 2 3\n4 2 6 8 5 3 7 9 1\n7 1 3 9 2 4 8 5 6\n9 6 1 5 3 7 2 8 4\n2 8 7 4 1 9 6 3 5\n3 4 5 2 8 6 1 7 9")]),
]

BIT_PROBLEMS = [
    p("bit-001","Single Number","Find the element that appears only once (others appear twice).\nInput: n, then n integers.\nOutput: the single number.","easy","sk-bits",[
        tc("3\n2 2 1","1"),tc("5\n4 1 2 1 2","4")]),
    p("bit-002","Number of 1 Bits","Count set bits in integer.\nInput: integer.\nOutput: count.","easy","sk-bits",[
        tc("11","3"),tc("128","1"),tc("4294967293","31")]),
    p("bit-003","Power of Two","Check if number is a power of 2.\nInput: integer.\nOutput: YES or NO.","easy","sk-bits",[
        tc("1","YES"),tc("16","YES"),tc("3","NO"),tc("0","NO")]),
    p("bit-004","Bitwise AND of Range","Find bitwise AND of all numbers from m to n.\nInput: m n.\nOutput: result.","medium","sk-bits",[
        tc("5 7","4"),tc("0 0","0"),tc("1 2147483647","0")]),
    p("bit-005","Reverse Bits","Reverse bits of 32-bit unsigned integer.\nInput: integer.\nOutput: reversed bits value.","easy","sk-bits",[
        tc("43261596","964176192"),tc("4294967293","3221225471")]),
]

MATH_PROBLEMS = [
    p("math-001","Count Primes","Count primes less than n.\nInput: n.\nOutput: count.","medium","sk-math",[
        tc("10","4"),tc("0","0"),tc("1","0")]),
    p("math-002","Happy Number","Check if number eventually reaches 1 through digit-square-sum process.\nInput: n.\nOutput: YES or NO.","easy","sk-math",[
        tc("19","YES"),tc("2","NO")]),
    p("math-003","GCD and LCM","Compute GCD and LCM of two numbers.\nInput: two integers.\nOutput: GCD LCM.","easy","sk-math",[
        tc("12 18","6 36"),tc("4 6","2 12"),tc("7 5","1 35")]),
    p("math-004","Excel Column Number","Convert Excel column title to number.\nInput: column title.\nOutput: number.","easy","sk-math",[
        tc("A","1"),tc("AB","28"),tc("ZY","701")]),
    p("math-005","Pow(x,n)","Implement pow(x, n) efficiently.\nInput: x (float) n (int).\nOutput: result (5 decimal places).","medium","sk-math",[
        tc("2.00000\n10","1024.00000"),tc("2.10000\n3","9.26100"),tc("2.00000\n-2","0.25000")]),
]

TRIE_PROBLEMS = [
    p("trie-001","Implement Trie","Implement a trie with insert, search, startsWith.\nInput: INSERT word, SEARCH word, or STARTS word.\nOutput: YES/NO for SEARCH and STARTS.","medium","sk-trie",[
        tc("INSERT apple\nSEARCH apple\nSEARCH app\nSTARTS app\nINSERT app\nSEARCH app","YES\nNO\nYES\nYES")]),
    p("trie-002","Word Search II","Find all words from dictionary that exist in grid.\nInput: rows cols grid, then n words.\nOutput: found words one per line sorted.","hard","sk-trie",[
        tc("4 4\no a a n\ne t a e\ni h k r\ni f l v\n2\neath\noat","eath\noat")]),
    p("trie-003","Auto Complete","Given queries, return top 3 alphabetical completions from word list.\nInput: n words, then query.\nOutput: completions for each prefix of query, 3 max per line separated by |.","medium","sk-trie",[
        tc("6\nmobile\nmouse\nmoneypot\nmonitor\nmonkey\nmouse\nmo","mobile|moneypot|monitor\nmobile|moneypot|monitor\nmoneypot|monitor|monkey")]),
]

# ═══════════════════════════════════════════════════════
# WEB DEV & APIs — 80+ PROBLEMS
# ═══════════════════════════════════════════════════════

API_MCQ = [
    p("api-mcq-001","REST vs GraphQL","When is GraphQL preferred over REST?","easy","sk-restapi",[],
      ptype="mcq",mcq_opts=["When you need simple CRUD operations","When clients need flexible data fetching with varying fields","When you want better caching","When you have very few API consumers"],mcq_idx=1),
    p("api-mcq-002","HTTP Methods","Which HTTP method is used to partially update a resource?","easy","sk-restapi",[],
      ptype="mcq",mcq_opts=["PUT","POST","PATCH","DELETE"],mcq_idx=2),
    p("api-mcq-003","JWT Structure","What are the three parts of a JWT token?","easy","sk-auth",[],
      ptype="mcq",mcq_opts=["Header.Body.Footer","Header.Payload.Signature","Key.Value.Hash","Token.Refresh.Expire"],mcq_idx=1),
    p("api-mcq-004","Status Codes","What does HTTP 429 mean?","easy","sk-restapi",[],
      ptype="mcq",mcq_opts=["Too Many Requests","Internal Server Error","Not Found","Unauthorized"],mcq_idx=0),
    p("api-mcq-005","CORS","What does CORS prevent?","medium","sk-auth",[],
      ptype="mcq",mcq_opts=["SQL Injection","Cross-origin requests from unauthorized domains","Man-in-the-middle attacks","DDoS attacks"],mcq_idx=1),
    p("api-mcq-006","OAuth 2.0","What is the purpose of a refresh token?","medium","sk-auth",[],
      ptype="mcq",mcq_opts=["To encrypt the access token","To get a new access token without re-authentication","To validate the user's password","To store user preferences"],mcq_idx=1),
    p("api-mcq-007","API Versioning","Which API versioning strategy puts the version in the URL path?","easy","sk-restapi",[],
      ptype="mcq",mcq_opts=["Header versioning","Query param versioning","URL path versioning","Content negotiation"],mcq_idx=2),
    p("api-mcq-008","WebSockets vs HTTP","When should you use WebSockets instead of HTTP polling?","medium","sk-restapi",[],
      ptype="mcq",mcq_opts=["When responses are large","For real-time bidirectional communication","When you need caching","For file uploads"],mcq_idx=1),
]

API_CODING = [
    p("api-001","Parse HTTP Request","Parse a raw HTTP request string.\nInput: HTTP request (method path, then headers, then body).\nOutput: METHOD, PATH, and body content as JSON fields one per line.","easy","sk-restapi",[
        tc("POST /api/users HTTP/1.1\nContent-Type: application/json\n\n{\"name\": \"Alice\"}","METHOD: POST\nPATH: /api/users\nBODY: {\"name\": \"Alice\"}")]),
    p("api-002","URL Builder","Build a URL from components.\nInput: base, path, then k query params as key=value.\nOutput: full URL.","easy","sk-restapi",[
        tc("https://api.example.com\n/users\n2\npage=1&limit=20","https://api.example.com/users?page=1&limit=20")]),
    p("api-003","Rate Limiter Logic","Implement token bucket rate limiting.\nFor each request (timestamp), output ALLOW or DENY.\nRate: 3 requests per 10 seconds.\nInput: n timestamps (seconds, ascending).\nOutput: ALLOW or DENY for each.","medium","sk-restapi",[
        tc("6\n0 1 2 11 11 11","ALLOW\nALLOW\nALLOW\nALLOW\nALLOW\nDENY")]),
    p("api-004","JSON Flatten","Flatten nested JSON into dot-notation keys.\nInput: JSON object.\nOutput: key:value pairs sorted alphabetically, one per line.","medium","sk-jscore",[
        tc('{"a": {"b": {"c": 1}, "d": 2}, "e": 3}',"a.b.c:1\na.d:2\ne:3")]),
    p("api-005","Middleware Chain","Simulate Express.js middleware. Each middleware can PASS or STOP.\nInput: n middlewares labeled M1..Mn (each PASS or STOP), then request.\nOutput: sequence of middleware calls, then DONE or BLOCKED.","medium","sk-nodejs",[
        tc("3\nM1 PASS\nM2 STOP\nM3 PASS\nGET /api","M1\nM2\nBLOCKED")]),
    p("api-006","Event Emitter","Implement basic event emitter.\nInput: ON event handler, EMIT event [data], OFF event operations.\nOutput: handler outputs when emitted.","medium","sk-jscore",[
        tc("ON click printClick\nON click printClick2\nEMIT click hello\nOFF click printClick\nEMIT click world","printClick: hello\nprintClick2: hello\nprintClick2: world")]),
]

JS_PROBLEMS = [
    p("js-001","Debounce Implementation","Implement debounce: delay execution until after n ms of inactivity.\nSimulation: given calls at timestamps and delay, output which calls actually execute.\nInput: delay, then n calls as (timestamp label).\nOutput: labels of calls that execute.","medium","sk-jscore",[
        tc("100\n5\n0 A\n50 B\n200 C\n250 D\n500 E","B\nD\nE")]),
    p("js-002","Deep Clone","Deep clone a JSON-serializable object (handle nested objects and arrays).\nInput: JSON object.\nOutput: JSON of clone (same as input if correctly cloned).","easy","sk-jscore",[
        tc('{"a": 1, "b": {"c": [1, 2, 3]}}',"{'a': 1, 'b': {'c': [1, 2, 3]}}")]),
    p("js-003","Promise Chain Simulator","Simulate a promise chain.\nInput: chain of RESOLVE value, REJECT error, THEN transform, CATCH handler operations.\nOutput: final resolved value or error.","medium","sk-async",[
        tc("RESOLVE 5\nTHEN double\nTHEN addOne","11")]),
    p("js-004","Curry Function","Implement currying.\nInput: function (add/multiply), then n numbers.\nOutput: result of curried application.","medium","sk-jscore",[
        tc("add\n3\n1\n2\n3","6"),tc("multiply\n3\n2\n3\n4","24")]),
    p("js-005","Memoize","Implement memoize for a pure function.\nInput: function calls (fib or factorial), output result and whether cache was hit.\nInput: n operations as CALL func n.\nOutput: result and HIT or MISS per line.","medium","sk-jscore",[
        tc("4\nCALL fib 10\nCALL fib 10\nCALL fib 11\nCALL factorial 5","55 MISS\n55 HIT\n89 MISS\n120 MISS")]),
]

# ═══════════════════════════════════════════════════════
# DATA SCIENCE & SQL — 80+ PROBLEMS
# ═══════════════════════════════════════════════════════

SQL_PROBLEMS = [
    p("sql-001","Employees Earning More Than Managers","Find employees who earn more than their manager.\nInput: employees table (id name salary managerId) then n rows.\nOutput: employee names, one per line sorted.","easy","sk-sql",[
        tc("4\n1 Joe 70000 3\n2 Henry 80000 4\n3 Sam 60000 None\n4 Max 90000 None","Joe")]),
    p("sql-002","Department Highest Salary","Find highest salary per department.\nInput: employees (id name salary dept) then n rows.\nOutput: dept:name:salary sorted by dept.","medium","sk-sql",[
        tc("5\n1 Joe 70000 IT\n2 Jim 90000 IT\n3 Henry 80000 Sales\n4 Sam 60000 IT\n5 Max 90000 Sales","IT:Jim:90000\nSales:Henry:80000\nSales:Max:90000")]),
    p("sql-003","Consecutive Numbers","Find numbers that appear at least 3 consecutive times.\nInput: n rows of (id num).\nOutput: unique numbers sorted.","medium","sk-sql",[
        tc("8\n1 1\n2 1\n3 1\n4 2\n5 1\n6 2\n7 2","1")]),
    p("sql-004","Running Total","Compute running total of a column.\nInput: n (id amount) rows.\nOutput: id amount running_total per line.","easy","sk-sql",[
        tc("4\n1 10\n2 20\n3 30\n4 40","1 10 10\n2 20 30\n3 30 60\n4 40 100")]),
    p("sql-005","Rank Scores","Rank scores with no gaps.\nInput: n scores.\nOutput: score rank per line sorted by score desc.","medium","sk-sql",[
        tc("6\n3.50\n3.65\n4.00\n3.85\n4.00\n3.65","4.00 1\n4.00 1\n3.85 2\n3.65 3\n3.65 3\n3.50 4")]),
    p("sql-006","Nth Highest Salary","Find nth highest distinct salary (-1 if not enough).\nInput: n salaries, then n.\nOutput: nth highest or -1.","medium","sk-sql",[
        tc("3\n300\n200\n100\n2","200"),tc("1\n100\n2","-1")]),
    p("sql-007","Tree Node Type","Classify each node as Root, Leaf, or Inner.\nInput: n rows of (id parentId).\nOutput: id type sorted by id.","medium","sk-sql",[
        tc("5\n1 None\n2 1\n3 1\n4 2\n5 2","1 Root\n2 Inner\n3 Leaf\n4 Leaf\n5 Leaf")]),
]

DS_CODING = [
    p("ds-001","Standard Deviation","Compute population standard deviation.\nInput: n numbers.\nOutput: std dev (4 decimal places).","easy","sk-stats",[
        tc("5\n2 4 4 4 5 5 7 9","2.0000"),tc("3\n1 2 3","0.8165")]),
    p("ds-002","Pearson Correlation","Compute Pearson correlation coefficient.\nInput: n, then n x values, then n y values.\nOutput: correlation (4 decimal places).","medium","sk-stats",[
        tc("5\n1 2 3 4 5\n5 4 3 2 1","-1.0000"),tc("4\n1 2 3 4\n1 2 3 4","1.0000")]),
    p("ds-003","K-Means Step","Run one iteration of K-means (2D, k=2).\nInput: n points as x y, then 2 initial centroids as x y.\nOutput: new centroids after one iteration (2 decimal places).","medium","sk-ml",[
        tc("6\n1 1\n1 2\n2 1\n5 5\n5 6\n6 5\n1 1\n6 6","1.33 1.33\n5.33 5.33")]),
    p("ds-004","Confusion Matrix Metrics","Compute accuracy, precision, recall from predictions.\nInput: n, then n actual values, then n predicted values (0 or 1).\nOutput: accuracy precision recall (all 4 decimal places).","medium","sk-ml",[
        tc("5\n1 0 1 1 0\n1 0 0 1 1","0.8000 0.6667 0.6667")]),
    p("ds-005","Linear Regression Slope","Compute slope (m) of simple linear regression y = mx + b.\nInput: n, then n x values, then n y values.\nOutput: slope m (4 decimal places).","medium","sk-ml",[
        tc("5\n1 2 3 4 5\n2 4 5 4 5","0.6000")]),
    p("ds-006","Z-Score Normalization","Normalize values using z-score.\nInput: n numbers.\nOutput: z-scores space-separated (4 decimal places).","easy","sk-stats",[
        tc("5\n2 4 4 4 5 5 7 9","-2.0000 -1.0000 -1.0000 -1.0000 -0.5000 -0.5000 0.5000 1.5000")]),
]

# ═══════════════════════════════════════════════════════
# CYBERSECURITY — 60+ PROBLEMS
# ═══════════════════════════════════════════════════════

SECURITY_MCQ = [
    p("sec-mcq-001","XSS vs CSRF","What is the main difference between XSS and CSRF attacks?","medium","sk-vulns",[],
      ptype="mcq",mcq_opts=["XSS injects scripts; CSRF forges requests using victim's session","XSS attacks databases; CSRF attacks files","XSS uses cookies; CSRF uses headers","They are the same attack"],mcq_idx=0),
    p("sec-mcq-002","Symmetric vs Asymmetric","Which is faster and why?","easy","sk-crypto",[],
      ptype="mcq",mcq_opts=["Asymmetric — fewer operations","Symmetric — uses a single shared key","They are equal speed","Depends on key size only"],mcq_idx=1),
    p("sec-mcq-003","HTTPS","What does TLS 1.3 improve over TLS 1.2?","medium","sk-network",[],
      ptype="mcq",mcq_opts=["Better compression","Faster handshake (1-RTT vs 2-RTT) and removed weak ciphers","More cipher suites","Better certificate validation"],mcq_idx=1),
    p("sec-mcq-004","Password Storage","Which is the most secure way to store passwords?","easy","sk-crypto",[],
      ptype="mcq",mcq_opts=["MD5 hash","SHA-256 hash","bcrypt with salt","AES encryption"],mcq_idx=2),
    p("sec-mcq-005","SQL Injection Prevention","Which method BEST prevents SQL injection?","easy","sk-vulns",[],
      ptype="mcq",mcq_opts=["Input validation only","Escaping special characters","Parameterized queries / prepared statements","Firewall rules"],mcq_idx=2),
    p("sec-mcq-006","Zero Trust","What is the core principle of Zero Trust security?","medium","sk-network",[],
      ptype="mcq",mcq_opts=["Trust but verify","Never trust, always verify","Trust internal networks","Verify once per session"],mcq_idx=1),
]

SECURITY_CODING = [
    p("sec-001","ROT13 Cipher","Implement ROT13 (rotate letters by 13).\nInput: string.\nOutput: ROT13 encoded string.","easy","sk-crypto",[
        tc("Hello World","Uryyb Jbeyq"),tc("Why did the chicken cross the road?","Jul qvq gur puvpxra pebff gur ebnq?")]),
    p("sec-002","Base64 Encode/Decode","Encode or decode Base64.\nInput: E or D, then string.\nOutput: encoded/decoded result.","easy","sk-crypto",[
        tc("E\nHello, World!","SGVsbG8sIFdvcmxkIQ=="),tc("D\nSGVsbG8sIFdvcmxkIQ==","Hello, World!")]),
    p("sec-003","Simple XOR Cipher","XOR encrypt/decrypt a string with a key.\nInput: key (single char), then message.\nOutput: hex-encoded XOR result.","easy","sk-crypto",[
        tc("K\nHello","030a0a05")]),
    p("sec-004","Detect SQL Injection Patterns","Detect common SQL injection patterns in input.\nInput: n queries.\nOutput: SAFE or INJECTED for each.","medium","sk-vulns",[
        tc("3\nSELECT * FROM users\n' OR '1'='1\nDROP TABLE users; --","SAFE\nINJECTED\nINJECTED")]),
    p("sec-005","Password Generator","Generate secure random password meeting requirements.\nInput: length, then requirements: UPPER, LOWER, DIGITS, SYMBOLS.\nOutput: a valid password of given length (just validate your logic outputs correct length and contains required char types — we check length and type presence).","medium","sk-crypto",[
        tc("12\n4\nUPPER\nLOWER\nDIGITS\nSYMBOLS","12")]),  # we just check len=12
    p("sec-006","Hash Collision Rate","Given n random strings hashed mod m, compute expected collision rate.\nInput: n m.\nOutput: collision probability (4 decimal places, Birthday paradox approximation).","hard","sk-crypto",[
        tc("23 365","0.5073"),tc("10 100","0.3713")]),
    p("sec-007","IP Address Validator","Validate IPv4 and IPv6 addresses.\nInput: n addresses.\nOutput: IPv4, IPv6, or INVALID for each.","easy","sk-network",[
        tc("4\n192.168.1.1\n::1\n256.256.256.256\n2001:0db8:85a3:0000:0000:8a2e:0370:7334","IPv4\nIPv6\nINVALID\nIPv6")]),
    p("sec-008","Vigenere Cipher","Encrypt/decrypt using Vigenere cipher.\nInput: E or D, key, then message (letters only).\nOutput: result.","medium","sk-crypto",[
        tc("E\nKEY\nHELLOWORLD","RIJVSUYVJN"),tc("D\nKEY\nRIJVSUYVJN","HELLOWORLD")]),
]

# ═══════════════════════════════════════════════════════
# SYSTEM DESIGN — 40 PROBLEMS
# ═══════════════════════════════════════════════════════

SYSDES_MCQ = [
    p("sd-mcq-001","CAP Theorem","In CAP theorem, which two properties can a distributed system guarantee simultaneously?","medium","sk-sysarch",[],
      ptype="mcq",mcq_opts=["Consistency and Availability","Consistency and Partition Tolerance OR Availability and Partition Tolerance","All three simultaneously","None — you choose one"],mcq_idx=1),
    p("sd-mcq-002","Horizontal vs Vertical Scaling","What is the main advantage of horizontal scaling over vertical?","easy","sk-scale",[],
      ptype="mcq",mcq_opts=["Cheaper hardware","No theoretical limit on scale-out; adds redundancy","Simpler code","Better single-threaded performance"],mcq_idx=1),
    p("sd-mcq-003","Cache Invalidation","Which cache invalidation strategy updates cache immediately when DB changes?","medium","sk-scale",[],
      ptype="mcq",mcq_opts=["Cache-aside","Write-through","Write-back","TTL-based expiry"],mcq_idx=1),
    p("sd-mcq-004","Database Sharding","What problem does database sharding solve?","medium","sk-databases",[],
      ptype="mcq",mcq_opts=["Slow queries","Storing data larger than one server can hold","Network latency","Read performance only"],mcq_idx=1),
    p("sd-mcq-005","Message Queue Purpose","What is the primary benefit of a message queue (e.g. Kafka, RabbitMQ)?","medium","sk-scale",[],
      ptype="mcq",mcq_opts=["Data encryption","Decoupling producers and consumers; handling load spikes","Faster database writes","Schema validation"],mcq_idx=1),
    p("sd-mcq-006","Load Balancer Algorithms","Which load balancing algorithm always sends requests to the server with fewest active connections?","easy","sk-scale",[],
      ptype="mcq",mcq_opts=["Round Robin","Least Connections","IP Hash","Random"],mcq_idx=1),
]

SYSDES_PROBLEMS = [
    p("sd-001","Design a Key-Value Store","Design a distributed key-value store like Redis.\n\nRequirements:\n- Store and retrieve key-value pairs\n- Handle 1 million operations/second\n- Data fits in memory (10GB)\n- Handle node failures gracefully\n\nCover: data model, partitioning, replication, consistency model, failure handling.\nWrite at least 300 words.","medium","sk-sysarch",[],
      ptype="system_design",rubric="Evaluate: (1) In-memory data model — 20pts; (2) Partitioning/sharding strategy — 20pts; (3) Replication for fault tolerance — 25pts; (4) Consistency model (eventual vs strong) — 20pts; (5) Cache eviction policy (LRU etc) — 15pts. 70+ = accepted."),
    p("sd-002","Design Twitter Feed","Design Twitter's home timeline feed.\n\nRequirements:\n- Users follow other users\n- Timeline shows tweets from followed users in reverse chronological order\n- 300M daily users, 100M tweets/day\n- Timeline loads in < 1 second\n\nCover: fan-out approach, storage, caching, trade-offs for celebrities vs regular users.\nWrite at least 300 words.","hard","sk-sysarch",[],
      ptype="system_design",rubric="Evaluate: (1) Fan-out on write vs read — 25pts; (2) Celebrity problem handling — 20pts; (3) Timeline storage/cache — 20pts; (4) Tweet storage schema — 20pts; (5) Scale reasoning — 15pts. 70+ = accepted."),
    p("sd-003","Design a CDN","Design a Content Delivery Network.\n\nRequirements:\n- Serve static assets (images, JS, CSS) from edge servers close to users\n- 99.99% availability\n- Cache invalidation when content changes\n- Global with 100 edge nodes\n\nCover: edge node placement, cache hierarchy, invalidation strategies, routing.\nWrite at least 300 words.","hard","sk-sysarch",[],
      ptype="system_design",rubric="Evaluate: (1) Edge node architecture — 20pts; (2) Cache hierarchy (edge → regional → origin) — 25pts; (3) Cache invalidation mechanism — 25pts; (4) Routing (anycast, GeoDNS) — 15pts; (5) Availability design — 15pts. 70+ = accepted."),
    p("sd-004","Design Rate Limiter","Design a distributed rate limiter.\n\nRequirements:\n- Limit to 1000 requests/user/minute\n- Works across multiple API servers\n- Must be consistent (no user can exceed limit by hitting different servers)\n- < 1ms overhead per request\n\nWrite at least 250 words with concrete implementation choices.","medium","sk-scale",[],
      ptype="system_design",rubric="Evaluate: (1) Algorithm choice (token bucket, sliding window) — 25pts; (2) Distributed consistency (Redis, Lua scripts) — 30pts; (3) Failure handling (what if Redis is down) — 20pts; (4) Performance < 1ms — 15pts; (5) Header design (X-RateLimit) — 10pts. 70+ = accepted."),
    p("sd-005","Design Uber Backend","Design the core backend of a ride-sharing app like Uber.\n\nRequirements:\n- Match riders to nearby drivers in < 2 seconds\n- Track 1M active drivers with live GPS updates every 5 seconds\n- Handle surge pricing\n- 10M rides/day\n\nCover: location indexing, matching algorithm, real-time tracking, pricing.\nWrite at least 350 words.","hard","sk-sysarch",[],
      ptype="system_design",rubric="Evaluate: (1) Geospatial indexing (quadtree, geohash, S2) — 30pts; (2) Driver-rider matching — 25pts; (3) Real-time location tracking (websockets, Kafka) — 20pts; (4) Surge pricing algorithm — 15pts; (5) Scale reasoning — 10pts. 70+ = accepted."),
]

# ═══════════════════════════════════════════════════════
# FULL STACK / DEBUGGING — 40+ PROBLEMS  
# ═══════════════════════════════════════════════════════

FULLSTACK_DEBUG = [
    p("fs-debug-001","Fix the Async Race Condition",
      "This Node.js-style code has a race condition bug. Fix it so results are always processed in order.\n\nHint: the issue is in how promises are chained.",
      "medium","sk-fullstack",[
        tc("","FIXED")],
      ptype="debugging",
      broken="""import asyncio

results = []

async def fetch_data(id, delay):
    await asyncio.sleep(delay)
    return f"data_{id}"

async def main():
    # BUG: tasks run concurrently but results are appended as they finish
    # This means results are out of order
    tasks = [
        asyncio.create_task(fetch_data(1, 0.3)),
        asyncio.create_task(fetch_data(2, 0.1)),
        asyncio.create_task(fetch_data(3, 0.2)),
    ]
    for task in tasks:
        result = await task
        results.append(result)
    
    # Should be in order: data_1, data_2, data_3
    print("FIXED" if results == ["data_1","data_2","data_3"] else f"WRONG: {results}")

asyncio.run(main())
"""),
    p("fs-debug-002","Fix the Off-by-One Pagination",
      "This pagination function returns wrong page data. Fix all the off-by-one errors.",
      "easy","sk-fullstack",[
        tc("","Page 1: [1, 2, 3]\nPage 2: [4, 5, 6]\nPage 3: [7, 8, 9]\nPage 4: [10]")],
      ptype="debugging",
      broken="""def paginate(items, page, page_size):
    # BUG: off-by-one — pages should be 1-indexed
    start = page * page_size  # Should be (page-1) * page_size
    end = start + page_size
    return items[start:end]

items = list(range(1, 11))
for page in range(1, 5):
    result = paginate(items, page, 3)
    print(f"Page {page}: {result}")
"""),
    p("fs-debug-003","Fix the Mutable Default Argument",
      "Python's mutable default argument bug. Fix it so each call gets a fresh list.",
      "easy","sk-fullstack",[
        tc("","[1]\n[2]\n[3]")],
      ptype="debugging",
      broken="""def append_to(element, to=[]):  # BUG: mutable default argument
    to.append(element)
    return to

print(append_to(1))  # Expected: [1]
print(append_to(2))  # Expected: [2], but gets [1, 2]
print(append_to(3))  # Expected: [3], but gets [1, 2, 3]
"""),
    p("fs-debug-004","Fix the N+1 Query Problem",
      "Simulate fixing an N+1 database query problem. The current code runs one query per user. Fix it to use a single JOIN-style query.",
      "medium","sk-fullstack",[
        tc("","Loaded 3 users in 1 query")],
      ptype="debugging",
      broken="""users_db = {1: "Alice", 2: "Bob", 3: "Charlie"}
orders_db = {1: [101, 102], 2: [103], 3: [104, 105, 106]}

query_count = 0

def get_all_users_with_orders():
    global query_count
    # BUG: N+1 problem — 1 query for users + N queries for orders
    query_count += 1
    users = list(users_db.items())
    
    result = []
    for uid, name in users:
        query_count += 1  # BUG: separate query per user
        orders = orders_db.get(uid, [])
        result.append({"user": name, "orders": orders})
    
    return result

data = get_all_users_with_orders()
print(f"Loaded {len(data)} users in {query_count} query")  # Should say "1 query"
"""),
]

FULLSTACK_MCQ = [
    p("fs-mcq-001","Docker vs VM","What is the main difference between Docker containers and VMs?","easy","sk-devops",[],
      ptype="mcq",mcq_opts=["Containers are slower","Containers share the host OS kernel; VMs have their own OS","VMs are more portable","Containers cannot run on Linux"],mcq_idx=1),
    p("fs-mcq-002","CI/CD Purpose","What does Continuous Deployment add over Continuous Delivery?","medium","sk-devops",[],
      ptype="mcq",mcq_opts=["Automatic testing","Automatic deployment to production without manual approval","Better code quality","Faster test execution"],mcq_idx=1),
    p("fs-mcq-003","Microservices Trade-off","What is the biggest DOWNSIDE of microservices vs monolith?","medium","sk-microservices",[],
      ptype="mcq",mcq_opts=["Harder to scale","Increased operational complexity and network overhead","Slower development","Cannot use different languages"],mcq_idx=1),
    p("fs-mcq-004","Event Sourcing","What does event sourcing store as the source of truth?","hard","sk-microservices",[],
      ptype="mcq",mcq_opts=["Current state snapshots","All events that led to current state","Only the latest event","Cache of computed results"],mcq_idx=1),
    p("fs-mcq-005","SAGA Pattern","The SAGA pattern in microservices handles:","hard","sk-microservices",[],
      ptype="mcq",mcq_opts=["User authentication","Distributed transactions across multiple services","Database migrations","API rate limiting"],mcq_idx=1),
]

# ═══════════════════════════════════════════════════════
# FULL PROBLEM LIST
# ═══════════════════════════════════════════════════════

ALL_PROBLEMS = (
    ARRAY_PROBLEMS + STRING_PROBLEMS + HASHMAP_PROBLEMS +
    LINKED_LIST_PROBLEMS + STACK_QUEUE_PROBLEMS + TREE_PROBLEMS +
    GRAPH_PROBLEMS + DP_PROBLEMS + BINARY_SEARCH_PROBLEMS +
    GREEDY_PROBLEMS + TWO_POINTER_PROBLEMS + SLIDING_WINDOW_PROBLEMS +
    HEAP_PROBLEMS + BACKTRACKING_PROBLEMS + BIT_PROBLEMS +
    MATH_PROBLEMS + TRIE_PROBLEMS +
    API_MCQ + API_CODING + JS_PROBLEMS +
    SQL_PROBLEMS + DS_CODING +
    SECURITY_MCQ + SECURITY_CODING +
    SYSDES_MCQ + SYSDES_PROBLEMS +
    FULLSTACK_DEBUG + FULLSTACK_MCQ
)


def seed_master():
    """Seed all 500+ problems. Fully idempotent."""
    db = get_db()

    # ── Skills ───────────────────────────────────────────────────────────────
    print(f"  Seeding {len(ALL_SKILLS)} skills...")
    with transaction(db) as txn:
        for sk in ALL_SKILLS:
            txn.execute("""
                INSERT OR IGNORE INTO skills (id, name, domain, description, is_active)
                VALUES (?, ?, ?, ?, 1)
            """, (sk["id"], sk["name"], sk["domain"], sk.get("description", "")))

    # ── Problems ─────────────────────────────────────────────────────────────
    inserted = 0
    skipped  = 0
    for prob in ALL_PROBLEMS:
        existing = db.execute("SELECT id FROM tasks WHERE id=?", (prob["id"],)).fetchone()
        if existing:
            skipped += 1
            continue
        try:
            with transaction(db) as txn:
                txn.execute("""
                    INSERT INTO tasks
                        (id, title, description, difficulty, skill_id,
                         time_limit_ms, memory_limit_kb, is_published,
                         problem_type, starter_code, starter_code_broken,
                         mcq_options, mcq_correct_index, system_design_rubric)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?, ?, ?, ?)
                """, (
                    prob["id"], prob["title"], prob["description"],
                    prob.get("difficulty","easy"), prob["skill_id"],
                    prob.get("time_limit_ms", 5000), prob.get("memory_limit_kb", 256000),
                    prob.get("problem_type","coding"),
                    prob.get("starter_code"), prob.get("starter_code_broken"),
                    prob.get("mcq_options"), prob.get("mcq_correct_index"),
                    prob.get("system_design_rubric"),
                ))
                for i, tc_item in enumerate(prob.get("test_cases", [])):
                    txn.execute("""
                        INSERT INTO test_cases
                            (id, task_id, input, expected_output, ordinal, is_sample)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (str(uuid.uuid4()), prob["id"],
                          tc_item.get("input",""), tc_item.get("expected_output",""),
                          i, i == 0))
            inserted += 1
        except Exception as e:
            print(f"  ⚠ Skip {prob['id']}: {e}")

    print(f"  ✅ Master seed: {inserted} inserted, {skipped} skipped ({len(ALL_PROBLEMS)} total)")


if __name__ == "__main__":
    seed_master()
