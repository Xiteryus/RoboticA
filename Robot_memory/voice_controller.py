# -*- coding: Windows-1252 -*-
"""
Contr�leur vocal pour le robot
Permet de contr�ler le robot par commandes vocales en parall�le du webserver
"""

import threading
import time
import subprocess
import os
from motor import Motor, motorStop, drive, backward
from servo_controller_improved import servo_controller
from servo_controller import set_angle
from led_controller_improved import led_controller_improved

class VoiceController:
    def __init__(self):
        # �tats du robot
        self.current_mode = None  # 'ir', 'labyrinthe' ou None
        self.is_moving = False
        self.current_direction = None
        
        # Instances partag�es (d�finies par webserver)
        self.camera = None
        self.back_light_controller = None
        self.challenge2_mode = None
        self.labyrinthe_mode = None
        
        # Thread de reconnaissance vocale
        self.voice_thread = None
        self.running = False
        
        # Fichier de commandes
        self.output_file = "output.txt"
        self.file_position = 0
        
        # Angles de direction
        self.ANGLE_CENTER = 90
        self.ANGLE_LEFT = 120
        self.ANGLE_RIGHT = 60
        self.ANGLE_SHARP_LEFT = 130
        self.ANGLE_SHARP_RIGHT = 50
        
        # Configuration des servos t�te
        self.head_positions = {
            'horizontal': 90,  # Servo 1
            'vertical': 90     # Servo 2
        }
        
        print("Contr�leur vocal initialis�")
    
    def set_shared_instances(self, camera, back_light_controller, challenge2_mode, labyrinthe_mode):
        """Configure les instances partag�es depuis le webserver"""
        self.camera = camera
        self.back_light_controller = back_light_controller
        self.challenge2_mode = challenge2_mode
        self.labyrinthe_mode = labyrinthe_mode
        print("Instances partag�es configur�es pour le contr�le vocal")
    
    def clear_output(self):
        """Efface le fichier de sortie et remet le pointeur � z�ro - UTF-8 propre"""
        try:
            with open(self.output_file, "w", encoding='utf-8') as file:
                file.write("")
            self.file_position = 0
            print("Fichier de sortie effac� (UTF-8)")
        except Exception as e:
            print(f"Erreur effacement fichier: {e}")
    
    def process_voice_commands(self):
        """Traite les commandes vocales depuis output.txt - Version avec gestion encodage"""
        print("Thread de traitement des commandes vocales d�marr�")
        
        while self.running:
            try:
                if os.path.exists(self.output_file):
                    # Essayer de lire avec diff�rents encodages
                    encodings_to_try = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
                    file_read_success = False
                    
                    for encoding in encodings_to_try:
                        try:
                            with open(self.output_file, "r", encoding=encoding) as file:
                                file.seek(self.file_position)
                                new_lines = file.readlines()
                                
                                if new_lines:
                                    print(f"{len(new_lines)} nouvelles lignes lues ({encoding})")
                                    
                                    # Traiter toutes les nouvelles lignes
                                    for line in new_lines:
                                        line = line.strip()
                                        if line:
                                            # Extraire la commande (apr�s l'horodatage)
                                            if ':' in line:
                                                command = line.split(':', 1)[1].strip()
                                            else:
                                                command = line
                                            
                                            if command:
                                                print(f"Commande vocale d�tect�e: '{command}'")
                                                self.execute_command(command)
                                
                                self.file_position = file.tell()
                                file_read_success = True
                                break  # Sortir de la boucle des encodages
                                
                        except UnicodeDecodeError:
                            print(f"�chec lecture avec {encoding}")
                            continue
                    
                    # Si aucun encodage ne fonctionne, nettoyer le fichier
                    if not file_read_success:
                        print("Nettoyage du fichier � cause des probl�mes d'encodage")
                        self.clear_output()
                            
            except Exception as e:
                print(f"Erreur lecture fichier: {e}")
            
            time.sleep(0.5)  # V�rifier toutes les 500ms
    
    def execute_command(self, command):
        """Ex�cute une commande vocale"""
        # Nettoyer et normaliser la commande
        command = command.lower().strip()
        print(f"Ex�cution de la commande: '{command}'")
        
        # Commandes de mode
        if any(keyword in command for keyword in ["start ir", "mode ir", "infrarouge", "suivi ligne"]):
            self.start_ir_mode()
            
        elif any(keyword in command for keyword in ["start labyrinthe", "labyrinthe", "maze"]):
            self.start_labyrinthe_mode()
            
        elif any(keyword in command for keyword in ["stop mode", "arreter mode", "arret mode"]):
            self.stop_current_mode()
        
        # Commandes de mouvement
        elif any(keyword in command for keyword in ["avancer", "forward", "avant"]):
            self.move_forward()
            
        elif any(keyword in command for keyword in ["reculer", "backward", "back", "arriere"]):
            self.move_backward()
            
        elif any(keyword in command for keyword in ["gauche", "left", "tourner gauche"]):
            self.turn_left()
            
        elif any(keyword in command for keyword in ["droite", "right", "tourner droite"]):
            self.turn_right()
            
        elif any(keyword in command for keyword in ["stop", "arret", "halt", "arreter"]):
            self.stop_movement()
        
        # Commandes de t�te
        elif any(keyword in command for keyword in ["regarder gauche", "look left", "tete gauche"]):
            self.look_left()
            
        elif any(keyword in command for keyword in ["regarder droite", "look right", "tete droite"]):
            self.look_right()
            
        elif any(keyword in command for keyword in ["regarder haut", "look up", "tete haut"]):
            self.look_up()
            
        elif any(keyword in command for keyword in ["regarder bas", "look down", "tete bas"]):
            self.look_down()
            
        elif any(keyword in command for keyword in ["centre", "center", "milieu", "centrer"]):
            self.center_head()
        
        # Commandes de d�tection
        elif any(keyword in command for keyword in ["couleur", "color", "detection couleur"]):
            self.toggle_color_detection()
            
        elif any(keyword in command for keyword in ["fleche", "arrow", "detection fleche"]):
            self.toggle_arrow_detection()
        
        # Commandes sp�ciales
        elif any(keyword in command for keyword in ["photo", "picture", "prendre photo"]):
            self.take_photo()
            
        elif any(keyword in command for keyword in ["arc en ciel", "rainbow", "arc-en-ciel"]):
            self.rainbow_effect()
        
        else:
            print(f"Commande non reconnue: '{command}'")
    
    # M�thodes de contr�le des modes
    def start_ir_mode(self):
        """D�marre le mode IR (Challenge 2)"""
        print("D�marrage du mode IR...")
        if not self.challenge2_mode:
            print("Challenge2 mode non disponible")
            return
            
        if self.current_mode == 'ir':
            print("Mode IR d�j� actif")
            return
            
        # Arr�ter le mode actuel
        self.stop_current_mode()
        time.sleep(0.5)
        
        # D�marrer le mode IR
        if self.challenge2_mode.start():
            self.current_mode = 'ir'
            print("Mode IR d�marr� par commande vocale")
            self.speak("Mode infrarouge activ�")
        else:
            print("Erreur d�marrage mode IR")
            self.speak("Erreur d�marrage")
    
    def start_labyrinthe_mode(self):
        """D�marre le mode labyrinthe"""
        print("D�marrage du mode labyrinthe...")
        if not self.labyrinthe_mode:
            print("Labyrinthe mode non disponible")
            return
            
        if self.current_mode == 'labyrinthe':
            print("Mode labyrinthe d�j� actif")
            return
            
        # Arr�ter le mode actuel
        self.stop_current_mode()
        time.sleep(0.5)
        
        # D�marrer le mode labyrinthe
        if self.labyrinthe_mode.start():
            self.current_mode = 'labyrinthe'
            print("Mode labyrinthe d�marr� par commande vocale")
            self.speak("Mode labyrinthe activ�")
        else:
            print("Erreur d�marrage mode labyrinthe")
            self.speak("Erreur d�marrage")
    
    def stop_current_mode(self):
        """Arr�te le mode actuel"""
        print("Arr�t du mode actuel...")
        if self.current_mode == 'ir' and self.challenge2_mode:
            self.challenge2_mode.stop()
            print("Mode IR arr�t�")
            self.speak("Mode arr�t�")
        elif self.current_mode == 'labyrinthe' and self.labyrinthe_mode:
            self.labyrinthe_mode.stop()
            print("Mode labyrinthe arr�t�")
            self.speak("Mode arr�t�")
        
        self.current_mode = None
        self.stop_movement()
    
    # M�thodes de mouvement
    def move_forward(self):
        """Fait avancer le robot"""
        if self.current_mode is None:  # Seulement en mode manuel
            print("Commande: AVANCER")
            self.is_moving = True
            self.current_direction = 'forward'
            if self.back_light_controller:
                self.back_light_controller.on_move_forward()
            try:
                drive()
                print("Robot en mouvement vers l'avant")
                self.speak("J'avance")
            except Exception as e:
                print(f"Erreur mouvement avant: {e}")
        else:
            print("Robot en mode automatique, commande ignor�e")
    
    def move_backward(self):
        """Fait reculer le robot"""
        if self.current_mode is None:
            print("Commande: RECULER")
            self.is_moving = True
            self.current_direction = 'backward'
            if self.back_light_controller:
                self.back_light_controller.on_move_backward()
            try:
                backward()
                print("Robot en mouvement vers l'arri�re")
                self.speak("Je recule")
            except Exception as e:
                print(f"Erreur mouvement arri�re: {e}")
        else:
            print("Robot en mode automatique, commande ignor�e")
    
    def turn_left(self):
        """Tourne � gauche"""
        if self.current_mode is None:
            print("Commande: TOURNER GAUCHE")
            try:
                set_angle(0, self.ANGLE_LEFT)
                if self.back_light_controller:
                    self.back_light_controller.on_turn_left()
                print("Direction: gauche")
                self.speak("Gauche")
            except Exception as e:
                print(f"Erreur direction gauche: {e}")
        else:
            print("Robot en mode automatique, commande ignor�e")
    
    def turn_right(self):
        """Tourne � droite"""
        if self.current_mode is None:
            print("Commande: TOURNER DROITE")
            try:
                set_angle(0, self.ANGLE_RIGHT)
                if self.back_light_controller:
                    self.back_light_controller.on_turn_right()
                print("Direction: droite")
                self.speak("Droite")
            except Exception as e:
                print(f"Erreur direction droite: {e}")
        else:
            print("Robot en mode automatique, commande ignor�e")
    
    def stop_movement(self):
        """Arr�te le mouvement"""
        print("Commande: STOP")
        self.is_moving = False
        self.current_direction = None
        try:
            motorStop()
            set_angle(0, self.ANGLE_CENTER)
            if self.back_light_controller:
                self.back_light_controller.on_stop()
            print("Robot arr�t�")
            self.speak("Stop")
        except Exception as e:
            print(f"Erreur arr�t: {e}")
    
    # M�thodes de contr�le de la t�te
    def look_left(self):
        """Tourne la t�te � gauche"""
        print("Commande: REGARDER GAUCHE")
        try:
            self.head_positions['horizontal'] = min(self.head_positions['horizontal'] + 20, 150)
            servo_controller.move_to_angle(1, self.head_positions['horizontal'])
            print(f"T�te gauche: {self.head_positions['horizontal']}�")
        except Exception as e:
            print(f"Erreur t�te gauche: {e}")
    
    def look_right(self):
        """Tourne la t�te � droite"""
        print("Commande: REGARDER DROITE")
        try:
            self.head_positions['horizontal'] = max(self.head_positions['horizontal'] - 20, 30)
            servo_controller.move_to_angle(1, self.head_positions['horizontal'])
            print(f"T�te droite: {self.head_positions['horizontal']}�")
        except Exception as e:
            print(f"Erreur t�te droite: {e}")
    
    def look_up(self):
        """L�ve la t�te"""
        print("Commande: REGARDER HAUT")
        try:
            self.head_positions['vertical'] = min(self.head_positions['vertical'] + 20, 150)
            servo_controller.move_to_angle(2, self.head_positions['vertical'])
            print(f"T�te haut: {self.head_positions['vertical']}�")
        except Exception as e:
            print(f"Erreur t�te haut: {e}")
    
    def look_down(self):
        """Baisse la t�te"""
        print("Commande: REGARDER BAS")
        try:
            self.head_positions['vertical'] = max(self.head_positions['vertical'] - 20, 30)
            servo_controller.move_to_angle(2, self.head_positions['vertical'])
            print(f"T�te bas: {self.head_positions['vertical']}�")
        except Exception as e:
            print(f"Erreur t�te bas: {e}")
    
    def center_head(self):
        """Centre la t�te"""
        print("Commande: CENTRER T�TE")
        try:
            self.head_positions['horizontal'] = 90
            self.head_positions['vertical'] = 90
            servo_controller.move_to_angle(1, 90)
            servo_controller.move_to_angle(2, 90)
            print("T�te centr�e")
            self.speak("T�te centr�e")
        except Exception as e:
            print(f"Erreur centrage t�te: {e}")
    
    # M�thodes de d�tection
    def toggle_color_detection(self):
        """Active/d�sactive la d�tection de couleur"""
        print("Commande: DETECTION COULEUR")
        if self.camera:
            try:
                status = self.camera.toggle_color_detection()
                if status:
                    print("D�tection couleur activ�e")
                    self.speak("Couleurs activ�es")
                else:
                    print("D�tection couleur d�sactiv�e")
                    self.speak("Couleurs d�sactiv�es")
            except Exception as e:
                print(f"Erreur d�tection couleur: {e}")
        else:
            print("Cam�ra non disponible")
    
    def toggle_arrow_detection(self):
        """Active/d�sactive la d�tection de fl�ches"""
        print("Commande: DETECTION FLECHE")
        if self.camera:
            try:
                status = self.camera.toggle_arrow_detection()
                if status:
                    print("D�tection fl�ches activ�e")
                    self.speak("Fl�ches activ�es")
                else:
                    print("D�tection fl�ches d�sactiv�e")
                    self.speak("Fl�ches d�sactiv�es")
            except Exception as e:
                print(f"Erreur d�tection fl�che: {e}")
        else:
            print("Cam�ra non disponible")
    
    # M�thodes sp�ciales
    def take_photo(self):
        """Prend une photo"""
        print("Commande: PRENDRE PHOTO")
        if self.camera:
            try:
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                filename = f"/home/pi/Pictures/voice_photo_{timestamp}.jpg"
                self.camera.photo(filename)
                print(f"Photo prise: {filename}")
                self.speak("Photo prise")
            except Exception as e:
                print(f"Erreur photo: {e}")
        else:
            print("Cam�ra non disponible")
    
    def rainbow_effect(self):
        """Lance l'effet arc-en-ciel"""
        print("Commande: ARC-EN-CIEL")
        try:
            led_controller_improved.start_rainbow_effect()
            print("Effet arc-en-ciel lanc�")
            self.speak("Arc en ciel")
            
            # Arr�ter apr�s 5 secondes
            threading.Timer(5.0, led_controller_improved.stop_effect).start()
        except Exception as e:
            print(f"Erreur effet LED: {e}")
    
    def speak(self, text):
        """Fait parler le robot"""
        try:
            subprocess.run(['espeak', '-s', '150', '-a', '100', text], 
                         capture_output=True, timeout=5)
            print(f"TTS: {text}")
        except:
            print(f"[TTS]: {text}")
    
    def start(self):
        """D�marre le contr�leur vocal - Version avec nettoyage encodage"""
        print("D�marrage du contr�leur vocal...")
        
        # Initialiser les servos si possible
        try:
            servo_controller.initialize_servos()
            print("Servos initialis�s")
        except Exception as e:
            print(f"Erreur initialisation servos: {e}")
        
        # Nettoyer et cr�er le fichier output.txt en UTF-8 propre
        try:
            # Si le fichier existe, essayer de le lire et le nettoyer
            if os.path.exists(self.output_file):
                print("Nettoyage du fichier existant...")
                
                # Essayer de lire le contenu existant
                existing_lines = []
                encodings_to_try = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
                
                for encoding in encodings_to_try:
                    try:
                        with open(self.output_file, "r", encoding=encoding) as f:
                            existing_lines = f.readlines()
                        print(f"Fichier lu avec {encoding}")
                        break
                    except UnicodeDecodeError:
                        continue
                
                # Recr�er le fichier en UTF-8 avec seulement les lignes valides
                with open(self.output_file, "w", encoding='utf-8') as f:
                    for line in existing_lines[-5:]:  # Garder seulement les 5 derni�res lignes
                        try:
                            clean_line = line.strip()
                            if clean_line:
                                f.write(clean_line + "\n")
                        except:
                            pass
            else:
                # Cr�er un nouveau fichier
                with open(self.output_file, "w", encoding='utf-8') as f:
                    f.write("")
            
            print(f"Fichier {self.output_file} pr�t (UTF-8)")
            
        except Exception as e:
            print(f"Erreur pr�paration fichier: {e}")
        
        # D�marrer le thread de traitement
        self.running = True
        self.voice_thread = threading.Thread(target=self.process_voice_commands)
        self.voice_thread.daemon = True
        self.voice_thread.start()
        
        print("Contr�leur vocal actif!")
        print("Lecture des commandes depuis:", self.output_file)
        self.speak("Contr�le vocal activ�")
    
    def stop(self):
        """Arr�te le contr�leur vocal"""
        print("Arr�t du contr�leur vocal...")
        self.running = False
        
        # Arr�ter les modes actifs
        self.stop_current_mode()
        
        # Attendre que le thread se termine
        if self.voice_thread and self.voice_thread.is_alive():
            self.voice_thread.join(timeout=2)
        
        print("Contr�leur vocal arr�t�")