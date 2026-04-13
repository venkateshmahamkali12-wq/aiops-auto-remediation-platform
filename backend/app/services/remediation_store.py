"""In-memory store for remediations. Swap for a database in production."""

from typing import Optional

from app.models import Remediation, RemediationStatus

_store: dict[str, Remediation] = {}


def save(remediation: Remediation) -> Remediation:
    _store[remediation.id] = remediation
    return remediation


def get(remediation_id: str) -> Optional[Remediation]:
    return _store.get(remediation_id)


def list_all(status: Optional[RemediationStatus] = None) -> list[Remediation]:
    items = list(_store.values())
    if status:
        items = [r for r in items if r.status == status]
    return sorted(items, key=lambda r: r.created_at, reverse=True)


def update_status(remediation_id: str, status: RemediationStatus, **kwargs) -> Optional[Remediation]:
    rem = _store.get(remediation_id)
    if rem is None:
        return None
    rem.status = status
    for key, value in kwargs.items():
        if hasattr(rem, key):
            setattr(rem, key, value)
    return rem


def clear():
    """For testing."""
    _store.clear()
