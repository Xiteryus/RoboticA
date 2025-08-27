# -*- coding: Windows-1252 -*-
from motor import *
from servo_controller_improved import servo_controller
from gpiozero import InputDevice
from servo_controller import set_angle
from ultrasound import checkdist
import threading
from time import sleep
import time

# Configuration des pins des capteurs de ligne
line_pin_left = 17
line_pin_middle = 27
line_pin_right = 22

# Configuration des angles du servo de direction
ANGLE_CENTER = 90     # Position centrale
ANGLE_LEFT = 120      # Virage a gauche (augmente pour plus de braquage)
ANGLE_RIGHT = 60      # Virage a droite (diminue pour plus de braquage)
ANGLE_SHARP_LEFT = 130   # Virage serre a gauche
ANGLE_SHARP_RIGHT = 50   # Virage serre a droite

RIGHT_ANGLE_LEFT = 180
RIGHT_ANGLE_RIGHT = 0

# Configuration moteur
MOTOR_SPEED_NORMAL = 25   # Vitesse normale
MOTOR_SPEED_SLOW = 15     # Vitesse reduite en virage
MOTOR_SPEED_SEARCH = 10   # Vitesse de recherche

# D?finition des fonctions motor manquantes
def motor_25():
    """Avance ? vitesse normale"""
    Motor(1, 1, MOTOR_SPEED_NORMAL)

def motor_25_negative():
    """Recule ? vitesse normale"""
    Motor(1, -1, MOTOR_SPEED_NORMAL)

def drive():
    """Maintient le mouvement"""
    Motor(1, 1, MOTOR_SPEED_NORMAL)

