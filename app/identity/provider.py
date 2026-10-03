"""Read-only provider for the controlled Enterprise Identity fixture."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import TypeAdapter, ValidationError

from app.config import REPOSITORY_ROOT
from app.identity.models import EnterpriseIdentity, IdentityOption


DEFAULT_IDENTITY_PATH = REPOSITORY_ROOT / "data" / "identity" / "enterprise_identities.json"


class IdentityProviderError(RuntimeError):
    """Raised when the controlled identity fixture cannot be validated."""


class IdentityProvider:
    def __init__(self, fixture_path: Path = DEFAULT_IDENTITY_PATH) -> None:
        self.fixture_path = fixture_path
        self._identities = self._load()
        self._by_username = {item.corporate_username: item for item in self._identities}

        if len(self._by_username) != len(self._identities):
            raise IdentityProviderError("Enterprise Identity usernames must be unique")

    def _load(self) -> tuple[EnterpriseIdentity, ...]:
        try:
            raw = json.loads(self.fixture_path.read_text(encoding="utf-8"))
            identities = TypeAdapter(list[EnterpriseIdentity]).validate_python(raw)
        except (OSError, json.JSONDecodeError, ValidationError) as exc:
            raise IdentityProviderError(f"Invalid Enterprise Identity fixture: {exc}") from exc

        identity_ids = {item.identity_id for item in identities}
        employee_ids = {item.employee_id for item in identities}
        if len(identity_ids) != len(identities) or len(employee_ids) != len(identities):
            raise IdentityProviderError("Enterprise Identity IDs and employee mappings must be unique")
        return tuple(identities)

    def list_active_options(self) -> list[IdentityOption]:
        return [
            IdentityOption(
                corporate_username=item.corporate_username,
                display_name=item.display_name,
                job_title=item.job_title,
            )
            for item in self._identities
            if item.account_status == "active"
        ]

    def get_by_username(self, corporate_username: str) -> EnterpriseIdentity | None:
        identity = self._by_username.get(corporate_username)
        return identity if identity and identity.account_status == "active" else None

    @property
    def count(self) -> int:
        return len(self._identities)

