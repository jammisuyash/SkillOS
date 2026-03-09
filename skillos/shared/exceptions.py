"""
skillos/shared/exceptions.py

All domain exceptions in one place.
Callers import these — never raw Exception.

This makes error handling consistent and API responses predictable.
"""


class SkillOSError(Exception):
    """Base exception for all SkillOS errors."""
    status_code: int = 500
    message: str = "Internal server error"


class NotFoundError(SkillOSError):
    status_code = 404
    def __init__(self, resource: str, id: str):
        self.message = f"{resource} '{id}' not found"
        super().__init__(self.message)


class ValidationError(SkillOSError):
    status_code = 400
    def __init__(self, detail: str):
        self.message = detail
        super().__init__(detail)


class TaskNotPublishedError(SkillOSError):
    status_code = 400
    def __init__(self, task_id: str):
        self.message = f"Task '{task_id}' is not published"
        super().__init__(self.message)


class UnsupportedLanguageError(SkillOSError):
    status_code = 400
    def __init__(self, language: str):
        self.message = f"Language '{language}' is not supported in this phase"
        super().__init__(self.message)


class ForbiddenError(SkillOSError):
    status_code = 403
    def __init__(self, detail: str = "Access forbidden"):
        self.message = detail
        super().__init__(detail)
