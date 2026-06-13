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


def check_brak_pochylenia_lewo_prawo(landmarks):
    left_shoulder = landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER]
    right_shoulder = landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER]
    left_hip = landmarks[mp_pose.PoseLandmark.LEFT_HIP]
    right_hip = landmarks[mp_pose.PoseLandmark.RIGHT_HIP]

    # Sprawdzamy pionowość linii ramiona-biodra
    left_side_vertical = is_vertical(left_shoulder, left_hip, 0.1)
    right_side_vertical = is_vertical(right_shoulder, right_hip, 0.1)

    # Sprawdzamy czy ramiona są w miarę poziomo
    shoulders_horizontal = is_horizontal(left_shoulder, right_shoulder, 0.05)

    return left_side_vertical and right_side_vertical and shoulders_horizontal

def check_brak_zgarbienia(landmarks):
    left_ear = landmarks[mp_pose.PoseLandmark.LEFT_EAR]
    left_shoulder = landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER]


    # Sprawdzamy pionowość linii ucho-ramię
    left_side_vertical = is_vertical(left_shoulder, left_ear, 0.1)


    return left_side_vertical

def check_zgiecie_kolan(landmarks):
    pass

def check_brak_skretu_tulowia(landmarks):
    pass

def check_podniesienie_przedmiotu_z_ziemi(landmarks):
    check_brak_zgarbienia(landmarks) and check_brak_pochylenia_lewo_prawo(landmarks) and check_brak_skretu_tulowia(
        landmarks) and check_zgiecie_kolan(landmarks)
    pass




def is_diagonal_up(a, b, tolerance=40):
    ang = angle(a, b)
    # dopuszczalne kąty: 25–75 lub -155–-105
    return (25 < ang < 75) or (-155 < ang < -105)

def pierwsze(landmarks, part):
    left_shoulder = landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER]
    right_shoulder = landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER]
    left_elbow = landmarks[mp_pose.PoseLandmark.LEFT_ELBOW]
    right_elbow = landmarks[mp_pose.PoseLandmark.RIGHT_ELBOW]
    left_wrist = landmarks[mp_pose.PoseLandmark.LEFT_WRIST]
    right_wrist = landmarks[mp_pose.PoseLandmark.RIGHT_WRIST]
    left_hip = landmarks[mp_pose.PoseLandmark.LEFT_HIP]
    right_hip = landmarks[mp_pose.PoseLandmark.RIGHT_HIP]
    left_knee = landmarks[mp_pose.PoseLandmark.LEFT_KNEE]
    right_knee = landmarks[mp_pose.PoseLandmark.RIGHT_KNEE]

    if left_shoulder.visibility < 0.5 or right_shoulder.visibility < 0.5 or left_elbow.visibility < 0.5 or right_elbow.visibility < 0.5 or left_wrist.visibility < 0.5 or right_wrist.visibility < 0.5 or left_hip.visibility < 0.5 or right_hip.visibility < 0.5 or left_knee.visibility < 0.5 or right_knee.visibility < 0.5:
        return "N"

    if part == 1:
        if (left_wrist.y > left_hip.y
        and right_wrist.y > right_hip.y):
            return "ok"
        return "working on it"

    if part == 2:
       if right_knee.y<right_hip.y and left_knee.y<left_hip.y:
            return "ok"
       return "working on it"

    if part == 3:
        if (left_wrist.y > left_hip.y
                and right_wrist.y > right_hip.y):
            return "ok"
        return "working on it"




def start(landmarks, excercise, part):
    left_shoulder = landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER]
    right_shoulder = landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER]
    left_elbow = landmarks[mp_pose.PoseLandmark.LEFT_ELBOW]
    right_elbow = landmarks[mp_pose.PoseLandmark.RIGHT_ELBOW]
    left_wrist = landmarks[mp_pose.PoseLandmark.LEFT_WRIST]
    right_wrist = landmarks[mp_pose.PoseLandmark.RIGHT_WRIST]
    left_hip = landmarks[mp_pose.PoseLandmark.LEFT_HIP]
    right_hip = landmarks[mp_pose.PoseLandmark.RIGHT_HIP]
    left_knee = landmarks[mp_pose.PoseLandmark.LEFT_KNEE]
    right_knee = landmarks[mp_pose.PoseLandmark.RIGHT_KNEE]

    if left_shoulder.visibility <0.5 or right_shoulder.visibility <0.5 or left_elbow.visibility <0.5 or right_elbow.visibility <0.5 or left_wrist.visibility <0.5 or right_wrist.visibility <0.5 or left_hip.visibility <0.5 or right_hip.visibility <0.5 or left_knee.visibility <0.5 or right_knee.visibility <0.5:
        return "N"



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
    stop = (
        left_half_down and right_half_up
    )
    if stop:
        letter="S"

    elif excercise == 1:
        letter = pierwsze(landmarks,part)



    history.append(letter)
    most_common = max(set(history), key=history.count)
    return most_common