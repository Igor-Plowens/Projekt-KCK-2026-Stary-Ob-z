import sqlite3
from datetime import datetime


class CyberTrainerDB:
    def __init__(self, db_path="fitness.db"):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")

        self.create_tables()
        self.ensure_default_data()

    def create_tables(self):
        self.conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            display_name TEXT
        );

        CREATE TABLE IF NOT EXISTS teams (
            team_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        );

        CREATE TABLE IF NOT EXISTS team_members (
            team_id INTEGER,
            user_id INTEGER,

            PRIMARY KEY (team_id, user_id),

            FOREIGN KEY (team_id)
                REFERENCES teams(team_id)
                ON DELETE CASCADE,

            FOREIGN KEY (user_id)
                REFERENCES users(user_id)
                ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS exercise_types (
            exercise_type_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        );

        CREATE TABLE IF NOT EXISTS exercise_definitions (
            exercise_definition_id INTEGER PRIMARY KEY AUTOINCREMENT,
            exercise_type_id INTEGER NOT NULL,
            name TEXT NOT NULL,

            FOREIGN KEY (exercise_type_id)
                REFERENCES exercise_types(exercise_type_id)
                ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS training_sessions (
            session_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            started_at TEXT NOT NULL,
            notes TEXT,

            FOREIGN KEY (user_id)
                REFERENCES users(user_id)
                ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS exercise_attempts (
            attempt_id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            exercise_definition_id INTEGER NOT NULL,
            successful INTEGER NOT NULL,
            duration_seconds INTEGER,
            reps INTEGER,
            weight_kg REAL,
            distance_meters REAL,

            FOREIGN KEY (session_id)
                REFERENCES training_sessions(session_id)
                ON DELETE CASCADE,

            FOREIGN KEY (exercise_definition_id)
                REFERENCES exercise_definitions(exercise_definition_id)
                ON DELETE CASCADE
        );
        """)

        self.conn.commit()

    # --------------------------------------------------
    # Dane startowe
    # --------------------------------------------------

    def ensure_default_data(self):
        self.get_or_create_user("XYZ", "XYZ")
        self.get_or_create_exercise_definition(
            exercise_type_name="Podnoszenie przedmiotu",
            exercise_name="Podnoszenie przedmiotu z podłogi na stół",
        )

    # --------------------------------------------------
    # Użytkownicy
    # --------------------------------------------------

    def get_user_by_username(self, username):
        cur = self.conn.execute(
            """
            SELECT user_id, username, display_name
            FROM users
            WHERE username = ?
            """,
            (username,),
        )
        row = cur.fetchone()
        return dict(row) if row else None

    def get_or_create_user(self, username, display_name=None):
        username = (username or "").strip()
        display_name = (display_name or username).strip()

        if not username:
            raise ValueError("Nazwa użytkownika nie może być pusta.")

        existing = self.get_user_by_username(username)
        if existing is not None:
            return existing["user_id"]

        cur = self.conn.execute(
            """
            INSERT INTO users(username, display_name)
            VALUES (?, ?)
            """,
            (username, display_name),
        )
        self.conn.commit()
        return cur.lastrowid

    # Czytelniejszy alias dla kodu GUI.
    def add_user(self, username, display_name=None):
        return self.get_or_create_user(username, display_name)

    def fetch_users(self):
        cur = self.conn.execute(
            """
            SELECT user_id, username, display_name
            FROM users
            ORDER BY username COLLATE NOCASE
            """
        )
        return [dict(row) for row in cur.fetchall()]

    def get_usernames(self):
        return [row["username"] for row in self.fetch_users()]

    # --------------------------------------------------
    # Ćwiczenia i treningi
    # --------------------------------------------------

    def get_or_create_exercise_type(self, name):
        name = (name or "").strip()
        if not name:
            raise ValueError("Nazwa typu ćwiczenia nie może być pusta.")

        cur = self.conn.execute(
            "SELECT exercise_type_id FROM exercise_types WHERE name = ?",
            (name,),
        )
        row = cur.fetchone()
        if row:
            return row["exercise_type_id"]

        cur = self.conn.execute(
            "INSERT INTO exercise_types(name) VALUES (?)",
            (name,),
        )
        self.conn.commit()
        return cur.lastrowid

    def get_or_create_exercise_definition(self, exercise_type_name, exercise_name):
        exercise_type_id = self.get_or_create_exercise_type(exercise_type_name)
        exercise_name = (exercise_name or "").strip()

        if not exercise_name:
            raise ValueError("Nazwa ćwiczenia nie może być pusta.")

        cur = self.conn.execute(
            """
            SELECT exercise_definition_id
            FROM exercise_definitions
            WHERE exercise_type_id = ? AND name = ?
            """,
            (exercise_type_id, exercise_name),
        )
        row = cur.fetchone()
        if row:
            return row["exercise_definition_id"]

        cur = self.conn.execute(
            """
            INSERT INTO exercise_definitions(exercise_type_id, name)
            VALUES (?, ?)
            """,
            (exercise_type_id, exercise_name),
        )
        self.conn.commit()
        return cur.lastrowid

    def create_training_session(self, user_id, started_at=None, notes=""):
        started_at = started_at or datetime.now().isoformat(timespec="seconds")
        cur = self.conn.execute(
            """
            INSERT INTO training_sessions(user_id, started_at, notes)
            VALUES (?, ?, ?)
            """,
            (user_id, started_at, notes),
        )
        self.conn.commit()
        return cur.lastrowid

    def add_exercise_attempt(
        self,
        session_id,
        exercise_definition_id,
        successful,
        duration_seconds=None,
        reps=None,
        weight_kg=None,
        distance_meters=None,
    ):
        cur = self.conn.execute(
            """
            INSERT INTO exercise_attempts(
                session_id,
                exercise_definition_id,
                successful,
                duration_seconds,
                reps,
                weight_kg,
                distance_meters
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session_id,
                exercise_definition_id,
                int(bool(successful)),
                duration_seconds,
                reps,
                weight_kg,
                distance_meters,
            ),
        )
        self.conn.commit()
        return cur.lastrowid

    def save_training_result(
        self,
        username,
        exercise_name,
        successful,
        duration_seconds,
        reps,
        exercise_type_name="Podnoszenie przedmiotu",
        notes="",
        started_at=None,
    ):
        user_id = self.get_or_create_user(username)
        exercise_definition_id = self.get_or_create_exercise_definition(
            exercise_type_name=exercise_type_name,
            exercise_name=exercise_name,
        )
        session_id = self.create_training_session(
            user_id=user_id,
            started_at=started_at,
            notes=notes,
        )
        attempt_id = self.add_exercise_attempt(
            session_id=session_id,
            exercise_definition_id=exercise_definition_id,
            successful=successful,
            duration_seconds=int(duration_seconds or 0),
            reps=int(reps or 0),
        )
        return {
            "user_id": user_id,
            "session_id": session_id,
            "attempt_id": attempt_id,
        }

    def fetch_attempt_data(self):
        cur = self.conn.execute("""
        SELECT
            u.username,
            ts.started_at,
            ea.successful,
            ea.duration_seconds,
            ea.reps,
            ea.weight_kg,
            ea.distance_meters,
            ed.name AS exercise_name,
            et.name AS exercise_type
        FROM exercise_attempts ea
        JOIN training_sessions ts
            ON ea.session_id = ts.session_id
        JOIN users u
            ON ts.user_id = u.user_id
        JOIN exercise_definitions ed
            ON ea.exercise_definition_id = ed.exercise_definition_id
        JOIN exercise_types et
            ON ed.exercise_type_id = et.exercise_type_id
        ORDER BY ts.started_at
        """)

        return [dict(row) for row in cur.fetchall()]


    def fetch_user_comparison_stats(self):
        """
        Zwraca zbiorcze statystyki wszystkich użytkowników.
        Użytkownicy bez treningów również są zwracani z wartościami 0,
        dzięki czemu wykres faktycznie porównuje wszystkich użytkowników z bazy.
        """
        cur = self.conn.execute("""
        SELECT
            u.user_id,
            u.username,
            COALESCE(u.display_name, u.username) AS display_name,
            COUNT(ea.attempt_id) AS attempts,
            COALESCE(SUM(ea.reps), 0) AS total_reps,
            COALESCE(SUM(ea.duration_seconds), 0) AS total_duration_seconds,
            COALESCE(SUM(CASE WHEN ea.successful = 1 THEN 1 ELSE 0 END), 0) AS successful_attempts,
            CASE
                WHEN COUNT(ea.attempt_id) = 0 THEN 0.0
                ELSE 100.0 * SUM(CASE WHEN ea.successful = 1 THEN 1 ELSE 0 END) / COUNT(ea.attempt_id)
            END AS success_rate
        FROM users u
        LEFT JOIN training_sessions ts
            ON u.user_id = ts.user_id
        LEFT JOIN exercise_attempts ea
            ON ts.session_id = ea.session_id
        GROUP BY u.user_id, u.username, u.display_name
        ORDER BY total_reps DESC, attempts DESC, u.username COLLATE NOCASE
        """)

        return [dict(row) for row in cur.fetchall()]

    def fetch_team_stats(self):
        cur = self.conn.execute("""
        SELECT
            t.name AS team_name,
            COUNT(ea.attempt_id) AS attempts
        FROM teams t
        JOIN team_members tm
            ON t.team_id = tm.team_id
        JOIN users u
            ON tm.user_id = u.user_id
        JOIN training_sessions ts
            ON u.user_id = ts.user_id
        JOIN exercise_attempts ea
            ON ts.session_id = ea.session_id
        GROUP BY t.team_id
        """)

        return [dict(row) for row in cur.fetchall()]

    def close(self):
        self.conn.close()