class Challenge2V2:
    def __init__(self, led_controller=None, back_light_controller=None, camera=None):
        self.running = False
        self.thread = None
        self.led_controller = led_controller
        self.back_light_controller = back_light_controller
        self.camera = camera
        
        # Capteurs - seront initialisés au démarrage
        self.left = None
        self.middle = None
        self.right = None
        
        # Variables d'?tat
        self.virage = 0  # -1=gauche ; 0=toutdroit ; 1=droit
        
        # Configuration obstacle
        self.obstacle_distance = 150  # Distance en mm pour d?tecter un obstacle
        
        # Thread pour mise ? jour couleur
        self.color_update_thread = None
        self.color_update_running = False
    
    def update_color_from_camera(self):
        """Thread pour mettre ? jour la couleur des LEDs selon la cam?ra"""
        last_dominant = None
        
        while self.color_update_running and self.running:
            try:
                if self.camera and self.camera.show_color_detection:
                    # R?cup?rer les couleurs d?tect?es
                    colors = self.camera.get_detected_colors()
                    dominant = self.camera.get_dominant_color()
                    
                    # Ne mettre ? jour que si on a une couleur dominante
                    if dominant and dominant != last_dominant and len(colors) > 0:
                        if self.led_controller:
                            self.led_controller.set_color_by_name(dominant)
                            last_dominant = dominant
                            print(f"Couleur dominante d?tect?e: {dominant}")
                    elif not dominant and self.led_controller:
                        # Si aucune couleur détectée, mettre en blanc
                        self.led_controller.set_front_leds(255, 255, 255)
                        last_dominant = None
                            
                time.sleep(0.5)  # Mise ? jour 2 fois par seconde
            except Exception as e:
                print(f"Erreur mise ? jour couleur: {e}")
                time.sleep(1)

    def tracking(self, virage):
        """Fonction de suivi de ligne originale avec LEDs arri?re"""
        status_right = self.right.value
        status_middle = self.middle.value
        status_left = self.left.value

        print("Current : ", status_left, " +", status_middle, " + ", status_right, "\n")

        if status_left == 0 and status_middle == 0 and status_right == 0: #1
            # Arr?t et notification des LEDs arri?re
            if self.back_light_controller:
                self.back_light_controller.on_stop()
            
            motor_25()
            set_angle(0, ANGLE_CENTER)
            sleep(0.5)
            motorStop()
            
            print(virage)
            
            if virage == -1:
                set_angle(0, ANGLE_SHARP_RIGHT)
                if self.back_light_controller:
                    self.back_light_controller.on_turn_right()
            elif virage == 1:
                set_angle(0, ANGLE_SHARP_LEFT)
                if self.back_light_controller:
                    self.back_light_controller.on_turn_left()
            
            sleep(0.5)

            # Recherche de la ligne en reculant
            while(status_left != 1 and status_middle != 1 and status_right != 1):
                status_right = self.right.value
                status_middle = self.middle.value
                status_left = self.left.value
                motor_25_negative()
                if self.back_light_controller:
                    self.back_light_controller.on_move_backward()
                    
            motorStop()
            
            if virage == -1:
                set_angle(0, ANGLE_LEFT)
            elif virage == 1:
                set_angle(0, ANGLE_RIGHT)
                
            sleep(0.5)
            motor_25()

        else:
            drive()
            
            # Mise ? jour des LEDs arri?re selon la direction
            if status_left == 0 and status_middle == 0 and status_right == 1: #2
                set_angle(0, ANGLE_SHARP_RIGHT)
                virage = 1
                if self.back_light_controller:
                    self.back_light_controller.on_turn_right()
                
            elif status_left == 0 and status_middle == 1 and status_right == 0: #3
                set_angle(0, ANGLE_CENTER)
                virage = 0
                if self.back_light_controller:
                    self.back_light_controller.on_move_forward()
                
            elif status_left == 0 and status_middle == 1 and status_right == 1: #4
                set_angle(0, ANGLE_RIGHT)
                virage = 1
                if self.back_light_controller:
                    self.back_light_controller.on_turn_right()
                
            elif status_left == 1 and status_middle == 0 and status_right == 0: #5
                set_angle(0, ANGLE_SHARP_LEFT)
                virage = -1
                if self.back_light_controller:
                    self.back_light_controller.on_turn_left()
                
            elif status_left == 1 and status_middle == 1 and status_right == 0: #7
                set_angle(0, ANGLE_LEFT)
                virage = -1
                if self.back_light_controller:
                    self.back_light_controller.on_turn_left()
                
            elif status_left == 1 and status_middle == 1 and status_right == 1: #8
                set_angle(0, ANGLE_CENTER)
                virage = 0
                if self.back_light_controller:
                    self.back_light_controller.on_move_forward()
        
        return status_left, status_middle, status_right, virage

    def evitement(self):
        """Fonction d'?vitement d'obstacle originale avec LEDs arri?re"""
        motorStop()
        if self.back_light_controller:
            self.back_light_controller.on_stop()
            
        tete = 0  # -1=gauche , 1=droite 
        sleep(1)
        
        # Scan gauche
        set_angle(1, RIGHT_ANGLE_LEFT)
        sleep(2)
        print(checkdist())
        if checkdist() < 250:
            tete = -1
        
        sleep(1)
        
        # Scan droite
        set_angle(1, RIGHT_ANGLE_RIGHT)
        sleep(2)
        print(checkdist())
        if checkdist() < 250:
            tete = 1
        
        print(tete)
        
        # Retour au centre
        set_angle(1, ANGLE_CENTER)
        motor_25_negative()
        if self.back_light_controller:
            self.back_light_controller.on_move_backward()
        set_angle(0, ANGLE_CENTER)
        sleep(1)
        
        motorStop()
        
        # Contournement selon la direction
        if tete == -1:
            set_angle(0, ANGLE_RIGHT)
            if self.back_light_controller:
                self.back_light_controller.on_turn_right()
            motor_25()
            sleep(2)
            set_angle(0, ANGLE_LEFT)
            if self.back_light_controller:
                self.back_light_controller.on_turn_left()
            
        elif tete == 1:
            set_angle(0, ANGLE_LEFT)
            if self.back_light_controller:
                self.back_light_controller.on_turn_left()
            motor_25()
            sleep(2)
            set_angle(0, ANGLE_RIGHT)
            if self.back_light_controller:
                self.back_light_controller.on_turn_right()
            
        elif tete == 0:
            set_angle(0, ANGLE_LEFT)
            if self.back_light_controller:
                self.back_light_controller.on_turn_left()
            motor_25()
            sleep(2)
            set_angle(0, ANGLE_RIGHT)
            if self.back_light_controller:
                self.back_light_controller.on_turn_right()
        
        # Recherche de la ligne
        status_right = self.right.value
        status_middle = self.middle.value
        status_left = self.left.value
        
        while status_left != 1 and status_middle != 1 and status_right != 1:
            status_right = self.right.value
            status_middle = self.middle.value
            status_left = self.left.value
            motor_25()
            if self.back_light_controller:
                self.back_light_controller.on_move_forward()
        
        tete = 0

    def _main_loop(self):
        """Boucle principale du programme comme l'original"""
        # Initialiser les capteurs au démarrage
        try:
            self.left = InputDevice(pin=line_pin_right)
            self.middle = InputDevice(pin=line_pin_middle)
            self.right = InputDevice(pin=line_pin_left)
        except Exception as e:
            print(f"Erreur initialisation capteurs: {e}")
            self.running = False
            return
        
        servo_controller.initialize_servos()
        
        # Désactiver la détection de flèches si elle est active
        if self.camera and self.camera.arrow_detection_enabled:
            self.camera.toggle_arrow_detection()
            print("Détection de flèches désactivée pour le mode IR")
        
        # Activer la détection de couleur sur la caméra
        if self.camera:
            self.camera.show_color_detection = True
            print("Détection de couleur activée")
            
        # D?marrer la mise ? jour des couleurs
        if self.camera:
            self.color_update_running = True
            self.color_update_thread = threading.Thread(target=self.update_color_from_camera, daemon=True)
            self.color_update_thread.start()
        
        status_right_before = 0
        status_middle_before = 1
        status_left_before = 0
        
        counter = 0
        virage = 0  # -1=gauche ; 0=toutdroit ; 1=droit
        
        while self.running:  # Condition de fin ajout?e
            try:
                # Suivi de ligne
                a, b, c, virage = self.tracking(virage)
                print("Past : ", status_left_before, " +", status_middle_before, " + ", status_right_before)
                
                # D?tection d'obstacle
                if checkdist() < self.obstacle_distance:
                    self.evitement()
                
                # Petite pause pour ne pas surcharger le CPU
                time.sleep(0.02)
                
            except Exception as e:
                print(f"Erreur dans la boucle principale: {e}")
                break
        
        # Arr?t des moteurs quand on sort de la boucle
        motorStop()
        print("Boucle principale termin?e")

    def start(self):
        """D?marre le programme"""
        if self.running:
            return False
        
        self.running = True
        self.virage = 0
        
        self.thread = threading.Thread(target=self._main_loop, daemon=True)
        self.thread.start()
        return True

    def stop(self):
        """Arr?te le programme - CONDITION DE FIN"""
        if not self.running:
            return False
        
        print("Arr?t demand? depuis l'interface web...")
        self.running = False  # Met fin ? la boucle while
        
        # Arr?t imm?diat des moteurs
        motorStop()
        
        # Arr?ter la mise ? jour des couleurs
        self.color_update_running = False
        if self.color_update_thread:
            self.color_update_thread.join(timeout=1)
        
        # D?sactiver la d?tection de couleur
        if self.camera:
            self.camera.show_color_detection = False
        
        # Attendre la fin du thread principal
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=3.0)
        
        # R?initialiser les servos
        servo_controller.initialize_servos()
        
        # ?teindre les LEDs
        if self.led_controller:
            self.led_controller.set_front_leds(0, 0, 0)
        if self.back_light_controller:
            self.back_light_controller.on_stop()
        
        # Libérer les pins GPIO des capteurs
        try:
            if self.left:
                self.left.close()
                self.left = None
            if self.middle:
                self.middle.close()
                self.middle = None
            if self.right:
                self.right.close()
                self.right = None
        except Exception as e:
            print(f"Erreur lors de la libération des capteurs: {e}")
        
        print("Challenge 2 V2 arr?t? compl?tement")
        return True

    def is_running(self):
        """Retourne True si le programme est en cours"""
        return self.running

    def get_status(self):
        """Retourne le statut actuel"""
        sensors = (self.left.value if self.left else 0, 
                  self.middle.value if self.middle else 0, 
                  self.right.value if self.right else 0)
        return {
            'running': self.running,
            'sensors': sensors,
            'virage': self.virage,
            'obstacle_detected': checkdist() < self.obstacle_distance,
            'stats': {}
        }
    
    def set_obstacle_distance(self, distance):
        """Configure la distance de d?tection d'obstacle"""
        self.obstacle_distance = distance

# Instance globale
challenge2_v2 = None

# Pour maintenir la compatibilit? avec l'ancien code
if __name__ == "__main__":
    # Ex?cution autonome (sans webserver)
    # Cr?er une instance simplifi?e pour test
    challenge = Challenge2V2()
    challenge.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        challenge.stop()
        print("Programme arr?t?")