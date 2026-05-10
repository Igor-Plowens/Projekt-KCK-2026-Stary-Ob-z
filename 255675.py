import sys
import cv2

from PyQt6 import uic
from PyQt6.QtWidgets import QApplication, QMainWindow, QGraphicsScene
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtCore import QTimer

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi("OknoProgramu.ui", self)

        self.scene = QGraphicsScene()
        self.graphicsView.setScene(self.scene)

        self.scene2 = QGraphicsScene()
        self.graphicsView_2.setScene(self.scene2)

        self.cap = cv2.VideoCapture(0)
        self.cap2 = cv2.VideoCapture(1)

        if not self.cap.isOpened():
            print("Nie można otworzyć kamery 0")
            sys.exit()

        if not self.cap2.isOpened():
            print("Nie można otworzyć kamery 1")
            sys.exit()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(30)  # ~33 FPS

    def update_frame(self):
        ret, frame = self.cap.read()
        if ret and frame is not None:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frame = frame.copy()

            h, w, ch = frame.shape
            bytes_per_line = ch * w

            image = QImage(frame.data,w,h,bytes_per_line,QImage.Format.Format_RGB888)

            pixmap = QPixmap.fromImage(image)
            self.scene.clear()
            self.scene.addPixmap(pixmap)

        ret2, frame2 = self.cap2.read()
        if ret2 and frame2 is not None:
            frame2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2RGB)
            frame2 = frame2.copy()

            h, w, ch = frame2.shape
            bytes_per_line = ch * w

            image2 = QImage(frame2.data,w,h,bytes_per_line,QImage.Format.Format_RGB888)

            pixmap2 = QPixmap.fromImage(image2)
            self.scene2.clear()
            self.scene2.addPixmap(pixmap2)

    def closeEvent(self, event):
        if self.cap.isOpened():
            self.cap.release()

        if self.cap2.isOpened():
            self.cap2.release()

        event.accept()

if __name__ == "__main__":

    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())