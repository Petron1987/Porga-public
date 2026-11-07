"""Transactional per-run and shared daily accounting across process restarts."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from porga.core.lifecycle import ensure_running
from porga.core.store import uid


class BudgetExceeded(RuntimeError):
    pass


def budget_day():
    return datetime.now(timezone(timedelta(hours=8))).date().isoformat()


def totals(db, run_id):
    rows = db.execute("SELECT tokens,usd FROM reservations WHERE run_id=?", (run_id,)).fetchall()
    return (
        len(rows),
        sum(r["tokens"] for r in rows),
        sum((Decimal(r["usd"]) for r in rows), Decimal(0)),
    )


class Ledger:
    def __init__(self, settings, store, run_id):
        self.settings, self.store, self.run_id = settings, store, run_id

    def summary(self):
        with self.store.connect() as db:
            return totals(db, self.run_id)

    @property
    def calls(self):
        return self.summary()[0]

    @property
    def tokens(self):
        return self.summary()[1]

    @property
    def usd(self):
        return self.summary()[2]

    def price(self, input_tokens, output_tokens):
        s = self.settings
        return (s.input_price * input_tokens + s.output_price * output_tokens) / 1_000_000

    def reserve(self, input_bytes):
        s = self.settings
        if input_bytes > s.max_input_bytes:
            raise BudgetExceeded("Request exceeds input byte limit")
        input_cap = input_bytes + 4096
        tokens, cost = input_cap + s.max_output_tokens, self.price(input_cap, s.max_output_tokens)
        reservation_id, day = uid(), budget_day()
        with self.store.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            ensure_running(db, self.run_id)
            calls, used_tokens, usd = totals(db, self.run_id)
            daily = sum(
                (
                    Decimal(r[0])
                    for r in db.execute("SELECT usd FROM reservations WHERE day=?", (day,))
                ),
                Decimal(0),
            )
            if (
                calls + 1 > s.max_calls
                or used_tokens + tokens > s.max_tokens
                or usd + cost > s.max_usd
                or daily + cost > s.daily_max_usd
            ):
                raise BudgetExceeded("Run or shared daily budget exhausted before model call")
            db.execute(
                "INSERT INTO reservations VALUES(?,?,?,?,?,?,?,?,?,?)",
                (
                    reservation_id,
                    self.run_id,
                    day,
                    input_cap,
                    s.max_output_tokens,
                    tokens,
                    str(cost),
                    "reserved",
                    None,
                    None,
                ),
            )
            self.store.event(
                db,
                self.run_id,
                "model_reserved",
                {
                    "call": calls + 1,
                    "reservation_id": reservation_id,
                    "reserved_tokens": tokens,
                    "reserved_usd": str(cost),
                },
            )
        return reservation_id, input_cap, s.max_output_tokens

    def settle(self, reserved, usage):
        reservation_id, input_cap, output_cap = reserved
        if (
            usage.input_tokens < 0
            or usage.output_tokens < 0
            or usage.requests != 1
            or usage.total_tokens != usage.input_tokens + usage.output_tokens
            or usage.total_tokens <= 0
        ):
            raise BudgetExceeded("Missing or invalid model usage; reservation retained")
        actual = self.price(usage.input_tokens, usage.output_tokens)
        with self.store.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            changed = db.execute(
                "UPDATE reservations SET tokens=?,usd=?,status='settled',input_tokens=?,"
                "output_tokens=? WHERE id=? AND run_id=? AND status='reserved'",
                (
                    usage.total_tokens,
                    str(actual),
                    usage.input_tokens,
                    usage.output_tokens,
                    reservation_id,
                    self.run_id,
                ),
            )
            if changed.rowcount != 1:
                raise ValueError("Reservation already settled or missing")
            self.store.event(
                db,
                self.run_id,
                "model_usage",
                {
                    "reservation_id": reservation_id,
                    "input_tokens": usage.input_tokens,
                    "output_tokens": usage.output_tokens,
                    "estimated_usd": str(actual),
                },
            )
        if usage.input_tokens > input_cap or usage.output_tokens > output_cap:
            raise BudgetExceeded("Provider exceeded reservation; actual usage recorded")
