"""Session-bound in-memory state for demonstration-only mock actions."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from datetime import UTC, datetime
from threading import RLock
from typing import Any, Literal


ActionName = Literal["create_mock_hr_ticket", "create_mock_travel_request"]


@dataclass
class PendingAction:
    session_id: str
    employee_id: str
    action_name: ActionName
    arguments: dict[str, Any]
    public_context: dict[str, Any] = field(default_factory=dict)


class MockActionStore:
    """Disposable state; it is neither policy evidence nor operational authority."""

    def __init__(self) -> None:
        self._pending: dict[str, PendingAction] = {}
        self._records: list[dict[str, Any]] = []
        self._ticket_counter = 0
        self._travel_counter = 0
        self._lock = RLock()

    def propose(self, *, session_id: str, employee_id: str, action_name: ActionName,
                arguments: dict[str, Any]) -> PendingAction:
        pending = PendingAction(
            session_id=session_id, employee_id=employee_id, action_name=action_name,
            arguments=deepcopy(arguments),
        )
        with self._lock:
            self._pending[session_id] = pending
        return deepcopy(pending)

    def pending(self, session_id: str) -> PendingAction | None:
        with self._lock:
            value = self._pending.get(session_id)
            return deepcopy(value) if value else None

    def attach_public_context(self, session_id: str, context: dict[str, Any]) -> None:
        with self._lock:
            pending = self._pending.get(session_id)
            if pending:
                pending.public_context = deepcopy(context)

    def complete(self, *, session_id: str, employee_id: str,
                 action_name: ActionName,
                 expected_request_type: str | None = None) -> dict[str, Any] | None:
        """Atomically consume the matching pending action and create one mock record."""
        with self._lock:
            pending = self._pending.get(session_id)
            if (
                pending is None
                or pending.employee_id != employee_id
                or pending.action_name != action_name
                or (
                    expected_request_type is not None
                    and pending.arguments.get("request_type") != expected_request_type
                )
            ):
                return None
            del self._pending[session_id]
            if action_name == "create_mock_hr_ticket":
                self._ticket_counter += 1
                reference = f"MOCK-HRT-{self._ticket_counter:04d}"
            else:
                self._travel_counter += 1
                reference = f"MOCK-TR-{self._travel_counter:04d}"
            record = {
                "action_name": action_name, "reference": reference,
                "employee_id": employee_id, **deepcopy(pending.arguments),
                "status": "created", "created_at": datetime.now(UTC).isoformat(),
            }
            self._records.append(record)
            return deepcopy(record)

    def records(self) -> list[dict[str, Any]]:
        with self._lock:
            return deepcopy(self._records)

    def reset(self) -> None:
        with self._lock:
            self._pending.clear()
            self._records.clear()
            self._ticket_counter = 0
            self._travel_counter = 0


mock_action_store = MockActionStore()


def get_mock_action_store() -> MockActionStore:
    return mock_action_store
