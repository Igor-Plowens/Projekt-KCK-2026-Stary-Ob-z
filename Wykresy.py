import db_engine as db
import matplotlib.pyplot as plt
from collections import defaultdict
from datetime import datetime, timedelta
import random



class CyberTrainerAnalytics:
    def __init__(self, db):
        self.db = db

    def plot_monthly_training_count(self):
        trainings = self.db.get_all_trainings()

        monthly = defaultdict(int)

        for training in trainings:
            month = training["training_date"][:7]
            monthly[month] += 1

        months = sorted(monthly.keys())
        totals = [monthly[m] for m in months]

        plt.figure(figsize=(10, 5))

        plt.plot(
            months,
            totals,
            marker="o",
            linewidth=3
        )

        plt.title("Monthly Training Sessions")
        plt.xlabel("Month")
        plt.ylabel("Sessions")

        plt.grid(True)

        plt.tight_layout()
        plt.show()


    def plot_monthly_success_rate(self):
        rows = self.db.fetch_flat_training_data()

        monthly = defaultdict(
            lambda: {
                "success": 0,
                "total": 0
            }
        )

        for row in rows:
            month = row["training_date"][:7]

            monthly[month]["total"] += 1

            if row["successful"]:
                monthly[month]["success"] += 1

        months = sorted(monthly.keys())

        success_rates = []

        for month in months:
            data = monthly[month]

            rate = (
                data["success"] /
                data["total"]
            ) * 100

            success_rates.append(rate)

        plt.figure(figsize=(10, 5))

        plt.plot(
            months,
            success_rates,
            marker="o",
            linewidth=3
        )

        plt.title("Monthly Success Rate")
        plt.xlabel("Month")
        plt.ylabel("Success Rate (%)")

        plt.ylim(0, 100)

        plt.grid(True)

        plt.tight_layout()
        plt.show()


    def plot_monthly_training_time(self):
        rows = self.db.fetch_flat_training_data()

        monthly_seconds = defaultdict(int)

        for row in rows:
            month = row["training_date"][:7]

            monthly_seconds[month] += row[
                "duration_in_seconds"
            ]

        months = sorted(monthly_seconds.keys())

        hours = [
            monthly_seconds[m] / 3600
            for m in months
        ]

        plt.figure(figsize=(10, 5))

        plt.bar(months, hours)

        plt.title("Monthly Training Time")
        plt.xlabel("Month")
        plt.ylabel("Hours")

        plt.tight_layout()
        plt.show()

    def plot_category_distribution(self):
        rows = self.db.fetch_flat_training_data()

        categories = defaultdict(int)

        for row in rows:
            categories[row["category_name"]] += 1

        labels = list(categories.keys())
        values = list(categories.values())

        plt.figure(figsize=(8, 8))

        plt.pie(
            values,
            labels=labels,
            autopct="%1.1f%%"
        )

        plt.title("Exercise Category Distribution")

        plt.tight_layout()
        plt.show()

    # =====================================================
    # GRAPH 5
    # SUCCESS RATE BY CATEGORY
    # =====================================================

    def plot_success_by_category(self):
        rows = self.db.fetch_flat_training_data()

        categories = defaultdict(
            lambda: {
                "success": 0,
                "total": 0
            }
        )

        for row in rows:
            cat = row["category_name"]

            categories[cat]["total"] += 1

            if row["successful"]:
                categories[cat]["success"] += 1

        labels = []
        success_rates = []

        for cat, data in categories.items():
            labels.append(cat)

            rate = (
                data["success"] /
                data["total"]
            ) * 100

            success_rates.append(rate)

        plt.figure(figsize=(10, 5))

        plt.bar(
            labels,
            success_rates
        )

        plt.title("Success Rate By Category")
        plt.ylabel("Success Rate (%)")

        plt.ylim(0, 100)

        plt.tight_layout()
        plt.show()


    def plot_daily_activity(self):
        trainings = self.db.get_all_trainings()

        daily = defaultdict(int)

        for training in trainings:
            daily[training["training_date"]] += 1

        dates = sorted(daily.keys())

        x = [
            datetime.strptime(
                d,
                "%Y-%m-%d"
            )
            for d in dates
        ]

        y = [daily[d] for d in dates]

        plt.figure(figsize=(14, 5))

        plt.bar(x, y)

        plt.title("Daily Training Activity")
        plt.xlabel("Date")
        plt.ylabel("Sessions")

        plt.tight_layout()
        plt.show()



def populate_demo_data(db):
    existing = db.conn.execute("""
        SELECT COUNT(*) AS count
        FROM trainings
    """).fetchone()["count"]

    if existing > 0:
        print("Database already contains data.")
        return
    categories = {
        "Pompki": db.create_category(
            "Pompki",
            "Standardowe męskie pompki"
        ),

        "Brzuszki": db.create_category(
            "Brzuszki",
            "Standardowe brzuszki"
        ),

        "Podnoszenie ciężaru": db.create_category(
            "Podnoszenie ciężaru",
            "Standardowe podnoszenie ciężaru"
        ),

        "Przysiady": db.create_category(
            "Przysiady",
            "Standardowe przysiady"
        )
    }

    start_date = datetime(2025, 1, 1)

    for day_offset in range(180):
        current_date = start_date + timedelta(days=day_offset)
        if random.random() < 0.65:

            training_id = db.create_training(
                current_date.strftime("%Y-%m-%d"),
                notes="Automated demo training"
            )

            for series_index in range(
                random.randint(1, 3)
            ):
                series_id = db.create_series(
                    name=f"Series {series_index + 1}",
                    description="Generated series"
                )

                for exercise_index in range(
                    random.randint(3, 8)
                ):
                    category_name = random.choice(
                        list(categories.keys())
                    )

                    exercise_id = db.create_exercise(
                        exercise_type_id=categories[
                            category_name
                        ],

                        duration_in_seconds=random.randint(
                            120,
                            2400
                        ),

                        successful=random.random() < 0.75
                    )

                    db.add_exercise_to_series(
                        series_id=series_id,
                        exercise_index=exercise_index,
                        exercise_id=exercise_id
                    )

                db.add_series_to_training(
                    training_id=training_id,
                    series_index=series_index,
                    series_id=series_id
                )

    print("Demo data inserted.")



if __name__ == "__main__":
    db = db.CyberTrainerDB()

    populate_demo_data(db)

    analytics = CyberTrainerAnalytics(db)

    analytics.plot_monthly_training_count()

    analytics.plot_monthly_success_rate()

    analytics.plot_monthly_training_time()

    analytics.plot_category_distribution()

    analytics.plot_success_by_category()

    analytics.plot_daily_activity()

    db.close()
