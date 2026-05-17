import sys
import cv2

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
        self.graphicsView.setScene(self.scene)

        self.scene2 = QGraphicsScene()
        self.graphicsView_2.setScene(self.scene2)

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

    def update_frame(self):
        ret, frame = self.cap.read()
        if ret:
            self.show_frame(frame, self.graphicsView, self.scene)

        if second_camera and self.cap2:
            ret2, frame2 = self.cap2.read()
            if ret2:
                self.show_frame(frame2, self.graphicsView_2, self.scene2)

    def show_frame(self, frame, view, scene):
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        h, w, ch = frame.shape
        bytes_per_line = ch * w

        image = QImage(frame.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)

        pixmap = QPixmap.fromImage(image)

        pixmap = pixmap.scaled(
            view.viewport().size(),
            Qt.AspectRatioMode.KeepAspectRatioByExpanding,
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