# -*- coding: Windows-1252 -*-
#!/usr/bin/env python3

import time
import threading
from gpiozero import InputDevice
from motor import Motor, motorStop
from servo_controller_improved import servo_controller
# PAS D'IMPORT DE CAMERA - on utilisera celle pass�e en param�tre
from line_detection import LineDetector

class LineFollowerImproved:
    # Mappage des actions base sur les capteurs IR (gauche, centre, droite)
    ACTION_MAP = {
        (0,0,0): "lost",           # Aucun capteur ne detecte - VRAIMENT PERDU
        (1,1,1): "forward",        # Tous les capteurs detectent
        (0,1,0): "forward",        # Seul le centre detecte
        (1,1,0): "slight_right",   # Gauche et centre detectent
        (0,1,1): "slight_left",    # Centre et droite detectent
        (1,0,0): "turn_right",     # Seule la gauche detecte - RESTAUR� turn au lieu de sharp
        (0,0,1): "turn_left",      # Seule la droite detecte - RESTAUR� turn au lieu de sharp
        (1,0,1): "forward"         # Gauche et droite detectent (cas rare) - continuer
    }

    def __init__(self, camera_instance=None):
        # Capteurs IR pour suivi de ligne
        self.sensors = {
            'left':   InputDevice(17),
            'middle': InputDevice(27),
            'right':  InputDevice(22),
        }
        
        # Vitesses de moteur
        self.speeds = {
            'normal': 20,      # Vitesse normale
            'turn': 18,        # Vitesse en virage
            'search': 8,       # Vitesse de recherche (R�DUITE pour plus de contr�le)
            'recovery': 10     # Vitesse de r�cup�ration (R�DUITE)
        }
        
        # Angles de direction pour les roues
        self.wheel_angles = {
            'center': 90,
            'slight_left': 100,
            'slight_right': 80,
            'turn_left': 110,
            'turn_right': 70,
            'sharp_left': 125,     # Plus agressif (�tait 120)
            'sharp_right': 55,     # Plus agressif (�tait 60)
            'extreme_left': 135,   # Nouveau : angle extr�me pour r�cup�ration difficile
            'extreme_right': 45,   # Nouveau : angle extr�me pour r�cup�ration difficile
        }
        
        # Positions de la t�te de cam�ra
        self.head_positions = {
            'normal': 90,      # Position normale
            'down': 60,        # Position baiss�e pour r�cup�ration
            'very_down': 55,   # Position basse maximum (limite physique)
            'scan_left': 120,  # Scan vers la gauche
            'scan_right': 60   # Scan vers la droite
        }
        
        # UTILISER LA CAM�RA EXISTANTE au lieu d'en cr�er une nouvelle
        self.camera = camera_instance
        self.line_detector = LineDetector()
        
        # �tat du syst�me
        self.running = False
        self.thread = None
        self.recovery_mode = False
        self.last_wheel_angle = self.wheel_angles['center']
        self.lost_line_count = 0
        self.max_lost_attempts = 6  # R�duit de 8 � 6 pour �viter attente trop longue
        
        # Statistiques
        self.stats = {
            'ir_detections': 0,
            'camera_recoveries': 0,
            'successful_recoveries': 0,
            'failed_recoveries': 0
        }

    def set_camera(self, camera_instance):
        """D�finit l'instance de cam�ra � utiliser"""
        self.camera = camera_instance

    def read_ir_sensors(self):
        """Lit les capteurs IR et retourne un tuple (gauche, centre, droite)"""
        return tuple(int(self.sensors[k].value) for k in ('left', 'middle', 'right'))

    def get_action_from_sensors(self, sensor_pattern):
        """D�termine l'action � prendre bas�e sur les capteurs IR"""
        return self.ACTION_MAP.get(sensor_pattern, 'stop')

    def steer_wheels(self, angle_name):
        """Oriente les roues selon l'angle sp�cifi�"""
        if angle_name in self.wheel_angles:
            angle = self.wheel_angles[angle_name]
            servo_controller.move_to_angle(0, angle, blocking=False)
            self.last_wheel_angle = angle
            time.sleep(0.03)

    def move_motor(self, forward=True, speed_name='normal'):
        """Contr�le le moteur avec la vitesse sp�cifi�e"""
        if speed_name in self.speeds:
            speed = self.speeds[speed_name]
            direction = 1 if forward else -1
            Motor(1, direction, speed)

    def stop_all_motors(self):
        """Arr�te tous les moteurs"""
        motorStop()

    def move_head_horizontal(self, direction, angle_offset=20):
        """D�place la t�te horizontalement (gauche/droite) - SERVO 1"""
        try:
            current_pos = servo_controller.get_current_position(1)
            if current_pos is None:
                current_pos = 90  # Position par d�faut
            
            if direction == 'left':
                target_angle = min(current_pos + angle_offset, 150)
            elif direction == 'right':
                target_angle = max(current_pos - angle_offset, 30)
            elif direction == 'center':
                target_angle = 90
            else:
                return False
            
            print(f"Mouvement t�te horizontal vers {direction} (angle {target_angle}�)")
            servo_controller.move_to_angle(1, target_angle, blocking=True)
            time.sleep(0.3)
            return True
            
        except Exception as e:
            print(f"Erreur mouvement t�te horizontal: {e}")
            return False

    def reset_all_servos(self):
        """Remet tous les servos en position initiale"""
        print("R�initialisation de tous les servos...")
        try:
            # Servo 0: Roues au centre
            servo_controller.move_to_angle(0, 90, blocking=True)
            time.sleep(0.3)
            
            # Servo 1: T�te gauche/droite au centre
            servo_controller.move_to_angle(1, 90, blocking=True)
            time.sleep(0.3)
            
            # Servo 2: T�te haut/bas � la normale (90� = position normale)
            servo_controller.move_to_angle(2, 90, blocking=True)
            time.sleep(0.3)
            
            print("Tous les servos r�initialis�s")
            
        except Exception as e:
            print(f"Erreur lors de la r�initialisation des servos: {e}")

    def convert_camera_direction_to_wheels(self, camera_direction):
        """Convertit la direction cam�ra en angle de roues appropri�"""
        direction_mapping = {
            'sharp_left': 'sharp_left',
            'left': 'turn_left', 
            'center': 'center',
            'right': 'turn_right',
            'sharp_right': 'sharp_right'
        }
        return direction_mapping.get(camera_direction, 'center')

    def convert_camera_angle_to_direction(self, angle):
        """Convertit l'angle d�tect� par la cam�ra en direction d'action"""
        if angle is None:
            return 'center'
        
        # Conversion angle cam�ra -> direction robot
        # Angles n�gatifs = ligne � gauche, positifs = ligne � droite
        if angle < -25:
            return 'sharp_left'
        elif angle < -10:
            return 'left'
        elif angle < 10:
            return 'center'
        elif angle < 25:
            return 'right'
        else:
            return 'sharp_right'

    def move_head(self, position_name, blocking=True):
        """D�place la t�te de la cam�ra - SERVO 2 pour haut/bas"""
        if position_name in self.head_positions:
            angle = self.head_positions[position_name]
            print(f"D�placement t�te vers {position_name} (angle {angle}�)")
            # CORRECTION : Utiliser servo 2 pour la t�te haut/bas (pas servo 1)
            servo_controller.move_to_angle(2, angle, blocking=blocking)
            if blocking:
                # Temps adapt� selon l'amplitude du mouvement
                if position_name == 'very_down':
                    time.sleep(0.4)  # Plus de temps pour stabilisation
                else:
                    time.sleep(0.3)   # Autres mouvements

    def camera_line_recovery(self):
        """Procedure de recuperation de ligne utilisant la camera"""
        print("=== DEBUT RECUPERATION CAMERA ===")
        self.stats['camera_recoveries'] += 1
        self.recovery_mode = True
        
        # Verifier que la camera est disponible
        if not self.camera:
            print("ERREUR: Aucune camera disponible pour la recuperation")
            self.stats['failed_recoveries'] += 1
            self.recovery_mode = False
            return False
        
        try:
            # 1. Arreter le mouvement et baisser la tete AU MAXIMUM POSSIBLE
            self.stop_all_motors()
            print("Tete baissee au maximum possible pour analyse camera")
            self.move_head('very_down', blocking=True)
            time.sleep(0.4)  # Temps reduit car mouvement moins important
            
            # 2. Reculer PLUS LONGTEMPS en braquant dans la direction opposee
            center_angle = self.wheel_angles['center']
            if self.last_wheel_angle > center_angle:
                # Derniere direction etait a gauche, reculer vers la droite
                backup_angle = 'sharp_right'
                recovery_angle = 'sharp_left'
                extreme_recovery = 'extreme_left'
            else:
                # Derniere direction etait a droite, reculer vers la gauche
                backup_angle = 'sharp_left'
                recovery_angle = 'sharp_right'
                extreme_recovery = 'extreme_right'
            
            print(f"Recul PROLONGE avec angle {backup_angle}")
            self.steer_wheels(backup_angle)
            self.move_motor(forward=False, speed_name='search')
            time.sleep(2.0)  # Temps reduit (etait 3.0) mais vitesse plus lente
            self.stop_all_motors()
            
            # 3. Pause pour stabilisation et analyse
            print("Stabilisation et analyse de la zone...")
            time.sleep(0.25)  # Temps reduit car mouvement moins important
            
            # 4. RECUPERATION CAMERA AVEC LIMITE DE TEMPS
            print("=== DEBUT RECUPERATION CAMERA ===")
            start_time = time.time()
            recovery_timeout = 15.0  # Maximum 15 secondes pour la r�cup�ration cam�ra
            recovery_attempts = 0
            max_recovery_attempts = 3  # REDUIT de 5 � 3 tentatives
            success = False
            
            while (recovery_attempts < max_recovery_attempts and 
                   not success and 
                   (time.time() - start_time) < recovery_timeout):
                
                recovery_attempts += 1
                print(f"Tentative de recuperation {recovery_attempts}/{max_recovery_attempts}")
                
                # Rechercher la ligne avec la camera
                print("Analyse camera pour localiser la ligne...")
                found_angle, result = self.line_detector.find_line_with_scanning(self.camera)
                
                if result == "found" and found_angle is not None:
                    print(f"Ligne detectee par camera a l'angle {found_angle}")
                    
                    # Convertir l'angle en direction precise
                    camera_direction = self.convert_camera_angle_to_direction(found_angle)
                    print(f"Direction calculee: {camera_direction}")
                    
                    # Appliquer la direction detectee
                    wheel_direction = self.convert_camera_direction_to_wheels(camera_direction)
                    print(f"Orientation roues: {wheel_direction}")
                    
                    # Orienter les roues selon la detection camera
                    self.steer_wheels(wheel_direction)
                    time.sleep(0.2)  # Temps reduit
                    
                    # Avancer prudemment vers la ligne - DUREE REDUITE
                    print("Avancement vers la ligne detectee...")
                    self.move_motor(forward=True, speed_name='recovery')
                    time.sleep(0.5)  # REDUIT de 0.8 � 0.5
                    self.stop_all_motors()
                    
                    # Verification immediate
                    time.sleep(0.1)  # Stabilisation rapide
                    sensor_check = self.read_ir_sensors()
                    print(f"Capteurs IR apres repositionnement: {sensor_check}")
                    
                    # Conditions de succes : au moins le centre OU 2 capteurs
                    if (sensor_check == (1,1,1) or 
                        sensor_check == (1,1,0) or 
                        sensor_check == (0,1,1) or
                        sensor_check == (0,1,0)):  # Centre detecte = succ�s
                        
                        print(f"SUCCES ! Ligne recuperee avec capteurs: {sensor_check}")
                        self.stats['successful_recoveries'] += 1
                        success = True
                        break
                    
                    elif any(sensor_check):  # D�tection partielle
                        print(f"Detection partielle: {sensor_check}, ajustement RAPIDE...")
                        
                        # AJUSTEMENT PLUS RAPIDE ET SIMPLE
                        if sensor_check[0] == 1 and sensor_check[1] == 0:  # Seule gauche
                            print("Micro-ajustement vers la droite...")
                            self.steer_wheels('slight_right')
                        elif sensor_check[2] == 1 and sensor_check[1] == 0:  # Seule droite
                            print("Micro-ajustement vers la gauche...")
                            self.steer_wheels('slight_left')
                        else:
                            print("Detection OK, on continue...")
                            success = True
                            break
                        
                        # Mouvement d'ajustement tres court
                        self.move_motor(forward=True, speed_name='search')
                        time.sleep(0.2)  # TRES court
                        self.stop_all_motors()
                        
                        # Verification finale rapide
                        final_check = self.read_ir_sensors()
                        print(f"Capteurs apres ajustement: {final_check}")
                        if any(final_check):  # N'importe quelle detection = OK
                            print(f"SUCCES apres ajustement ! Capteurs: {final_check}")
                            self.stats['successful_recoveries'] += 1
                            success = True
                            break
                    
                    else:
                        print("Aucune detection IR, recul court...")
                        # Recul tres court pour nouvelle tentative
                        self.move_motor(forward=False, speed_name='search')
                        time.sleep(0.3)  # TRES court
                        self.stop_all_motors()
                
                else:
                    print("Aucune ligne detectee par camera, repositionnement rapide...")
                    # Mouvement de recherche RAPIDE
                    search_direction = 'turn_left' if recovery_attempts % 2 == 1 else 'turn_right'
                    self.steer_wheels(search_direction)
                    self.move_motor(forward=True, speed_name='search')
                    time.sleep(0.4)  # REDUIT
                    self.stop_all_motors()
                
                time.sleep(0.1)  # Pause courte entre tentatives
            
            # Verification du timeout
            if (time.time() - start_time) >= recovery_timeout:
                print("TIMEOUT de recuperation camera atteint")
            
            print(f"=== FIN BOUCLE RECUPERATION - Succes: {success} ===")
            
            if not success:
                print("Echec de recuperation camera rapide")
                # PAS de r�cup�ration extr�me - on reprend le suivi normal
                print("Reprise du suivi IR malgre l'echec")
                success = True  # Forcer la reprise
            
            # 7. Remettre la tete en position normale RAPIDEMENT
            print("Remise tete en position normale...")
            self.move_head('normal', blocking=True)  # Direct en position normale
            time.sleep(0.2)  # Temps reduit
            
            # 8. Remettre les roues au centre RAPIDEMENT
            print("Remise des roues au centre...")
            self.steer_wheels('center')
            time.sleep(0.1)  # Temps tres reduit
            
            # 9. FORCER LA REPRISE DU SUIVI IR
            print("REPRISE FORCEE du suivi IR...")
            self.lost_line_count = 0  # Reset du compteur
            
            return success
            
        except Exception as e:
            print(f"Erreur durant la recuperation camera: {e}")
            self.stats['failed_recoveries'] += 1
            return False
        finally:
            self.recovery_mode = False
            # FORCER la reprise du suivi IR m�me en cas d'erreur
            self.lost_line_count = 0
            print("=== FIN RECUPERATION CAMERA ===")
    
    def extreme_recovery(self, extreme_angle):
        """Procedure de recuperation extreme avec angles maximaux"""
        print(f"=== RECUPERATION EXTREME avec {extreme_angle} ===")
        
        try:
            # 1. Recul avec angle extreme PLUS LONG mais vitesse reduite
            print(f"Recul EXTREME avec angle {extreme_angle}")
            self.steer_wheels(extreme_angle)
            self.move_motor(forward=False, speed_name='search')
            time.sleep(2.5)  # Temps reduit (etait 3.5) mais vitesse plus lente
            self.stop_all_motors()
            
            # 2. Rotation sur place PLUS LONGUE
            print("Rotation sur place prolongee pour balayage")
            opposite_extreme = 'extreme_right' if 'left' in extreme_angle else 'extreme_left'
            self.steer_wheels(opposite_extreme)
            self.move_motor(forward=True, speed_name='search')
            time.sleep(1.2)  # Legerement reduit (etait 1.5)
            self.stop_all_motors()
            
            # 3. BOUCLE DE RECUPERATION EXTREME
            for attempt in range(3):
                print(f"Tentative extreme {attempt + 1}/3")
                
                # Nouvelle recherche camera avec analyse
                time.sleep(0.4)
                found_angle, result = self.line_detector.find_line_with_scanning(self.camera)
                
                if result == "found" and found_angle is not None:
                    print(f"Ligne trouvee avec recuperation extreme a l'angle {found_angle} !")
                    
                    # UTILISER L'ANGLE DETECTE pour orienter correctement
                    camera_direction = self.convert_camera_angle_to_direction(found_angle)
                    print(f"Direction camera extreme: {camera_direction}")
                    
                    # Conversion en angle de roue avec extremes
                    if camera_direction == 'sharp_left':
                        final_angle = 'extreme_left'
                    elif camera_direction == 'left':
                        final_angle = 'sharp_left'
                    elif camera_direction == 'right':
                        final_angle = 'sharp_right'
                    elif camera_direction == 'sharp_right':
                        final_angle = 'extreme_right'
                    else:
                        final_angle = 'center'
                    
                    # Avancement prudent avec direction adaptee
                    self.steer_wheels(final_angle)
                    self.move_motor(forward=True, speed_name='search')
                    time.sleep(1.0)
                    self.stop_all_motors()
                    
                    # Verification avec les conditions strictes
                    sensor_check = self.read_ir_sensors()
                    print(f"Capteurs apres recuperation extreme: {sensor_check}")
                    
                    if (sensor_check == (1,1,1) or sensor_check == (1,1,0) or 
                        sensor_check == (0,1,1) or sensor_check == (0,1,0)):
                        print("Recuperation extreme reussie !")
                        self.stats['successful_recoveries'] += 1
                        return True
                    elif any(sensor_check):
                        print("Detection partielle en mode extreme, ajustement...")
                        # Un petit ajustement final
                        if sensor_check[0] == 1 and not sensor_check[1]:
                            self.steer_wheels('slight_right')
                        elif sensor_check[2] == 1 and not sensor_check[1]:
                            self.steer_wheels('slight_left')
                        
                        self.move_motor(forward=True, speed_name='search')
                        time.sleep(0.3)
                        self.stop_all_motors()
                        
                        final_check = self.read_ir_sensors()
                        if (final_check == (1,1,1) or final_check == (1,1,0) or 
                            final_check == (0,1,1) or final_check == (0,1,0)):
                            print("Recuperation extreme reussie apres ajustement !")
                            self.stats['successful_recoveries'] += 1
                            return True
                
                # Si pas de succes, petit repositionnement pour tentative suivante
                if attempt < 2:  # Pas au dernier essai
                    search_dir = 'extreme_left' if attempt % 2 == 0 else 'extreme_right'
                    self.steer_wheels(search_dir)
                    self.move_motor(forward=False, speed_name='search')
                    time.sleep(0.8)
                    self.stop_all_motors()
            
            print("Recuperation extreme echouee")
            self.stats['failed_recoveries'] += 1
            return False
            
        except Exception as e:
            print(f"Erreur durant la recuperation extreme: {e}")
            return False

    def handle_ir_action(self, action):
        """G�re les actions bas�es sur les capteurs IR"""
        if action == 'forward':
            self.steer_wheels('center')
            self.move_motor(forward=True, speed_name='normal')
            
        elif action == 'slight_left':
            self.steer_wheels('slight_left')
            self.move_motor(forward=True, speed_name='turn')
            
        elif action == 'slight_right':
            self.steer_wheels('slight_right')
            self.move_motor(forward=True, speed_name='turn')
            
        elif action == 'turn_left':
            self.steer_wheels('turn_left')
            self.move_motor(forward=True, speed_name='turn')
            
        elif action == 'turn_right':
            self.steer_wheels('turn_right')
            self.move_motor(forward=True, speed_name='turn')
            
        else:  # stop ou action inconnue
            self.stop_all_motors()

    def _main_loop(self):
        """Boucle principale de suivi de ligne"""
        print("D�marrage du suivi de ligne am�lior�")
        
        # V�rifier que la cam�ra est disponible
        if not self.camera:
            print("ERREUR: Aucune cam�ra disponible pour le suivi de ligne")
            return
        
        # Initialisation des positions avec v�rification
        print("Initialisation des positions de d�part...")
        self.reset_all_servos()  # R�initialisation compl�te
        time.sleep(1.0)  # Plus de temps pour la stabilisation compl�te
        
        # Test initial de la cam�ra ET des servos
        print("Test initial de la cam�ra...")
        test_frame = self.camera.get_frame_for_processing()
        if test_frame is None:
            print("ATTENTION: Probl�me avec la cam�ra d�tect�")
        else:
            print("Cam�ra op�rationnelle")
        
        print("Test des servos...")
        # Test rapide des servos avec petit mouvement
        try:
            # Test servo 2 (t�te haut/bas)
            self.move_head('down', blocking=True)
            time.sleep(0.2)
            self.move_head('normal', blocking=True)
            
            # Test servo 0 (roues)
            self.steer_wheels('slight_left')
            time.sleep(0.2)
            self.steer_wheels('center')
            
            # Test servo 1 (t�te gauche/droite)
            self.move_head_horizontal('left', 10)
            time.sleep(0.2)
            self.move_head_horizontal('center')
            
            print("Servos op�rationnels")
        except Exception as e:
            print(f"ATTENTION: Probl�me avec les servos: {e}")
        
        while self.running:
            try:
                # Lecture des capteurs IR
                sensor_pattern = self.read_ir_sensors()
                action = self.get_action_from_sensors(sensor_pattern)
                
                # CONDITION AMELIOREE ET TOLERANTE
                if sensor_pattern == (0,0,0):  # Vraiment perdu
                    self.lost_line_count += 1
                    print(f"Ligne completement perdue (tentative {self.lost_line_count}/{self.max_lost_attempts})")
                    
                    if self.lost_line_count >= self.max_lost_attempts:
                        # Tenter une recuperation par camera
                        print("Declenchement de la recuperation camera...")
                        recovery_success = self.camera_line_recovery()
                        
                        # FORCER LA REPRISE DU SUIVI IR dans tous les cas
                        print("REPRISE IMMEDIATE du suivi IR apres recuperation")
                        self.lost_line_count = 0  # Reset force
                        
                        # TEST: Lire imm�diatement les capteurs pour v�rifier la reprise
                        time.sleep(0.1)
                        test_sensors = self.read_ir_sensors()
                        print(f"TEST REPRISE: Capteurs apres recuperation: {test_sensors}")
                        
                        if not recovery_success:
                            print("Recuperation partiellement echouee mais reprise du suivi IR")
                        
                    else:
                        # Arret temporaire et nouvelle tentative AVEC MOUVEMENT DE RECHERCHE
                        self.stop_all_motors()
                        # Petit mouvement de recherche pour essayer de retrouver la ligne
                        search_direction = 'slight_left' if self.lost_line_count % 2 == 1 else 'slight_right'
                        self.steer_wheels(search_direction)
                        self.move_motor(forward=True, speed_name='search')
                        time.sleep(0.3)  # Mouvement court de recherche
                        self.stop_all_motors()
                        time.sleep(0.1)
                else:
                    # Ligne detectee par IR (au moins un capteur), traitement normal
                    if self.lost_line_count > 0:
                        print(f"Ligne retrouvee par capteurs IR: {sensor_pattern}")
                        self.lost_line_count = 0
                    
                    self.stats['ir_detections'] += 1
                    # DEBUG: Afficher l'action pour comprendre le comportement
                    if self.stats['ir_detections'] % 50 == 0:  # Tous les 50 d�tections
                        print(f"DEBUG: Capteurs {sensor_pattern} -> Action: {action}")
                    
                    self.handle_ir_action(action)
                
                time.sleep(0.02)  # Fr�quence de 50Hz
                
            except Exception as e:
                print(f"Erreur dans la boucle principale: {e}")
                break
        
        # Nettoyage final
        print("Nettoyage final...")
        self.stop_all_motors()
        self.reset_all_servos()  # R�initialisation compl�te
        print("Suivi de ligne arr�t�")

    def start(self):
        """D�marre le suivi de ligne"""
        if self.running:
            print("Le suivi de ligne est d�j� en cours")
            return False
            
        if not self.camera:
            print("ERREUR: Aucune cam�ra disponible pour d�marrer le suivi")
            return False
            
        self.running = True
        self.lost_line_count = 0
        self.recovery_mode = False
        
        # R�initialiser les statistiques
        for key in self.stats:
            self.stats[key] = 0
            
        self.thread = threading.Thread(target=self._main_loop, daemon=True)
        self.thread.start()
        print("Suivi de ligne d�marr�")
        return True

    def stop(self):
        """Arr�te le suivi de ligne"""
        if not self.running:
            return False
            
        print("Arr�t du suivi de ligne...")
        self.running = False
        
        # Attendre la fin du thread
        if self.thread and threading.current_thread() is not self.thread:
            self.thread.join(timeout=3.0)
        
        # Nettoyage final
        self.stop_all_motors()
        try:
            self.reset_all_servos()  # Reinitialisation complete de tous les servos
        except:
            # En cas d'erreur, essayer individuellement
            try:
                self.steer_wheels('center')
                self.move_head('normal', blocking=True)
            except:
                pass
            
        print("Suivi de ligne arr�t�")
        print(f"Statistiques: {self.stats}")
        return True

    def is_running(self):
        """Retourne True si le suivi de ligne est actif"""
        return self.running

    def get_status(self):
        """Retourne le statut actuel du syst�me"""
        sensor_pattern = self.read_ir_sensors()
        return {
            'running': self.running,
            'recovery_mode': self.recovery_mode,
            'sensors': sensor_pattern,
            'lost_count': self.lost_line_count,
            'stats': self.stats.copy(),
            'last_wheel_angle': self.last_wheel_angle,
            'camera_available': self.camera is not None
        }

# Instance globale qui sera initialis�e dans webserver.py
line_follower = None