# -*- coding: Windows-1252 -*-
"""
Mode Labyrinthe pour l'interface web
Détection de flèches et navigation autonome
"""

import threading
import time
from motor import Motor, motorStop, drive, backward
from servo_controller_improved import servo_controller
from servo_controller import set_angle
from ultrasound import checkdist
from time import sleep

class LabyrintheMode:
    def __init__(self, camera=None, led_controller=None, back_light_controller=None):
        self.running = False
        self.thread = None
        self.camera = camera
        self.led_controller = led_controller
        self.back_light_controller = back_light_controller
        
        # Configuration des angles du servo de direction
        self.ANGLE_CENTER = 90
        self.ANGLE_LEFT = 120
        self.ANGLE_RIGHT = 60
        self.ANGLE_SHARP_LEFT = 130
        self.ANGLE_SHARP_RIGHT = 50
        
        # Configuration tête
        self.RIGHT_ANGLE_LEFT = 180
        self.RIGHT_ANGLE_RIGHT = 0
        
        # Distance obstacle (mm)
        self.obstacle_distance = 300
        
        # Statistiques
        self.stats = {
            'fleches_detectees': 0,
            'virages_gauche': 0,
            'virages_droite': 0,
            'obstacles_detectes': 0,
            'marches_arriere': 0
        }
        
    def get_direction(self):
        """Récupère la direction de la flèche détectée"""
        if not self.camera:
            return "none"
            
        # S'assurer que la détection de flèches est activée
        if not self.camera.arrow_detection_enabled:
            self.camera.toggle_arrow_detection()
            
        # Capturer une frame et analyser
        self.camera.get_frame()
        direction = self.camera.get_arrow_direction()
        return direction
        
    def chose(self):
        """Détermine la direction à prendre en analysant plusieurs images"""
        directions = {"left": 0, "right": 0, "none": 0}
        
        print("Analyse des flèches...")
        
        # Analyser 5 images
        for j in range(5):
            if not self.running:
                return "none"
                
            direction = self.get_direction()
            print(f"Détection {j+1}: {direction}")
            
            if direction in directions:
                directions[direction] += 1
                
            sleep(1)
        
        # Prendre la direction majoritaire
        max_count = max(directions.values())
        for direction, count in directions.items():
            if count == max_count:
                if direction != "none":
                    self.stats['fleches_detectees'] += 1
                return direction
        
        return "none"
    
    def moov(self):
        """Mouvement principal du robot dans le labyrinthe"""
        # Centrer la tête
        set_angle(1, 100)
        set_angle(2, 100)
        
        # Avancer jusqu'à l'obstacle
        print("Avance jusqu'à l'obstacle...")
        if self.back_light_controller:
            self.back_light_controller.on_move_forward()
            
        while checkdist() > self.obstacle_distance and self.running:
            drive()
            
        motorStop()
        self.stats['obstacles_detectes'] += 1
        
        if not self.running:
            return
            
        sleep(1)
        
        # Analyser la direction
        direction = self.chose()
        print(f"Direction choisie: {direction}")
        
        if direction == "none":
            # Pas de flèche détectée, reculer
            print("Aucune flèche détectée, marche arrière")
            if self.back_light_controller:
                self.back_light_controller.on_move_backward()
            backward()
            sleep(2)
            motorStop()
            self.stats['marches_arriere'] += 1
            
        elif direction == "left":
            # Virage à gauche
            print("Virage à gauche détecté")
            self.stats['virages_gauche'] += 1
            
            # Reculer en braquant à droite
            set_angle(0, self.ANGLE_SHARP_RIGHT)
            if self.back_light_controller:
                self.back_light_controller.on_backward_turn_right()
            backward()
            sleep(0.5)
            motorStop()
            
            # Avancer en braquant à gauche
            set_angle(0, self.ANGLE_SHARP_LEFT)
            if self.back_light_controller:
                self.back_light_controller.on_turn_left()
            drive()
            sleep(4)
            motorStop()
            
            # Remettre les roues au centre et continuer
            set_angle(0, self.ANGLE_CENTER)
            if self.back_light_controller:
                self.back_light_controller.on_move_forward()
            drive()
            
        elif direction == "right":
            # Virage à droite
            print("Virage à droite détecté")
            self.stats['virages_droite'] += 1
            
            # Reculer en braquant à gauche
            set_angle(0, self.ANGLE_SHARP_LEFT)
            if self.back_light_controller:
                self.back_light_controller.on_backward_turn_left()
            backward()
            sleep(0.5)
            motorStop()
            
            # Avancer en braquant à droite
            set_angle(0, self.ANGLE_SHARP_RIGHT)
            if self.back_light_controller:
                self.back_light_controller.on_turn_right()
            drive()
            sleep(4)
            motorStop()
            
            # Remettre les roues au centre et continuer
            set_angle(0, self.ANGLE_CENTER)
            if self.back_light_controller:
                self.back_light_controller.on_move_forward()
            drive()
    
    def _main_loop(self):
        """Boucle principale du mode labyrinthe"""
        print("Démarrage du mode labyrinthe...")
        
        # Initialiser les servos
        servo_controller.initialize_servos()
        
        # Désactiver la détection de couleur si elle est active
        if self.camera and self.camera.show_color_detection:
            self.camera.toggle_color_detection()
            print("Détection de couleur désactivée pour le mode labyrinthe")
        
        # Activer la détection de flèches
        if self.camera and not self.camera.arrow_detection_enabled:
            self.camera.toggle_arrow_detection()
            print("Détection de flèches activée")
        
        # Mettre les LEDs en blanc pour le mode labyrinthe
        if self.led_controller:
            self.led_controller.set_front_leds(255, 255, 255)
            print("LEDs mises en blanc pour le mode labyrinthe")
        
        try:
            while self.running:
                self.moov()
                
                # Petite pause entre chaque cycle
                if self.running:
                    sleep(0.1)
                    
        except Exception as e:
            print(f"Erreur dans la boucle labyrinthe: {e}")
        finally:
            # Arrêt propre
            motorStop()
            if self.back_light_controller:
                self.back_light_controller.on_stop()
            print("Mode labyrinthe arrêté")
    
    def start(self):
        """Démarre le mode labyrinthe"""
        if self.running:
            return False
            
        self.running = True
        
        # Réinitialiser les stats
        for key in self.stats:
            self.stats[key] = 0
            
        self.thread = threading.Thread(target=self._main_loop, daemon=True)
        self.thread.start()
        
        return True
    
    def stop(self):
        """Arrête le mode labyrinthe"""
        if not self.running:
            return False
            
        print("Arrêt du mode labyrinthe...")
        self.running = False
        
        # Arrêt immédiat des moteurs
        motorStop()
        
        # Attendre la fin du thread
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=3.0)
        
        # Réinitialiser les servos
        servo_controller.initialize_servos()
        
        # Éteindre les LEDs
        if self.led_controller:
            self.led_controller.set_front_leds(0, 0, 0)
        if self.back_light_controller:
            self.back_light_controller.on_stop()
            
        # Désactiver la détection de flèches
        if self.camera and self.camera.arrow_detection_enabled:
            self.camera.toggle_arrow_detection()
        
        print("Mode labyrinthe complètement arrêté")
        return True
    
    def is_running(self):
        """Retourne True si le mode est actif"""
        return self.running
    
    def get_status(self):
        """Retourne le statut actuel"""
        return {
            'running': self.running,
            'obstacle_distance': self.obstacle_distance,
            'stats': self.stats.copy()
        }
    
    def set_obstacle_distance(self, distance):
        """Configure la distance de détection d'obstacle"""
        self.obstacle_distance = distance
        print(f"Distance obstacle configurée à {distance}mm")