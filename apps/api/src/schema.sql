PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS accounts (
  id TEXT PRIMARY KEY,
  login_code_salt TEXT NOT NULL,
  login_code_hash TEXT NOT NULL,
  age INTEGER NOT NULL CHECK (age >= 18),
  last_period_start TEXT,
  cycle_date_unsure INTEGER NOT NULL DEFAULT 0 CHECK (cycle_date_unsure IN (0, 1)),
  goal TEXT NOT NULL CHECK (goal IN ('strength', 'general_fitness', 'energy')),
  dietary_preference TEXT NOT NULL DEFAULT 'none',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS selected_exercises (
  account_id TEXT NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
  exercise_id TEXT NOT NULL,
  position INTEGER NOT NULL CHECK (position BETWEEN 0 AND 4),
  PRIMARY KEY (account_id, exercise_id),
  UNIQUE (account_id, position)
);

CREATE TABLE IF NOT EXISTS period_starts (
  account_id TEXT NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
  start_date TEXT NOT NULL,
  PRIMARY KEY (account_id, start_date)
);

CREATE TABLE IF NOT EXISTS daily_checkins (
  id TEXT PRIMARY KEY,
  account_id TEXT NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
  checkin_date TEXT NOT NULL,
  flow TEXT NOT NULL CHECK (flow IN ('none', 'spotting', 'light', 'moderate', 'heavy')),
  mood TEXT NOT NULL,
  energy INTEGER NOT NULL CHECK (energy BETWEEN 1 AND 5),
  sleep_hours REAL NOT NULL CHECK (sleep_hours BETWEEN 0 AND 24),
  pain INTEGER NOT NULL CHECK (pain BETWEEN 0 AND 10),
  workout_done INTEGER NOT NULL CHECK (workout_done IN (0, 1)),
  UNIQUE (account_id, checkin_date)
);

CREATE TABLE IF NOT EXISTS plan_hearts (
  account_id TEXT NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
  plan_kind TEXT NOT NULL CHECK (plan_kind IN ('workout', 'grocery')),
  phase TEXT NOT NULL CHECK (phase IN ('menstrual', 'follicular', 'ovulatory', 'luteal')),
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (account_id, plan_kind, phase)
);

CREATE TABLE IF NOT EXISTS phase_plan_locks (
  account_id TEXT NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
  phase TEXT NOT NULL CHECK (phase IN ('menstrual', 'follicular', 'ovulatory', 'luteal')),
  workout_plan_json TEXT NOT NULL,
  grocery_plan_json TEXT NOT NULL,
  locked_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (account_id, phase)
);
