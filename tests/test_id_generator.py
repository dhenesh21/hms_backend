"""
Tests for app.core.id_generator - proves the retry-on-collision logic
actually works, by directly forcing the exact race condition it's meant
to fix (two inserts racing for the same sequential number).
"""
import pytest
from sqlalchemy import Column, Integer, String, create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.core.id_generator import create_with_retry, next_sequence_number, MAX_RETRIES


class _DummyModel(Base):
    """A throwaway table just for this test, with a UNIQUE code column -
    mirrors the shape of UHID/bill_number/er_number etc."""
    __tablename__ = "_id_generator_test_dummy"
    id = Column(Integer, primary_key=True)
    code = Column(String(20), unique=True, nullable=False)


@pytest.fixture(scope="module")
def dummy_engine():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    _DummyModel.__table__.create(engine)
    yield engine
    _DummyModel.__table__.drop(engine)


@pytest.fixture
def dummy_session(dummy_engine):
    Session = sessionmaker(bind=dummy_engine)
    s = Session()
    yield s
    s.close()


def test_next_sequence_number_starts_at_one(dummy_session):
    assert next_sequence_number(dummy_session, _DummyModel) == 1


def test_create_with_retry_succeeds_normally(dummy_session):
    obj = create_with_retry(dummy_session, _DummyModel, lambda n: _DummyModel(code=f"CODE{n:04d}"))
    assert obj.code == "CODE0001"


def test_create_with_retry_resolves_a_real_collision(dummy_session):
    """
    This is the actual bug scenario: another request already grabbed the
    "next" number before we tried to insert. The naive count()+1 approach
    would crash with an IntegrityError here. create_with_retry must detect
    the collision and automatically move to the next number instead.
    """
    # Simulate "someone else already took CODE0002" by inserting it directly
    dummy_session.add(_DummyModel(code="CODE0002"))
    dummy_session.commit()

    # next_sequence_number will suggest 2 again (count()+1 = 2, since only
    # 1 row exists) - this IS the race condition. create_with_retry must
    # recover from the resulting collision on its first attempt.
    obj = create_with_retry(dummy_session, _DummyModel, lambda n: _DummyModel(code=f"CODE{n:04d}"))
    assert obj.code != "CODE0002"  # did not silently overwrite/crash
    assert obj.id is not None      # actually got saved


def test_create_with_retry_gives_up_after_max_retries(dummy_session):
    """If every attempt collides, it should raise the real database error
    rather than looping forever or silently returning something wrong.
    build_instance here deliberately ignores the suggested number and
    always targets an already-taken code, so every attempt is guaranteed
    to collide regardless of how the sequence number shifts."""
    from sqlalchemy.exc import IntegrityError

    dummy_session.add(_DummyModel(code="ALWAYS_TAKEN"))
    dummy_session.commit()

    with pytest.raises(IntegrityError):
        create_with_retry(dummy_session, _DummyModel, lambda n: _DummyModel(code="ALWAYS_TAKEN"))


def test_create_with_retry_works_past_five_sequential_creates(dummy_session):
    """
    Regression test for a real bug: create_with_retry originally always
    started counting from attempt=1 on every call instead of using the
    actual current count. That made it appear to work for the first few
    rows (small numbers happened to be free) and then silently break
    forever once 5+ rows existed, because every one of the 5 retry
    attempts collided with an already-used number. This creates 8 rows
    in a row (past that threshold) to prove it no longer happens.
    """
    for i in range(8):
        obj = create_with_retry(dummy_session, _DummyModel, lambda n: _DummyModel(code=f"SEQ{n:04d}"))
        assert obj.id is not None
    count = dummy_session.query(_DummyModel).filter(_DummyModel.code.like("SEQ%")).count()
    assert count == 8
