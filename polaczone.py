import sys
import os
import cv2
import mediapipe as mp
from wideo import check_brak_pochylenia_lewo_prawo, check_brak_zgarbienia
from wideo import start
import time
from PyQt6.QtWidgets import QApplication, QMainWindow, QGraphicsScene
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtCore import QTimer, Qt, QUrl
from PyQt6.QtMultimedia import QSoundEffect

from ui_okno import Ui_MainWindow  # <- wygenerowany plik

second_camera = False


class MainWindow(QMainWindow, Ui_MainWindow):
    def __init__(self):
        super().__init__()
        self.setupUi(self)

        self.scene = QGraphicsScene()
        self.KameraLewa.setScene(self.scene)

        self.mp_pose = mp.solutions.pose
        self.mp_drawing = mp.solutions.drawing_utils
        self.pose = self.mp_pose.Pose();
        self.scene2 = QGraphicsScene()
        self.KameraPrawa.setScene(self.scene2)
        self.quitTimer = None
        self.sounds = {}
        self.last_sound_name = None
        self.last_sound_time = 0
        self.sound_cooldown = 4
        self.load_sounds()
        # kamera 1
        self.cap = cv2.VideoCapture(0)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

        if not self.cap.isOpened():
            print("Nie można otworzyć kamery 0")
            sys.exit()

        # kamera 2
        self.cap2 = None
        if second_camera:
            self.cap2 = cv2.VideoCapture(1)
            self.cap2.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
            self.cap2.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

            if not self.cap2.isOpened():
                print("Nie można otworzyć kamery 1")
                sys.exit()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(30)

    def load_sounds(self):
        sounds_dir = os.path.join(os.path.dirname(__file__), "assets", "sounds")
        sound_files = {
            "back": "proste_plecy.wav",
            "head": "glowa_do_tylu.wav",
            "position": "popraw_pozycje.wav",
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

    def play_posture_sound(self, sound_name):
        now = time.time()

        if now - self.last_sound_time < self.sound_cooldown:
            return

        sound = self.sounds.get(sound_name)
        if sound is None or sound.source().isEmpty() or sound.isPlaying():
            return

        sound.play()
        self.last_sound_name = sound_name
        self.last_sound_time = now

    def update_frame(self):
        ret, frame = self.cap.read()
        if ret:
            self.show_frame(frame, self.KameraLewa, self.scene)

        if second_camera and self.cap2:
            ret2, frame2 = self.cap2.read()
            if ret2:
                self.show_frame(frame2, self.KameraPrawa, self.scene2)

    def show_frame(self, frame, view, scene):
        draw_frame = frame.copy()

        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        results = self.pose.process(rgb_frame)

        letter = ""
        back_straight = False
        glowa_niewysunieta = False
        # rysowanie szkieletu
        if results.pose_landmarks:
            landmarks = results.pose_landmarks.landmark

            letter = start(landmarks,self.excercise,self.part)
            back_straight = check_brak_pochylenia_lewo_prawo(landmarks)
            glowa_niewysunieta = check_brak_zgarbienia(landmarks)

            self.mp_drawing.draw_landmarks(
                draw_frame,
                results.pose_landmarks,
                self.mp_pose.POSE_CONNECTIONS
            )

        # napisy
        if self.quitTimer is not None:
            progress = int((((time.time() - self.quitTimer) * 10) / 5))

            cv2.putText(
                draw_frame,
                f"[{'||' * progress}{' ' * (10 - progress)}]",
                (30, 60),
                cv2.FONT_HERSHEY_SIMPLEX,
                1.5,
                (0, 255, 0),
                3
            )

        if letter == "N":
            self.play_posture_sound("position")

        if results.pose_landmarks:
            if not back_straight:
                self.play_posture_sound("back")
            elif not glowa_niewysunieta:
                self.play_posture_sound("head")
        if letter == "working on it":
            cv2.putText(
                draw_frame,
                f"etap: {self.part}",
                (30, 60),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (0, 255, 0),
                3
            )
        if letter == "ok":
            cv2.putText(
                draw_frame,
                "etap ukonczony",
                (30, 60),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (0, 255, 0),
                3
            )
            self.part+=1
            if self.part == 4:
                self.part=1

        if letter == "S":
            if self.quitTimer is None:
                self.quitTimer = time.time()

            elif time.time() - self.quitTimer >= 5:
                sys.exit(app.exec())
        # tu sie kończy

        else:
            self.quitTimer = None

        # konwersja do RGB do Qt
        qt_frame = cv2.cvtColor(draw_frame, cv2.COLOR_BGR2RGB)

        h, w, ch = qt_frame.shape
        bytes_per_line = ch * w

        image = QImage(
            qt_frame.data,
            w,
            h,
            bytes_per_line,
            QImage.Format.Format_RGB888
        )

        pixmap = QPixmap.fromImage(image)

        pixmap = pixmap.scaled(
            view.viewport().size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )

        scene.clear()
        scene.addPixmap(pixmap)

    def closeEvent(self, event):
        if self.cap:
            self.cap.release()

        if self.cap2:
            self.cap2.release()

        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())