import math
from collections import deque
import mediapipe as mp
import numpy as np
import time

mp_pose = mp.solutions.pose
history = deque(maxlen=5)
_history_letter = deque(maxlen=5)

def _lm(landmarks, name):
    return landmarks[getattr(mp_pose.PoseLandmark, name).value]


def _visible(point, min_visibility=0.5):
    return getattr(point, "visibility", 1.0) >= min_visibility


def _all_visible(landmarks, names, min_visibility=0.5):
    return all(_visible(_lm(landmarks, name), min_visibility) for name in names)


def _dist(a, b):
    return math.hypot(a.x - b.x, a.y - b.y)


def _mid(a, b):
    return ((a.x + b.x) / 2.0, (a.y + b.y) / 2.0)

def _best_side(landmarks):
    """Wybiera lewa albo prawa strone ciala, ktora jest lepiej widoczna z kamery bocznej."""
    left_names = ["LEFT_EAR", "LEFT_SHOULDER", "LEFT_HIP", "LEFT_KNEE"]
    right_names = ["RIGHT_EAR", "RIGHT_SHOULDER", "RIGHT_HIP", "RIGHT_KNEE"]

    left_score = sum(getattr(_lm(landmarks, name), "visibility", 1.0) for name in left_names)
    right_score = sum(getattr(_lm(landmarks, name), "visibility", 1.0) for name in right_names)
    return "LEFT" if left_score >= right_score else "RIGHT"

def angle_3p(a, b, c):
    """Kat ABC w stopniach."""
    a = np.array([a.x, a.y])
    b = np.array([b.x, b.y])
    c = np.array([c.x, c.y])
    radians = np.arctan2(c[1] - b[1], c[0] - b[0]) - np.arctan2(a[1] - b[1], a[0] - b[0])
    deg = abs(math.degrees(radians))
    if deg > 180:
        deg = 360 - deg
    return deg

def angle(a, b):
    dx = a.x - b.x
    dy = a.y - b.y
    return math.degrees(math.atan2(dy, dx))


def is_horizontal(a, b, tolerance=0.07):
    return abs(a.y - b.y) < tolerance


def is_vertical(a, b, tolerance=0.12):
    return abs(a.x - b.x) < tolerance


def check_widoczna_postac(landmarks, min_visibility=0.5):
    potrzebne = [
        "LEFT_SHOULDER", "RIGHT_SHOULDER",
        "LEFT_HIP", "RIGHT_HIP",
        "LEFT_KNEE", "RIGHT_KNEE",
    ]
    return _all_visible(landmarks, potrzebne, min_visibility)

def check_brak_pochylenia_lewo_prawo(landmarks):
    """
    Ocena z kamery przedniej.
    True oznacza, ze barki i biodra sa prawie poziomo, a srodek barkow jest nad srodkiem bioder.
    """
    potrzebne = ["LEFT_SHOULDER", "RIGHT_SHOULDER", "LEFT_HIP", "RIGHT_HIP"]
    if not _all_visible(landmarks, potrzebne):
        return False

    left_shoulder = _lm(landmarks, "LEFT_SHOULDER")
    right_shoulder = _lm(landmarks, "RIGHT_SHOULDER")
    left_hip = _lm(landmarks, "LEFT_HIP")
    right_hip = _lm(landmarks, "RIGHT_HIP")

    shoulder_width = max(abs(right_shoulder.x - left_shoulder.x), 0.05)
    shoulders_horizontal = abs(left_shoulder.y - right_shoulder.y) < 0.07
    hips_horizontal = abs(left_hip.y - right_hip.y) < 0.09

    shoulder_mid_x, _ = _mid(left_shoulder, right_shoulder)
    hip_mid_x, _ = _mid(left_hip, right_hip)
    body_centered = abs(shoulder_mid_x - hip_mid_x) < 0.35 * shoulder_width

    left_side_vertical = abs(left_shoulder.x - left_hip.x) < 0.45 * shoulder_width
    right_side_vertical = abs(right_shoulder.x - right_hip.x) < 0.45 * shoulder_width

    return shoulders_horizontal and hips_horizontal and body_centered and left_side_vertical and right_side_vertical

