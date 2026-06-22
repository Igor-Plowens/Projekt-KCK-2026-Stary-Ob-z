import math
from collections import deque

import mediapipe as mp
import numpy as np

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


def angle(a, b):
    dx = a.x - b.x
    dy = a.y - b.y
    return math.degrees(math.atan2(dy, dx))


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


def check_zgiecie_kolan(landmarks, min_angle=70, max_angle=165):
    if not _all_visible(landmarks, ["LEFT_HIP", "LEFT_KNEE", "LEFT_ANKLE", "RIGHT_HIP", "RIGHT_KNEE", "RIGHT_ANKLE"]):
        return False

    lk = angle_3p(_lm(landmarks, "LEFT_HIP"), _lm(landmarks, "LEFT_KNEE"), _lm(landmarks, "LEFT_ANKLE"))
    rk = angle_3p(_lm(landmarks, "RIGHT_HIP"), _lm(landmarks, "RIGHT_KNEE"), _lm(landmarks, "RIGHT_ANKLE"))
    return (min_angle <= lk <= max_angle) or (min_angle <= rk <= max_angle)


def check_brak_skretu_tulowia(landmarks, tolerance=0.12):
    if not _all_visible(landmarks, ["LEFT_SHOULDER", "RIGHT_SHOULDER", "LEFT_HIP", "RIGHT_HIP"]):
        return False

    ls = _lm(landmarks, "LEFT_SHOULDER")
    rs = _lm(landmarks, "RIGHT_SHOULDER")
    lh = _lm(landmarks, "LEFT_HIP")
    rh = _lm(landmarks, "RIGHT_HIP")

    barki_nachylenie = ls.y - rs.y
    biodra_nachylenie = lh.y - rh.y
    return abs(barki_nachylenie - biodra_nachylenie) < tolerance


def check_podniesienie_przedmiotu_z_ziemi(landmarks):
    return (
        check_widoczna_postac(landmarks)
        and check_proste_plecy_przod(landmarks)
        and check_brak_skretu_tulowia(landmarks)
        and check_zgiecie_kolan(landmarks)
    )


def is_diagonal_up(a, b, tolerance=40):
    ang = angle(a, b)
    # Dopuszczalne katy: 25-75 lub -155--105.
    return (25 < ang < 75) or (-155 < ang < -105)


def pierwsze(landmarks, part):
    left_shoulder = _lm(landmarks, "LEFT_SHOULDER")
    right_shoulder = _lm(landmarks, "RIGHT_SHOULDER")
    left_elbow = _lm(landmarks, "LEFT_ELBOW")
    right_elbow = _lm(landmarks, "RIGHT_ELBOW")
    left_wrist = _lm(landmarks, "LEFT_WRIST")
    right_wrist = _lm(landmarks, "RIGHT_WRIST")
    left_hip = _lm(landmarks, "LEFT_HIP")
    right_hip = _lm(landmarks, "RIGHT_HIP")
    left_knee = _lm(landmarks, "LEFT_KNEE")
    right_knee = _lm(landmarks, "RIGHT_KNEE")

    needed = [left_shoulder, right_shoulder, left_elbow, right_elbow, left_wrist, right_wrist, left_hip, right_hip, left_knee, right_knee]
    if any(not _visible(point) for point in needed):
        return "N"

    if part == 1:
        if left_wrist.y > left_hip.y and right_wrist.y > right_hip.y:
            return "ok"
        return "working on it"

    if part == 2:
        if right_knee.y < right_hip.y and left_knee.y < left_hip.y:
            return "ok"
        return "working on it"

    if part == 3:
        if left_wrist.y > left_hip.y and right_wrist.y > right_hip.y:
            return "ok"
        return "working on it"

    return "working on it"


