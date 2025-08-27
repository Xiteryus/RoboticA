#!/usr/bin/env python3
# -*- coding: Windows-1252 -*-

import time
import threading
from gpiozero import InputDevice
from motor import Motor, motorStop
from servo_controller_improved import servo_controller
from line_detection import LineDetector

class LineFollower:
    # Actions basées sur les capteurs IR (gauche, centre, droite)
    ACTION_MAP = {
        (0,0,0): "lost",           # Aucun capteur ne détecte
        (1,1,1): "forward",        # Tous les capteurs détectent
        (0,1,0): "forward",        # Seul le centre détecte
        (1,1,0): "slight_right",   # Gauche et centre détectent
        (0,1,1): "slight_left",    # Centre et droite détectent
        (1,0,0): "turn_right",     # Seule la gauche détecte
        (0,0,1): "turn_left",      # Seule la droite détecte
        (1,0,1): "forward"         # Gauche et droite détectent
    }

    def __init__(self, camera=None):
        # Capteurs IR
        self.sensors = {
            'left':   InputDevice(17),
            'middle': InputDevice(27),
            'right':  InputDevice(22),
        }
        
        # Vitesses
        self.speeds = {
            'normal': 20,      # Vitesse normale
            'turn': 18,        # Vitesse en virage
            'search': 12       # Vitesse de recherche
        }
        
        # Angles des roues (les originaux qui marchent)
        self.wheel_angles = {
            'center': 90,
            'left': 110,
            'right': 70,
            'sharp_left': 115,
            'sharp_right': 65,
        }
        
        # Camera pour la récupération
        self.camera = camera
        self.line_detector = LineDetector() if camera else None
        
        # Etat
        self.running = False
        self.thread = None
        self.last_wheel_angle = self.wheel_angles['center']
        self.lost_count = 0

    def read_ir_sensors(self):
        """Lit les capteurs IR dans l'ordre gauche, centre, droite"""
        return tuple(int(self.sensors[k].value) for k in ('left', 'middle', 'right'))

    def get_action_from_sensors(self, pattern):
        """Détermine l'action selon le pattern des capteurs"""
        return self.ACTION_MAP.get(pattern, 'lost')

    def steer_wheels(self, direction):
        """Oriente les roues selon la direction"""
        if direction in self.wheel_angles:
            angle = self.wheel_angles[direction]
            servo_controller.move_to_angle(0, angle, blocking=False)
            self.last_wheel_angle = angle
            time.sleep(0.05)  # Petit délai pour le mouvement

    def move_motor(self, forward=True, speed_name='normal'):
        """Controle le moteur"""
        speed = self.speeds[speed_name]
        Motor(1, 1 if forward else -1, speed)

    def stop_all_motors(self):
        """Arrête tous les moteurs"""
        motorStop()

    def move_head(self, position):
        """Déplace la tête pour la caméra"""
        head_positions = {
            'normal': 90,
            'down': 60,
            'very_down': 55
        }
        if position in head_positions:
            angle = head_positions[position]
            servo_controller.move_to_angle(2, angle, blocking=True)
            time.sleep(0.3)

    def camera_recovery(self):
        """Récupération simple avec caméra"""
        if not self.camera or not self.line_detector:
            print("Pas de caméra disponible pour la récupération")
            return False
            
        print("=== DÉBUT RÉCUPÉRATION CAMÉRA ===")
        
        try:
            # 1. Arrêter et baisser la tête
            self.stop_all_motors()
            self.move_head('very_down')
            
            # 2. Reculer un peu
            center_angle = self.wheel_angles['center']
            if self.last_wheel_angle > center_angle:
                backup_direction = 'sharp_right'
            else:
                backup_direction = 'sharp_left'
                
            print(f"Recul avec angle {backup_direction}")
            self.steer_wheels(backup_direction)
            self.move_motor(forward=False, speed_name='search')
            time.sleep(1.5)
            self.stop_all_motors()
            
            # 3. Chercher la ligne avec la caméra (3 tentatives max)
            for attempt in range(3):
                print(f"Tentative caméra {attempt + 1}/3")
                
                # Analyser avec la caméra
                found_angle, result = self.line_detector.find_line_with_scanning(self.camera)
                
                if result == "found" and found_angle is not None:
                    print(f"Ligne trouvée à l'angle {found_angle}°")
                    
                    # Convertir l'angle en direction
                    if found_angle > 110:
                        wheel_direction = 'sharp_right'
                    elif found_angle > 100:
                        wheel_direction = 'right'
                    elif found_angle < 70:
                        wheel_direction = 'sharp_left'
                    elif found_angle < 80:
                        wheel_direction = 'left'
                    else:
                        wheel_direction = 'center'
                    
                    print(f"Direction calculée: {wheel_direction}")
                    
                    # Orienter et avancer vers la ligne
                    self.steer_wheels(wheel_direction)
                    self.move_motor(forward=True, speed_name='search')
                    time.sleep(1.0)
                    self.stop_all_motors()
                    
                    # Vérifier si on a retrouvé la ligne
                    time.sleep(0.2)
                    sensor_check = self.read_ir_sensors()
                    
                    if any(sensor_check):  # Au moins un capteur détecte
                        print(f"Succès ! Capteurs: {sensor_check}")
                        self.move_head('normal')
                        self.steer_wheels('center')
                        return True
                
                # Si pas trouvé, petit mouvement de recherche
                search_dir = 'left' if attempt % 2 == 0 else 'right'
                self.steer_wheels(search_dir)
                self.move_motor(forward=True, speed_name='search')
                time.sleep(0.5)
                self.stop_all_motors()
            
            print("Récupération caméra échouée")
            self.move_head('normal')
            return False
            
        except Exception as e:
            print(f"Erreur récupération caméra: {e}")
            self.move_head('normal')
            return False

    def simple_recovery(self):
        """Récupération simple sans caméra (code original)"""
        # Avancer un peu pour passer la discontinuité
        self.move_motor(forward=True, speed_name='search')
        time.sleep(0.1)
        self.stop_all_motors()

        # Définir les directions de récupération
        center = self.wheel_angles['center']
        if self.last_wheel_angle > center:
            reverse_dir = 'sharp_right'
            forward_dir = 'sharp_left'
        else:
            reverse_dir = 'sharp_left'
            forward_dir = 'sharp_right'

        # Reculer jusqu'à retrouver la ligne (capteur centre)
        self.steer_wheels(reverse_dir)
        self.move_motor(forward=False, speed_name='search')
        start_time = time.time()
        while time.time() - start_time < 3.0:  # Timeout 3 secondes
            _, middle, _ = self.read_ir_sensors()
            if middle == 1:
                break
            time.sleep(0.01)
        self.stop_all_motors()

        # Avancer jusqu'à retrouver la ligne
        self.steer_wheels(forward_dir)
        self.move_motor(forward=True, speed_name='search')
        start_time = time.time()
        while time.time() - start_time < 3.0:  # Timeout 3 secondes
            _, middle, _ = self.read_ir_sensors()
            if middle == 1:
                break
            time.sleep(0.01)
        self.stop_all_motors()

        return True

    def handle_ir_action(self, action):
        """Exécute l'action déterminée par les capteurs IR"""
        if action == "forward":
            self.steer_wheels('center')
            self.move_motor(forward=True, speed_name='normal')
            
        elif action == "slight_left":
            self.steer_wheels('left')
            self.move_motor(forward=True, speed_name='turn')
            
        elif action == "slight_right":
            self.steer_wheels('right')
            self.move_motor(forward=True, speed_name='turn')
            
        elif action == "turn_left":
            self.steer_wheels('sharp_left')
            self.move_motor(forward=True, speed_name='turn')
            
        elif action == "turn_right":
            self.steer_wheels('sharp_right')
            self.move_motor(forward=True, speed_name='turn')

    def main_loop(self):
        """Boucle principale de suivi de ligne"""
        print("Démarrage du suivi de ligne")
        
        # Position initiale
        self.steer_wheels('center')
        self.move_head('normal')
        
        while self.running:
            try:
                # Lire les capteurs
                sensor_pattern = self.read_ir_sensors()
                action = self.get_action_from_sensors(sensor_pattern)
                
                if action == 'lost':
                    self.lost_count += 1
                    print(f"Ligne perdue (tentative {self.lost_count})")
                    
                    if self.lost_count >= 5:  # Après 5 échecs
                        # Essayer récupération caméra si disponible
                        if self.camera:
                            print("Tentative récupération caméra...")
                            recovery_success = self.camera_recovery()
                        else:
                            print("Tentative récupération simple...")
                            recovery_success = self.simple_recovery()
                            
                        if recovery_success:
                            self.lost_count = 0
                            print("Récupération réussie")
                        else:
                            print("Récupération échouée, arrêt")
                            break
                    else:
                        # Arrêt temporaire
                        self.stop_all_motors()
                        time.sleep(0.1)
                else:
                    # Ligne détectée, traitement normal
                    if self.lost_count > 0:
                        print(f"Ligne retrouvée: {sensor_pattern}")
                        self.lost_count = 0
                    
                    self.handle_ir_action(action)
                
                time.sleep(0.02)  # Fréquence 50Hz
                
            except Exception as e:
                print(f"Erreur dans la boucle principale: {e}")
                break
        
        # Nettoyage final
        self.stop_all_motors()
        self.steer_wheels('center')
        print("Suivi de ligne arrêté")

    def start(self):
        """Démarre le suivi de ligne"""
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self.main_loop, daemon=True)
        self.thread.start()

    def stop_follow(self):
        """Arrête le suivi de ligne"""
        self.running = False
        if self.thread:
            self.thread.join()
        self.stop_all_motors()

# Pour les tests
if __name__ == '__main__':
    lf = LineFollower()
    lf.start()
    try:
        while lf.running:
            time.sleep(0.5)
    except KeyboardInterrupt:
        pass
    finally:
        lf.stop_follow()