# -*- coding: Windows-1252 -*-
#!/usr/bin/env python3

import time
import threading
from motor import Motor, motorStop
from servo_controller_improved import servo_controller
from line_detection import LineDetector

class LineFollowerCamera:
    def __init__(self, camera_instance=None, led_controller=None, back_light_controller=None):
        # Camera instance
        self.camera = camera_instance
        self.line_detector = LineDetector()
        
        # Contrôleurs
        self.led_controller = led_controller
        self.back_light_controller = back_light_controller
        
        # Vitesses
        self.speeds = {
            'normal': 20,
            'turn': 15,
            'slow': 10,
            'arrow_turn': 12  # Vitesse pour suivre les flèches
        }
        
        # Angles de direction
        self.wheel_angles = {
            'center': 90,
            'slight_left': 100,
            'slight_right': 80,
            'turn_left': 110,
            'turn_right': 70,
            'sharp_left': 120,
            'sharp_right': 60
        }
        
        # État
        self.running = False
        self.thread = None
        self.last_arrow_direction = None
        self.last_dominant_color = None
        
        # Statistiques
        self.stats = {
            'frames_analyzed': 0,
            'arrows_detected': 0,
            'color_changes': 0
        }

    def analyze_frame(self):
        """Analyse une frame pour la détection de ligne et flèches"""
        frame = self.camera.get_frame_for_processing()
        if frame is None:
            return None, None
        
        self.stats['frames_analyzed'] += 1
        
        # Détection de ligne
        line_result = self.line_detector.detect_line_in_frame(frame)
        
        # Détection de flèche (si activée)
        arrow_direction = None
        if self.camera.arrow_detector and self.camera.show_arrow_detection:
            arrow_direction, _ = self.camera.arrow_detector.detect_arrow_advanced(frame)
            if arrow_direction and arrow_direction != self.last_arrow_direction:
                self.stats['arrows_detected'] += 1
                self.last_arrow_direction = arrow_direction
                print(f"Flèche détectée: {arrow_direction}")
        
        return line_result, arrow_direction

    def update_leds_from_detection(self):
        """Met à jour les LEDs selon les détections"""
        if not self.led_controller:
            return
            
        # Couleur dominante
        if self.camera.show_color_detection:
            dominant = self.camera.get_dominant_color()
            if dominant and dominant != self.last_dominant_color:
                self.led_controller.set_color_by_name(dominant)
                self.last_dominant_color = dominant
                self.stats['color_changes'] += 1
                print(f"Changement couleur LED: {dominant}")

    def follow_arrow_direction(self, arrow_direction):
        """Suit la direction indiquée par une flèche"""
        print(f"Suivi de la flèche vers la {arrow_direction}")
        
        if arrow_direction == 'left':
            # Virage à gauche prononcé
            self.steer_wheels('sharp_left')
            self.move_motor(forward=True, speed_name='arrow_turn')
            
            # Indication LED
            if self.led_controller:
                self.led_controller.flash_leds(255, 0, 0, 0.2, 3)  # Flash rouge
                
            # Feux arrière
            if self.back_light_controller:
                self.back_light_controller.on_turn_left()
                
            time.sleep(2.0)  # Temps de virage
            
        elif arrow_direction == 'right':
            # Virage à droite prononcé
            self.steer_wheels('sharp_right')
            self.move_motor(forward=True, speed_name='arrow_turn')
            
            # Indication LED
            if self.led_controller:
                self.led_controller.flash_leds(0, 0, 255, 0.2, 3)  # Flash bleu
                
            # Feux arrière
            if self.back_light_controller:
                self.back_light_controller.on_turn_right()
                
            time.sleep(2.0)  # Temps de virage
        
        # Retour au centre
        self.steer_wheels('center')

    def steer_wheels(self, angle_name):
        """Oriente les roues"""
        if angle_name in self.wheel_angles:
            angle = self.wheel_angles[angle_name]
            servo_controller.move_to_angle(0, angle, blocking=False)
            time.sleep(0.03)

    def move_motor(self, forward=True, speed_name='normal'):
        """Contrôle le moteur"""
        if speed_name in self.speeds:
            speed = self.speeds[speed_name]
            direction = 1 if forward else -1
            Motor(1, direction, speed)

    def stop_all_motors(self):
        """Arrête tous les moteurs"""
        motorStop()

    def handle_line_detection(self, line_result):
        """Gère la détection de ligne"""
        if not line_result or not line_result.get('line_detected'):
            return 'lost'
            
        angle = line_result.get('angle')
        direction = line_result.get('direction')
        
        # Convertir la direction en action
        if direction == 'forward':
            self.steer_wheels('center')
            self.move_motor(forward=True, speed_name='normal')
            return 'forward'
        elif direction == 'slight_left':
            self.steer_wheels('slight_left')
            self.move_motor(forward=True, speed_name='turn')
            return 'left'
        elif direction == 'slight_right':
            self.steer_wheels('slight_right')
            self.move_motor(forward=True, speed_name='turn')
            return 'right'
        elif direction == 'turn_left':
            self.steer_wheels('turn_left')
            self.move_motor(forward=True, speed_name='turn')
            return 'left'
        elif direction == 'turn_right':
            self.steer_wheels('turn_right')
            self.move_motor(forward=True, speed_name='turn')
            return 'right'
        else:
            return 'lost'

    def _main_loop(self):
        """Boucle principale du mode caméra"""
        print("Démarrage du suivi de ligne par caméra")
        
        # Initialisation
        servo_controller.initialize_servos()
        time.sleep(1)
        
        # Activer les overlays nécessaires
        self.camera.show_line_detection = True
        self.camera.show_arrow_detection = True
        self.camera.show_color_detection = True
        
        lost_count = 0
        max_lost = 5
        
        while self.running:
            try:
                # Analyser la frame
                line_result, arrow_direction = self.analyze_frame()
                
                # Mettre à jour les LEDs
                self.update_leds_from_detection()
                
                # Priorité aux flèches
                if arrow_direction:
                    self.follow_arrow_direction(arrow_direction)
                    lost_count = 0
                    continue
                
                # Sinon, suivre la ligne
                action = self.handle_line_detection(line_result)
                
                # Mettre à jour les feux arrière
                if self.back_light_controller:
                    if action == 'forward':
                        self.back_light_controller.on_move_forward()
                    elif action == 'left':
                        self.back_light_controller.on_turn_left()
                    elif action == 'right':
                        self.back_light_controller.on_turn_right()
                
                # Gérer la perte de ligne
                if action == 'lost':
                    lost_count += 1
                    if lost_count >= max_lost:
                        print("Ligne perdue, recherche...")
                        self.stop_all_motors()
                        
                        # LED jaune pour recherche
                        if self.led_controller:
                            self.led_controller.set_front_leds(255, 255, 0)
                        
                        # Balayage simple
                        self.steer_wheels('turn_left')
                        self.move_motor(forward=True, speed_name='slow')
                        time.sleep(0.5)
                        
                        self.steer_wheels('turn_right')
                        time.sleep(1.0)
                        
                        self.steer_wheels('center')
                        lost_count = 0
                    else:
                        self.stop_all_motors()
                        time.sleep(0.1)
                else:
                    lost_count = 0
                
                time.sleep(0.05)  # 20Hz pour l'analyse caméra
                
            except Exception as e:
                print(f"Erreur dans la boucle principale caméra: {e}")
                break
        
        # Nettoyage
        print("Arrêt du mode caméra...")
        self.stop_all_motors()
        servo_controller.initialize_servos()
        
        # Désactiver les overlays
        self.camera.show_line_detection = False
        self.camera.show_arrow_detection = False
        self.camera.show_color_detection = False
        
        # Éteindre les LEDs
        if self.led_controller:
            self.led_controller.set_front_leds(0, 0, 0)
        if self.back_light_controller:
            self.back_light_controller.on_stop()

    def start(self):
        """Démarre le suivi par caméra"""
        if self.running:
            return False
            
        if not self.camera:
            print("Erreur: Aucune caméra disponible")
            return False
            
        self.running = True
        self.last_arrow_direction = None
        self.last_dominant_color = None
        
        # Réinitialiser les stats
        for key in self.stats:
            self.stats[key] = 0
            
        self.thread = threading.Thread(target=self._main_loop, daemon=True)
        self.thread.start()
        return True

    def stop(self):
        """Arrête le suivi par caméra"""
        if not self.running:
            return False
            
        self.running = False
        
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=3.0)
            
        self.stop_all_motors()
        return True

    def is_running(self):
        """Retourne True si actif"""
        return self.running

    def get_status(self):
        """Retourne le statut"""
        return {
            'running': self.running,
            'stats': self.stats.copy(),
            'camera_available': self.camera is not None
        }

# Instance globale
line_follower_camera = None