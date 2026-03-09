"""
github/service.py

GitHub integration — fetch public profile, repos, contribution data.
Uses GitHub REST API v3 (no auth needed for public data, rate limit: 60 req/hr).
With GITHUB_TOKEN env var: 5000 req/hr.

WHAT WE SHOW:
  - Avatar, bio, location, public repos count, followers/following
  - Top 6 repos (by stars) with language, description, stars, forks
  - Contribution streak / commit count (approximate from events API)
  - Languages used across repos
"""
import json, urllib.request, urllib.error, os
from skillos.db.database import get_db, fetchone
from skillos.shared.logger import get_logger

log = get_logger("github")

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
_HEADERS = {
    "Accept": "application/vnd.github.v3+json",
    "User-Agent": "SkillOS/2.0",
    **({"Authorization": f"Bearer {GITHUB_TOKEN}"} if GITHUB_TOKEN else {}),
}
_CACHE_TTL = 3600  # 1 hour


def _gh_get(url: str) -> dict | list | None:
    """GET from GitHub API with error handling."""
    try:
        req = urllib.request.Request(url, headers=_HEADERS)
        with urllib.request.urlopen(req, timeout=8) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        log.warning("github.http_error", url=url, status=e.code)
        return None
    except Exception as e:
        log.warning("github.fetch_error", url=url, error=str(e))
        return None


def connect_github_account(user_id: str, github_username: str) -> dict:
    """Link a GitHub username to a SkillOS user account."""
    github_username = github_username.strip().lstrip("@")
    if not github_username:
        from skillos.shared.exceptions import ValidationError
        raise ValidationError("GitHub username required")
    # Verify the account exists
    profile = _gh_get(f"https://api.github.com/users/{github_username}")
    if not profile:
        from skillos.shared.exceptions import ValidationError
        raise ValidationError("GitHub user not found")
    db = get_db()
    db.execute("UPDATE users SET github_username=? WHERE id=?", (github_username, user_id))
    db.commit()
    return {"ok": True, "github_username": github_username, "github_name": profile.get("name")}


def get_github_username(user_id: str) -> str | None:
    row = fetchone("SELECT github_username FROM users WHERE id=?", (user_id,))
    return row.get("github_username") if row else None


def get_github_profile(username: str) -> dict:
    """Fetch full GitHub profile data for a username."""
    user_data = _gh_get(f"https://api.github.com/users/{username}")
    if not user_data:
        return {"error": "GitHub profile not found", "username": username}

    # Top repos by stars
    repos_raw = _gh_get(f"https://api.github.com/users/{username}/repos?sort=stars&per_page=20&type=owner")
    repos = []
    lang_counts: dict[str, int] = {}
    if repos_raw and isinstance(repos_raw, list):
        for r in repos_raw[:6]:
            repos.append({
                "name":        r.get("name"),
                "description": r.get("description") or "",
                "url":         r.get("html_url"),
                "stars":       r.get("stargazers_count", 0),
                "forks":       r.get("forks_count", 0),
                "language":    r.get("language") or "—",
                "updated_at":  r.get("updated_at", "")[:10],
            })
        for r in repos_raw:
            lang = r.get("language")
            if lang:
                lang_counts[lang] = lang_counts.get(lang, 0) + 1

    # Recent events (for activity indicator)
    events = _gh_get(f"https://api.github.com/users/{username}/events/public?per_page=30")
    recent_commits = 0
    if events and isinstance(events, list):
        recent_commits = sum(1 for e in events if e.get("type") == "PushEvent")

    top_languages = sorted(lang_counts.items(), key=lambda x: x[1], reverse=True)[:5]

    return {
        "username":      user_data.get("login"),
        "name":          user_data.get("name") or user_data.get("login"),
        "bio":           user_data.get("bio") or "",
        "avatar_url":    user_data.get("avatar_url"),
        "profile_url":   user_data.get("html_url"),
        "public_repos":  user_data.get("public_repos", 0),
        "followers":     user_data.get("followers", 0),
        "following":     user_data.get("following", 0),
        "location":      user_data.get("location") or "",
        "company":       user_data.get("company") or "",
        "blog":          user_data.get("blog") or "",
        "created_at":    user_data.get("created_at", "")[:10],
        "repos":         repos,
        "top_languages": [{"language": l, "count": c} for l, c in top_languages],
        "recent_push_events": recent_commits,
    }


def get_github_for_user(user_id: str) -> dict | None:
    """Get GitHub data for a SkillOS user (if they've connected their account)."""
    username = get_github_username(user_id)
    if not username:
        return None
    return get_github_profile(username)
