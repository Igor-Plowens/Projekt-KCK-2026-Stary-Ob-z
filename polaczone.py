import os
import sys
import time
import traceback
from datetime import datetime

import cv2
import numpy as np

from PyQt6.QtCore import Qt, QThread, QUrl
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtMultimedia import QSoundEffect
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QGraphicsScene,
    QInputDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
)

from camera_worker import CameraWorker, CameraResult
from db_engine import CyberTrainerDB
from stany import Stany, StanTreningu
from ui_okno import Ui_MainWindow
from wideo import PrzysiadCounter
from Wykresy import CyberTrainerAnalytics


class MainWindow(QMainWindow, Ui_MainWindow):
    """
    Główny wątek aplikacji.

    Ten obiekt obsługuje wyłącznie UI, dźwięki, bazę danych i łączenie wyników
    z workerów kamer. Odczyt kamer oraz MediaPipe działają w osobnych QThreadach
    w pliku camera_worker.py.
    """

    def __init__(self):
        super().__init__()
        self.setupUi(self)
        self.setWindowTitle("Cyber Trener")

        self.scene_menu = QGraphicsScene(self)
        self.KameraMenu.setScene(self.scene_menu)

        self.scene_left = QGraphicsScene(self)
        self.KameraLewa.setScene(self.scene_left)

        self.scene_right = QGraphicsScene(self)
        self.KameraPrawa.setScene(self.scene_right)

        self.stream_targets = {
            "menu": (self.KameraMenu, self.scene_menu),
            "front": (self.KameraLewa, self.scene_left),
            "side": (self.KameraPrawa, self.scene_right),
        }
        self.camera_threads = {}
        self.camera_workers = {}
        self.latest_results = {
            "front": None,
            "side": None,
        }

        self.stop_gesture_started_at = None
        self.exercise = 1
        self.part = 1
        self.last_ok_time = 0
        self.rep_counter = PrzysiadCounter(wymagane_powtorzenia=3)
        self.training_started_at = None
        self.result_saved = False
        self.summary_requested_by_reps = False
        self._handling_camera_error = False

        self.db = CyberTrainerDB()
        self.current_user = "XYZ"
        self.current_user_id = self.db.get_or_create_user(self.current_user, self.current_user)
        self.users = self.db.get_usernames()
        self.titleLabel.setText(f"Witaj {self.current_user}!")

        self.sounds = {}
        self.last_sound_name = None
        self.last_sound_time = 0
        self.sound_cooldown = 4
        self.load_sounds()

        self.stany = None
        self.create_stany()

        self.connect_buttons()
        self.set_page("menu")
        self.show_blank(self.KameraMenu, self.scene_menu, "Kamera menu gotowa")
        self.show_blank(self.KameraLewa, self.scene_left, "Kamera przednia gotowa")
        self.show_blank(self.KameraPrawa, self.scene_right, "Kamera boczna gotowa")
        self.start_menu_preview()

    # --------------------------------------------------
    # Bezpieczne opakowanie
    # --------------------------------------------------

    def show_error(self, title, exc):
        text = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
        print(text)
        QMessageBox.critical(self, title, text[-3500:])

    def set_page(self, page_name):
        pages = {
            "menu": getattr(self, "page_menu", None),
            "training": getattr(self, "page_training", None),
            "summary": getattr(self, "page_summary", None),
        }
        page = pages.get(page_name)
        if page is not None:
            self.stackedWidget.setCurrentWidget(page)
            return

        # Fallback, gdy ui_okno.py jest nieaktualny względem OknoProgramu.ui.
        index_fallback = {"menu": 0, "training": 1, "summary": 2}.get(page_name, 0)
        if index_fallback < self.stackedWidget.count():
            self.stackedWidget.setCurrentIndex(index_fallback)

    # --------------------------------------------------
    # Przyciski
    # --------------------------------------------------

    def connect_buttons(self):
        self.startButton.clicked.connect(self.start_training_safe)
        self.exitButton.clicked.connect(self.close)
        self.startAgainButton.clicked.connect(self.start_training_safe)
        self.backToMenuButton.clicked.connect(self.show_menu)

        if hasattr(self, "trainingQualityChartButton"):
            self.trainingQualityChartButton.clicked.connect(self.show_current_training_quality_chart)

        if hasattr(self, "chooseUserButton"):
            self.chooseUserButton.clicked.connect(self.choose_user)
        if hasattr(self, "addUserButton"):
            self.addUserButton.clicked.connect(self.add_user)
        if hasattr(self, "statsButton"):
            self.statsButton.clicked.connect(self.show_all_users_stats)

    def start_training_safe(self):
        try:
            self.start_training()
        except Exception as exc:
            self.stop_camera(clear_scenes=False)
            self.show_error("Błąd startu treningu", exc)
            self.set_page("menu")
            self.start_menu_preview()

    def refresh_users(self):
        self.users = self.db.get_usernames()

    def choose_user(self):
        self.refresh_users()

        if not self.users:
            QMessageBox.information(self, "Użytkownik", "Najpierw dodaj użytkownika.")
            return

        user, accepted = QInputDialog.getItem(
            self,
            "Wybierz użytkownika",
            "Użytkownik:",
            self.users,
            self.users.index(self.current_user) if self.current_user in self.users else 0,
            False,
        )

        if not accepted or not user:
            return

        self.current_user = user
        self.current_user_id = self.db.get_or_create_user(user)
        self.titleLabel.setText(f"Witaj {self.current_user}!")

    def add_user(self):
        user, accepted = QInputDialog.getText(
            self,
            "Dodaj użytkownika",
            "Nazwa użytkownika:",
        )

        if not accepted:
            return

        user = user.strip()
        if not user:
            QMessageBox.warning(self, "Dodaj użytkownika", "Nazwa użytkownika nie może być pusta.")
            return

        try:
            self.current_user_id = self.db.add_user(user, user)
        except Exception as exc:
            QMessageBox.critical(self, "Baza danych", f"Nie udało się dodać użytkownika:\n{exc}")
            return

        self.refresh_users()
        self.current_user = user
        self.titleLabel.setText(f"Witaj {self.current_user}!")
        QMessageBox.information(self, "Dodaj użytkownika", f"Dodano / wybrano użytkownika: {user}")


    def show_all_users_stats(self):
        try:
            charts_dir = os.path.join(os.path.dirname(__file__), "assets", "charts")
            os.makedirs(charts_dir, exist_ok=True)
            output_path = os.path.join(charts_dir, "porownanie_uzytkownikow.png")

            analytics = CyberTrainerAnalytics(self.db)
            analytics.save_users_comparison_chart(output_path)

            rows = self.db.fetch_user_comparison_stats()

            dialog = QDialog(self)
            dialog.setWindowTitle("Statystyki użytkowników")
            dialog.resize(1100, 720)

            layout = QVBoxLayout(dialog)

            title = QLabel("Porównanie statystyk wszystkich użytkowników", dialog)
            title.setAlignment(Qt.AlignmentFlag.AlignCenter)
            title.setStyleSheet("font-size: 18px; font-weight: 700;")
            layout.addWidget(title)

            chart_label = QLabel(dialog)
            chart_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            pixmap = QPixmap(output_path)
            if pixmap.isNull():
                chart_label.setText("Nie udało się wczytać wykresu.")
            else:
                if pixmap.width() > 1040:
                    pixmap = pixmap.scaledToWidth(
                        1040,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                chart_label.setPixmap(pixmap)

            chart_scroll = QScrollArea(dialog)
            chart_scroll.setWidgetResizable(False)
            chart_scroll.setWidget(chart_label)
            layout.addWidget(chart_scroll, 3)

            summary_label = QLabel(self.format_users_stats_summary(rows), dialog)
            summary_label.setWordWrap(True)
            summary_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

            scroll = QScrollArea(dialog)
            scroll.setWidgetResizable(True)
            scroll.setWidget(summary_label)
            layout.addWidget(scroll)

            close_button = QPushButton("Zamknij", dialog)
            close_button.clicked.connect(dialog.accept)
            layout.addWidget(close_button)

            dialog.exec()
        except Exception as exc:
            self.show_error("Błąd podczas wyświetlania statystyk", exc)

    def show_after_training_stats(self):
        try:
            charts_dir = os.path.join(os.path.dirname(__file__), "assets", "charts")
            os.makedirs(charts_dir, exist_ok=True)
            output_path = os.path.join(charts_dir, "statystyki_po_treningu.png")

            analytics = CyberTrainerAnalytics(self.db)
            analytics.save_users_comparison_chart(output_path)

            rows = self.db.fetch_user_comparison_stats()

            dialog = QDialog(self)
            dialog.setWindowTitle("Statystyki po treningu")
            dialog.resize(1100, 720)

            layout = QVBoxLayout(dialog)

            title = QLabel("Porównanie statystyk wszystkich użytkowników", dialog)
            title.setAlignment(Qt.AlignmentFlag.AlignCenter)
            title.setStyleSheet("font-size: 18px; font-weight: 700;")
            layout.addWidget(title)

            chart_label = QLabel(dialog)
            chart_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            pixmap = QPixmap(output_path)
            if pixmap.isNull():
                chart_label.setText("Nie udało się wczytać wykresu.")
            else:
                if pixmap.width() > 1040:
                    pixmap = pixmap.scaledToWidth(
                        1040,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                chart_label.setPixmap(pixmap)

            chart_scroll = QScrollArea(dialog)
            chart_scroll.setWidgetResizable(False)
            chart_scroll.setWidget(chart_label)
            layout.addWidget(chart_scroll, 3)

            summary_label = QLabel(self.format_users_stats_summary(rows), dialog)
            summary_label.setWordWrap(True)
            summary_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

            scroll = QScrollArea(dialog)
            scroll.setWidgetResizable(True)
            scroll.setWidget(summary_label)
            layout.addWidget(scroll)

            close_button = QPushButton("Zamknij", dialog)
            close_button.clicked.connect(dialog.accept)
            layout.addWidget(close_button)

            dialog.exec()
        except Exception as exc:
            self.show_error("Błąd podczas wyświetlania statystyk", exc)

    def show_current_training_quality_chart(self):
        try:
            wynik = self.stany.ostatni_wynik if self.stany else None
            if wynik is None:
                QMessageBox.information(
                    self,
                    "Jakość treningu",
                    "Brak wyniku bieżącego treningu do pokazania.",
                )
                return

            charts_dir = os.path.join(os.path.dirname(__file__), "assets", "charts")
            os.makedirs(charts_dir, exist_ok=True)
            output_path = os.path.join(charts_dir, "jakosc_biezacego_treningu.png")

            analytics = CyberTrainerAnalytics(self.db)
            chart_path = analytics.save_current_training_quality_chart(wynik, output_path) or output_path

            dialog = QDialog(self)
            dialog.setWindowTitle("Jakość bieżącego treningu")
            dialog.resize(850, 560)

            layout = QVBoxLayout(dialog)

            title = QLabel("Wykres kołowy jakości treningu", dialog)
            title.setAlignment(Qt.AlignmentFlag.AlignCenter)
            title.setStyleSheet("font-size: 18px; font-weight: 700;")
            layout.addWidget(title)

            chart_label = QLabel(dialog)
            chart_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

            pixmap = QPixmap(chart_path)
            if pixmap.isNull():
                chart_label.setText("Nie udało się wczytać wykresu jakości treningu.")
            else:
                if pixmap.width() > 780:
                    pixmap = pixmap.scaledToWidth(
                        780,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                chart_label.setPixmap(pixmap)

            chart_scroll = QScrollArea(dialog)
            chart_scroll.setWidgetResizable(True)
            chart_scroll.setWidget(chart_label)
            layout.addWidget(chart_scroll, 1)

            opis = QLabel(
                f"Dobrze: {wynik.dobre_klatki}  |  "
                f"Średnio: {wynik.srednie_klatki}  |  "
                f"Źle: {wynik.zle_klatki}  |  "
                f"Poprawność: {wynik.poprawnosc:.1f}%",
                dialog,
            )
            opis.setAlignment(Qt.AlignmentFlag.AlignCenter)
            opis.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            layout.addWidget(opis)

            close_button = QPushButton("Zamknij", dialog)
            close_button.clicked.connect(dialog.accept)
            layout.addWidget(close_button)

            dialog.exec()
        except Exception as exc:
            self.show_error("Błąd podczas wyświetlania wykresu jakości treningu", exc)

    def format_users_stats_summary(self, rows):
        if not rows:
            return "Brak użytkowników w bazie danych."

        total_attempts = sum(int(row.get("attempts") or 0) for row in rows)
        total_reps = sum(int(row.get("total_reps") or 0) for row in rows)
        total_duration = sum(int(row.get("total_duration_seconds") or 0) for row in rows)

        if total_attempts == 0:
            return (
                "W bazie są użytkownicy, ale nie zapisano jeszcze żadnego treningu.\n"
                "Po zakończeniu treningów ten widok porówna liczbę powtórzeń, prób, czas i skuteczność."
            )

        lines = [
            f"Łącznie: {total_attempts} prób, {total_reps} powtórzeń, {total_duration / 60:.1f} min treningu.",
            "",
        ]

        for index, row in enumerate(rows, start=1):
            attempts = int(row.get("attempts") or 0)
            reps = int(row.get("total_reps") or 0)
            duration_minutes = int(row.get("total_duration_seconds") or 0) / 60.0
            success_rate = float(row.get("success_rate") or 0.0)
            name = row.get("display_name") or row.get("username") or "?"
            lines.append(
                f"{index}. {name}: {reps} powtórzeń, {attempts} prób, "
                f"{duration_minutes:.1f} min, skuteczność {success_rate:.1f}%."
            )

        return "\n".join(lines)

    # --------------------------------------------------
    # Stan treningu
    # --------------------------------------------------

    def create_stany(self):
        self.stany = Stany(
            on_status_changed=self.update_status,
            on_progress_changed=self.update_progress,
            on_result=self.update_result,
        )

    def start_training(self):
        self.stop_camera(clear_scenes=False)
        self.create_stany()
        self.latest_results = {"front": None, "side": None}
        self.stop_gesture_started_at = None
        self.exercise = 1
        self.part = 1
        self.last_ok_time = 0
        self.rep_counter.wymagane_powtorzenia = self.stany.wymagane_powtorzenia
        self.rep_counter.reset()
        self.training_started_at = datetime.now().isoformat(timespec="seconds")
        self.result_saved = False
        self.summary_requested_by_reps = False
        self._handling_camera_error = False

        self.set_page("training")
        self.summaryLabel.setText("Tutaj pojawią się wyniki treningu.")
        self.show_blank(self.KameraLewa, self.scene_left, "Uruchamianie kamery przedniej...")
        self.show_blank(self.KameraPrawa, self.scene_right, "Uruchamianie kamery bocznej...")

        self.stany.start()
        self.stany.potwierdz_gotowosc()
        self.stany.rozpocznij_cwiczenie()
        self.rep_counter.wymagane_powtorzenia = self.stany.wymagane_powtorzenia

        self.start_camera()
        self.play_sound("start", use_cooldown=False)

    def show_menu(self):
        self.stop_camera(clear_scenes=False)
        self.latest_results = {"front": None, "side": None}
        self.set_page("menu")
        self.start_menu_preview()

    def show_summary(self):
        if self.stany and self.stany.stan == StanTreningu.CWICZENIE:
            self.stany.wyswietl_ocene_wykonania()

        wynik = self.stany.ostatni_wynik if self.stany else None
        if wynik is None:
            self.summaryLabel.setText("Brak danych z treningu.")
        else:
            zapis = self.save_result_to_db(wynik)
            powod = (
                "Wykonano wymaganą liczbę powtórzeń."
                if self.summary_requested_by_reps
                else "Zakończono ręcznie gestem stop / przyciskiem."
            )
            komentarze = "\n".join(wynik.komentarze_postawy())
            self.summaryLabel.setText(
                f"Użytkownik: {self.current_user}\n"
                f"Ćwiczenie: {wynik.nazwa_cwiczenia}\n"
                f"Powód zakończenia: {powod}\n"
                f"Czas: {wynik.czas_trwania:.1f} s\n"
                f"Powtórzenia: {wynik.powtorzenia}/{wynik.wymagane_powtorzenia}\n"
                f"Poprawność: {wynik.poprawnosc:.1f}%\n"
                f"Dobrze: {wynik.dobre_klatki}\n"
                f"Średnio: {wynik.srednie_klatki}\n"
                f"Źle: {wynik.zle_klatki}\n"
                f"\nKomentarze:\n{komentarze}\n\n"
                f"{zapis}"
            )

        self.stop_camera(clear_scenes=False)
        self.set_page("summary")

    def save_result_to_db(self, wynik):
        if self.result_saved:
            return "Wynik był już zapisany w bazie."

        try:
            self.db.save_training_result(
                username=self.current_user,
                exercise_name=wynik.nazwa_cwiczenia,
                successful=wynik.successful,
                duration_seconds=int(wynik.czas_trwania),
                reps=wynik.powtorzenia,
                exercise_type_name="Podnoszenie przedmiotu",
                notes=(
                    f"Poprawność: {wynik.poprawnosc:.1f}%, "
                    f"dobre={wynik.dobre_klatki}, "
                    f"średnie={wynik.srednie_klatki}, "
                    f"złe={wynik.zle_klatki}"
                ),
                started_at=self.training_started_at,
            )
            self.result_saved = True
            return "Wynik zapisano w bazie danych."
        except Exception as exc:
            return f"Nie udało się zapisać wyniku w bazie: {exc}"

    # --------------------------------------------------
    # Dźwięki
    # --------------------------------------------------

    def load_sounds(self):
        sounds_dir = os.path.join(os.path.dirname(__file__), "assets", "sounds")
        sound_files = {
            "back": "proste_plecy.wav",
            "head": "glowa_do_tylu.wav",
            "position": "popraw_pozycje.wav",
            "pose": "brak_sylwetki.wav",
            "camera": "blad_kamery.wav",
            "start": "rozpoczecie_treningu_za_321.wav",
            "good": "dobrze.wav",
        }

        for name, filename in sound_files.items():
            sound = QSoundEffect(self)
            sound.setVolume(0.9)

            path = os.path.join(sounds_dir, filename)
            if os.path.exists(path):
                sound.setSource(QUrl.fromLocalFile(path))
            else:
                print(f"Brak pliku dźwiękowego: {path}")

            self.sounds[name] = sound

    def play_sound(self, sound_name, use_cooldown=True):
        now = time.time()

        if use_cooldown and now - self.last_sound_time < self.sound_cooldown:
            return

        sound = self.sounds.get(sound_name)
        if sound is None or sound.source().isEmpty() or sound.isPlaying():
            return

        sound.play()
        self.last_sound_name = sound_name
        self.last_sound_time = now

    # --------------------------------------------------
    # Workery kamer
    # --------------------------------------------------

    def start_menu_preview(self):
        """Uruchamia podgląd kamery przedniej na ekranie menu głównego."""
        self.stop_camera(clear_scenes=False)
        self.show_blank(self.KameraMenu, self.scene_menu, "Uruchamianie kamery menu...")
        self.start_stream(
            stream_name="menu",
            camera_index=0,
            camera_role="front",
            use_gesture=False,
        )
        return True

    def start_camera(self):
        """Uruchamia dwie kamery treningowe w osobnych QThreadach."""
        self.start_stream(
            stream_name="front",
            camera_index=0,
            camera_role="front",
            use_gesture=True,
        )
        self.start_stream(
            stream_name="side",
            camera_index=1,
            camera_role="side",
            use_gesture=False,
        )
        return True

    def start_stream(self, stream_name, camera_index, camera_role, use_gesture=False):
        self.stop_stream(stream_name)

        thread = QThread(self)
        worker = CameraWorker(
            camera_index=camera_index,
            stream_name=stream_name,
            camera_role=camera_role,
            use_gesture=use_gesture,
        )
        worker.set_training_context(self.exercise, self.part, use_gesture)
        worker.moveToThread(thread)

        thread.started.connect(worker.run)
        worker.frame_ready.connect(self.on_camera_result)
        worker.camera_error.connect(self.on_camera_error)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)

        self.camera_threads[stream_name] = thread
        self.camera_workers[stream_name] = worker
        thread.start()

    def stop_stream(self, stream_name):
        worker = self.camera_workers.pop(stream_name, None)
        thread = self.camera_threads.pop(stream_name, None)

        if worker is not None:
            worker.stop()

        if thread is not None:
            thread.quit()
            thread.wait(1500)

    def stop_camera(self, clear_scenes=True):
        for worker in list(self.camera_workers.values()):
            worker.stop()

        for thread in list(self.camera_threads.values()):
            thread.quit()
            thread.wait(1500)

        self.camera_workers.clear()
        self.camera_threads.clear()
        self.stop_gesture_started_at = None

        if clear_scenes:
            self.scene_menu.clear()
            self.scene_left.clear()
            self.scene_right.clear()

    def on_camera_result(self, result: CameraResult):
        target = self.stream_targets.get(result.stream_name)
        if target is not None:
            view, scene = target
            self.show_frame(result.frame, view, scene)

        if result.stream_name == "front":
            self.latest_results["front"] = result
            self.analyze_training_frame()
        elif result.stream_name == "side":
            self.latest_results["side"] = result

    def on_camera_error(self, stream_name, message):
        print(message)
        target = self.stream_targets.get(stream_name)
        if target is not None:
            view, scene = target
            self.show_blank(view, scene, message)

        self.play_sound("camera", use_cooldown=False)

        if stream_name == "menu":
            return

        if self._handling_camera_error:
            return

        self._handling_camera_error = True
        QMessageBox.critical(self, "Błąd kamery", message)
        self.show_menu()
        self._handling_camera_error = False

    def update_front_worker_context(self):
        worker = self.camera_workers.get("front")
        if worker is not None:
            worker.set_training_context(self.exercise, self.part, True)

    # --------------------------------------------------
    # Łączenie wyników kamer i logika treningu
    # --------------------------------------------------

    def analyze_training_frame(self):
        if self.stackedWidget.currentWidget() != getattr(self, "page_training", None):
            return

        left = self.latest_results.get("front")
        right = self.latest_results.get("side")

        if left is None:
            return

        # W aktualnym projekcie trening wymaga kamery bocznej, więc nie zliczamy
        # powtórzeń, dopóki druga kamera nie dostarczy pierwszego wyniku.
        if "side" in self.camera_workers and right is None:
            self.poseStatusLabel.setText("Sylwetka: czekam na kamerę boczną")
            return

        if right is not None:
            wykryto_postac = left.detected and right.detected
            plecy_proste = left.front_back_ok and right.side_back_ok
            glowa_ok = right.head_side_ok
        else:
            wykryto_postac = left.detected
            plecy_proste = left.front_back_ok
            glowa_ok = left.head_front_ok

        self.update_posture_labels(wykryto_postac, plecy_proste, glowa_ok)

        self.stany.aktualizuj_ocene_klatki(
            wykryto_postac=wykryto_postac,
            plecy_proste=plecy_proste,
            glowa_ok=glowa_ok,
            gest=left.gesture,
        )

        self.handle_training_gesture(left.gesture)

        front_landmarks = left.landmarks
        side_landmarks = right.landmarks if right is not None else None
        licznik = self.rep_counter.update(
            front_landmarks=front_landmarks,
            side_landmarks=side_landmarks,
            posture_ok=wykryto_postac and plecy_proste and glowa_ok,
        )

        if licznik["new_rep"]:
            wykonano_wszystkie = self.stany.zarejestruj_powtorzenie()
            self.play_sound("good", use_cooldown=False)

            if wykonano_wszystkie and not self.summary_requested_by_reps:
                self.summary_requested_by_reps = True
                self.update_repetition_labels("wykonano wszystkie powtórzenia")
                self.Powtorzenia_3.setText("Koniec: wykonano wszystkie powtórzenia")
                self.show_summary()
                return

        self.update_repetition_labels(licznik["stage"])
        self.play_current_correction_sound(wykryto_postac, plecy_proste, glowa_ok)
        self.handle_stop_gesture(left.gesture)

    def handle_training_gesture(self, gesture):
        if gesture != "ok":
            return

        now = time.time()
        if now - self.last_ok_time <= 0.7:
            return

        self.part += 1
        self.last_ok_time = now
        if self.part == 4:
            self.part = 1

        self.update_front_worker_context()

    # --------------------------------------------------
    # Aktualizacja UI
    # --------------------------------------------------

    def update_status(self, text):
        self.Powtorzenia_3.setText(text.split("\n")[0])

    def update_progress(self, dobre, srednie, zle, wszystkie, powtorzenia=0, wymagane_powtorzenia=0):
        self.label.setText(f"Dobrze: {dobre}")
        self.label_3.setText(f"Średnio: {srednie}")
        self.label_4.setText(f"Źle: {zle}")
        self.Powtorzenia.setText(f"Powtórzenia: {powtorzenia}/{wymagane_powtorzenia}")

    def update_result(self, wynik):
        self.Powtorzenia_2.setText(f"Poprawność: {wynik.poprawnosc:.1f}%")

    def update_repetition_labels(self, stage=""):
        if self.stany is None:
            return
        self.Powtorzenia.setText(
            f"Powtórzenia: {self.stany.powtorzenia}/{self.stany.wymagane_powtorzenia}"
        )
        if stage:
            self.Powtorzenia_2.setText(f"Etap: {stage}")

    def update_posture_labels(self, wykryto_postac, plecy_proste, glowa_ok):
        self.poseStatusLabel.setText("Sylwetka: widoczna" if wykryto_postac else "Sylwetka: brak z jednej kamery")
        self.backStatusLabel.setText("Plecy: OK" if plecy_proste else "Plecy: popraw")
        self.headStatusLabel.setText("Głowa: OK" if glowa_ok else "Głowa: cofnij / nie pochylaj")

    def play_current_correction_sound(self, wykryto_postac, plecy_proste, glowa_ok):
        if not wykryto_postac:
            self.play_sound("pose")
        elif not plecy_proste:
            self.play_sound("back")
        elif not glowa_ok:
            self.play_sound("head")

    def handle_stop_gesture(self, gesture):
        if gesture == "S":
            if self.stop_gesture_started_at is None:
                self.stop_gesture_started_at = time.time()

            elapsed = time.time() - self.stop_gesture_started_at
            self.Powtorzenia_3.setText(f"Kończenie treningu: {elapsed:.1f}/3.0 s")

            if elapsed >= 3:
                self.stop_gesture_started_at = None
                self.show_summary()
        else:
            self.stop_gesture_started_at = None

    def show_frame(self, bgr_frame, view, scene):
        rgb_frame = cv2.cvtColor(bgr_frame, cv2.COLOR_BGR2RGB)
        rgb_frame = np.ascontiguousarray(rgb_frame)
        h, w, ch = rgb_frame.shape
        image = QImage(rgb_frame.data, w, h, ch * w, QImage.Format.Format_RGB888).copy()
        pixmap = QPixmap.fromImage(image).scaled(
            view.viewport().size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        scene.clear()
        scene.addPixmap(pixmap)
        scene.setSceneRect(pixmap.rect().toRectF())

    def show_blank(self, view, scene, text):
        frame = np.zeros((720, 1280, 3), dtype=np.uint8)
        cv2.putText(frame, text, (60, 360), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 255, 255), 3)
        self.show_frame(frame, view, scene)

    def closeEvent(self, event):
        self.stop_camera()
        if hasattr(self, "db") and self.db is not None:
            self.db.close()
            self.db = None
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)

    def excepthook(exc_type, exc_value, exc_traceback):
        text = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
        print(text)
        QMessageBox.critical(None, "Nieobsłużony błąd", text[-3500:])

    sys.excepthook = excepthook

    window = MainWindow()
    window.show()
    sys.exit(app.exec())
