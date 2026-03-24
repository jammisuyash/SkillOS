"""
db/migrations.py

Schema migrations as ordered SQL strings.
Run with: python -m db.migrations

Rules:
  1. Migrations are append-only — never edit an existing migration
  2. Each migration is idempotent (IF NOT EXISTS, CREATE INDEX IF NOT EXISTS)
  3. The migrations table tracks what's been run
  4. Running twice is always safe

This is not a migration framework — it's 40 lines of discipline.
"""

import sqlite3
from skillos.db.database import get_db, transaction

MIGRATIONS = [
    # ─────────────────────────────────────────────────────────────────────
    # 001 — Core schema: tasks, test_cases, submissions
    #       Users are intentionally absent (Phase 1 hardcodes user_id).
    #       Auth is Phase 2. Correctness is Phase 1.
    # ─────────────────────────────────────────────────────────────────────
    ("001_core_schema", """
        CREATE TABLE IF NOT EXISTS tasks (
            id              TEXT PRIMARY KEY,
            title           TEXT NOT NULL,
            description     TEXT NOT NULL,
            difficulty      TEXT NOT NULL CHECK(difficulty IN ('easy','medium','hard')),
            skill_id        TEXT,
            time_limit_ms   INTEGER NOT NULL DEFAULT 2000,
            memory_limit_kb INTEGER NOT NULL DEFAULT 131072,
            is_published    INTEGER NOT NULL DEFAULT 0,
            created_at      TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS test_cases (
            id              TEXT PRIMARY KEY,
            task_id         TEXT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
            input           TEXT NOT NULL,
            expected_output TEXT NOT NULL,
            is_hidden       INTEGER NOT NULL DEFAULT 0,
            comparison_mode TEXT NOT NULL DEFAULT 'exact'
                                CHECK(comparison_mode IN ('exact','float','multiline')),
            ordinal         INTEGER NOT NULL
        );

        CREATE TABLE IF NOT EXISTS submissions (
            id               TEXT PRIMARY KEY,
            user_id          TEXT NOT NULL,
            task_id          TEXT NOT NULL REFERENCES tasks(id),
            code             TEXT NOT NULL,
            language         TEXT NOT NULL DEFAULT 'python'
                                 CHECK(language IN ('python','python3','javascript','java','cpp','c','go','rust','typescript')),
            status           TEXT NOT NULL DEFAULT 'pending'
                                 CHECK(status IN (
                                     'pending','accepted','wrong_answer',
                                     'timeout','runtime_error','crash'
                                 )),
            passed_cases     INTEGER,
            total_cases      INTEGER,
            max_runtime_ms   INTEGER,
            max_memory_kb    INTEGER,
            performance_tier TEXT CHECK(performance_tier IN ('fast','acceptable','slow') OR
                                       performance_tier IS NULL),
            stdout_sample    TEXT,
            stderr_sample    TEXT,
            submitted_at     TEXT NOT NULL DEFAULT (datetime('now')),
            evaluated_at     TEXT
        );

        -- Indexes for the queries that actually matter
        CREATE INDEX IF NOT EXISTS idx_submissions_user_time
            ON submissions(user_id, submitted_at DESC);

        CREATE INDEX IF NOT EXISTS idx_submissions_pending
            ON submissions(status)
            WHERE status = 'pending';

        CREATE INDEX IF NOT EXISTS idx_test_cases_task_ordinal
            ON test_cases(task_id, ordinal);
    """),

    # ─────────────────────────────────────────────────────────────────────
    # 002 — Phase 2: users, skills, user_skill_scores
    #       Auth is now real. Skill scoring is now active.
    #       user_skill_scores is derived — always replayable from submissions.
    # ─────────────────────────────────────────────────────────────────────
    ("002_users_skills_scores", """
        CREATE TABLE IF NOT EXISTS users (
            id            TEXT PRIMARY KEY,
            email         TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            display_name  TEXT NOT NULL,
            created_at    TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS skills (
            id          TEXT PRIMARY KEY,
            name        TEXT UNIQUE NOT NULL,
            description TEXT,
            domain      TEXT NOT NULL DEFAULT 'general',
            is_active   INTEGER NOT NULL DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS user_skill_scores (
            id              TEXT PRIMARY KEY,
            user_id         TEXT NOT NULL REFERENCES users(id),
            skill_id        TEXT NOT NULL REFERENCES skills(id),
            current_score   REAL NOT NULL DEFAULT 0,
            tasks_attempted INTEGER NOT NULL DEFAULT 0,
            tasks_passed    INTEGER NOT NULL DEFAULT 0,
            last_updated_at TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE(user_id, skill_id)
        );

        CREATE INDEX IF NOT EXISTS idx_users_email
            ON users(email);

        CREATE INDEX IF NOT EXISTS idx_user_skill_scores_user
            ON user_skill_scores(user_id);
    """),

    # ─────────────────────────────────────────────────────────────────────
    # 003 — Phase 3: seed skills catalogue
    #       Skills are now real entities. Tasks reference them by FK.
    #       Seeded here so the catalogue is available after any fresh migration.
    #       Add new skills here as the task library grows.
    # ─────────────────────────────────────────────────────────────────────






    ("007_fix_submissions_language_constraint", """
        CREATE TABLE IF NOT EXISTS submissions_new (
            id               TEXT PRIMARY KEY,
            user_id          TEXT NOT NULL,
            task_id          TEXT NOT NULL,
            code             TEXT NOT NULL,
            language         TEXT NOT NULL DEFAULT 'python3',
            status           TEXT NOT NULL DEFAULT 'pending',
            passed_cases     INTEGER,
            total_cases      INTEGER,
            max_runtime_ms   INTEGER,
            max_memory_kb    INTEGER,
            performance_tier TEXT,
            stdout_sample    TEXT,
            stderr_sample    TEXT,
            submitted_at     TEXT NOT NULL DEFAULT (datetime('now')),
            evaluated_at     TEXT,
            mcq_answer       INTEGER,
            ai_feedback      TEXT,
            ai_score         INTEGER,
            proctoring_flags TEXT,
            tab_switches     INTEGER NOT NULL DEFAULT 0,
            time_spent_seconds INTEGER NOT NULL DEFAULT 0
        );
    """),
    ("006_tasks_columns", """
        ALTER TABLE tasks ADD COLUMN is_daily INTEGER DEFAULT 0;
        ALTER TABLE tasks ADD COLUMN is_active INTEGER DEFAULT 1;
    """),
    ("005_user_profiles", """
        CREATE TABLE IF NOT EXISTS user_profiles (
            user_id TEXT PRIMARY KEY REFERENCES users(id),
            bio TEXT,
            avatar_url TEXT,
            github_url TEXT,
            linkedin_url TEXT,
            website_url TEXT,
            college TEXT,
            graduation_year INTEGER,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        );
    """),
    ("004_skills_columns", """
        ALTER TABLE skills ADD COLUMN domain TEXT NOT NULL DEFAULT 'general';
        ALTER TABLE skills ADD COLUMN is_active INTEGER NOT NULL DEFAULT 1;
    """),
    ("003_skills_catalogue", """
        INSERT OR IGNORE INTO skills (id, name, description) VALUES
            ('skill-python-001', 'Python Fundamentals',
             'Basic Python: I/O, data types, control flow, functions'),
            ('skill-arrays-001', 'Arrays & Strings',
             'Linear data structure manipulation and string algorithms'),
            ('skill-hashmaps-001', 'Hash Maps & Sets',
             'Lookup tables, frequency counting, set operations'),
            ('skill-recursion-001', 'Recursion & Backtracking',
             'Recursive decomposition, base cases, backtracking patterns'),
            ('skill-sorting-001', 'Sorting & Searching',
             'Comparison sorts, binary search, and their variants'),
            ('skill-graphs-001', 'Graphs & Trees',
             'BFS, DFS, shortest paths, tree traversals');
    """),


    # ─────────────────────────────────────────────────────────────────────────
    # 004 — Email verification + password reset tokens
    #       Tokens are single-use, time-limited, stored hashed.
    # ─────────────────────────────────────────────────────────────────────────
    ("004_auth_tokens", """
        ALTER TABLE users ADD COLUMN is_email_verified INTEGER NOT NULL DEFAULT 0;
        ALTER TABLE users ADD COLUMN google_id TEXT;
        ALTER TABLE users ADD COLUMN avatar_url TEXT;

        CREATE TABLE IF NOT EXISTS auth_tokens (
            id          TEXT PRIMARY KEY,
            user_id     TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            token_hash  TEXT NOT NULL UNIQUE,
            token_type  TEXT NOT NULL CHECK(token_type IN ('email_verify','password_reset')),
            expires_at  TEXT NOT NULL,
            used_at     TEXT,
            created_at  TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE INDEX IF NOT EXISTS idx_auth_tokens_hash
            ON auth_tokens(token_hash);

        CREATE INDEX IF NOT EXISTS idx_auth_tokens_user
            ON auth_tokens(user_id, token_type);
    """),

    # ─────────────────────────────────────────────────────────────────────────
    # 005 — Certification system
    #       Certifications are earned, not bought. Score thresholds enforced.
    #       cert_id is public-facing verification code (UUID, shareable URL).
    # ─────────────────────────────────────────────────────────────────────────
    ("005_certifications", """
        CREATE TABLE IF NOT EXISTS certification_types (
            id            TEXT PRIMARY KEY,
            name          TEXT NOT NULL UNIQUE,
            description   TEXT NOT NULL,
            skill_id      TEXT REFERENCES skills(id),
            min_score     REAL NOT NULL DEFAULT 80,
            min_tasks     INTEGER NOT NULL DEFAULT 5,
            badge_color   TEXT NOT NULL DEFAULT '#1a4731',
            is_active     INTEGER NOT NULL DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS user_certifications (
            id              TEXT PRIMARY KEY,
            user_id         TEXT NOT NULL REFERENCES users(id),
            cert_type_id    TEXT NOT NULL REFERENCES certification_types(id),
            cert_code       TEXT NOT NULL UNIQUE,
            score_at_issue  REAL NOT NULL,
            issued_at       TEXT NOT NULL DEFAULT (datetime('now')),
            expires_at      TEXT,
            is_revoked      INTEGER NOT NULL DEFAULT 0,
            UNIQUE(user_id, cert_type_id)
        );

        CREATE INDEX IF NOT EXISTS idx_user_certs_user
            ON user_certifications(user_id);

        CREATE INDEX IF NOT EXISTS idx_user_certs_code
            ON user_certifications(cert_code);

        INSERT OR IGNORE INTO certification_types
            (id, name, description, skill_id, min_score, min_tasks, badge_color)
        VALUES
            ('cert-python',   'Python Fundamentals',    'Verified Python programming ability — I/O, control flow, data types, functions', 'skill-python-001',    80, 3, '#1a4731'),
            ('cert-arrays',   'Arrays & Strings',       'Verified mastery of linear data structures and string manipulation algorithms',  'skill-arrays-001',    80, 2, '#1a3a5c'),
            ('cert-hashmaps', 'Hash Maps & Sets',       'Verified ability to apply hash-based data structures to solve lookup problems',  'skill-hashmaps-001',  80, 1, '#6b21a8'),
            ('cert-sorting',  'Sorting & Searching',    'Verified knowledge of comparison sorts, binary search, and their applications', 'skill-sorting-001',   80, 2, '#b45309'),
            ('cert-recursion','Recursion & Backtracking','Verified understanding of recursive decomposition and backtracking patterns',  'skill-recursion-001', 80, 1, '#0f766e'),
            ('cert-graphs',   'Graphs & Trees',         'Verified ability to traverse graphs and trees using BFS, DFS, and related algorithms', 'skill-graphs-001', 82, 2, '#9f1239'),
            ('cert-fullstack','Full Stack Engineer',    'Verified across Python Fundamentals, Arrays & Strings, and Sorting & Searching — demonstrates well-rounded engineering ability', NULL, 80, 8, '#1a4731');
    """),


    # ─────────────────────────────────────────────────────────────────────────
    # 005 — Auth hardening: rate limiting, login history, devices, 2FA, roles
    # ─────────────────────────────────────────────────────────────────────────
    ("005_auth_hardening", """
        -- Role-based access: user | recruiter | admin
        ALTER TABLE users ADD COLUMN role TEXT NOT NULL DEFAULT 'user'
            CHECK(role IN ('user','recruiter','admin'));

        -- 2FA fields
        ALTER TABLE users ADD COLUMN totp_secret     TEXT;
        ALTER TABLE users ADD COLUMN totp_enabled    INTEGER NOT NULL DEFAULT 0;
        ALTER TABLE users ADD COLUMN totp_backup_codes TEXT;

        -- Rate limit buckets (token bucket per IP per action)
        CREATE TABLE IF NOT EXISTS rate_limit_buckets (
            key         TEXT PRIMARY KEY,
            tokens      REAL NOT NULL DEFAULT 0,
            last_refill TEXT NOT NULL DEFAULT (datetime('now'))
        );

        -- Login history
        CREATE TABLE IF NOT EXISTS login_history (
            id          TEXT PRIMARY KEY,
            user_id     TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            ip_address  TEXT,
            user_agent  TEXT,
            device_id   TEXT,
            country     TEXT,
            status      TEXT NOT NULL CHECK(status IN ('success','failed','blocked')),
            fail_reason TEXT,
            logged_at   TEXT NOT NULL DEFAULT (datetime('now'))
        );

        -- Known devices (trust on first use)
        CREATE TABLE IF NOT EXISTS user_devices (
            id           TEXT PRIMARY KEY,
            user_id      TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            device_id    TEXT NOT NULL,
            device_name  TEXT,
            user_agent   TEXT,
            ip_address   TEXT,
            first_seen   TEXT NOT NULL DEFAULT (datetime('now')),
            last_seen    TEXT NOT NULL DEFAULT (datetime('now')),
            is_trusted   INTEGER NOT NULL DEFAULT 0,
            UNIQUE(user_id, device_id)
        );

        -- Active sessions (for session list + revocation)
        CREATE TABLE IF NOT EXISTS user_sessions (
            id           TEXT PRIMARY KEY,
            user_id      TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            token_hash   TEXT NOT NULL UNIQUE,
            device_id    TEXT,
            ip_address   TEXT,
            user_agent   TEXT,
            created_at   TEXT NOT NULL DEFAULT (datetime('now')),
            expires_at   TEXT NOT NULL,
            revoked_at   TEXT,
            last_used_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE INDEX IF NOT EXISTS idx_login_history_user
            ON login_history(user_id, logged_at DESC);

        CREATE INDEX IF NOT EXISTS idx_sessions_token
            ON user_sessions(token_hash);

        CREATE INDEX IF NOT EXISTS idx_sessions_user
            ON user_sessions(user_id);

        CREATE INDEX IF NOT EXISTS idx_devices_user
            ON user_devices(user_id);
    """),

]


