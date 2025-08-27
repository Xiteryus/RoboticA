# -*- coding: Windows-1252 -*-

import cv2
import numpy as np

class ArrowDetector:
    def __init__(self, threshold=70, min_area=1000):
        self.threshold = threshold
        self.min_area = min_area

    def detect_arrow(self, frame):
        if frame is None:
            return None, frame

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        _, thresh = cv2.threshold(blurred, self.threshold, 255, cv2.THRESH_BINARY_INV)

        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return "none", frame

        contour = max(contours, key=cv2.contourArea)
        if cv2.contourArea(contour) < self.min_area:
            return "none", frame

        M = cv2.moments(contour)
        if M["m00"] == 0:
            return "none", frame
        cx = int(M["m10"] / M["m00"])
        cy = int(M["m01"] / M["m00"])
        center = (cx, cy)

        # Approximation polygonale
        epsilon = 0.02 * cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, epsilon, True)

        if len(approx) < 3:
            return "none", frame  # Pas suffisant pour une flèche

        # Trouver le segment le plus court
        min_dist = float("inf")
        tip = None

        for i in range(len(approx)):
            pt1 = approx[i][0]
            pt2 = approx[(i + 1) % len(approx)][0]
            dist = np.linalg.norm(pt2 - pt1)

            if dist < min_dist:
                min_dist = dist
                tip = (pt1, pt2)

        if tip is None:
            return "none", frame

        # Choisir l'extrémité du segment le plus proche du bord comme la "pointe"
        # (par rapport au centre du contour)
        tip_point = tip[0] if np.linalg.norm(tip[0] - np.array(center)) > np.linalg.norm(tip[1] - np.array(center)) else tip[1]

        direction = "left" if tip_point[0] < cx else "right"

        # Affichage
        cv2.circle(frame, center, 5, (255, 0, 0), -1)
        cv2.circle(frame, tuple(tip_point), 5, (0, 0, 255), -1)
        cv2.drawContours(frame, [approx], -1, (0, 255, 0), 2)
        cv2.putText(frame, f"Direction: {direction}", (10, 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)

        return direction, frame
        
        
        # arrow_detection.py


 
 
def detect_arrow_from_camera():
    """
    Capture une image depuis la caméra et retourne 'left', 'right' ou 'none'.
    """
    cap = cv2.VideoCapture(0)
    ret, frame = cap.read()
    cap.release()
    if not ret:
        return "none"
    
    detector = ArrowDetector()
    direction, _ = detector.detect_arrow(frame)
    return direction



# Code de test si lancé directement
if __name__ == "__main__":
    detector = ArrowDetector()
    cap = cv2.VideoCapture(0)

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        direction, vis = detector.detect_arrow(frame)
        cv2.imshow("Arrow Detection", vis)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()
