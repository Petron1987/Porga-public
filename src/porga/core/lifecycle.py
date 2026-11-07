class RunCancelled(RuntimeError):
    pass


def ensure_running(db, run_id):
    row = db.execute("SELECT status FROM runs WHERE id=?", (run_id,)).fetchone()
    if row and row[0] == "cancel_requested":
        raise RunCancelled("Cancellation requested by the operator")
    if not row or row[0] != "running":
        raise ValueError("Run is not active")
