# -*- coding: Windows-1252 -*-
"""
Mode Labyrinthe pour l'interface web
D�tection de fl�ches et navigation autonome
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
        
        # Configuration t�te
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
        """R�cup�re la direction de la fl�che d�tect�e"""
        if not self.camera:
            return "none"
            
        # S'assurer que la d�tection de fl�ches est activ�e
        if not self.camera.arrow_detection_enabled:
            self.camera.toggle_arrow_detection()
            
        # Capturer une frame et analyser
        self.camera.get_frame()
        direction = self.camera.get_arrow_direction()
        return direction
        
    def chose(self):
        """D�termine la direction � prendre en analysant plusieurs images"""
        directions = {"left": 0, "right": 0, "none": 0}
        
        print("Analyse des fl�ches...")
        
        # Analyser 5 images
        for j in range(5):
            if not self.running:
                return "none"
                
            direction = self.get_direction()
            print(f"D�tection {j+1}: {direction}")
            
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
        # Centrer la t�te
        set_angle(1, 100)
        set_angle(2, 100)
        
        # Avancer jusqu'� l'obstacle
        print("Avance jusqu'� l'obstacle...")
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
            # Pas de fl�che d�tect�e, reculer
            print("Aucune fl�che d�tect�e, marche arri�re")
            if self.back_light_controller:
                self.back_light_controller.on_move_backward()
            backward()
            sleep(2)
            motorStop()
            self.stats['marches_arriere'] += 1
            
        elif direction == "left":
            # Virage � gauche
            print("Virage � gauche d�tect�")
            self.stats['virages_gauche'] += 1
            
            # Reculer en braquant � droite
            set_angle(0, self.ANGLE_SHARP_RIGHT)
            if self.back_light_controller:
                self.back_light_controller.on_backward_turn_right()
            backward()
            sleep(0.5)
            motorStop()
            
            # Avancer en braquant � gauche
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
            # Virage � droite
            print("Virage � droite d�tect�")
            self.stats['virages_droite'] += 1
            
            # Reculer en braquant � gauche
            set_angle(0, self.ANGLE_SHARP_LEFT)
            if self.back_light_controller:
                self.back_light_controller.on_backward_turn_left()
            backward()
            sleep(0.5)
            motorStop()
            
            # Avancer en braquant � droite
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
        print("D�marrage du mode labyrinthe...")
        
        # Initialiser les servos
        servo_controller.initialize_servos()
        
        # D�sactiver la d�tection de couleur si elle est active
        if self.camera and self.camera.show_color_detection:
            self.camera.toggle_color_detection()
            print("D�tection de couleur d�sactiv�e pour le mode labyrinthe")
        
        # Activer la d�tection de fl�ches
        if self.camera and not self.camera.arrow_detection_enabled:
            self.camera.toggle_arrow_detection()
            print("D�tection de fl�ches activ�e")
        
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
            # Arr�t propre
            motorStop()
            if self.back_light_controller:
                self.back_light_controller.on_stop()
            print("Mode labyrinthe arr�t�")
    
    def start(self):
        """D�marre le mode labyrinthe"""
        if self.running:
            return False
            
        self.running = True
        
        # R�initialiser les stats
        for key in self.stats:
            self.stats[key] = 0
            
        self.thread = threading.Thread(target=self._main_loop, daemon=True)
        self.thread.start()
        
        return True
    
    def stop(self):
        """Arr�te le mode labyrinthe"""
        if not self.running:
            return False
            
        print("Arr�t du mode labyrinthe...")
        self.running = False
        
        # Arr�t imm�diat des moteurs
        motorStop()
        
        # Attendre la fin du thread
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=3.0)
        
        # R�initialiser les servos
        servo_controller.initialize_servos()
        
        # �teindre les LEDs
        if self.led_controller:
            self.led_controller.set_front_leds(0, 0, 0)
        if self.back_light_controller:
            self.back_light_controller.on_stop()
            
        # D�sactiver la d�tection de fl�ches
        if self.camera and self.camera.arrow_detection_enabled:
            self.camera.toggle_arrow_detection()
        
        print("Mode labyrinthe compl�tement arr�t�")
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
        """Configure la distance de d�tection d'obstacle"""
        self.obstacle_distance = distance
        print(f"Distance obstacle configur�e � {distance}mm")