def detect_training_state(landmarks, excercise, part):
    left_shoulder = _lm(landmarks, "LEFT_SHOULDER")
    right_shoulder = _lm(landmarks, "RIGHT_SHOULDER")
    left_elbow = _lm(landmarks, "LEFT_ELBOW")
    right_elbow = _lm(landmarks, "RIGHT_ELBOW")
    left_wrist = _lm(landmarks, "LEFT_WRIST")
    right_wrist = _lm(landmarks, "RIGHT_WRIST")
    left_hip = _lm(landmarks, "LEFT_HIP")
    right_hip = _lm(landmarks, "RIGHT_HIP")
    left_knee = _lm(landmarks, "LEFT_KNEE")
    right_knee = _lm(landmarks, "RIGHT_KNEE")

    needed = [left_shoulder, right_shoulder, left_elbow, right_elbow, left_wrist, right_wrist, left_hip, right_hip, left_knee, right_knee]
    if any(not _visible(point) for point in needed):
        return "N"

    def wrist_elbow_angle(wrist, elbow):
        dx = wrist.x - elbow.x
        dy = wrist.y - elbow.y
        return abs(math.degrees(math.atan2(dy, dx)))

    left_half_down = left_wrist.y < left_elbow.y and abs(left_elbow.y - left_shoulder.y) < 0.1
    right_half_up = right_wrist.y > right_elbow.y and abs(right_elbow.y - right_shoulder.y) < 0.1
    left_diagonal = left_wrist.y < left_elbow.y and wrist_elbow_angle(left_wrist, left_elbow) > 15
    right_diagonal = right_wrist.y < right_elbow.y and wrist_elbow_angle(right_wrist, right_elbow) > 15

    letter = ""

    # Stop.
    stop = left_half_down and right_half_up
    if stop:
        letter = "S"
    elif excercise == 1:
        letter = pierwsze(landmarks, part)

    history.append(letter)
    return max(set(history), key=history.count)



# =====================================================
# Licznik podniesień przedmiotu: ziemia -> stół obok
# =====================================================

def _visible_points(landmarks, names, min_visibility=0.45):
    points = []
    for name in names:
        point = _lm(landmarks, name)
        if _visible(point, min_visibility):
            points.append(point)
    return points


def _avg_x(points):
    return sum(point.x for point in points) / len(points)


def _avg_y(points):
    return sum(point.y for point in points) / len(points)


def _body_height_for_counter(landmarks):
    shoulders = _visible_points(landmarks, ["LEFT_SHOULDER", "RIGHT_SHOULDER"], 0.35)
    ankles = _visible_points(landmarks, ["LEFT_ANKLE", "RIGHT_ANKLE"], 0.35)
    hips = _visible_points(landmarks, ["LEFT_HIP", "RIGHT_HIP"], 0.35)

    if shoulders and ankles:
        return max(_avg_y(ankles) - _avg_y(shoulders), 0.25)
    if shoulders and hips:
        return max((_avg_y(hips) - _avg_y(shoulders)) * 2.0, 0.25)
    return 0.60


def check_rece_przy_ziemi(landmarks):
    """
    Przybliżenie momentu, w którym użytkownik sięga po przedmiot z ziemi.
    Współrzędna y w MediaPipe rośnie w dół obrazu.
    """
    wrists = _visible_points(landmarks, ["LEFT_WRIST", "RIGHT_WRIST"])
    hips = _visible_points(landmarks, ["LEFT_HIP", "RIGHT_HIP"])
    knees = _visible_points(landmarks, ["LEFT_KNEE", "RIGHT_KNEE"])

    if not wrists or not hips or not knees:
        return False

    body_h = _body_height_for_counter(landmarks)
    wrist_y = _avg_y(wrists)
    hip_y = _avg_y(hips)
    knee_y = _avg_y(knees)

    hands_below_hips = wrist_y > hip_y + 0.08 * body_h
    hands_near_knees_or_lower = wrist_y > knee_y - 0.15 * body_h
    knees_bent = check_zgiecie_kolan(landmarks, min_angle=55, max_angle=165)

    return hands_below_hips and hands_near_knees_or_lower and knees_bent


