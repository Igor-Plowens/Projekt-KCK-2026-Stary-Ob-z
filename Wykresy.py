from collections import defaultdict
from datetime import datetime
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


class CyberTrainerAnalytics:
    """
    Wykresy dla aktualnej bazy fitness.db.
    Klasa korzysta z db.fetch_attempt_data(), czyli z tabel:
    users, training_sessions, exercise_attempts, exercise_definitions i exercise_types.
    """

    def __init__(self, db):
        self.db = db

    def _attempt_rows(self):
        if not hasattr(self.db, "fetch_attempt_data"):
            return []
        return self.db.fetch_attempt_data()

    def _save_or_show(self, fig, output_path=None):
        fig.tight_layout()
        if output_path:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            fig.savefig(output_path, dpi=130, bbox_inches="tight")
            plt.close(fig)
            return output_path
        plt.show()
        return None

    def _empty_chart(self, title, message, output_path=None, figsize=(7.5, 3.4)):
        fig, ax = plt.subplots(figsize=figsize)
        ax.set_title(title)
        ax.text(0.5, 0.5, message, ha="center", va="center", wrap=True)
        ax.set_axis_off()
        return self._save_or_show(fig, output_path)

    def _format_date_label(self, value):
        if not value:
            return "brak daty"
        text = str(value)
        for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
            try:
                dt = datetime.strptime(text[:19] if "S" in fmt else text[:10], fmt)
                return dt.strftime("%d.%m %H:%M") if "H" in fmt else dt.strftime("%d.%m.%Y")
            except ValueError:
                pass
        return text[:16]

    # --------------------------------------------------
    # Wykresy zapisywane do plików PNG, używane w ekranie podsumowania
    # --------------------------------------------------

    def save_current_training_quality_chart(self, wynik, output_path):
        labels = ["Dobrze", "Średnio", "Źle"]
        values = [
            int(getattr(wynik, "dobre_klatki", 0)),
            int(getattr(wynik, "srednie_klatki", 0)),
            int(getattr(wynik, "zle_klatki", 0)),
        ]

        if sum(values) == 0:
            return self._empty_chart(
                "Jakość bieżącego treningu",
                "Brak ocenionych klatek do pokazania.",
                output_path,
            )

        fig, ax = plt.subplots(figsize=(7.5, 3.4))
        ax.pie(values,labels=labels,autopct="%1.1f%%")
        ax.set_title("Jakość bieżącego treningu")
        return self._save_or_show(fig, output_path)

    def save_posture_issue_chart(self, wynik, output_path):
        labels = ["Nieproste plecy", "Głowa pochylona / wysunięta", "Brak sylwetki"]
        values = [
            int(getattr(wynik, "plecy_nieproste_klatki", 0)),
            int(getattr(wynik, "glowa_zle_klatki", 0)),
            int(getattr(wynik, "brak_sylwetki_klatki", 0)),
        ]

        if sum(values) == 0:
            return self._empty_chart(
                "Najczęstsze problemy z postawą",
                "Nie wykryto wyraźnych problemów z plecami, głową ani widocznością sylwetki.",
                output_path,
            )

        fig, ax = plt.subplots(figsize=(8.0, 3.4))
        ax.bar(labels, values)
        ax.set_title("Najczęstsze problemy z postawą")
        ax.set_ylabel("Liczba klatek")
        ax.tick_params(axis="x", labelrotation=12)
        ax.grid(axis="y", alpha=0.3)
        return self._save_or_show(fig, output_path)

    def save_user_reps_history_chart(self, username, output_path, limit=10):
        rows = [row for row in self._attempt_rows() if row.get("username") == username]
        rows = rows[-limit:]

        if not rows:
            return self._empty_chart(
                "Historia powtórzeń użytkownika",
                "Brak wcześniejszych zapisanych treningów dla tego użytkownika.",
                output_path,
            )

        labels = [self._format_date_label(row.get("started_at")) for row in rows]
        reps = [int(row.get("reps") or 0) for row in rows]

        fig, ax = plt.subplots(figsize=(8.0, 3.4))
        ax.plot(labels, reps, marker="o", linewidth=2)
        ax.set_title(f"Historia powtórzeń: {username}")
        ax.set_ylabel("Powtórzenia")
        ax.set_xlabel("Trening")
        ax.grid(True, alpha=0.3)
        ax.tick_params(axis="x", labelrotation=25)
        return self._save_or_show(fig, output_path)

    def save_success_rate_by_exercise_chart(self, output_path):
        rows = self._attempt_rows()
        if not rows:
            return self._empty_chart(
                "Skuteczność według ćwiczenia",
                "Brak zapisanych prób w bazie danych.",
                output_path,
            )

        stats = defaultdict(lambda: {"success": 0, "total": 0})
        for row in rows:
            name = row.get("exercise_name") or "Nieznane ćwiczenie"
            stats[name]["total"] += 1
            if row.get("successful"):
                stats[name]["success"] += 1

        labels = []
        values = []
        for name, data in sorted(stats.items()):
            labels.append(name)
            values.append(data["success"] / data["total"] * 100.0)

        fig, ax = plt.subplots(figsize=(8.0, 3.4))
        ax.bar(labels, values)
        ax.set_title("Skuteczność według ćwiczenia")
        ax.set_ylabel("Udane próby (%)")
        ax.set_ylim(0, 100)
        ax.tick_params(axis="x", labelrotation=15)
        ax.grid(axis="y", alpha=0.3)
        return self._save_or_show(fig, output_path)

    def save_monthly_activity_chart(self, output_path, username=None):
        rows = self._attempt_rows()
        if username:
            rows = [row for row in rows if row.get("username") == username]

        if not rows:
            return self._empty_chart(
                "Aktywność miesięczna",
                "Brak zapisanych treningów do pokazania.",
                output_path,
            )

        monthly = defaultdict(int)
        for row in rows:
            started_at = str(row.get("started_at") or "")
            month = started_at[:7] if len(started_at) >= 7 else "brak daty"
            monthly[month] += 1

        months = sorted(monthly.keys())
        values = [monthly[month] for month in months]

        fig, ax = plt.subplots(figsize=(8.0, 3.4))
        ax.plot(months, values, marker="o", linewidth=2)
        ax.set_title("Aktywność miesięczna" + (f": {username}" if username else ""))
        ax.set_ylabel("Liczba prób")
        ax.set_xlabel("Miesiąc")
        ax.grid(True, alpha=0.3)
        return self._save_or_show(fig, output_path)


    def _user_comparison_rows(self):
        if hasattr(self.db, "fetch_user_comparison_stats"):
            return self.db.fetch_user_comparison_stats()

        rows = self._attempt_rows()
        stats = defaultdict(
            lambda: {
                "username": "?",
                "display_name": "?",
                "attempts": 0,
                "total_reps": 0,
                "total_duration_seconds": 0,
                "successful_attempts": 0,
                "success_rate": 0.0,
            }
        )

        for row in rows:
            username = row.get("username") or "?"
            stats[username]["username"] = username
            stats[username]["display_name"] = username
            stats[username]["attempts"] += 1
            stats[username]["total_reps"] += int(row.get("reps") or 0)
            stats[username]["total_duration_seconds"] += int(row.get("duration_seconds") or 0)
            if row.get("successful"):
                stats[username]["successful_attempts"] += 1

        result = []
        for data in stats.values():
            attempts = data["attempts"]
            data["success_rate"] = (data["successful_attempts"] / attempts * 100.0) if attempts else 0.0
            result.append(data)

        return sorted(result, key=lambda item: (-item["total_reps"], -item["attempts"], item["username"]))

    def save_users_comparison_chart(self, output_path):
        """Zapisuje wykres porównujący wszystkich użytkowników z bazy danych."""
        rows = self._user_comparison_rows()

        if not rows:
            return self._empty_chart(
                "Porównanie użytkowników",
                "Brak użytkowników w bazie danych.",
                output_path,
                figsize=(9.5, 4.8),
            )

        rows_with_activity = [row for row in rows if int(row.get("attempts") or 0) > 0]
        if not rows_with_activity:
            return self._empty_chart(
                "Porównanie użytkowników",
                "Użytkownicy są dodani do bazy, ale nie zapisano jeszcze żadnego treningu.",
                output_path,
                figsize=(9.5, 4.8),
            )

        labels = [row.get("display_name") or row.get("username") or "?" for row in rows]
        total_reps = [int(row.get("total_reps") or 0) for row in rows]
        attempts = [int(row.get("attempts") or 0) for row in rows]
        success_rates = [float(row.get("success_rate") or 0.0) for row in rows]

        y = list(range(len(labels)))
        fig_height = max(4.8, 1.6 + 0.45 * len(labels))
        fig, ax = plt.subplots(figsize=(10.5, fig_height))
        bars = ax.barh(y, total_reps)

        ax.set_title("Porównanie wszystkich użytkowników — wykonane powtórzenia")
        ax.set_xlabel("Suma powtórzeń")
        ax.set_ylabel("Użytkownik")
        ax.set_yticks(y)
        ax.set_yticklabels(labels)
        ax.invert_yaxis()
        ax.grid(axis="x", alpha=0.3)

        max_reps = max(total_reps) if total_reps else 0
        ax.set_xlim(0, max(1, max_reps * 1.35))

        for index, bar in enumerate(bars):
            width = bar.get_width()
            opis = f"{attempts[index]} prób, {success_rates[index]:.0f}% ud."
            ax.text(
                width + max(0.05, max_reps * 0.02),
                bar.get_y() + bar.get_height() / 2,
                opis,
                ha="left",
                va="center",
                fontsize=8,
            )

        return self._save_or_show(fig, output_path)

    # --------------------------------------------------
    # Metody zgodne ze starszym sposobem uruchamiania Wykresy.py
    # --------------------------------------------------

    def plot_monthly_activity(self):
        return self.save_monthly_activity_chart(None)

    def plot_monthly_attempts(self):
        return self.plot_monthly_activity()

    def plot_exercise_distribution(self):
        rows = self._attempt_rows()
        if not rows:
            return self._empty_chart("Rozkład ćwiczeń", "Brak danych.")

        counts = defaultdict(int)
        for row in rows:
            counts[row.get("exercise_name") or "Nieznane ćwiczenie"] += 1

        fig, ax = plt.subplots(figsize=(7, 5))
        ax.pie(counts.values(), labels=counts.keys(), autopct="%1.1f%%")
        ax.set_title("Rozkład ćwiczeń")
        return self._save_or_show(fig)

    def plot_success_rate(self):
        return self.save_success_rate_by_exercise_chart(None)

    def plot_user_leaderboard(self):
        rows = self._attempt_rows()
        if not rows:
            return self._empty_chart("Najaktywniejsi użytkownicy", "Brak danych.")

        totals = defaultdict(int)
        for row in rows:
            totals[row.get("username") or "?"] += 1

        labels = sorted(totals, key=totals.get, reverse=True)
        values = [totals[label] for label in labels]

        fig, ax = plt.subplots(figsize=(8, 4))
        ax.bar(labels, values)
        ax.set_title("Najaktywniejsi użytkownicy")
        ax.set_ylabel("Liczba prób")
        return self._save_or_show(fig)

    def plot_training_time(self):
        rows = self._attempt_rows()
        if not rows:
            return self._empty_chart("Czas treningów", "Brak danych.")

        totals = defaultdict(int)
        for row in rows:
            totals[row.get("username") or "?"] += int(row.get("duration_seconds") or 0)

        labels = list(totals.keys())
        hours = [totals[label] / 3600.0 for label in labels]

        fig, ax = plt.subplots(figsize=(8, 4))
        ax.bar(labels, hours)
        ax.set_title("Czas treningów według użytkownika")
        ax.set_ylabel("Godziny")
        return self._save_or_show(fig)

    def plot_team_activity(self):
        if not hasattr(self.db, "fetch_team_stats"):
            return self._empty_chart("Aktywność zespołów", "Baza nie udostępnia statystyk zespołów.")

        rows = self.db.fetch_team_stats()
        if not rows:
            return self._empty_chart("Aktywność zespołów", "Brak danych zespołów.")

        labels = [row.get("team_name") or "?" for row in rows]
        values = [int(row.get("attempts") or 0) for row in rows]

        fig, ax = plt.subplots(figsize=(8, 4))
        ax.bar(labels, values)
        ax.set_title("Aktywność zespołów")
        ax.set_ylabel("Liczba prób")
        return self._save_or_show(fig)


if __name__ == "__main__":
    from db_engine import CyberTrainerDB

    database = CyberTrainerDB()
    analytics = CyberTrainerAnalytics(database)
    analytics.plot_monthly_activity()
    analytics.plot_exercise_distribution()
    analytics.plot_success_rate()
    analytics.plot_user_leaderboard()
    analytics.plot_training_time()
    analytics.plot_team_activity()
    database.close()
