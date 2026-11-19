"""IteraGuard domain rulebook: proposal-only, no external side effects."""
from .engine import RulebookError, validate_book, build_questions, decide
__all__ = ["RulebookError", "validate_book", "build_questions", "decide"]
