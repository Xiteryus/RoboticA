# -*- coding: Windows-1252 -*-
#!/usr/bin/env python3

import time
import threading
from board import SCL, SDA
import busio
from adafruit_motor import servo
from adafruit_pca9685 import PCA9685

class ServoController:
    def __init__(self):
        self.i2c = busio.I2C(SCL, SDA)
        self.pca = PCA9685(self.i2c, address=0x5f)
        self.pca.frequency = 50
        
        # Positions actuelles des servos
        self.current_positions = {
            0: 90,  # Direction roues
            1: 90,  # Tete gauche-droite
            2: 90   # Tete haut-bas
        }
        
        # Positions initiales par defaut
        self.default_positions = {
            0: 95,  # Direction roues - position centrale
            1: 100,  # Tete gauche-droite - centre
            2: 80   # Tete haut-bas - centre
        }
        
        # Limites de mouvement pour chaque servo
        self.limits = {
            0: {'min': 0, 'max': 180},   # Direction roues (limite reduite)
            1: {'min': 30, 'max': 150},   # Tete gauche-droite
            2: {'min': 30, 'max': 150}    # Tete haut-bas
        }
        
        # Vitesses de mouvement (delai entre chaque degre)
        self.speeds = {
            0: 0.005,  # Direction roues - plus rapide
            1: 0.010,  # Tete gauche-droite - moyen
            2: 0.010   # Tete haut-bas - moyen
        }
        
        # Threads pour mouvements non-bloquants
        self.movement_threads = {}
        self.stop_flags = {}
        
        # Initialiser tous les servos a leur position par defaut
        self.initialize_servos()
    
    def initialize_servos(self):
        """Initialise tous les servos a leur position par defaut"""
        for servo_id in self.current_positions:
            self.set_angle_direct(servo_id, self.default_positions[servo_id])
            time.sleep(0.1)
    
    def set_angle_direct(self, servo_id, angle):
        """Definit directement l'angle d'un servo sans animation"""
        if servo_id not in self.current_positions:
            return False
        
        # Limiter l'angle selon les contraintes
        min_angle = self.limits[servo_id]['min']
        max_angle = self.limits[servo_id]['max']
        angle = max(min_angle, min(max_angle, angle))
        
        try:
            servo_obj = servo.Servo(self.pca.channels[servo_id], 
                                  min_pulse=500, max_pulse=2400, 
                                  actuation_range=180)
            servo_obj.angle = angle
            self.current_positions[servo_id] = angle
            return True
        except:
            return False
    
    def move_to_angle(self, servo_id, target_angle, blocking=True):
        """Deplace un servo vers un angle avec animation fluide"""
        if servo_id not in self.current_positions:
            return False
        
        # Arreter le mouvement precedent s'il existe
        self.stop_movement(servo_id)
        
        if blocking:
            return self._smooth_move(servo_id, target_angle)
        else:
            # Mouvement non-bloquant dans un thread
            self.stop_flags[servo_id] = False
            thread = threading.Thread(target=self._smooth_move, 
                                    args=(servo_id, target_angle))
            thread.daemon = True
            thread.start()
            self.movement_threads[servo_id] = thread
            return True
    
    def _smooth_move(self, servo_id, target_angle):
        """Mouvement fluide d'un servo"""
        # Limiter l'angle
        min_angle = self.limits[servo_id]['min']
        max_angle = self.limits[servo_id]['max']
        target_angle = max(min_angle, min(max_angle, target_angle))
        
        current = self.current_positions[servo_id]
        speed = self.speeds[servo_id]
        
        if target_angle > current:
            # Mouvement vers le haut
            for angle in range(int(current), int(target_angle) + 1):
                if self.stop_flags.get(servo_id, False):
                    break
                self.set_angle_direct(servo_id, angle)
                time.sleep(speed)
        else:
            # Mouvement vers le bas
            for angle in range(int(current), int(target_angle) - 1, -1):
                if self.stop_flags.get(servo_id, False):
                    break
                self.set_angle_direct(servo_id, angle)
                time.sleep(speed)
        
        return True
    
    def stop_movement(self, servo_id):
        """Arrete le mouvement d'un servo"""
        if servo_id in self.stop_flags:
            self.stop_flags[servo_id] = True
        
        if servo_id in self.movement_threads:
            thread = self.movement_threads[servo_id]
            if thread.is_alive():
                thread.join(timeout=1.0)
            del self.movement_threads[servo_id]
    
    def return_to_center(self, servo_id, blocking=False):
        """Retourne un servo a sa position centrale"""
        center_angle = self.default_positions[servo_id]
        return self.move_to_angle(servo_id, center_angle, blocking)
    
    def get_current_position(self, servo_id):
        """Retourne la position actuelle d'un servo"""
        return self.current_positions.get(servo_id, 90)
    
    def set_speed(self, servo_id, speed):
        """Modifie la vitesse d'un servo (delai en secondes)"""
        if servo_id in self.speeds:
            self.speeds[servo_id] = max(0.001, min(0.1, speed))
    
    def cleanup(self):
        """Nettoie les ressources"""
        # Arreter tous les mouvements
        for servo_id in list(self.movement_threads.keys()):
            self.stop_movement(servo_id)
        
        # Retourner tous les servos au centre
        for servo_id in self.current_positions:
            self.return_to_center(servo_id, blocking=True)
        
        time.sleep(0.5)
        self.pca.deinit()

# Instance globale pour utilisation dans d'autres modules
servo_controller = ServoController()