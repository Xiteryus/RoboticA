# -*- coding: Windows-1252 -*-
"""
Contrôleur des feux arrière du robot (back_light.py)
Gère l'éclairage en fonction des mouvements :
- LEDs 2,4,5,7 : feux de position rouges (faible en mouvement, fort à l'arrêt)
- LED 4 et 6 : clignotants gauche/droite
- LEDs blanches en marche arrière
"""

import threading
import time
from enum import Enum

class RobotState(Enum):
    STOPPED = "stopped"
    MOVING_FORWARD = "forward"
    MOVING_BACKWARD = "backward"
    TURNING_LEFT = "left"
    TURNING_RIGHT = "right"

class BackLightController:
    def __init__(self, led_bar):
        """
        Initialise le contrôleur des LEDs arrière
        
        Args:
            led_bar: Instance de Adeept_SPI_LedPixel
        """
        self.led_bar = led_bar
        self.current_state = RobotState.STOPPED
        self.last_movement_time = time.time()
        self.stop_timer = None
        
        # Configuration des LEDs
        self.rear_leds = [2, 4, 5, 7]  # LEDs feux de position
        self.left_blinker = 3   # LED clignotant gauche (corrigé)
        self.right_blinker = 6  # LED clignotant droite
        self.white_lights = [3, 6]  # LEDs phares blancs marche arrière
        
        # Paramètres d'intensité
        self.low_intensity = 50    # Intensité faible en mouvement
        self.high_intensity = 180  # Intensité forte à l'arrêt
        self.white_intensity = 200 # Intensité lumière blanche (marche arrière)
        
        # Contrôle des clignotants
        self.blinker_active = False
        self.blinker_direction = None
        self.blinker_thread = None
        self.blinker_stop_event = threading.Event()
        
        # Thread principal de gestion
        self.running = True
        self.control_thread = threading.Thread(target=self._control_loop, daemon=True)
        self.control_thread.start()
        
        # Initialiser les LEDs
        self._set_rear_lights(self.high_intensity)

    def set_robot_state(self, state, direction=None):
        """
        Met à jour l'état du robot
        
        Args:
            state: RobotState
            direction: 'left' ou 'right' pour les virages
        """
        self.current_state = state
        self.last_movement_time = time.time()
        
        # Annuler le timer d'arrêt précédent
        if self.stop_timer:
            self.stop_timer.cancel()
        
        if state == RobotState.STOPPED:
            # Programmer l'augmentation d'intensité après 3 secondes d'arrêt (augmenté)
            self.stop_timer = threading.Timer(3.0, self._increase_brightness)
            self.stop_timer.start()
            self._handle_stopped()
        elif state == RobotState.MOVING_FORWARD:
            self._handle_forward()
        elif state == RobotState.MOVING_BACKWARD:
            self._handle_backward()
        elif state == RobotState.TURNING_LEFT:
            self._handle_turn_left()
        elif state == RobotState.TURNING_RIGHT:
            self._handle_turn_right()

    def _handle_stopped(self):
        """Gère l'état arrêté"""
        self._stop_blinkers()
        self._set_rear_lights(self.low_intensity)  # Commence par faible intensité

    def _handle_forward(self):
        """Gère l'état marche avant"""
        self._stop_blinkers()
        self._clear_white_lights()
        self._set_rear_lights(self.low_intensity)

    def _handle_backward(self):
        """Gère l'état marche arrière avec clignotants possibles"""
        # Ne pas arrêter les clignotants en marche arrière
        self._set_white_lights()

    def _handle_turn_left(self):
        """Gère l'état virage à gauche"""
        self._set_rear_lights(self.low_intensity)
        self._start_blinker('left')

    def _handle_turn_right(self):
        """Gère l'état virage à droite"""
        self._set_rear_lights(self.low_intensity)
        self._start_blinker('right')

    def _increase_brightness(self):
        """Augmente la luminosité des feux après arrêt prolongé"""
        if self.current_state == RobotState.STOPPED:
            self._set_rear_lights(self.high_intensity)

    def _set_rear_lights(self, intensity):
        """
        Allume les feux arrière rouges
        
        Args:
            intensity: Intensité lumineuse (0-255)
        """
        for led_id in self.rear_leds:
            # Ne pas écraser les clignotants actifs
            if not (self.blinker_active and led_id in [self.left_blinker, self.right_blinker]):
                self.led_bar.set_ledpixel(led_id, intensity, 0, 0)  # Rouge
        
        self.led_bar.show()

    def _set_white_lights(self):
        """Allume les phares de recul en blanc (LEDs 3 et 6) + garde les feux rouges"""
        # Phares blancs pour la marche arrière (LEDs 3 et 6)
        for led_id in self.white_lights:
            # Si c'est un clignotant actif, ne pas écraser
            if not (self.blinker_active and led_id in [self.left_blinker, self.right_blinker]):
                self.led_bar.set_ledpixel(led_id, self.white_intensity, self.white_intensity, self.white_intensity)
        
        # Garder les feux rouges sur les autres LEDs
        self._set_rear_lights(self.low_intensity)
        
        self.led_bar.show()

    def _clear_white_lights(self):
        """Éteint les phares blancs (LEDs 3 et 6) et remet les feux rouges"""
        # Éteindre les phares blancs
        for led_id in self.white_lights:
            if not (self.blinker_active and led_id in [self.left_blinker, self.right_blinker]):
                self.led_bar.set_ledpixel(led_id, 0, 0, 0)
        
        # Remettre les feux rouges normaux
        self._set_rear_lights(self.low_intensity)

    def _start_blinker(self, direction):
        """
        Démarre le clignotant
        
        Args:
            direction: 'left' ou 'right'
        """
        if self.blinker_active and self.blinker_direction == direction:
            return  # Déjà actif dans cette direction
        
        self._stop_blinkers()
        
        self.blinker_active = True
        self.blinker_direction = direction
        self.blinker_stop_event.clear()
        
        self.blinker_thread = threading.Thread(
            target=self._blinker_loop, 
            args=(direction,), 
            daemon=True
        )
        self.blinker_thread.start()

    def _stop_blinkers(self):
        """Arrête tous les clignotants"""
        if self.blinker_active:
            self.blinker_active = False
            self.blinker_stop_event.set()
            
            if self.blinker_thread and self.blinker_thread.is_alive():
                self.blinker_thread.join(timeout=0.5)
            
            # Éteindre les LEDs des clignotants (3 et 6)
            self.led_bar.set_ledpixel(self.left_blinker, 0, 0, 0)
            self.led_bar.set_ledpixel(self.right_blinker, 0, 0, 0)
            self.led_bar.show()

    def _blinker_loop(self, direction):
        """
        Boucle de clignotement
        
        Args:
            direction: 'left' ou 'right'
        """
        led_id = self.left_blinker if direction == 'left' else self.right_blinker
        blink_intensity = 255  # Orange/jaune pour les clignotants
        
        while self.blinker_active and not self.blinker_stop_event.is_set():
            # Allumer (orange/jaune)
            self.led_bar.set_ledpixel(led_id, blink_intensity, blink_intensity//2, 0)
            self.led_bar.show()
            
            if self.blinker_stop_event.wait(0.5):  # 500ms allumé
                break
            
            # Éteindre
            self.led_bar.set_ledpixel(led_id, 0, 0, 0)
            self.led_bar.show()
            
            if self.blinker_stop_event.wait(0.5):  # 500ms éteint
                break

    def _control_loop(self):
        """Boucle principale de contrôle"""
        while self.running:
            time.sleep(0.1)  # Vérification toutes les 100ms

    def cleanup(self):
        """Nettoie les ressources"""
        self.running = False
        self._stop_blinkers()
        
        if self.stop_timer:
            self.stop_timer.cancel()
        
        # Éteindre toutes les LEDs arrière (2, 3, 4, 5, 6, 7)
        for led_id in [2, 3, 4, 5, 6, 7]:
            self.led_bar.set_ledpixel(led_id, 0, 0, 0)
        self.led_bar.show()

    # Méthodes de commodité pour intégration avec le webserver
    def on_move_forward(self):
        """Robot avance"""
        self.set_robot_state(RobotState.MOVING_FORWARD)

    def on_move_backward(self):
        """Robot recule"""
        self.set_robot_state(RobotState.MOVING_BACKWARD)

    def on_turn_left(self):
        """Robot tourne à gauche"""
        self.set_robot_state(RobotState.TURNING_LEFT)

    def on_turn_right(self):
        """Robot tourne à droite"""
        self.set_robot_state(RobotState.TURNING_RIGHT)

    def on_backward_turn_left(self):
        """Robot recule et tourne à gauche"""
        self.set_robot_state(RobotState.MOVING_BACKWARD)
        self._start_blinker('left')

    def on_backward_turn_right(self):
        """Robot recule et tourne à droite"""
        self.set_robot_state(RobotState.MOVING_BACKWARD)
        self._start_blinker('right')

    def on_stop(self):
        """Robot s'arrête"""
        self.set_robot_state(RobotState.STOPPED)

    def get_status(self):
        """Retourne le statut actuel"""
        return {
            'state': self.current_state.value,
            'blinker_active': self.blinker_active,
            'blinker_direction': self.blinker_direction,
            'last_movement': self.last_movement_time
        }


# Fonctions utilitaires pour intégration facile

def create_back_light_controller(led_bar):
    """
    Crée et retourne une instance du contrôleur de feux arrière
    
    Args:
        led_bar: Instance de Adeept_SPI_LedPixel
        
    Returns:
        BackLightController: Instance du contrôleur
    """
    return BackLightController(led_bar)


# Exemple d'utilisation
if __name__ == "__main__":
    # Test avec simulation
    from temp import Adeept_SPI_LedPixel
    
    # Initialiser la barre LED
    led_bar = Adeept_SPI_LedPixel(count=14, bright=255, sequence='GRB', bus=0, device=0)
    
    if not led_bar.led_init_state:
        print("Erreur d'initialisation LED")
        exit(1)
    
    # Créer le contrôleur
    controller = create_back_light_controller(led_bar)
    
    try:
        print("Test du contrôleur de LEDs arrière...")
        print("1. État arrêté (intensité faible puis forte)")
        controller.on_stop()
        time.sleep(2)
        
        print("2. Marche avant")
        controller.on_move_forward()
        time.sleep(2)
        
        print("3. Virage à gauche (clignotant LED 3)")
        controller.on_turn_left()
        time.sleep(3)
        
        print("4. Virage à droite (clignotant LED 6)")
        controller.on_turn_right()
        time.sleep(3)
        
        print("5. Marche arrière (phares blancs LEDs 3 et 6)")
        controller.on_move_backward()
        time.sleep(2)
        
        print("6. Marche arrière + virage gauche (phares blancs + clignotant)")
        controller.on_backward_turn_left()
        time.sleep(3)
        
        print("7. Arrêt final (délai 3s avant intensité forte)")
        controller.on_stop()
        time.sleep(4)
        
        print("Status:", controller.get_status())
        
    except KeyboardInterrupt:
        print("\nArrêt demandé")
    finally:
        controller.cleanup()
        led_bar.led_close()
        print("Nettoyage terminé")