def check_rece_na_stole_obok(landmarks):
    """
    Przybliżenie odłożenia przedmiotu na stół obok.
    Nie wykrywamy samego przedmiotu ani stołu, więc sprawdzamy sekwencję:
    ręce były nisko, a potem wróciły w okolice bioder/tułowia i przynajmniej jedna ręka
    może być odsunięta na bok.
    """
    wrists = _visible_points(landmarks, ["LEFT_WRIST", "RIGHT_WRIST"])
    hips = _visible_points(landmarks, ["LEFT_HIP", "RIGHT_HIP"])
    shoulders = _visible_points(landmarks, ["LEFT_SHOULDER", "RIGHT_SHOULDER"])

    if not wrists or not hips or not shoulders:
        return False

    body_h = _body_height_for_counter(landmarks)
    wrist_y = _avg_y(wrists)
    hip_y = _avg_y(hips)
    shoulder_y = _avg_y(shoulders)

    # Stół w tym uproszczeniu traktujemy jako wysokość mniej więcej biodra / dolnego tułowia.
    hands_at_table_height = shoulder_y + 0.18 * body_h <= wrist_y <= hip_y + 0.10 * body_h

    left_shoulder = _lm(landmarks, "LEFT_SHOULDER")
    right_shoulder = _lm(landmarks, "RIGHT_SHOULDER")
    shoulder_width = max(abs(right_shoulder.x - left_shoulder.x), 0.08)
    body_center_x = (left_shoulder.x + right_shoulder.x) / 2.0
    hand_to_side = any(abs(wrist.x - body_center_x) > 0.60 * shoulder_width for wrist in wrists)

    # Nie wymagamy przesunięcia ręki na bok bezwzględnie, bo przy różnych ustawieniach kamery
    # stół może wyglądać jak ruch głównie w pionie.
    return hands_at_table_height or (hands_at_table_height and hand_to_side)


class PrzysiadCounter:
    """
    Liczy pełny cykl: ręce/przedmiot przy ziemi -> ręce na wysokości stołu.
    Nazwa klasy zostaje zgodna z UI, ale w praktyce chodzi o BHP podnoszenia przedmiotu.
    """

    def __init__(self, wymagane_powtorzenia=3, min_seconds_between_reps=1.0):
        self.wymagane_powtorzenia = wymagane_powtorzenia
        self.min_seconds_between_reps = min_seconds_between_reps
        self.reset()

    def reset(self):
        self.count = 0
        self.state = "czekam_na_dol"
        self.last_counted_at = 0.0
        self.last_stage = "czekam na sięgnięcie po przedmiot"

    def update(self, front_landmarks=None, side_landmarks=None, posture_ok=True):
        # Do liczenia ruchu rąk używamy kamery przedniej, a jeśli jej nie ma, kamery bocznej.
        landmarks = front_landmarks or side_landmarks
        new_rep = False

        if landmarks is None:
            self.last_stage = "brak sylwetki"
            return self.result(new_rep)

        if not posture_ok:
            self.last_stage = "najpierw popraw postawę"
            return self.result(new_rep)

        hands_low = check_rece_przy_ziemi(landmarks)
        hands_on_table = check_rece_na_stole_obok(landmarks)
        now = __import__("time").time()

        if self.state == "czekam_na_dol":
            if hands_low:
                self.state = "podnoszenie"
                self.last_stage = "przedmiot przy ziemi"
            else:
                self.last_stage = "zejdź po przedmiot"

        elif self.state == "podnoszenie":
            if hands_on_table and now - self.last_counted_at >= self.min_seconds_between_reps:
                self.count += 1
                self.last_counted_at = now
                self.state = "czekam_na_dol"
                self.last_stage = "odstawiono na stół"
                new_rep = True
            elif hands_low:
                self.last_stage = "podnieś i odłóż na stół"
            else:
                self.last_stage = "kontynuuj podnoszenie"

        return self.result(new_rep)

    def result(self, new_rep=False):
        return {
            "count": self.count,
            "new_rep": new_rep,
            "stage": self.last_stage,
            "state": self.state,
            "required": self.wymagane_powtorzenia,
        }
