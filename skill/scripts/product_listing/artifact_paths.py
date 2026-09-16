"""Resolve pinned skill artifacts independently of the installation folder."""
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[2]
LOCKED_SKILL_PREFIX = ".claude/skills/product-listing/"


def locked_skill_file(relative_path: str) -> Path:
    """Keep historical lock bytes intact while resolving within this skill only."""
    if not isinstance(relative_path, str) or not relative_path.startswith(LOCKED_SKILL_PREFIX):
        raise ValueError("locked artifact is outside the skill")
    root = SKILL_ROOT.resolve()
    candidate = (root / relative_path[len(LOCKED_SKILL_PREFIX):]).resolve()
    if not candidate.is_relative_to(root):
        raise ValueError("locked artifact escapes the skill")
    if not candidate.is_file():
        raise ValueError("locked artifact is missing: %s" % relative_path)
    return candidate
