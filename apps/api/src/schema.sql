PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS accounts (
  id TEXT PRIMARY KEY,
  login_code_salt TEXT NOT NULL,
  login_code_hash TEXT NOT NULL,
  age INTEGER NOT NULL CHECK (age >= 18),
  last_period_start TEXT,
  cycle_tracking_mode TEXT NOT NULL CHECK (
    cycle_tracking_mode IN ('period_date', 'unsure', 'hormonal_contraception')
  ),
  workouts_per_week INTEGER NOT NULL CHECK (workouts_per_week BETWEEN 1 AND 7),
  usual_split TEXT NOT NULL CHECK (
    usual_split IN ('Full body', 'Upper/Lower', 'Push/Pull/Legs', 'Body-part split', 'Not sure')
  ),
  goal TEXT NOT NULL CHECK (
    goal IN ('Strength', 'Muscle', 'Endurance', 'General fitness', 'Energy')
  ),
  profile_version INTEGER NOT NULL DEFAULT 2,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CHECK (
    (cycle_tracking_mode = 'period_date' AND last_period_start IS NOT NULL)
    OR (cycle_tracking_mode != 'period_date' AND last_period_start IS NULL)
  )
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
  phase TEXT NOT NULL CHECK (phase IN ('menstrual', 'follicular', 'ovulatory', 'luteal')),
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (account_id, phase)
);

CREATE TABLE IF NOT EXISTS phase_plan_locks (
  account_id TEXT NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
  phase TEXT NOT NULL CHECK (phase IN ('menstrual', 'follicular', 'ovulatory', 'luteal')),
  workout_plan_json TEXT NOT NULL,
  is_locked INTEGER NOT NULL DEFAULT 0 CHECK (is_locked IN (0, 1)),
  plan_saved_at TEXT,
  locked_at TEXT,
  PRIMARY KEY (account_id, phase)
);
