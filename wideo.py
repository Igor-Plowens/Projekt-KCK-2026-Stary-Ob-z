import math
from collections import deque
import mediapipe as mp
import time

mp_pose = mp.solutions.pose
history = deque(maxlen=5)


def angle(a, b):
    dx = a.x - b.x
    dy = a.y - b.y
    return math.degrees(math.atan2(dy, dx))


def is_horizontal(a, b, tolerance=0.07):
    return abs(a.y - b.y) < tolerance


def is_vertical(a, b, tolerance=0.12):
    return abs(a.x - b.x) < tolerance


def is_diagonal_up(a, b, tolerance=40):
    ang = angle(a, b)
    # dopuszczalne kąty: 25–75 lub -155–-105
    return (25 < ang < 75) or (-155 < ang < -105)


def detect_letter(landmarks):
    left_shoulder = landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER]
    right_shoulder = landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER]
    left_elbow = landmarks[mp_pose.PoseLandmark.LEFT_ELBOW]
    right_elbow = landmarks[mp_pose.PoseLandmark.RIGHT_ELBOW]
    left_wrist = landmarks[mp_pose.PoseLandmark.LEFT_WRIST]
    right_wrist = landmarks[mp_pose.PoseLandmark.RIGHT_WRIST]
    left_hip = landmarks[mp_pose.PoseLandmark.LEFT_HIP]
    right_hip = landmarks[mp_pose.PoseLandmark.RIGHT_HIP]

    letter = ""

    # 🔹 Priorytet liter: Y → L → I → T

    # Kąt między nadgarstkiem a łokciem
    def wrist_elbow_angle(wrist, elbow):
        dx = wrist.x - elbow.x
        dy = wrist.y - elbow.y
        return abs(math.degrees(math.atan2(dy, dx)))


    left_half_down = left_wrist.y<left_elbow.y and abs(left_elbow.y-left_shoulder.y) <0.1
    right_half_up = right_wrist.y>right_elbow.y and abs(right_elbow.y-right_shoulder.y)<0.1
    left_up = left_wrist.y < left_hip.y
    right_up = right_wrist.y < right_hip.y
    left_diagonal = left_wrist.y < left_elbow.y and wrist_elbow_angle(left_wrist, left_elbow) > 15
    right_diagonal = right_wrist.y < right_elbow.y and wrist_elbow_angle(right_wrist, right_elbow) > 15


    # Stop
    sprawdzenie = (
        left_half_down and right_half_up
    )
    if sprawdzenie:
        letter="S"




    history.append(letter)
    most_common = max(set(history), key=history.count)
    return most_common