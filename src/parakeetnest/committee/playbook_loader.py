"""Reusable markdown playbook loading for committee prompts."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


SUPPORTED_PERSONA_PLAYBOOKS: frozenset[str] = frozenset(
    {"dongdong", "xixi", "yoyo"}
)
REQUIRED_PLAYBOOK_FILES: tuple[str, ...] = (
    "system.md",
    "common.md",
    "dongdong.md",
    "xixi.md",
    "yoyo.md",
)

PERSONA_PLAYBOOK_FILES: dict[str, str] = {
    "dongdong": "dongdong.md",
    "xixi": "xixi.md",
    "yoyo": "yoyo.md",
}


class MissingCommitteePlaybookError(FileNotFoundError):
    """Raised when a required committee markdown playbook is missing."""


@dataclass(frozen=True)
class PlaybookLoader:
    """Load cached committee markdown playbooks from the package directory."""

    playbook_dir: Path | None = None
    _cache: dict[str, str] = field(default_factory=dict, init=False, repr=False)

    @property
    def _resolved_playbook_dir(self) -> Path:
        if self.playbook_dir is not None:
            return self.playbook_dir
        return Path(__file__).with_name("playbooks")

    def validate_required_files(self) -> None:
        """Raise a clear error if any required playbook file is missing."""
        missing = [
            filename
            for filename in REQUIRED_PLAYBOOK_FILES
            if not (self._resolved_playbook_dir / filename).is_file()
        ]
        if missing:
            missing_list = ", ".join(missing)
            raise MissingCommitteePlaybookError(
                f"Missing committee playbook file(s): {missing_list}"
            )

    def load_system_playbook(self) -> str:
        """Load the system committee playbook."""
        return self._load_markdown("system.md")

    def load_common_playbook(self) -> str:
        """Load the common committee playbook."""
        return self._load_markdown("common.md")

    def load_persona_playbook(self, persona_id: str) -> str:
        """Load a persona-specific playbook by stable persona ID."""
        normalized = str(persona_id).strip().lower()
        if normalized not in SUPPORTED_PERSONA_PLAYBOOKS:
            supported = ", ".join(sorted(SUPPORTED_PERSONA_PLAYBOOKS))
            raise ValueError(
                f"Unsupported committee persona playbook: {persona_id!r}. "
                f"Supported persona ids: {supported}"
            )
        return self._load_markdown(PERSONA_PLAYBOOK_FILES[normalized])

    def _load_markdown(self, filename: str) -> str:
        cached = self._cache.get(filename)
        if cached is not None:
            return cached

        path = self._resolved_playbook_dir / filename
        if not path.is_file():
            raise MissingCommitteePlaybookError(
                f"Missing committee playbook file: {path}"
            )
        content = path.read_text(encoding="utf-8").strip()
        self._cache[filename] = content
        return content
