import sqlite3
from contextlib import closing


class CyberTrainerDB:
    def __init__(self, db_path="cybertrainer.db"):
        self.conn = sqlite3.connect(db_path)
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.create_tables()

    def create_tables(self):
        self.conn.executescript("""
        CREATE TABLE IF NOT EXISTS exercises (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            description TEXT
        );

        CREATE TABLE IF NOT EXISTS trainings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            training_date TEXT NOT NULL,
            total_time_seconds INTEGER,
            notes TEXT
        );

        CREATE TABLE IF NOT EXISTS sprints (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            training_id INTEGER NOT NULL,
            sprint_order INTEGER NOT NULL,

            FOREIGN KEY (training_id)
                REFERENCES trainings(id)
                ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS activity_series (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sprint_id INTEGER NOT NULL,
            series_order INTEGER NOT NULL,

            FOREIGN KEY (sprint_id)
                REFERENCES sprints(id)
                ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS activities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            series_id INTEGER NOT NULL,
            exercise_id INTEGER NOT NULL,

            quantity INTEGER NOT NULL,
            duration_seconds INTEGER DEFAULT 0,

            FOREIGN KEY (series_id)
                REFERENCES activity_series(id)
                ON DELETE CASCADE,

            FOREIGN KEY (exercise_id)
                REFERENCES exercises(id)
        );
        """)

        self.conn.commit()

    def add_exercise(self, name, description=""):
        cur = self.conn.execute(
            """
            INSERT INTO exercises(name, description)
            VALUES (?, ?)
            """,
            (name, description)
        )

        self.conn.commit()
        return cur.lastrowid

    def get_exercises(self):
        cur = self.conn.execute(
            "SELECT id, name, description FROM exercises"
        )

        return cur.fetchall()


    def create_training(self, date, total_time_seconds=0, notes=""):
        cur = self.conn.execute(
            """
            INSERT INTO trainings(training_date, total_time_seconds, notes)
            VALUES (?, ?, ?)
            """,
            (date, total_time_seconds, notes)
        )

        self.conn.commit()
        return cur.lastrowid

    def add_sprint(self, training_id, sprint_order):
        cur = self.conn.execute(
            """
            INSERT INTO sprints(training_id, sprint_order)
            VALUES (?, ?)
            """,
            (training_id, sprint_order)
        )

        self.conn.commit()
        return cur.lastrowid

    def add_series(self, sprint_id, series_order):
        cur = self.conn.execute(
            """
            INSERT INTO activity_series(sprint_id, series_order)
            VALUES (?, ?)
            """,
            (sprint_id, series_order)
        )

        self.conn.commit()
        return cur.lastrowid

    def add_activity(
        self,
        series_id,
        exercise_id,
        quantity,
        duration_seconds=0
    ):
        cur = self.conn.execute(
            """
            INSERT INTO activities(
                series_id,
                exercise_id,
                quantity,
                duration_seconds
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                series_id,
                exercise_id,
                quantity,
                duration_seconds
            )
        )

        self.conn.commit()
        return cur.lastrowid

    # ---------------------------
    # Queries
    # ---------------------------

    def get_training_activities(self, training_id):
        cur = self.conn.execute("""
        SELECT
            e.name,
            a.quantity,
            a.duration_seconds,
            s.sprint_order,
            ser.series_order
        FROM activities a
        JOIN exercises e
            ON a.exercise_id = e.id
        JOIN activity_series ser
            ON a.series_id = ser.id
        JOIN sprints s
            ON ser.sprint_id = s.id
        WHERE s.training_id = ?
        ORDER BY
            s.sprint_order,
            ser.series_order
        """, (training_id,))

        return cur.fetchall()

    def close(self):
        self.conn.close()


