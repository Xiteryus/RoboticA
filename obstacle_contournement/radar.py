from servo_controller import *
from gpiozero import DistanceSensor
from time import sleep
from ultrasound import *
"""import matplotlib.pyplot as plt
import numpy as np"""


def servo_initialisation(angle):
    set_angle(2, 90)
    set_angle(1, angle)


def detection(angle):
    if angle >= 10 or angle <= 180:
        set_angle(1, angle)
        sleep(0.05)
        return round(checkdist(), 1)


def detection_environnement():
    angle = 10
    servo_initialisation(angle)
    detection_map = [0]*18
    for i in range(len(detection_map)):
        # mise a jour de la map de detection
        detection_map[i] = detection(angle)
        print("\n", detection_map)
        angle += 10
    return detection_map


if __name__ == "__main__":
    angle = 90
    servo_initialisation(angle)
    try:
        detection_map = [0]*18
        direction = 1
        while True:
            # mise a jour de la map de detection
            detection_map[(angle//10)-1] = detection(angle)
            print("\n", detection_map)

            # affichage graphique
            """fig = plt.figure(figsize=(10, 10))
            ax = fig.add_subplot(111, polar=True)

            N = len(detection_map)

            theta = np.linspace(0, np.pi, N)
            bars = ax.bar(theta, detection_map, width=0.4)

            ax.set_xticks(theta)
            ax.set_xticklabels(range(1, len(theta)+1))
            ax.yaxis.grid(True)
            plt.show()"""

            # mise a jour du sens de direction
            if angle >= 180 and direction == 1:
                direction = 0
            elif angle <= 10 and direction == 0:
                direction = 1
            
            # mise a jour de l'angle
            if direction:
                angle += 10
            else:
                angle -= 10
    except KeyboardInterrupt:
        print("\nArret du radar")
    finally:
        print("Reinitialisation des servomoteurs")
        servo_initialisation(100)