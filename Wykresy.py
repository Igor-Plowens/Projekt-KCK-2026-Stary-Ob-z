import db_engine as db
import matplotlib.pyplot as plt
from collections import defaultdict
from datetime import datetime, timedelta
import random



class CyberTrainerAnalytics:
    def __init__(self, db):
        self.db = db

    def plot_monthly_attempts(self):
        rows = self.db.fetch_attempt_data()

        monthly = defaultdict(int)

        for row in rows:
            month = row["completed_at"][:7]
            monthly[month] += 1

        months = sorted(monthly)

        values = [monthly[m] for m in months]

        plt.figure(figsize=(10, 5))

        plt.plot(
            months,
            values,
            marker="o"
        )

        plt.title("Monthly Exercise Attempts")
        plt.ylabel("Attempts")
        plt.grid(True)

        plt.show()

    def plot_monthly_success_rate(self):
        rows = self.db.fetch_attempt_data()

        monthly = defaultdict(
            lambda: {
                "success": 0,
                "total": 0
            }
        )

    def __init__(self, db):
        self.db = db

    def plot_monthly_activity(self):
        rows = self.db.fetch_attempt_data()

        monthly = defaultdict(int)

        for row in rows:
            month = row["started_at"][:7]
            monthly[month] += 1

        plt.figure(figsize=(10,5))

        plt.plot(
            list(monthly.keys()),
            list(monthly.values()),
            marker="o"
        )

        plt.title("Monthly Exercise Activity")

        plt.show()

    def plot_exercise_distribution(self):
        rows = self.db.fetch_attempt_data()

        counts = defaultdict(int)

        for row in rows:
            counts[row["exercise_name"]] += 1

        plt.figure(figsize=(8,8))

        plt.pie(
            counts.values(),
            labels=counts.keys(),
            autopct="%1.1f%%"
        )

        plt.title(
            "Exercise Distribution"
        )

        plt.show()

    def plot_success_rate(self):
        rows = self.db.fetch_attempt_data()

        stats = defaultdict(
            lambda:{
                "success":0,
                "total":0
            }
        )

        for row in rows:

            ex = row["exercise_name"]

            stats[ex]["total"] += 1

            if row["successful"]:
                stats[ex]["success"] += 1

        labels = []
        values = []

        for ex,data in stats.items():

            labels.append(ex)

            values.append(
                data["success"]
                /
                data["total"]
                * 100
            )

        plt.figure(figsize=(12,5))

        plt.bar(labels, values)

        plt.ylim(0,100)

        plt.title(
            "Success Rate By Exercise"
        )

        plt.show()

    def plot_user_leaderboard(self):
        rows = self.db.fetch_attempt_data()

        totals = defaultdict(int)

        for row in rows:
            totals[row["username"]] += 1

        users = sorted(
            totals,
            key=totals.get,
            reverse=True
        )

        values = [
            totals[u]
            for u in users
        ]

        plt.figure(figsize=(12,5))

        plt.bar(users, values)

        plt.title(
            "Most Active Users"
        )

        plt.ylabel(
            "Exercise Attempts"
        )

        plt.show()

    def plot_training_time(self):
        rows = self.db.fetch_attempt_data()

        totals = defaultdict(int)

        for row in rows:

            duration = (
                row["duration_seconds"]
                or 0
            )

            totals[
                row["username"]
            ] += duration

        users = list(totals.keys())

        hours = [
            totals[u] / 3600
            for u in users
        ]

        plt.figure(figsize=(12,5))

        plt.bar(users, hours)

        plt.title(
            "Training Time By User"
        )

        plt.ylabel("Hours")

        plt.show()

    def plot_team_activity(self):
        rows = self.db.fetch_team_stats()

        labels = [
            r["team_name"]
            for r in rows
        ]

        values = [
            r["attempts"]
            for r in rows
        ]

        plt.figure(figsize=(8,5))

        plt.bar(
            labels,
            values
        )

        plt.title(
            "Team Activity"
        )

        plt.show()

def populate_demo_data(database):

    if database.conn.execute(
        "SELECT COUNT(*) FROM users"
    ).fetchone()[0]:
        return

    users = []

    for i in range(10):

        cur = database.conn.execute("""
        INSERT INTO users(
            username,
            display_name
        )
        VALUES (?,?)
        """, (
            f"user{i}",
            f"User {i}"
        ))

        users.append(
            cur.lastrowid
        )

    red = database.conn.execute("""
    INSERT INTO teams(name)
    VALUES ('Red Team')
    """).lastrowid

    blue = database.conn.execute("""
    INSERT INTO teams(name)
    VALUES ('Blue Team')
    """).lastrowid

    for user in users:

        database.conn.execute("""
        INSERT INTO team_members
        VALUES (?,?)
        """, (
            random.choice(
                [red, blue]
            ),
            user
        ))

    exercise_type = database.conn.execute("""
    INSERT INTO exercise_types(name)
    VALUES ('Bodyweight')
    """).lastrowid

    exercises = []

    for name in [
        "Pushups",
        "Squats",
        "Pullups",
        "Running",
        "Plank"
    ]:

        cur = database.conn.execute("""
        INSERT INTO exercise_definitions(
            exercise_type_id,
            name
        )
        VALUES (?,?)
        """, (
            exercise_type,
            name
        ))

        exercises.append(
            cur.lastrowid
        )

    start = datetime(2025,1,1)

    for day in range(180):

        current = (
            start +
            timedelta(days=day)
        )

        for user in users:

            if random.random() < 0.5:

                cur = database.conn.execute("""
                INSERT INTO training_sessions(
                    user_id,
                    started_at
                )
                VALUES (?,?)
                """, (
                    user,
                    current.isoformat()
                ))

                session_id = cur.lastrowid

                for _ in range(
                    random.randint(3,8)
                ):

                    database.conn.execute("""
                    INSERT INTO exercise_attempts(
                        session_id,
                        exercise_definition_id,
                        successful,
                        duration_seconds,
                        reps,
                        weight_kg,
                        distance_meters
                    )
                    VALUES (?,?,?,?,?,?,?)
                    """, (
                        session_id,
                        random.choice(
                            exercises
                        ),
                        random.random() < 0.9,
                        random.randint(
                            60,
                            1800
                        ),
                        random.randint(
                            5,
                            50
                        ),
                        random.randint(
                            0,
                            100
                        ),
                        random.randint(
                            0,
                            5000
                        )
                    ))

    database.conn.commit()

if __name__ == "__main__":

    database = db.CyberTrainerDB()

    populate_demo_data(
        database
    )

    analytics = CyberTrainerAnalytics(
        database
    )

    analytics.plot_monthly_activity()

    analytics.plot_exercise_distribution()

    analytics.plot_success_rate()

    analytics.plot_user_leaderboard()

    analytics.plot_training_time()

    analytics.plot_team_activity()

    database.close()
