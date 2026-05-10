import cv2
import mediapipe as mp
import time
from wideo import detect_letter


def look():
    sprawdzenietime = None
    mp_pose = mp.solutions.pose
    mp_drawing = mp.solutions.drawing_utils

    cap = cv2.VideoCapture(0)

    pose = mp_pose.Pose()

    while True:
        ret, frame = cap.read()


        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = pose.process(rgb)

        letter = ""

        if results.pose_landmarks:
            landmarks = results.pose_landmarks.landmark

            letter = detect_letter(landmarks)

            mp_drawing.draw_landmarks(
                frame,
                results.pose_landmarks,
                mp_pose.POSE_CONNECTIONS
            )

        if sprawdzenietime is not None:
            cv2.putText(
                frame,
                f"[{'||' * int((((time.time() - sprawdzenietime)*20)/5))}{' '*(20-int((((time.time() - sprawdzenietime)*20)/5)))}]",
                (30, 60),
                cv2.FONT_HERSHEY_SIMPLEX,
                1.5,
                (0, 255, 0),
                3
            )

        if letter == "S":
            if sprawdzenietime is not None:
                if time.time()-sprawdzenietime >=5:
                    break
            else:
                sprawdzenietime = time.time()
        else:
            sprawdzenietime = None

        cv2.imshow("Rozpoznawanie liter", frame)

        if cv2.waitKey(1) & 0xFF == 27:
            break

    cap.release()
    cv2.destroyAllWindows()



look()



