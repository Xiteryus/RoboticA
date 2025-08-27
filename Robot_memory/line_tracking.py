#!/usr/bin/env python3
# -*- coding: Windows-1252 -*-

import time
import threading
from gpiozero import InputDevice
from motor import Motor, motorStop
from servo_controller_improved import servo_controller
from camera import PiCameraStream
import cv2
import numpy as np

class LineFollowerCamera:
    ACTION_MAP = {
        (0,0,0): "lost",
        (1,1,1): "forward", (0,1,0): "forward",
        (1,1,0): "slight_right", (0,1,1): "slight_left",
        (1,0,0): "turn_right",  (0,0,1): "turn_left",
        (1,0,1): "forward"
    }

    def __init__(self):
        # capteurs IR
        self.sensors = {
            'left':   InputDevice(17),
            'middle': InputDevice(27),
            'right':  InputDevice(22),
        }
        # vitesses
        self.v_norm    = 20
        self.v_turn    = 18
        self.v_search  = 12
        # angles IR
        self.angles = {
            'center':      90,
            'left':       110,
            'right':       70,
            'sharp_left': 115,
            'sharp_right': 65,
        }
        self.last_angle = self.angles['center']

        # caméra
        self.camera = PiCameraStream()
        self.head_down_angle = 60  
        self.head_up_angle   = 90  

        # contrôle de boucle
        self.running = False
        self.thread  = None

    def read_sensors(self):
        return tuple(int(self.sensors[k].value) for k in ('left','middle','right'))

    def decide(self, pattern):
        return self.ACTION_MAP.get(pattern, 'stop')

    def steer(self, name):
        servo_controller.move_to_angle(0, self.angles[name], blocking=False)
        self.last_angle = self.angles[name]
        time.sleep(0.03)

    def drive(self, forward, speed):
        Motor(1, 1 if forward else -1, speed)

    def stop_motors(self):
        motorStop()

    def detect_black_line(self, timeout=4):
        start = time.time()
        while time.time() - start < timeout:
            frame = self.camera.get_frame()
            if not frame:
                continue
            gray = cv2.imdecode(np.frombuffer(frame, np.uint8), cv2.IMREAD_GRAYSCALE)
            _, thresh = cv2.threshold(gray, 50, 255, cv2.THRESH_BINARY_INV)
            cnts, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            for c in cnts:
                if cv2.contourArea(c) > 2000:
                    return True
        return False

    def recover_with_camera(self):
        # baisser la tête
        servo_controller.move_to_angle(2, self.head_down_angle, blocking=True)
        time.sleep(0.2)

        # reculer braqué
        center = self.angles['center']
        rev = 'sharp_right' if self.last_angle > center else 'sharp_left'
        fwd = 'sharp_left'  if rev == 'sharp_right' else 'sharp_right'

        self.steer(rev)
        self.drive(False, self.v_search)
        time.sleep(1.0)
        self.stop_motors()

        # détecter ligne noire
        found = self.detect_black_line(timeout=3.0)
        self.stop_motors()

        if found:
            # avancer braqué
            self.steer(fwd)
            self.drive(True, self.v_search)
            time.sleep(0.5)
            self.stop_motors()

        # remonter la tête
        servo_controller.move_to_angle(2, self.head_up_angle, blocking=True)
        time.sleep(0.1)
        return found

    def _run_loop(self):
        while self.running:
            pat    = self.read_sensors()
            action = self.decide(pat)

            if action == 'forward':
                self.steer('center')
                self.drive(True, self.v_norm)

            elif action.endswith('left') or action.endswith('right'):
                name = 'left' if 'left' in action else 'right'
                if not action.startswith('slight'):
                    name = 'sharp_' + name
                self.steer(name)
                self.drive(True, self.v_turn)

            elif action == 'lost':
                self.stop_motors()
                print("Ligne IR perdue ? récupération caméra")
                if not self.recover_with_camera():
                    print("Échec récupération")
                    break

            else:
                self.stop_motors()

            time.sleep(0.02)

        # Fin de boucle, on stoppe moteurs
        self.stop_motors()

    def start(self):
        if self.running:
            return
        self.running = True
        self.thread  = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()

    def stop(self):
        """Arrêter la boucle et nettoyer ressources."""
        if not self.running:
            return
        self.running = False
        # On attend la fin du thread
        if self.thread and threading.current_thread() is not self.thread:
            self.thread.join(timeout=2.0)
        # Nettoyage caméra et moteurs
        try:
            self.camera.stop()
        except:
            pass
        self.stop_motors()

if __name__ == "__main__":
    lf = LineFollowerCamera()
    lf.start()
    try:
        while lf.running:
            time.sleep(0.5)
    except KeyboardInterrupt:
        pass
    finally:
        lf.stop()
