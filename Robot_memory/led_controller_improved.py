# -*- coding: Windows-1252 -*-
# led_controller_improved.py - Version am?lior?e avec contr?le des LEDs avant

import RPi.GPIO as GPIO
import time
import threading

class LEDControllerImproved:
    def __init__(self):
        # Mapping des pins GPIO pour chaque LED
        self.led_pins = {
            1: 9,
            2: 25,
            3: 11,
            4: 0,
            5: 19,
            6: 13,
            7: 1,
            8: 5,
            9: 6,
            10: 12
        }
        
        # ?tats des LEDs
        self.led_states = {i: 0 for i in range(1, 11)}
        
        # LEDs avant (gauche et droite)
        self.front_left_leds = [4, 5, 6]   # LEDs RGB gauche
        self.front_right_leds = [7, 8, 9]  # LEDs RGB droite
        
        # Thread pour les effets
        self.effect_thread = None
        self.effect_running = False
        
        # Initialisation
        self.setup()
    
    def setup(self):
        """Configure les pins GPIO"""
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)
        
        # Configurer tous les pins en sortie
        for pin in self.led_pins.values():
            GPIO.setup(pin, GPIO.OUT)
        
        # ?teindre toutes les LEDs au d?marrage
        self.all_leds_off()
    
    def switch(self, port, status):
        """Allume ou ?teint une LED sp?cifique"""
        if port not in self.led_pins:
            print(f"Port {port} invalide")
            return
            
        pin = self.led_pins[port]
        
        if status == 1:
            GPIO.output(pin, GPIO.HIGH)
        else:
            GPIO.output(pin, GPIO.LOW)
            
        self.led_states[port] = status
    
    def all_leds_off(self):
        """?teint toutes les LEDs"""
        for port in range(1, 11):
            self.switch(port, 0)
    
    def set_front_leds(self, r, g, b):
        """
        Configure les LEDs avant avec une couleur RGB
        r, g, b: valeurs de 0 ? 255
        
        Mappage selon le code original led_controller.py :
        LED gauche (4,5,6) : 
        - Bleu : 5=1, 6=1, 4=0
        - Rouge : 6=0, 5=1, 4=1  
        - Vert : 5=0, 6=1, 4=1
        
        LED droite (7,8,9) :
        - Rouge : 8=1, 9=1, 7=0
        - Bleu : 9=0, 8=1, 7=1
        - Vert : 8=0, 9=1, 7=1
        """
        # D?terminer quelle couleur afficher
        if r > 200 and g < 50 and b < 50:
            # Rouge pur
            # LED gauche - Rouge
            self.switch(6, 0)
            self.switch(5, 1)
            self.switch(4, 1)
            # LED droite - Rouge
            self.switch(8, 1)
            self.switch(9, 1)
            self.switch(7, 0)
            
        elif r < 50 and g > 200 and b < 50:
            # Vert pur
            # LED gauche - Vert
            self.switch(5, 0)
            self.switch(6, 1)
            self.switch(4, 1)
            # LED droite - Vert
            self.switch(8, 0)
            self.switch(9, 1)
            self.switch(7, 1)
            
        elif r < 50 and g < 50 and b > 200:
            # Bleu pur
            # LED gauche - Bleu
            self.switch(5, 1)
            self.switch(6, 1)
            self.switch(4, 0)
            # LED droite - Bleu
            self.switch(9, 0)
            self.switch(8, 1)
            self.switch(7, 1)
            
        elif r > 200 and g > 200 and b > 200:
            # Blanc (toutes les couleurs)
            # LED gauche - tout allum?
            self.switch(4, 0)
            self.switch(5, 0)
            self.switch(6, 0)
            # LED droite - tout allum?
            self.switch(7, 0)
            self.switch(8, 0)
            self.switch(9, 0)
            
        else:
            # Noir ou autre - tout ?teint
            # LED gauche
            self.switch(4, 1)
            self.switch(5, 1)
            self.switch(6, 1)
            # LED droite
            self.switch(7, 1)
            self.switch(8, 1)
            self.switch(9, 1)
    
    def set_color_by_name(self, color_name):
        """Configure les LEDs avant selon le nom de la couleur"""
        colors = {
            'rouge': (255, 0, 0),
            'vert': (0, 255, 0),
            'bleu': (0, 0, 255)
        }
        
        if color_name and color_name.lower() in colors:
            r, g, b = colors[color_name.lower()]
            self.set_front_leds(r, g, b)
        else:
            # Couleur par défaut (blanc) si pas de couleur détectée
            self.set_front_leds(255, 255, 255)
    
    def flash_leds(self, r, g, b, duration=0.5, count=3):
        """Fait clignoter les LEDs avant"""
        for _ in range(count):
            self.set_front_leds(r, g, b)
            time.sleep(duration)
            self.set_front_leds(0, 0, 0)
            time.sleep(duration)
    
    def rainbow_effect(self):
        """Effet arc-en-ciel sur les LEDs avant"""
        colors = [
            (255, 0, 0),    # Rouge
            (0, 255, 0),    # Vert
            (0, 0, 255),    # Bleu
            (255, 255, 255) # Blanc
        ]
        
        self.effect_running = True
        while self.effect_running:
            for r, g, b in colors:
                if not self.effect_running:
                    break
                self.set_front_leds(r, g, b)
                time.sleep(0.5)
    
    def start_rainbow_effect(self):
        """D?marre l'effet arc-en-ciel en arri?re-plan"""
        if self.effect_thread and self.effect_thread.is_alive():
            return
            
        self.effect_thread = threading.Thread(target=self.rainbow_effect, daemon=True)
        self.effect_thread.start()
    
    def stop_effect(self):
        """Arr?te l'effet en cours"""
        self.effect_running = False
        if self.effect_thread:
            self.effect_thread.join(timeout=1)
        self.set_front_leds(0, 0, 0)
    
    def cleanup(self):
        """Nettoie les ressources"""
        self.stop_effect()
        self.all_leds_off()
        GPIO.cleanup()
    
    def test_all_colors(self):
        """Test toutes les couleurs principales pour v?rification"""
        colors_to_test = [
            ('rouge', 255, 0, 0),
            ('vert', 0, 255, 0),
            ('bleu', 0, 0, 255),
            ('blanc', 255, 255, 255),
            ('?teint', 0, 0, 0)
        ]
        
        for name, r, g, b in colors_to_test:
            print(f"Test couleur: {name}")
            self.set_front_leds(r, g, b)
            time.sleep(2)
        
        print("Test termin?")
    
    def get_status(self):
        """Retourne l'?tat actuel des LEDs"""
        return self.led_states.copy()