def check_proste_plecy_przod(landmarks):
    """Alias czytelniejszy w polaczone.py."""
    return check_brak_pochylenia_lewo_prawo(landmarks)

def check_proste_plecy_bok(landmarks):
    """
    Ocena z kamery bocznej.
    MediaPipe nie widzi krzywizny kregoslupa, wiec uzywamy przyblizenia:
    ucho, bark i biodro powinny tworzyc prawie jedna linia.
    """
    side = _best_side(landmarks)
    ear = _lm(landmarks, f"{side}_EAR")
    shoulder = _lm(landmarks, f"{side}_SHOULDER")
    hip = _lm(landmarks, f"{side}_HIP")

    if not (_visible(ear) and _visible(shoulder) and _visible(hip)):
        return False

    torso_len = _dist(shoulder, hip)
    if torso_len < 0.08:
        return False

    # Kat bliski 180 stopni oznacza, ze glowa/szyja, bark i biodro leza na jednej osi.
    neck_back_angle = angle_3p(ear, shoulder, hip)
    return neck_back_angle >= 145

def check_glowa_ok_przod(landmarks):
    """
    Awaryjna ocena glowy z kamery przedniej.
    Nie wykrywa dobrze wysuniecia glowy, ale lapie duze przechylenie w lewo/prawo.
    """
    potrzebne = ["LEFT_EAR", "RIGHT_EAR", "LEFT_SHOULDER", "RIGHT_SHOULDER", "NOSE"]
    if not _all_visible(landmarks, potrzebne):
        return False

    left_ear = _lm(landmarks, "LEFT_EAR")
    right_ear = _lm(landmarks, "RIGHT_EAR")
    left_shoulder = _lm(landmarks, "LEFT_SHOULDER")
    right_shoulder = _lm(landmarks, "RIGHT_SHOULDER")
    nose = _lm(landmarks, "NOSE")

    ears_level = abs(left_ear.y - right_ear.y) < 0.06
    shoulder_mid_x, _ = _mid(left_shoulder, right_shoulder)
    shoulder_width = max(abs(right_shoulder.x - left_shoulder.x), 0.05)
    nose_centered = abs(nose.x - shoulder_mid_x) < 0.40 * shoulder_width

    return ears_level and nose_centered

def check_glowa_ok_bok(landmarks):
    """
    Ocena z kamery bocznej: glowa nie powinna byc wysunieta przed bark ani mocno pochylona w dol.
    Kierunek przodu wyznaczamy z relacji nos-ucho, wiec dziala gdy uzytkownik stoi bokiem w lewo albo w prawo.
    """
    side = _best_side(landmarks)
    ear = _lm(landmarks, f"{side}_EAR")
    shoulder = _lm(landmarks, f"{side}_SHOULDER")
    hip = _lm(landmarks, f"{side}_HIP")
    nose = _lm(landmarks, "NOSE")

    if not (_visible(ear) and _visible(shoulder) and _visible(hip)):
        return False

    torso_len = max(_dist(shoulder, hip), 0.08)
    max_forward = max(0.055, 0.25 * torso_len)
    max_nose_drop = max(0.040, 0.16 * torso_len)

    # Jesli nos jest widoczny, wiemy w ktora strone uzytkownik patrzy.
    if _visible(nose, 0.35) and abs(nose.x - ear.x) > 0.01:
        forward_sign = 1 if nose.x > ear.x else -1
        ear_forward = (ear.x - shoulder.x) * forward_sign
        nose_drop = nose.y - ear.y
    else:
        # Fallback: bez nosa sprawdzamy tylko, czy ucho nie ucieklo daleko od barku.
        ear_forward = abs(ear.x - shoulder.x)
        nose_drop = 0

    head_not_forward = ear_forward <= max_forward
    head_not_down = nose_drop <= max_nose_drop
    ear_above_shoulder = ear.y < shoulder.y + 0.04

    return head_not_forward and head_not_down and ear_above_shoulder

def check_brak_zgarbienia(landmarks):
    """
    Zostawione dla zgodnosci ze starszym kodem.
    Teraz oznacza: glowa z boku nie jest wysunieta do przodu ani pochylona w dol.
    """
    return check_glowa_ok_bok(landmarks)

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