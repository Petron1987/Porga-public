from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal

import pytest
from agents.usage import Usage

from porga.core.budget import BudgetExceeded, Ledger


def start(project, settings, store):
    return store.start(
        project.model_dump(mode="json"), settings.mode, settings.model_dump(mode="json")
    )


def test_budget_survives_new_ledger_instance(project, settings, store):
    s = settings.model_copy(update={"max_calls": 1})
    run_id = start(project, s, store)
    Ledger(s, store, run_id).reserve(100)
    with pytest.raises(BudgetExceeded):
        Ledger(s, store, run_id).reserve(100)


def test_daily_budget_is_shared_across_runs_and_atomic(project, settings, store):
    s = settings.model_copy(
        update={
            "input_price": Decimal(1),
            "output_price": Decimal(1),
            "daily_max_usd": Decimal("0.01"),
        }
    )
    ids = [start(project, s, store) for _ in range(3)]

    def attempt(run_id):
        try:
            Ledger(s, store, run_id).reserve(100)  # reserves USD 0.005796
            return True
        except BudgetExceeded:
            return False

    with ThreadPoolExecutor(max_workers=3) as pool:
        accepted = list(pool.map(attempt, ids))
    assert sum(accepted) == 1


def test_settlement_is_once_and_actual_overage_recorded(project, settings, store):
    run_id = start(project, settings, store)
    ledger = Ledger(settings, store, run_id)
    reserved = ledger.reserve(100)
    usage = Usage(requests=1, input_tokens=100, output_tokens=100, total_tokens=200)
    ledger.settle(reserved, usage)
    with pytest.raises(ValueError, match="already settled"):
        ledger.settle(reserved, usage)
    assert ledger.tokens == 200
    reserved = ledger.reserve(100)
    with pytest.raises(BudgetExceeded, match="actual usage recorded"):
        ledger.settle(
            reserved, Usage(requests=1, input_tokens=5000, output_tokens=100, total_tokens=5100)
        )
    assert ledger.tokens == 5300


def test_invalid_usage_retains_full_reservation(project, settings, store):
    run_id = start(project, settings, store)
    ledger = Ledger(settings, store, run_id)
    reserved = ledger.reserve(100)
    with pytest.raises(BudgetExceeded):
        ledger.settle(
            reserved, Usage(requests=1, input_tokens=100, output_tokens=100, total_tokens=0)
        )
    assert ledger.tokens == 5796