# Instance globale pour utilisation dans d'autres modules
led_controller_improved = LEDControllerImproved()

# Fonctions de compatibilit? avec l'ancien syst?me
def switchSetup():
    """Compatibilit? avec l'ancien code"""
    pass  # D?j? fait dans __init__

def switch(port, status):
    """Compatibilit? avec l'ancien code"""
    led_controller_improved.switch(port, status)

def set_all_switch_off():
    """Compatibilit? avec l'ancien code"""
    led_controller_improved.all_leds_off()

def allumer_leds_gauche():
    """Compatibilit? avec l'ancien code"""
    led_controller_improved.flash_leds(255, 0, 0, 0.5, 3)

def set_front_leds(r, g, b):
    """Interface simplifi?e pour les LEDs avant"""
    led_controller_improved.set_front_leds(r, g, b)

# Test du module
if __name__ == "__main__":
    try:
        print("Test du contr?leur LED am?lior?...")
        
        # Test des couleurs de base
        colors = ['rouge', 'vert', 'bleu']
        for color in colors:
            print(f"Couleur: {color}")
            led_controller_improved.set_color_by_name(color)
            time.sleep(1)
        
        # Test du blanc
        print("Test du blanc (aucune couleur d?tect?e)")
        led_controller_improved.set_color_by_name(None)
        time.sleep(2)
        
        # Test du clignotement
        print("Test clignotement...")
        led_controller_improved.flash_leds(255, 0, 0, 0.3, 5)
        
        # Test de l'effet arc-en-ciel
        print("Test effet arc-en-ciel (5 secondes)...")
        led_controller_improved.start_rainbow_effect()
        time.sleep(5)
        led_controller_improved.stop_effect()
        
        print("Test termin?")
        
    except KeyboardInterrupt:
        print("\nArr?t du test")
    finally:
        led_controller_improved.cleanup()