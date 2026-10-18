"""Guards: the seed reloads cleanly and nothing outside the Sim Clock reads real time."""

import re
from pathlib import Path

from sqlmodel import Session, func, select

from app.models import Pool, Product, Retailer, User
from seed import seed as seed_module

from tests.conftest import make_engine

BACKEND = Path(__file__).resolve().parents[1]


def test_seed_can_be_rerun():
    engine = make_engine()
    seed_module.reset_and_seed(engine)
    seed_module.reset_and_seed(engine)
    with Session(engine) as s:
        assert s.exec(select(func.count()).select_from(Product)).one() > 0
        assert s.exec(select(func.count()).select_from(Retailer)).one() > 0
        assert s.exec(select(func.count()).select_from(User)).one() > 0
        assert s.exec(select(func.count()).select_from(Pool)).one() > 0


def test_nothing_outside_the_sim_clock_reads_real_time():
    pattern = re.compile(r"\b(datetime\.now|datetime\.utcnow|utcnow|date\.today|time\.time)\s*\(")
    offenders = [
        str(path.relative_to(BACKEND))
        for folder in ("app", "seed")
        for path in (BACKEND / folder).rglob("*.py")
        if path.name != "clock.py" and pattern.search(path.read_text(encoding="utf-8"))
    ]
    assert offenders == []
