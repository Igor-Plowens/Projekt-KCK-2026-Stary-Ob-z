import sqlite3


class CyberTrainerDB:
    def __init__(self, db_path="cybertrainer.db"):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")

        self.create_tables()

    # =====================================================
    # TABLES
    # =====================================================

    def create_tables(self):
        self.conn.executescript("""
        CREATE TABLE IF NOT EXISTS exercise_categories (
            exercise_type_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            description TEXT
        );

        CREATE TABLE IF NOT EXISTS exercises (
            exercise_id INTEGER PRIMARY KEY AUTOINCREMENT,
            exercise_type_id INTEGER NOT NULL,
            duration_in_seconds INTEGER NOT NULL,
            successful BOOLEAN NOT NULL,

            FOREIGN KEY (exercise_type_id)
                REFERENCES exercise_categories(exercise_type_id)
                ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS series (
            series_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            description TEXT
        );

        CREATE TABLE IF NOT EXISTS series_exercises (
            series_id INTEGER NOT NULL,
            exercise_index INTEGER NOT NULL,
            exercise_id INTEGER NOT NULL,

            PRIMARY KEY (
                series_id,
                exercise_index
            ),

            FOREIGN KEY (series_id)
                REFERENCES series(series_id)
                ON DELETE CASCADE,

            FOREIGN KEY (exercise_id)
                REFERENCES exercises(exercise_id)
                ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS trainings (
            training_id INTEGER PRIMARY KEY AUTOINCREMENT,
            training_date TEXT NOT NULL,
            notes TEXT
        );

        CREATE TABLE IF NOT EXISTS training_series (
            training_id INTEGER NOT NULL,
            series_index INTEGER NOT NULL,
            series_id INTEGER NOT NULL,

            PRIMARY KEY (
                training_id,
                series_index,
                series_id
            ),

            FOREIGN KEY (training_id)
                REFERENCES trainings(training_id)
                ON DELETE CASCADE,

            FOREIGN KEY (series_id)
                REFERENCES series(series_id)
                ON DELETE CASCADE
        );
        """)

        self.conn.commit()

    # =====================================================
    # CATEGORY API
    # =====================================================

    def create_category(self, name, description=""):
        cur = self.conn.execute("""
            INSERT INTO exercise_categories(
                name,
                description
            )
            VALUES (?, ?)
        """, (name, description))

        self.conn.commit()
        return cur.lastrowid

    # =====================================================
    # EXERCISE API
    # =====================================================

    def create_exercise(
        self,
        exercise_type_id,
        duration_in_seconds,
        successful
    ):
        cur = self.conn.execute("""
            INSERT INTO exercises(
                exercise_type_id,
                duration_in_seconds,
                successful
            )
            VALUES (?, ?, ?)
        """, (
            exercise_type_id,
            duration_in_seconds,
            successful
        ))

        self.conn.commit()
        return cur.lastrowid

    # =====================================================
    # SERIES API
    # =====================================================

    def create_series(self, name="", description=""):
        cur = self.conn.execute("""
            INSERT INTO series(
                name,
                description
            )
            VALUES (?, ?)
        """, (name, description))

        self.conn.commit()
        return cur.lastrowid

    def add_exercise_to_series(
        self,
        series_id,
        exercise_index,
        exercise_id
    ):
        self.conn.execute("""
            INSERT INTO series_exercises(
                series_id,
                exercise_index,
                exercise_id
            )
            VALUES (?, ?, ?)
        """, (
            series_id,
            exercise_index,
            exercise_id
        ))

        self.conn.commit()

    # =====================================================
    # TRAINING API
    # =====================================================

    def create_training(self, training_date, notes=""):
        cur = self.conn.execute("""
            INSERT INTO trainings(
                training_date,
                notes
            )
            VALUES (?, ?)
        """, (
            training_date,
            notes
        ))

        self.conn.commit()
        return cur.lastrowid

    def add_series_to_training(
        self,
        training_id,
        series_index,
        series_id
    ):
        self.conn.execute("""
            INSERT INTO training_series(
                training_id,
                series_index,
                series_id
            )
            VALUES (?, ?, ?)
        """, (
            training_id,
            series_index,
            series_id
        ))

        self.conn.commit()

    # =====================================================
    # ANALYTICS DATA API
    # =====================================================

    def fetch_flat_training_data(self):
        """
        Flattened analytical dataset.
        """

        cur = self.conn.execute("""
        SELECT
            t.training_id,
            t.training_date,

            ts.series_index,

            s.series_id,
            s.name AS series_name,

            se.exercise_index,

            e.exercise_id,
            e.duration_in_seconds,
            e.successful,

            c.name AS category_name

        FROM trainings t

        JOIN training_series ts
            ON t.training_id = ts.training_id

        JOIN series s
            ON ts.series_id = s.series_id

        JOIN series_exercises se
            ON s.series_id = se.series_id

        JOIN exercises e
            ON se.exercise_id = e.exercise_id

        JOIN exercise_categories c
            ON e.exercise_type_id = c.exercise_type_id

        ORDER BY
            t.training_date,
            ts.series_index,
            se.exercise_index
        """)

        return [dict(row) for row in cur.fetchall()]

    def get_all_trainings(self):
        cur = self.conn.execute("""
            SELECT *
            FROM trainings
            ORDER BY training_date
        """)

        return [dict(row) for row in cur.fetchall()]

    # =====================================================
    # CLOSE
    # =====================================================

    def close(self):
        self.conn.close()