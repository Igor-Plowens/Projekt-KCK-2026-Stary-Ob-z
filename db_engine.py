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
            exercise_definition_id
                INTEGER PRIMARY KEY AUTOINCREMENT,

            exercise_type_id INTEGER NOT NULL,

            name TEXT NOT NULL,

            FOREIGN KEY (exercise_type_id)
                REFERENCES exercise_types(
                    exercise_type_id
                )
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
                REFERENCES training_sessions(
                    session_id
                )
                ON DELETE CASCADE,

            FOREIGN KEY (exercise_definition_id)
                REFERENCES exercise_definitions(
                    exercise_definition_id
                )
                ON DELETE CASCADE
        );
        """)

        self.conn.commit()

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
            ON ea.exercise_definition_id =
               ed.exercise_definition_id

        JOIN exercise_types et
            ON ed.exercise_type_id =
               et.exercise_type_id

        ORDER BY ts.started_at
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

    def get_or_create_user(self, username, display_name=None):
        cur = self.conn.execute(
            "SELECT user_id FROM users WHERE username = ?",
            (username,)
        )
        row = cur.fetchone()

        if row:
            return row["user_id"]

        return self.add_user(username, display_name or username)

    def add_user(self, username, display_name=None):
        cur = self.conn.execute(
            "INSERT OR IGNORE INTO users(username, display_name) VALUES (?, ?)",
            (username, display_name or username)
        )
        self.conn.commit()

        if cur.lastrowid:
            return cur.lastrowid

        return self.get_or_create_user(username, display_name)

    def fetch_users(self):
        cur = self.conn.execute(
            "SELECT user_id, username, display_name FROM users ORDER BY username"
        )
        return [dict(row) for row in cur.fetchall()]

    def ensure_default_datw(self):
        self.get_or_create_user("XYZ", "XYZ")
        self.get_or_create_exercise_definition(
            exercise_type_name="Podnoszenie przedmiotu",
            exercise_name="Podnoszenie przedmiotu z podłogi na stół",
        )



    def get_usernames(self):
        return [row["username"] for row in self.fetch_users()]

    def close(self):
        self.conn.close()
