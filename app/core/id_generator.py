"""
Shared sequential-number generator.

PROBLEM this fixes:
Every module that needs a human-readable sequential ID (UHID, bill number,
admission number, ER number, etc) was generating it as:

    count = db.query(Model).count() + 1
    number = f"PREFIX{count:07d}"

This has a real race condition: if two requests run this at the same time
(e.g. two reception desks registering patients simultaneously, which is a
completely normal scenario in a real hospital), both can read the same
count and generate the same number. The second INSERT then fails with a
raw IntegrityError -> the API returns an ugly 500 instead of succeeding.

FIX:
Wrap the insert-and-commit in a small retry loop. On a unique-constraint
violation, roll back, generate the next number, and try again (a handful
of times) before giving up. This does not require row-level locking or
a dedicated sequence table, and works the same on SQLite (tests) and
Postgres (production).
"""
from typing import Callable, TypeVar

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

T = TypeVar("T")

MAX_RETRIES = 5


def next_sequence_number(db: Session, model, digits: int = 7, filters: dict = None) -> int:
    """
    Returns the next sequential number for `model`, based on current row
    count (optionally scoped by `filters`, e.g. {"role": UserRole.DOCTOR}).
    Callers should format this into their own prefix string, e.g.
    f"UHID{n:07d}".

    Note: this alone does not fix the race condition - it must be combined
    with create_with_retry() below, which retries on collision.
    """
    query = db.query(model)
    if filters:
        for field, value in filters.items():
            query = query.filter(getattr(model, field) == value)
    return query.count() + 1


def create_with_retry(
    db: Session,
    model,
    build_instance: Callable[[int], T],
    max_retries: int = MAX_RETRIES,
) -> T:
    """
    Calls build_instance(attempt_number) to construct a new (unsaved) ORM
    object whose unique sequential field depends on attempt_number, adds it,
    and commits. If the commit fails due to a unique-constraint collision
    (another request generated the same number first), rolls back and
    retries with the next number, up to max_retries times.

    `model` is the ORM class being created (e.g. Patient) - used to compute
    the correct starting sequence number via next_sequence_number(). This
    is required: without it, retries would restart from 1 every call and
    permanently fail once enough rows already exist (each of the 5 retry
    attempts would collide with an already-used number).

    build_instance receives the sequence number to use for this attempt
    (starting from the current count+1, then +2, +3, ... on each retry) and
    must return a new, not-yet-added ORM instance using it.

    Usage:
        def build(n):
            return Patient(**data, uhid=f"UHID{n:07d}", ...)
        patient = create_with_retry(db, Patient, build)
    """
    base_attempt = next_sequence_number(db, model)
    last_error = None

    for i in range(max_retries):
        instance = build_instance(base_attempt + i)
        db.add(instance)
        try:
            db.commit()
            db.refresh(instance)
            return instance
        except IntegrityError as e:
            db.rollback()
            last_error = e
            continue

    # Exhausted retries - surface the real error rather than silently failing
    raise last_error
