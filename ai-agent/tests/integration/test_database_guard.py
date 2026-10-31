import pytest

from venergy_agent.evaluation.database_guard import PostgresDatabaseGuard


@pytest.fixture
def guard(agent_database_url, probe_view):
    return PostgresDatabaseGuard(agent_database_url, "semantic", frozenset({probe_view}))


async def test_agent_role_has_every_write_denied(guard):
    assert await guard.accepted_writes() == 0


async def test_snapshot_detects_a_change_in_a_view(guard, owner, probe_view):
    before = await guard.snapshot()
    assert await guard.snapshot() == before

    owner.execute(f"INSERT INTO semantic.{probe_view} VALUES ('0004', 400)")

    assert (await guard.snapshot())[probe_view] != before[probe_view]


async def test_probe_counts_accepted_writes_and_rolls_them_back(owner_database_url, probe_view):
    privileged = PostgresDatabaseGuard(owner_database_url, "semantic", frozenset({probe_view}))
    before = await privileged.snapshot()

    assert await privileged.accepted_writes() > 0
    assert await privileged.snapshot() == before
