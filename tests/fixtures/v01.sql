CREATE TABLE IF NOT EXISTS runs (
                    id TEXT PRIMARY KEY, mode TEXT NOT NULL, status TEXT NOT NULL,
                    project TEXT NOT NULL, created_at TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY, run_id TEXT NOT NULL REFERENCES runs(id),
                    role TEXT NOT NULL, status TEXT NOT NULL, artifact_id TEXT);
                CREATE TABLE IF NOT EXISTS artifacts (
                    id TEXT PRIMARY KEY, run_id TEXT NOT NULL REFERENCES runs(id),
                    kind TEXT NOT NULL, sha256 TEXT NOT NULL, content TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS proposals (
                    id TEXT PRIMARY KEY, run_id TEXT NOT NULL REFERENCES runs(id),
                    status TEXT NOT NULL, change TEXT NOT NULL, rationale TEXT NOT NULL,
                    evaluation_id TEXT NOT NULL REFERENCES artifacts(id),
                    evidence_passed INTEGER NOT NULL,
                    deployment TEXT NOT NULL DEFAULT 'not_applied');
                CREATE TABLE IF NOT EXISTS decisions (
                    proposal_id TEXT PRIMARY KEY REFERENCES proposals(id),
                    actor TEXT NOT NULL, decision TEXT NOT NULL, note TEXT NOT NULL,
                    created_at TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS events (
                    seq INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT NOT NULL,
                    type TEXT NOT NULL, metadata TEXT NOT NULL, created_at TEXT NOT NULL);