def run_migrations():
    db = get_db()
    db.execute("""
        CREATE TABLE IF NOT EXISTS schema_migrations (
            name       TEXT PRIMARY KEY,
            applied_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)
    db.commit()

    for name, sql in MIGRATIONS:
        already_run = db.execute(
            "SELECT 1 FROM schema_migrations WHERE name = ?", (name,)
        ).fetchone()

        if already_run:
            print(f"  skip  {name}")
            continue

        print(f"  apply {name}...")
        try:
            db.executescript(sql)
        except Exception as e:
            if "duplicate column" not in str(e).lower():
                raise
            db.execute(
                "INSERT INTO schema_migrations (name) VALUES (?)", (name,)
            )
            db.commit()
            print(f"  done  {name}")
        except Exception as e:
            db.rollback()
            print(f"  FAILED {name}: {e}")
            raise


if __name__ == "__main__":
    print("Running migrations...")
    run_migrations()
    print("Done.")


# append this to MIGRATIONS list — paste inside the list before the closing ]


# NOTE: append this inside MIGRATIONS list manually, or run patch below

# This is appended — do NOT edit existing migrations above

_NEW_MIGRATIONS = [
    ("006_profiles", """
        ALTER TABLE users ADD COLUMN username TEXT;
        ALTER TABLE users ADD COLUMN bio TEXT;
        ALTER TABLE users ADD COLUMN location TEXT;
        ALTER TABLE users ADD COLUMN education TEXT;
        ALTER TABLE users ADD COLUMN experience_years INTEGER DEFAULT 0;
        ALTER TABLE users ADD COLUMN github_url TEXT;
        ALTER TABLE users ADD COLUMN portfolio_url TEXT;
        ALTER TABLE users ADD COLUMN linkedin_url TEXT;
        ALTER TABLE users ADD COLUMN is_public INTEGER NOT NULL DEFAULT 1;
        ALTER TABLE users ADD COLUMN reputation INTEGER NOT NULL DEFAULT 0;
        ALTER TABLE users ADD COLUMN streak_current INTEGER NOT NULL DEFAULT 0;
        ALTER TABLE users ADD COLUMN streak_best INTEGER NOT NULL DEFAULT 0;
        ALTER TABLE users ADD COLUMN last_active_date TEXT;
        CREATE UNIQUE INDEX IF NOT EXISTS idx_users_username ON users(username) WHERE username IS NOT NULL;
    """),

    ("007_contests", """
        CREATE TABLE IF NOT EXISTS contests (
            id          TEXT PRIMARY KEY,
            title       TEXT NOT NULL,
            description TEXT,
            starts_at   TEXT NOT NULL,
            ends_at     TEXT NOT NULL,
            status      TEXT NOT NULL DEFAULT 'upcoming'
                            CHECK(status IN ('upcoming','active','ended')),
            created_at  TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS contest_problems (
            id         TEXT PRIMARY KEY,
            contest_id TEXT NOT NULL REFERENCES contests(id) ON DELETE CASCADE,
            task_id    TEXT NOT NULL REFERENCES tasks(id),
            points     INTEGER NOT NULL DEFAULT 100,
            ordinal    INTEGER NOT NULL DEFAULT 1,
            UNIQUE(contest_id, task_id)
        );
        CREATE TABLE IF NOT EXISTS contest_entries (
            id            TEXT PRIMARY KEY,
            contest_id    TEXT NOT NULL REFERENCES contests(id),
            user_id       TEXT NOT NULL REFERENCES users(id),
            total_score   INTEGER NOT NULL DEFAULT 0,
            problems_solved INTEGER NOT NULL DEFAULT 0,
            rank          INTEGER,
            registered_at TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE(contest_id, user_id)
        );
        CREATE INDEX IF NOT EXISTS idx_contest_entries_contest
            ON contest_entries(contest_id, total_score DESC);
    """),

    ("008_learning_paths", """
        CREATE TABLE IF NOT EXISTS learning_paths (
            id          TEXT PRIMARY KEY,
            title       TEXT NOT NULL,
            description TEXT,
            domain      TEXT NOT NULL DEFAULT 'software',
            difficulty  TEXT NOT NULL DEFAULT 'beginner'
                            CHECK(difficulty IN ('beginner','intermediate','advanced')),
            is_active   INTEGER NOT NULL DEFAULT 1,
            ordinal     INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS path_steps (
            id          TEXT PRIMARY KEY,
            path_id     TEXT NOT NULL REFERENCES learning_paths(id) ON DELETE CASCADE,
            title       TEXT NOT NULL,
            description TEXT,
            task_id     TEXT REFERENCES tasks(id),
            skill_id    TEXT REFERENCES skills(id),
            step_type   TEXT NOT NULL DEFAULT 'problem'
                            CHECK(step_type IN ('problem','reading','video','project')),
            ordinal     INTEGER NOT NULL DEFAULT 0,
            is_required INTEGER NOT NULL DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS user_path_progress (
            id           TEXT PRIMARY KEY,
            user_id      TEXT NOT NULL REFERENCES users(id),
            path_id      TEXT NOT NULL REFERENCES learning_paths(id),
            step_id      TEXT NOT NULL REFERENCES path_steps(id),
            completed_at TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE(user_id, path_id, step_id)
        );
        CREATE INDEX IF NOT EXISTS idx_path_progress_user
            ON user_path_progress(user_id, path_id);
    """),

    ("009_community", """
        CREATE TABLE IF NOT EXISTS discussions (
            id          TEXT PRIMARY KEY,
            user_id     TEXT NOT NULL REFERENCES users(id),
            task_id     TEXT REFERENCES tasks(id),
            title       TEXT NOT NULL,
            body        TEXT NOT NULL,
            is_solution INTEGER NOT NULL DEFAULT 0,
            upvotes     INTEGER NOT NULL DEFAULT 0,
            is_pinned   INTEGER NOT NULL DEFAULT 0,
            is_locked   INTEGER NOT NULL DEFAULT 0,
            created_at  TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at  TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS discussion_replies (
            id            TEXT PRIMARY KEY,
            discussion_id TEXT NOT NULL REFERENCES discussions(id) ON DELETE CASCADE,
            user_id       TEXT NOT NULL REFERENCES users(id),
            body          TEXT NOT NULL,
            upvotes       INTEGER NOT NULL DEFAULT 0,
            is_accepted   INTEGER NOT NULL DEFAULT 0,
            created_at    TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS discussion_votes (
            id            TEXT PRIMARY KEY,
            user_id       TEXT NOT NULL REFERENCES users(id),
            target_type   TEXT NOT NULL CHECK(target_type IN ('discussion','reply')),
            target_id     TEXT NOT NULL,
            vote          INTEGER NOT NULL DEFAULT 1,
            UNIQUE(user_id, target_type, target_id)
        );
        CREATE INDEX IF NOT EXISTS idx_discussions_task
            ON discussions(task_id, created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_discussions_user
            ON discussions(user_id, created_at DESC);
    """),

    ("010_companies", """
        CREATE TABLE IF NOT EXISTS companies (
            id           TEXT PRIMARY KEY,
            name         TEXT NOT NULL,
            domain       TEXT UNIQUE,
            description  TEXT,
            logo_url     TEXT,
            website      TEXT,
            plan         TEXT NOT NULL DEFAULT 'free'
                             CHECK(plan IN ('free','starter','growth','enterprise')),
            plan_expires_at TEXT,
            contacts_used   INTEGER NOT NULL DEFAULT 0,
            contacts_limit  INTEGER NOT NULL DEFAULT 0,
            created_at   TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS company_members (
            id         TEXT PRIMARY KEY,
            company_id TEXT NOT NULL REFERENCES companies(id),
            user_id    TEXT NOT NULL REFERENCES users(id),
            role       TEXT NOT NULL DEFAULT 'recruiter'
                           CHECK(role IN ('owner','admin','recruiter')),
            joined_at  TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE(company_id, user_id)
        );
        CREATE TABLE IF NOT EXISTS job_postings (
            id           TEXT PRIMARY KEY,
            company_id   TEXT NOT NULL REFERENCES companies(id),
            title        TEXT NOT NULL,
            description  TEXT,
            location     TEXT,
            remote       INTEGER NOT NULL DEFAULT 0,
            salary_min   INTEGER,
            salary_max   INTEGER,
            currency     TEXT DEFAULT 'INR',
            required_skills TEXT,
            min_score    INTEGER DEFAULT 0,
            is_active    INTEGER NOT NULL DEFAULT 1,
            created_at   TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS contact_requests (
            id           TEXT PRIMARY KEY,
            company_id   TEXT NOT NULL REFERENCES companies(id),
            recruiter_id TEXT NOT NULL REFERENCES users(id),
            candidate_id TEXT NOT NULL REFERENCES users(id),
            job_id       TEXT REFERENCES job_postings(id),
            message      TEXT,
            status       TEXT NOT NULL DEFAULT 'pending'
                             CHECK(status IN ('pending','accepted','declined','expired')),
            created_at   TEXT NOT NULL DEFAULT (datetime('now')),
            responded_at TEXT,
            UNIQUE(company_id, candidate_id)
        );
        CREATE INDEX IF NOT EXISTS idx_contacts_candidate
            ON contact_requests(candidate_id, status);
    """),

    ("011_payments", """
        CREATE TABLE IF NOT EXISTS payment_orders (
            id               TEXT PRIMARY KEY,
            company_id       TEXT REFERENCES companies(id),
            user_id          TEXT REFERENCES users(id),
            provider         TEXT NOT NULL DEFAULT 'razorpay',
            provider_order_id TEXT,
            provider_payment_id TEXT,
            amount_paise     INTEGER NOT NULL,
            currency         TEXT NOT NULL DEFAULT 'INR',
            plan             TEXT NOT NULL,
            status           TEXT NOT NULL DEFAULT 'created'
                                 CHECK(status IN ('created','paid','failed','refunded')),
            created_at       TEXT NOT NULL DEFAULT (datetime('now')),
            paid_at          TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_payments_company
            ON payment_orders(company_id, status);
    """),

    ("012_projects", """
        CREATE TABLE IF NOT EXISTS project_templates (
            id          TEXT PRIMARY KEY,
            title       TEXT NOT NULL,
            description TEXT,
            difficulty  TEXT NOT NULL DEFAULT 'medium',
            domain      TEXT NOT NULL DEFAULT 'backend',
            skill_ids   TEXT,
            eval_criteria TEXT,
            is_active   INTEGER NOT NULL DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS user_projects (
            id           TEXT PRIMARY KEY,
            user_id      TEXT NOT NULL REFERENCES users(id),
            template_id  TEXT NOT NULL REFERENCES project_templates(id),
            repo_url     TEXT,
            status       TEXT NOT NULL DEFAULT 'in_progress'
                             CHECK(status IN ('in_progress','submitted','evaluated','rejected')),
            score        REAL,
            feedback     TEXT,
            submitted_at TEXT,
            evaluated_at TEXT,
            created_at   TEXT NOT NULL DEFAULT (datetime('now'))
        );
    """),

    ("013_reputation_analytics", """
        CREATE TABLE IF NOT EXISTS reputation_events (
            id         TEXT PRIMARY KEY,
            user_id    TEXT NOT NULL REFERENCES users(id),
            event_type TEXT NOT NULL,
            points     INTEGER NOT NULL DEFAULT 0,
            ref_id     TEXT,
            ref_type   TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_rep_events_user
            ON reputation_events(user_id, created_at DESC);

        CREATE TABLE IF NOT EXISTS leaderboard_snapshots (
            id         TEXT PRIMARY KEY,
            user_id    TEXT NOT NULL REFERENCES users(id),
            period     TEXT NOT NULL CHECK(period IN ('weekly','monthly','alltime')),
            score      REAL NOT NULL DEFAULT 0,
            rank       INTEGER,
            snapped_at TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE(user_id, period)
        );
        CREATE INDEX IF NOT EXISTS idx_leaderboard_period
            ON leaderboard_snapshots(period, score DESC);

        CREATE TABLE IF NOT EXISTS daily_challenges (
            id         TEXT PRIMARY KEY,
            task_id    TEXT NOT NULL REFERENCES tasks(id),
            date       TEXT NOT NULL UNIQUE,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
    """),
]

_INTERVIEW_MIGRATIONS = [
    ("014_live_interviews", """
        CREATE TABLE IF NOT EXISTS interview_rooms (
            id               TEXT PRIMARY KEY,
            creator_id       TEXT NOT NULL REFERENCES users(id),
            candidate_email  TEXT NOT NULL,
            title            TEXT NOT NULL,
            scheduled_at     TEXT,
            duration_minutes INTEGER NOT NULL DEFAULT 60,
            task_id          TEXT REFERENCES tasks(id),
            invite_token     TEXT NOT NULL UNIQUE,
            status           TEXT NOT NULL DEFAULT 'scheduled'
                             CHECK(status IN ('scheduled','active','ended','cancelled')),
            started_at       TEXT,
            ended_at         TEXT,
            feedback         TEXT,
            rating           INTEGER DEFAULT 0 CHECK(rating >= 0 AND rating <= 5),
            created_at       TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_interview_rooms_creator
            ON interview_rooms(creator_id, created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_interview_rooms_invite
            ON interview_rooms(invite_token);

        CREATE TABLE IF NOT EXISTS interview_code_snapshots (
            id         TEXT PRIMARY KEY,
            room_id    TEXT NOT NULL REFERENCES interview_rooms(id) ON DELETE CASCADE,
            author_id  TEXT REFERENCES users(id),
            code       TEXT NOT NULL DEFAULT '',
            language   TEXT NOT NULL DEFAULT 'python3',
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_interview_code_room
            ON interview_code_snapshots(room_id, updated_at DESC);

        CREATE TABLE IF NOT EXISTS interview_events (
            id          TEXT PRIMARY KEY,
            room_id     TEXT NOT NULL REFERENCES interview_rooms(id) ON DELETE CASCADE,
            author_id   TEXT REFERENCES users(id),
            event_type  TEXT NOT NULL DEFAULT 'message'
                        CHECK(event_type IN ('message','note','hint','task_assigned','system')),
            content     TEXT NOT NULL,
            is_private  INTEGER NOT NULL DEFAULT 0,
            created_at  TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_interview_events_room
            ON interview_events(room_id, created_at ASC);
    """),
]

# Append to MIGRATIONS list at module load time
MIGRATIONS.extend(_NEW_MIGRATIONS)
MIGRATIONS.extend(_INTERVIEW_MIGRATIONS)

_V2_MIGRATIONS = [
    ("015_skill_history", """
        -- Track skill score over time for history charts
        CREATE TABLE IF NOT EXISTS skill_score_history (
            id          TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
            user_id     TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            skill_id    TEXT NOT NULL REFERENCES skills(id),
            score       REAL NOT NULL DEFAULT 0,
            delta       REAL NOT NULL DEFAULT 0,
            reason      TEXT NOT NULL DEFAULT 'submission',
            recorded_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_ssh_user_skill
            ON skill_score_history(user_id, skill_id, recorded_at DESC);

        -- Profile photo stored as URL or base64
        ALTER TABLE users ADD COLUMN avatar_url TEXT;
        ALTER TABLE users ADD COLUMN avatar_data TEXT;

        -- Monthly leaderboard snapshots
        CREATE TABLE IF NOT EXISTS monthly_rankings (
            id          TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
            user_id     TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            year_month  TEXT NOT NULL,
            rank        INTEGER NOT NULL DEFAULT 0,
            score       REAL NOT NULL DEFAULT 0,
            delta_rank  INTEGER NOT NULL DEFAULT 0,
            created_at  TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE(user_id, year_month)
        );
        CREATE INDEX IF NOT EXISTS idx_monthly_rankings_month
            ON monthly_rankings(year_month, rank ASC);
    """),

    ("016_problem_types", """
        -- Extended problem types: mcq, debugging, system_design
        ALTER TABLE tasks ADD COLUMN problem_type TEXT NOT NULL DEFAULT 'coding'
            CHECK(problem_type IN ('coding','mcq','debugging','system_design','fill_in_blank'));
        ALTER TABLE tasks ADD COLUMN starter_code TEXT;
        ALTER TABLE tasks ADD COLUMN starter_code_broken TEXT;
        ALTER TABLE tasks ADD COLUMN mcq_options TEXT;
        ALTER TABLE tasks ADD COLUMN mcq_correct_index INTEGER;
        ALTER TABLE tasks ADD COLUMN system_design_rubric TEXT;
        ALTER TABLE tasks ADD COLUMN ai_evaluation_prompt TEXT;

        -- MCQ submission answers
        ALTER TABLE submissions ADD COLUMN mcq_answer INTEGER;
        ALTER TABLE submissions ADD COLUMN ai_feedback TEXT;
        ALTER TABLE submissions ADD COLUMN ai_score INTEGER;
        ALTER TABLE submissions ADD COLUMN proctoring_flags TEXT;
        ALTER TABLE submissions ADD COLUMN tab_switches INTEGER NOT NULL DEFAULT 0;
        ALTER TABLE submissions ADD COLUMN time_spent_seconds INTEGER NOT NULL DEFAULT 0;
    """),

    ("017_proctoring", """
        -- Light proctoring session tracking
        CREATE TABLE IF NOT EXISTS proctoring_sessions (
            id              TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
            user_id         TEXT NOT NULL REFERENCES users(id),
            submission_id   TEXT REFERENCES submissions(id),
            task_id         TEXT REFERENCES tasks(id),
            tab_switches    INTEGER NOT NULL DEFAULT 0,
            focus_lost_count INTEGER NOT NULL DEFAULT 0,
            time_spent_s    INTEGER NOT NULL DEFAULT 0,
            flags           TEXT,
            started_at      TEXT NOT NULL DEFAULT (datetime('now')),
            ended_at        TEXT
        );

        -- More domain problems seeding flag
        CREATE TABLE IF NOT EXISTS seed_log (
            id    TEXT PRIMARY KEY,
            done_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
    """),
]

MIGRATIONS.extend(_V2_MIGRATIONS)


_REFERRAL_MIGRATIONS = [
    ("018_referrals_network", """
        -- Invite codes and referral tracking
        CREATE TABLE IF NOT EXISTS user_referrals (
            id                TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
            user_id           TEXT NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
            invite_code       TEXT NOT NULL UNIQUE,
            total_invited     INTEGER NOT NULL DEFAULT 0,
            total_activated   INTEGER NOT NULL DEFAULT 0,
            reputation_earned INTEGER NOT NULL DEFAULT 0,
            created_at        TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_referrals_code ON user_referrals(invite_code);

        CREATE TABLE IF NOT EXISTS referral_invites (
            id               TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
            referrer_user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            invited_user_id  TEXT NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
            activated_at     TEXT,
            created_at       TEXT NOT NULL DEFAULT (datetime('now'))
        );

        -- Company accounts (backend for recruiter dashboard)
        CREATE TABLE IF NOT EXISTS companies (
            id           TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
            owner_id     TEXT NOT NULL REFERENCES users(id),
            name         TEXT NOT NULL,
            domain       TEXT,
            plan         TEXT NOT NULL DEFAULT 'free',
            contacts_used INTEGER NOT NULL DEFAULT 0,
            contacts_limit INTEGER NOT NULL DEFAULT 0,
            created_at   TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS company_jobs (
            id           TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
            company_id   TEXT NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
            title        TEXT NOT NULL,
            description  TEXT,
            skills_required TEXT,
            location     TEXT,
            salary_range TEXT,
            is_active    INTEGER NOT NULL DEFAULT 1,
            created_at   TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS contact_requests (
            id               TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
            company_id       TEXT NOT NULL REFERENCES companies(id),
            recruiter_id     TEXT NOT NULL REFERENCES users(id),
            candidate_id     TEXT NOT NULL REFERENCES users(id),
            message          TEXT,
            status           TEXT NOT NULL DEFAULT 'sent',
            created_at       TEXT NOT NULL DEFAULT (datetime('now'))
        );

        -- Notification system
        CREATE TABLE IF NOT EXISTS notifications (
            id         TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
            user_id    TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            type       TEXT NOT NULL,
            title      TEXT NOT NULL,
            body       TEXT,
            is_read    INTEGER NOT NULL DEFAULT 0,
            data       TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_notif_user ON notifications(user_id, is_read, created_at DESC);
    """),
]

MIGRATIONS.extend(_REFERRAL_MIGRATIONS)

_V3_MIGRATIONS = [
    ("019_github_campus", """
        -- GitHub username for profile integration
        ALTER TABLE users ADD COLUMN github_username TEXT;

        -- College/campus for student leaderboard
        ALTER TABLE users ADD COLUMN college TEXT;
        ALTER TABLE users ADD COLUMN graduation_year INTEGER;
        ALTER TABLE users ADD COLUMN is_student INTEGER NOT NULL DEFAULT 0;

        -- AI code review cache
        CREATE TABLE IF NOT EXISTS code_reviews (
            id             TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
            user_id        TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            submission_id  TEXT REFERENCES submissions(id),
            language       TEXT NOT NULL DEFAULT 'python3',
            code_hash      TEXT NOT NULL,
            review_json    TEXT NOT NULL,
            source         TEXT NOT NULL DEFAULT 'ai',
            created_at     TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_review_user ON code_reviews(user_id, created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_review_hash ON code_reviews(code_hash);

        -- Job queue log (for observability)
        CREATE TABLE IF NOT EXISTS job_log (
            id         TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(16)))),
            job_type   TEXT NOT NULL,
            payload    TEXT,
            status     TEXT NOT NULL DEFAULT 'queued',
            result     TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            done_at    TEXT
        );
    """),
]

MIGRATIONS.extend(_V3_MIGRATIONS)

