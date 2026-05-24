import sys
import cv2
import mediapipe as mp
from wideo import start
import time
from PyQt6.QtWidgets import QApplication, QMainWindow, QGraphicsScene
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtCore import QTimer, Qt

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
        # kamera 1
        self.cap = cv2.VideoCapture(0)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

        self.excercise = 1
        self.part = 1
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

        # rysowanie szkieletu
        if results.pose_landmarks:
            landmarks = results.pose_landmarks.landmark

            letter = start(landmarks,self.excercise,self.part)

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
            cv2.putText(
                draw_frame,
                "Ustaw sie dobrze",
                (30, 60),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (0, 255, 0),
                3
            )
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