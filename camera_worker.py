import os
import time
from dataclasses import dataclass
from threading import Lock

import cv2
import mediapipe as mp
import numpy as np
from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot

from wideo import (
    check_glowa_ok_bok,
    check_glowa_ok_przod,
    check_proste_plecy_bok,
    check_proste_plecy_przod,
)

try:
    from wideo import detect_training_state
except ImportError:  # zgodność ze starszą wersją wideo.py
    detect_training_state = None

try:
    from wideo import detect_letter
except ImportError:  # zgodność ze starszą wersją wideo.py
    detect_letter = None


@dataclass(frozen=True)
class SimpleLandmark:
    """Lekka kopia landmarka MediaPipe bez zależności od obiektu protobuf."""

    x: float
    y: float
    z: float = 0.0
    visibility: float = 1.0


@dataclass
class CameraResult:
    stream_name: str
    camera_role: str
    frame: np.ndarray
    detected: bool = False
    front_back_ok: bool = False
    side_back_ok: bool = False
    back_ok: bool = False
    head_front_ok: bool = False
    head_side_ok: bool = False
    head_ok: bool = False
    gesture: str = ""
    landmarks: list | None = None


class CameraWorker(QObject):
    """
    Worker uruchamiany w osobnym QThread.
    Odczytuje jedną kamerę, wykonuje analizę MediaPipe i wysyła gotowe klatki do GUI.
    QWidget/QPixmap/QGraphicsScene nie są tutaj dotykane, bo UI musi działać w głównym wątku.
    """

    frame_ready = pyqtSignal(object)
    camera_error = pyqtSignal(str, str)
    finished = pyqtSignal(str)

    def __init__(
        self,
        camera_index: int,
        stream_name: str,
        camera_role: str,
        use_gesture: bool = False,
        width: int = 1280,
        height: int = 720,
        fps: int = 30,
        parent=None,
    ):
        super().__init__(parent)
        self.camera_index = camera_index
        self.stream_name = stream_name
        self.camera_role = camera_role  # "front" albo "side"
        self.use_gesture = use_gesture
        self.width = width
        self.height = height
        self.fps = fps

        self._running = False
        self._lock = Lock()
        self._exercise = 1
        self._part = 1

        self._mp_pose = mp.solutions.pose
        self._mp_drawing = mp.solutions.drawing_utils

    def stop(self):
        with self._lock:
            self._running = False

    def set_training_context(self, exercise: int, part: int, use_gesture: bool | None = None):
        with self._lock:
            self._exercise = exercise
            self._part = part
            if use_gesture is not None:
                self.use_gesture = use_gesture

    @pyqtSlot()
    def run(self):
        cap = None
        pose = None

        with self._lock:
            self._running = True

        try:
            cap = self._open_camera()
            if not cap.isOpened():
                self.camera_error.emit(
                    self.stream_name,
                    f"Nie można otworzyć kamery {self.camera_index}.",
                )
                return

            pose = self._mp_pose.Pose(
                min_detection_confidence=0.5,
                min_tracking_confidence=0.5,
            )

            frame_delay = 1.0 / max(self.fps, 1)

            while self._is_running():
                started_at = time.time()
                ret, frame = cap.read()

                if not ret or frame is None:
                    self.frame_ready.emit(
                        CameraResult(
                            stream_name=self.stream_name,
                            camera_role=self.camera_role,
                            frame=self._blank_frame("Brak obrazu"),
                        )
                    )
                    self._sleep_to_fps(started_at, frame_delay)
                    continue

                result = self._process_frame(frame, pose)
                self.frame_ready.emit(result)
                self._sleep_to_fps(started_at, frame_delay)

        except Exception as exc:
            self.camera_error.emit(self.stream_name, f"Błąd kamery {self.camera_index}: {exc}")
        finally:
            if cap is not None:
                cap.release()
            if pose is not None:
                pose.close()
            self.finished.emit(self.stream_name)

    def _is_running(self):
        with self._lock:
            return self._running

    def _get_training_context(self):
        with self._lock:
            return self._exercise, self._part, self.use_gesture

    def _open_camera(self):
        if os.name == "nt":
            cap = cv2.VideoCapture(self.camera_index, cv2.CAP_DSHOW)
        else:
            cap = cv2.VideoCapture(self.camera_index)

        cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        return cap

    def _sleep_to_fps(self, started_at: float, frame_delay: float):
        elapsed = time.time() - started_at
        to_sleep = frame_delay - elapsed
        if to_sleep > 0:
            time.sleep(to_sleep)

    def _blank_frame(self, text: str):
        frame = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        cv2.putText(
            frame,
            text,
            (60, self.height // 2),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.5,
            (255, 255, 255),
            3,
        )
        return frame

    def _copy_landmarks(self, landmarks):
        return [
            SimpleLandmark(
                x=point.x,
                y=point.y,
                z=getattr(point, "z", 0.0),
                visibility=getattr(point, "visibility", 1.0),
            )
            for point in landmarks
        ]

    def _process_frame(self, frame, pose):
        frame = cv2.flip(frame, 1)
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = pose.process(rgb)

        detected = False
        front_back_ok = False
        side_back_ok = False
        head_front_ok = False
        head_side_ok = False
        back_ok = False
        head_ok = False
        gesture = ""
        copied_landmarks = None

        if results.pose_landmarks:
            detected = True
            landmarks = results.pose_landmarks.landmark
            copied_landmarks = self._copy_landmarks(landmarks)

            exercise, part, use_gesture = self._get_training_context()
            if use_gesture:
                if detect_training_state is not None:
                    gesture = detect_training_state(landmarks, exercise, part)
                elif detect_letter is not None:
                    gesture = detect_letter(landmarks)

            if gesture == "N":
                detected = False

            if self.camera_role == "front":
                front_back_ok = check_proste_plecy_przod(landmarks)
                head_front_ok = check_glowa_ok_przod(landmarks)
                back_ok = front_back_ok
                head_ok = head_front_ok
            else:
                side_back_ok = check_proste_plecy_bok(landmarks)
                head_side_ok = check_glowa_ok_bok(landmarks)
                back_ok = side_back_ok
                head_ok = head_side_ok

            self._mp_drawing.draw_landmarks(
                frame,
                results.pose_landmarks,
                self._mp_pose.POSE_CONNECTIONS,
            )

        # Komunikatów o błędach postawy nie wypisujemy na obrazie — zostają dźwięki i etykiety UI.
        if gesture == "S":
            self._draw_info(frame, "Gest: S")
        elif gesture == "T":
            self._draw_info(frame, "Gest: T")
        elif gesture == "working on it":
            _, part, _ = self._get_training_context()
            self._draw_info(frame, f"Etap: {part}")
        elif gesture == "ok":
            self._draw_info(frame, "Etap ukończony")

        return CameraResult(
            stream_name=self.stream_name,
            camera_role=self.camera_role,
            frame=frame,
            detected=detected,
            front_back_ok=front_back_ok,
            side_back_ok=side_back_ok,
            back_ok=back_ok,
            head_front_ok=head_front_ok,
            head_side_ok=head_side_ok,
            head_ok=head_ok,
            gesture=gesture,
            landmarks=copied_landmarks,
        )

    def _draw_info(self, frame, text: str):
        cv2.putText(
            frame,
            text,
            (30, 60),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (0, 200, 255),
            2,
        )
