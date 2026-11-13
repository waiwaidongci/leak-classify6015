-- 002: retest_runs — sealed-model external re-tests on another dataset.
-- First startup creates the table from SQLAlchemy metadata; this file records structure.
-- retest_runs(id PK, run_id FK training_runs.id, dataset_id FK window_datasets.id,
--   status queued/running/succeeded/failed, result JSON, error, creator_id FK users.id, created_at)
-- Natural key: (run_id, dataset_id) unique — the same request never adds a second result.
-- No update API: failed tasks may only be re-queued via retry; succeeded re-tests stay as sealed.
CREATE TABLE IF NOT EXISTS retest_runs (
 id SERIAL PRIMARY KEY,
 run_id INTEGER NOT NULL REFERENCES training_runs(id),
 dataset_id INTEGER NOT NULL REFERENCES window_datasets(id),
 status VARCHAR(20) NOT NULL DEFAULT 'queued',
 result JSON NOT NULL DEFAULT '{}',
 error VARCHAR(1000),
 creator_id INTEGER NOT NULL REFERENCES users(id),
 created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
 CONSTRAINT uq_retest_run_dataset UNIQUE (run_id, dataset_id)
);
