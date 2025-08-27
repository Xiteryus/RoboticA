# -*- coding: Windows-1252 -*-
from flask import Flask, render_template, redirect, url_for, request, Response, send_file, jsonify
from temp import Adeept_SPI_LedPixel
import atexit  # Pour executer une fonction a l'arret du serveur
import threading
import time
import os  # Pour la gestion des fichiers
from led_controller_improved import led_controller_improved, set_front_leds  # Version am?lior?e
from motor import Motor, motorStop, motor_drive  # Import specifique des fonctions necessaires
from led_techno import * 
from servo_reboot import *
from camera import *  # Version modifiee avec detection couleurs et lignes
from power_control import *  # Import du module de controle d'alimentation
from servo_controller_improved import servo_controller  # Nouveau controleur servo
from back_light_2 import create_back_light_controller  # Import du contr?leur de feux arri?re
from voice_controller import VoiceController

# CR?ATION DE L'INSTANCE CAM?RA UNIQUE
camera = PiCameraStream()

voice_controller_instance = None
# from line_follower_improved import LineFollowerImproved
line_follower = None

# IMPORT DU CHALLENGE 2
from Challenge2_2 import Challenge2V2
challenge2_follower = None  # Sera initialisé après les LEDs

# IMPORT DU MODE LABYRINTHE
from labyrinthe_mode import LabyrintheMode
labyrinthe_mode = None  # Sera initialisé après les LEDs

app = Flask(__name__)

# Variables globales pour gerer les mouvements
current_movement = None
movement_thread = None
steering_thread = None
return_to_center_timer = None

# Initialisation de la LED et des feux arri?re
led_bar = Adeept_SPI_LedPixel(count=14, bright=255, sequence='GRB', bus=0, device=0)
back_light_controller = None

if led_bar.led_init_state:
    # Initialiser le contr?leur de feux arri?re
    back_light_controller = create_back_light_controller(led_bar)
    
    # Ne pas initialiser line_follower pour ?viter le conflit de pins
    # line_follower = LineFollowerImproved(camera_instance=camera)
    line_follower = None  # On n'utilise pas ce mode avec challenge2_v2
    
    # Initialiser le Challenge 2 V2 avec les contrôleurs LED et caméra
    challenge2_follower = Challenge2V2(
        led_controller=led_controller_improved,
        back_light_controller=back_light_controller,
        camera=camera  # Passer la caméra pour la détection de couleur
    )
    
    # Initialiser le mode labyrinthe avec les contrôleurs
    labyrinthe_mode = LabyrintheMode(
        camera=camera,
        led_controller=led_controller_improved,
        back_light_controller=back_light_controller
    )
    
    # LED verte de statut (LED 0)
    led_bar.set_ledpixel(0, 0, 255, 0)
    led_bar.show()
    print("Contrôleurs initialisés: feux arrière, Challenge 2, mode labyrinthe")
else:
    print("Erreur d'initialisation LED.")

# Fonction appelee a la fermeture du serveur
def cleanup_led():
    global led_update_running
    print("Extinction de la LED...")
    
    # Arr?ter le thread de mise ? jour des LEDs
    led_update_running = False
    if led_update_thread:
        led_update_thread.join(timeout=1)
    
    # Nettoyer le contr?leur de feux arri?re
    if back_light_controller:
        back_light_controller.cleanup()
    
    # Nettoyer le contr?leur LED am?lior?
    led_controller_improved.cleanup()
    
    if led_bar.led_init_state:
        led_bar.led_close()
    try:
        # Arrêter le suivi de ligne si actif
        if line_follower and line_follower.is_running():
            line_follower.stop()
        # Arrêter le Challenge 2 si actif
        if challenge2_follower and challenge2_follower.is_running():
            challenge2_follower.stop()
        # Arrêter le mode labyrinthe si actif
        if labyrinthe_mode and labyrinthe_mode.is_running():
            labyrinthe_mode.stop()
        camera.stop()
        servo_controller.cleanup()
        motorStop()
    except:
        pass

# Enregistrement de la fonction de nettoyage
atexit.register(cleanup_led)

@app.route('/')
def home():
    return render_template("index.html")

@app.route('/favicon.ico')
def favicon():
    return '', 204  # No Content - evite l'erreur 404
    
@app.route('/led-gauche', methods=['POST'])
def led_gauche():
    allumer_leds_gauche()
    return redirect(url_for('home'))
    
@app.route('/leds', methods=['POST'])
def leds():
    man()
    return redirect(url_for('home'))

@app.route('/moteur/start', methods=['POST'])
def moteur_start():
    global movement_thread, current_movement
    direction = request.form.get("direction")
    
    # Arreter le mouvement precedent
    if movement_thread and movement_thread.is_alive():
        current_movement = None
        movement_thread.join(timeout=0.5)
    
    # Demarrer le nouveau mouvement
    current_movement = direction
    movement_thread = threading.Thread(target=continuous_movement, args=(direction,))
    movement_thread.daemon = True
    movement_thread.start()
    
    return '', 204

def continuous_movement(direction):
    """Mouvement continu jusqu'a l'arret avec feux arri?re"""
    global current_movement
    
    if direction == "haut":
        # Notifier le contr?leur que le robot avance
        if back_light_controller:
            back_light_controller.on_move_forward()
        
        # Demarrage immediat puis maintien
        motor_drive(25, 1, 0.2)  # Demarrage plus rapide
        while current_movement == "haut":
            Motor(1, 1, 25)  # Maintien du mouvement
            time.sleep(0.02)  # Controle plus frequent
        motorStop()  # Arret immediat
        
        # Notifier l'arr?t
        if back_light_controller:
            back_light_controller.on_stop()
        
    elif direction == "bas":
        # Notifier le contr?leur que le robot recule
        if back_light_controller:
            back_light_controller.on_move_backward()
        
        # Demarrage immediat puis maintien
        motor_drive(25, -1, 0.2)  # Demarrage plus rapide
        while current_movement == "bas":
            Motor(1, -1, 25)  # Maintien du mouvement
            time.sleep(0.02)  # Controle plus frequent
        motorStop()  # Arret immediat
        
        # Notifier l'arr?t
        if back_light_controller:
            back_light_controller.on_stop()

@app.route('/moove', methods=['POST'])
def moove():
    global steering_thread, return_to_center_timer
    direction = request.form.get("direction")
    
    if direction in ["gauche", "droite"]:
        # Annuler le timer de retour au centre precedent
        if return_to_center_timer:
            return_to_center_timer.cancel()
        
        # Arreter le thread de direction precedent
        if steering_thread and steering_thread.is_alive():
            steering_thread.join(timeout=0.1)
        
        # Demarrer le nouveau mouvement de direction
        steering_thread = threading.Thread(target=handle_steering, args=(direction,))
        steering_thread.daemon = True
        steering_thread.start()
        
    elif direction == "center":
        # Retour immediat au centre sans delai
        if return_to_center_timer:
            return_to_center_timer.cancel()
        return_steering_to_center()
        
    elif direction == "stop":
        motorStop()
        # Programmer le retour au centre apres 0.5 seconde pour les autres cas
        if return_to_center_timer:
            return_to_center_timer.cancel()
        return_to_center_timer = threading.Timer(0.5, return_steering_to_center)
        return_to_center_timer.start()
    
    return '', 204

def handle_steering(direction):
    """Gere la direction des roues de maniere fluide avec angles augmentes et feux"""
    if direction == "gauche":
        target_angle = 130  # Braquage a gauche plus prononce
        # Activer le clignotant gauche
        if back_light_controller:
            back_light_controller.on_turn_left()
    elif direction == "droite":
        target_angle = 50   # Braquage a droite plus prononce
        # Activer le clignotant droit
        if back_light_controller:
            back_light_controller.on_turn_right()
    else:
        return
    
    # Mouvement fluide vers la position cible
    servo_controller.move_to_angle(0, target_angle, blocking=False)

def return_steering_to_center():
    """Retourne la direction au centre (90 degres) et arr?te les clignotants"""
    servo_controller.return_to_center(0, blocking=False)
    
    # Arr?ter les clignotants et retour ? l'?tat normal
    if back_light_controller:
        back_light_controller.on_stop()

@app.route('/moteur/stop', methods=['POST'])
def moteur_stop():
    global current_movement
    current_movement = None
    motorStop()
    
    # Notifier l'arr?t au contr?leur de feux
    if back_light_controller:
        back_light_controller.on_stop()
    
    return '', 204
    
@app.route('/angle_reboot', methods=['POST'])
def angle_reboot():
    # Utiliser le nouveau controleur pour le reboot
    servo_controller.initialize_servos()
    return redirect(url_for('home'))

# Nouvelles routes pour controle de la tete
@app.route('/head/move', methods=['POST'])
def head_move():
    direction = request.form.get("direction")
    servo_id = int(request.form.get("servo_id", 1))  # 1=gauche-droite, 2=haut-bas
    
    current_pos = servo_controller.get_current_position(servo_id)
    
    if direction == "haut" and servo_id == 2:
        target_angle = min(current_pos + 20, 150)
    elif direction == "bas" and servo_id == 2:
        target_angle = max(current_pos - 20, 30)
    elif direction == "gauche" and servo_id == 1:
        target_angle = min(current_pos + 20, 150)
    elif direction == "droite" and servo_id == 1:
        target_angle = max(current_pos - 20, 30)
    else:
        return '', 400
    
    servo_controller.move_to_angle(servo_id, target_angle, blocking=False)
    return '', 204

@app.route('/head/center', methods=['POST'])
def head_center():
    servo_id = int(request.form.get("servo_id", 1))
    servo_controller.return_to_center(servo_id, blocking=False)
    return '', 204

@app.route('/head/center_all', methods=['POST'])
def head_center_all():
    """Remet tous les servos au centre"""
    for servo_id in [0, 1, 2]:
        servo_controller.return_to_center(servo_id, blocking=False)
    return '', 204

# Nouvelles routes pour la detection de couleurs
@app.route('/toggle_color_detection', methods=['POST'])
def toggle_color_detection():
    """Active/desactive la detection de couleurs"""
    status = camera.toggle_color_detection()
    return jsonify({
        'status': 'active' if status else 'inactive',
        'message': 'Detection couleur activee' if status else 'Detection couleur desactivee'
    })

@app.route('/get_detected_colors', methods=['GET'])
def get_detected_colors():
    """Retourne les couleurs actuellement detectees"""
    colors = camera.get_detected_colors()
    dominant = camera.get_dominant_color()
    
    return jsonify({
        'detected_colors': [color['color'] for color in colors],
        'dominant_color': dominant,
        'count': len(colors),
        'details': colors
    })

@app.route('/color_status', methods=['GET'])
def color_status():
    """Retourne le statut de la detection"""
    return jsonify({
        'detection_active': camera.show_color_detection,
        'detected_colors': [color['color'] for color in camera.get_detected_colors()],
        'dominant_color': camera.get_dominant_color()
    })

# ============================================================================
# ROUTES POUR LE SUIVI DE LIGNE
# ============================================================================

@app.route('/line_control')
def line_control():
    """Nouvelle page de contr?le du suivi de ligne V2"""
    return render_template("line_control.html")

# ============================================================================
# ROUTES CHALLENGE 2 (MODE IR)
# ============================================================================

@app.route('/challenge2/start', methods=['POST'])
def start_challenge2():
    """Démarre le Challenge 2 - Mode IR"""
    try:
        if challenge2_follower and challenge2_follower.is_running():
            return jsonify({
                'status': 'already_running',
                'message': 'Le Challenge 2 est déjà actif'
            })
        
        # Arrêter les autres modes s'ils sont actifs
        if line_follower and line_follower.is_running():
            line_follower.stop()
            time.sleep(0.5)  # Attendre que l'arrêt soit complet
        if labyrinthe_mode and labyrinthe_mode.is_running():
            labyrinthe_mode.stop()
            time.sleep(0.5)  # Attendre que l'arrêt soit complet
        
        success = challenge2_follower.start() if challenge2_follower else False
        if success:
            return jsonify({
                'status': 'started',
                'message': 'Challenge 2 (Mode IR) démarré avec détection couleur'
            })
        else:
            return jsonify({
                'status': 'error',
                'message': 'Erreur lors du démarrage du Challenge 2'
            }), 500
            
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Erreur: {str(e)}'
        }), 500

@app.route('/challenge2/stop', methods=['POST'])
def stop_challenge2():
    """Arr?te compl?tement le Challenge 2"""
    try:
        if not challenge2_follower:
            return jsonify({
                'status': 'error',
                'message': 'Challenge 2 non initialis?'
            }), 500
            
        success = challenge2_follower.stop()
        if success:
            return jsonify({
                'status': 'stopped',
                'message': 'Challenge 2 arr?t? compl?tement'
            })
        else:
            return jsonify({
                'status': 'not_running',
                'message': 'Le Challenge 2 n\'?tait pas actif'
            })
            
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Erreur lors de l\'arr?t: {str(e)}'
        }), 500

@app.route('/challenge2/set_obstacle_distance', methods=['POST'])
def set_obstacle_distance():
    """Configure la distance de d?tection d'obstacle"""
    try:
        data = request.get_json()
        distance = int(data.get('distance', 20)) * 10  # Conversion cm vers mm
        
        if challenge2_follower and hasattr(challenge2_follower, 'set_obstacle_distance'):
            challenge2_follower.set_obstacle_distance(distance)
            return jsonify({
                'status': 'success',
                'message': f'Distance obstacle configur?e ? {distance}mm ({distance//10}cm)'
            })
        else:
            return jsonify({
                'status': 'error',
                'message': 'Challenge 2 non initialis? ou m?thode non disponible'
            }), 500
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Erreur: {str(e)}'
        }), 500

# ============================================================================
# ROUTES MODE LABYRINTHE
# ============================================================================

@app.route('/labyrinthe/start', methods=['POST'])
def start_labyrinthe():
    """Démarre le mode labyrinthe avec détection de flèches"""
    try:
        # Arrêter le Challenge 2 s'il est actif
        if challenge2_follower and challenge2_follower.is_running():
            challenge2_follower.stop()
            time.sleep(0.5)  # Attendre que l'arrêt soit complet
            
        if labyrinthe_mode and labyrinthe_mode.is_running():
            return jsonify({
                'status': 'already_running',
                'message': 'Le mode labyrinthe est déjà actif'
            })
            
        # Démarrer le mode labyrinthe
        success = labyrinthe_mode.start() if labyrinthe_mode else False
        if success:
            return jsonify({
                'status': 'started',
                'message': 'Mode labyrinthe démarré'
            })
        else:
            return jsonify({
                'status': 'error',
                'message': 'Erreur lors du démarrage du mode labyrinthe'
            }), 500
            
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Erreur: {str(e)}'
        }), 500

@app.route('/labyrinthe/stop', methods=['POST'])
def stop_labyrinthe():
    """Arrête le mode labyrinthe"""
    try:
        success = labyrinthe_mode.stop() if labyrinthe_mode else False
        if success:
            return jsonify({
                'status': 'stopped',
                'message': 'Mode labyrinthe arrêté'
            })
        else:
            return jsonify({
                'status': 'not_running',
                'message': 'Le mode labyrinthe n\'était pas actif'
            })
            
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Erreur: {str(e)}'
        }), 500

@app.route('/labyrinthe/set_obstacle_distance', methods=['POST'])
def set_labyrinthe_obstacle_distance():
    """Configure la distance de détection d'obstacle pour le labyrinthe"""
    try:
        data = request.get_json()
        distance = int(data.get('distance', 30)) * 10  # Conversion cm vers mm
        
        if labyrinthe_mode:
            labyrinthe_mode.set_obstacle_distance(distance)
            return jsonify({
                'status': 'success',
                'message': f'Distance obstacle configurée à {distance}mm ({distance//10}cm)'
            })
        else:
            return jsonify({
                'status': 'error',
                'message': 'Mode labyrinthe non initialisé'
            }), 500
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Erreur: {str(e)}'
        }), 500

@app.route('/line_follower/start', methods=['POST'])
def start_line_follower():
    """Démarre le suivi de ligne amélioré avec feux"""
    try:
        if not line_follower:
            return jsonify({
                'status': 'error',
                'message': 'Line follower non initialisé'
            }), 500
            
        if line_follower.is_running():
            return jsonify({
                'status': 'already_running',
                'message': 'Le suivi de ligne est déjà actif'
            })
        
        # Arrêter les autres modes si actifs
        if challenge2_follower and challenge2_follower.is_running():
            challenge2_follower.stop()
            time.sleep(0.5)
        if labyrinthe_mode and labyrinthe_mode.is_running():
            labyrinthe_mode.stop()
            time.sleep(0.5)
        
        success = line_follower.start()
        if success:
            # Passer en mode suivi de ligne pour les feux
            if back_light_controller:
                back_light_controller.on_move_forward()
            
            return jsonify({
                'status': 'started',
                'message': 'Suivi de ligne démarré avec succès'
            })
        else:
            return jsonify({
                'status': 'error',
                'message': 'Erreur lors du démarrage du suivi de ligne'
            }), 500
            
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Erreur: {str(e)}'
        }), 500

@app.route('/line_follower/stop', methods=['POST'])
def stop_line_follower():
    """Arr?te le suivi de ligne avec feux"""
    try:
        if not line_follower:
            return jsonify({
                'status': 'error',
                'message': 'Line follower non initialis?'
            }), 500
            
        success = line_follower.stop()
        
        # Arr?ter les feux
        if back_light_controller:
            back_light_controller.on_stop()
            
        if success:
            return jsonify({
                'status': 'stopped',
                'message': 'Suivi de ligne arr?t?'
            })
        else:
            return jsonify({
                'status': 'not_running',
                'message': 'Le suivi de ligne n\'?tait pas actif'
            })
            
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Erreur lors de l\'arr?t: {str(e)}'
        }), 500

@app.route('/line_follower/status', methods=['GET'])
def line_follower_status():
    """Retourne le statut du suivi de ligne"""
    try:
        if not line_follower:
            return jsonify({
                'status': 'error',
                'message': 'Line follower non initialis?'
            }), 500
            
        status = line_follower.get_status()
        return jsonify({
            'status': 'success',
            'data': status
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Erreur lors de la r?cup?ration du statut: {str(e)}'
        }), 500

@app.route('/line_detection/toggle', methods=['POST'])
def toggle_line_detection():
    """Active/d?sactive l'affichage de la d?tection de ligne sur la cam?ra"""
    try:
        status = camera.toggle_line_detection()
        return jsonify({
            'status': 'active' if status else 'inactive',
            'message': 'Affichage d?tection ligne activ?' if status else 'Affichage d?tection ligne d?sactiv?'
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Erreur: {str(e)}'
        }), 500

@app.route('/line_detection/info', methods=['GET'])
def line_detection_info():
    """Retourne les informations de d?tection de ligne"""
    try:
        info = camera.get_line_detection_info()
        return jsonify({
            'status': 'success',
            'data': info
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Erreur: {str(e)}'
        }), 500

@app.route('/line_detection/test', methods=['POST'])
def test_line_detection():
    """Teste la d?tection de ligne sur une image"""
    try:
        # Analyser la position actuelle de la ligne
        angle, direction = camera.analyze_line_position()
        
        if angle is not None:
            return jsonify({
                'status': 'line_detected',
                'angle': angle,
                'direction': direction,
                'message': f'Ligne d?tect?e - Direction: {direction}, Angle: {angle}°'
            })
        else:
            return jsonify({
                'status': 'no_line',
                'message': 'Aucune ligne d?tect?e'
            })
            
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Erreur lors du test: {str(e)}'
        }), 500

# ============================================================================
# ROUTES POUR LA DETECTION DE FLECHES
# ============================================================================

@app.route('/arrow_detection/toggle', methods=['POST'])
def toggle_arrow_detection():
    """Active/d?sactive la d?tection de fl?ches"""
    try:
        status = camera.toggle_arrow_detection()
        return jsonify({
            'status': 'active' if status else 'inactive',
            'message': 'D?tection fl?ches activ?e' if status else 'D?tection fl?ches d?sactiv?e'
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Erreur: {str(e)}'
        }), 500

@app.route('/arrow_detection/status', methods=['GET'])
def arrow_detection_status():
    """Retourne le statut de la détection de flèches"""
    try:
        return jsonify({
            'detection_active': camera.arrow_detection_enabled,
            'arrow_detected': camera.get_arrow_direction(),
            'status': 'success'
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Erreur: {str(e)}'
        }), 500

# ============================================================================
# ROUTES POUR LE STATUT GLOBAL
# ============================================================================

@app.route('/line_follower/status_all', methods=['GET'])
def line_follower_status_all():
    """Retourne le statut de tous les modes"""
    try:
        # Statut mode IR (Challenge 2)
        ir_status = challenge2_follower.get_status() if challenge2_follower else {
            'running': False,
            'sensors': (0, 0, 0),
            'obstacle_detected': False,
            'virage': 0,
            'stats': {}
        }
        
        # Statut mode labyrinthe
        labyrinthe_status = labyrinthe_mode.get_status() if labyrinthe_mode else {
            'running': False,
            'stats': {}
        }
        
        # Informations caméra supplémentaires
        arrow = camera.get_arrow_direction()
        colors = camera.get_detected_colors()
        dominant_color = camera.get_dominant_color()
        
        return jsonify({
            'status': 'success',
            'ir_mode': ir_status,
            'labyrinthe_mode': {
                'running': labyrinthe_status.get('running', False),
                'arrow_detected': arrow,
                'dominant_color': dominant_color,
                'detected_colors': [c['color'] for c in colors],
                'stats': labyrinthe_status.get('stats', {})
            }
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Erreur: {str(e)}'
        }), 500

# Variable globale pour le contrôle vocal
voice_controller_instance = None

# ============================================================================
# ROUTES POUR LE CONTRÔLE VOCAL - VERSION COMPLÈTE
# ============================================================================

@app.route('/voice_control/start', methods=['POST'])
def start_voice_control():
    """Démarre le contrôle vocal"""
    global voice_controller_instance
    try:
        print("?? Demande de démarrage du contrôle vocal")
        
        if voice_controller_instance and voice_controller_instance.running:
            print("?? Contrôle vocal déjà actif")
            return jsonify({
                'status': 'already_running',
                'message': 'Le contrôle vocal est déjà actif'
            })
        
        # Créer le contrôleur vocal
        print("?? Création du contrôleur vocal...")
        voice_controller_instance = VoiceController()
        
        # Partager les instances avec le contrôleur vocal
        print("?? Configuration des instances partagées...")
        voice_controller_instance.set_shared_instances(
            camera=camera,
            back_light_controller=back_light_controller,
            challenge2_mode=challenge2_follower,
            labyrinthe_mode=labyrinthe_mode
        )
        
        # Démarrer le contrôleur
        print("?? Démarrage du contrôleur vocal...")
        voice_controller_instance.start()
        
        print("? Contrôle vocal démarré avec succès")
        return jsonify({
            'status': 'started',
            'message': 'Contrôle vocal démarré'
        })
        
    except Exception as e:
        print(f"? Erreur démarrage contrôle vocal: {e}")
        import traceback
        traceback.print_exc()
        
        return jsonify({
            'status': 'error',
            'message': f'Erreur: {str(e)}'
        }), 500

@app.route('/voice_control/stop', methods=['POST'])
def stop_voice_control():
    """Arrête le contrôle vocal"""
    global voice_controller_instance
    try:
        print("?? Demande d'arrêt du contrôle vocal")
        
        if not voice_controller_instance or not voice_controller_instance.running:
            print("?? Contrôle vocal non actif")
            return jsonify({
                'status': 'not_running',
                'message': 'Le contrôle vocal n\'est pas actif'
            })
        
        # Arrêter le contrôleur
        print("?? Arrêt du contrôleur vocal...")
        voice_controller_instance.stop()
        voice_controller_instance = None
        
        print("? Contrôle vocal arrêté")
        return jsonify({
            'status': 'stopped',
            'message': 'Contrôle vocal arrêté'
        })
        
    except Exception as e:
        print(f"? Erreur arrêt contrôle vocal: {e}")
        return jsonify({
            'status': 'error',
            'message': f'Erreur: {str(e)}'
        }), 500

@app.route('/voice_control/status', methods=['GET'])
def voice_control_status():
    """Retourne le statut du contrôle vocal"""
    global voice_controller_instance
    try:
        is_active = voice_controller_instance is not None and voice_controller_instance.running
        
        status_data = {
            'active': is_active,
            'current_mode': voice_controller_instance.current_mode if voice_controller_instance else None,
            'is_moving': voice_controller_instance.is_moving if voice_controller_instance else False
        }
        
        return jsonify({
            'status': 'success',
            'data': status_data
        })
        
    except Exception as e:
        print(f"? Erreur statut contrôle vocal: {e}")
        return jsonify({
            'status': 'error',
            'message': f'Erreur: {str(e)}'
        }), 500

@app.route('/voice_control/last_command', methods=['GET'])
def get_last_voice_command():
    """Retourne la dernière commande vocale reconnue - Version avec gestion encodage"""
    try:
        last_command = ""
        output_file = "output.txt"
        
        if os.path.exists(output_file):
            # Essayer plusieurs encodages
            encodings_to_try = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
            
            for encoding in encodings_to_try:
                try:
                    with open(output_file, "r", encoding=encoding) as f:
                        lines = f.readlines()
                        if lines:
                            # Prendre la dernière ligne non vide
                            for line in reversed(lines):
                                line = line.strip()
                                if line:
                                    # Extraire juste la commande (après l'horodatage)
                                    if ':' in line:
                                        last_command = line.split(':', 1)[1].strip()
                                    else:
                                        last_command = line
                                    break
                    
                    print(f"? Fichier lu avec encodage {encoding}")
                    break  # Sortir de la boucle si succès
                    
                except UnicodeDecodeError:
                    print(f"?? Échec encodage {encoding}, essai suivant...")
                    continue
            
            # Si aucun encodage ne fonctionne, nettoyer le fichier
            if not last_command and os.path.exists(output_file):
                print("?? Nettoyage du fichier output.txt à cause des problèmes d'encodage")
                with open(output_file, "w", encoding='utf-8') as f:
                    f.write("")
                last_command = "Fichier nettoyé - problème d'encodage résolu"
        
        return jsonify({
            'status': 'success',
            'last_command': last_command
        })
        
    except Exception as e:
        print(f"? Erreur lecture dernière commande: {e}")
        return jsonify({
            'status': 'error',
            'message': f'Erreur: {str(e)}'
        }), 500

@app.route('/voice_control/simulate', methods=['POST'])
def simulate_voice_command():
    """Route pour simuler une commande vocale (pour tests) - Version avec encodage UTF-8"""
    try:
        data = request.get_json()
        command = data.get('command', '').strip()
        
        if not command:
            return jsonify({
                'status': 'error',
                'message': 'Commande vide'
            }), 400
        
        # Nettoyer le fichier output.txt d'abord pour éviter les problèmes d'encodage
        output_file = "output.txt"
        
        # Lire le contenu existant avec gestion d'erreur
        existing_content = []
        if os.path.exists(output_file):
            try:
                with open(output_file, "r", encoding='utf-8') as f:
                    existing_content = f.readlines()
            except UnicodeDecodeError:
                print("?? Problème d'encodage détecté, nettoyage du fichier...")
                existing_content = []
        
        # Réécrire le fichier en UTF-8 propre
        timestamp = time.strftime("%H:%M:%S")
        with open(output_file, "w", encoding='utf-8') as f:
            # Garder les dernières lignes valides
            for line in existing_content[-10:]:  # Garder seulement les 10 dernières
                try:
                    f.write(line)
                except:
                    pass
            # Ajouter la nouvelle commande
            f.write(f"{timestamp}: {command}\n")
        
        print(f"?? Commande simulée (UTF-8): {command}")
        
        return jsonify({
            'status': 'success',
            'message': f'Commande "{command}" simulée'
        })
        
    except Exception as e:
        print(f"? Erreur simulation commande: {e}")
        return jsonify({
            'status': 'error',
            'message': f'Erreur: {str(e)}'
        }), 500

@app.route('/voice_control/test_file', methods=['POST'])
def test_voice_file():
    """Test direct d'écriture dans le fichier output.txt"""
    try:
        output_file = "output.txt"
        timestamp = time.strftime("%H:%M:%S")
        test_command = "avancer"
        
        # Écrire directement dans le fichier
        with open(output_file, "a", encoding='utf-8') as f:
            f.write(f"{timestamp}: {test_command}\n")
        
        print(f"?? Test d'écriture dans {output_file}: {test_command}")
        
        return jsonify({
            'status': 'success',
            'message': f'Test écrit dans {output_file}',
            'command': test_command,
            'file': output_file
        })
        
    except Exception as e:
        print(f"? Erreur test fichier: {e}")
        return jsonify({
            'status': 'error',
            'message': f'Erreur: {str(e)}'
        }), 500

@app.route('/voice_control/read_file', methods=['GET'])
def read_voice_file():
    """Lit le contenu complet du fichier output.txt"""
    try:
        output_file = "output.txt"
        content = []
        
        if os.path.exists(output_file):
            with open(output_file, "r", encoding='utf-8') as f:
                content = f.readlines()
        
        return jsonify({
            'status': 'success',
            'file': output_file,
            'exists': os.path.exists(output_file),
            'lines': len(content),
            'content': [line.strip() for line in content if line.strip()]
        })
        
    except Exception as e:
        print(f"? Erreur lecture fichier: {e}")
        return jsonify({
            'status': 'error',
            'message': f'Erreur: {str(e)}'
        }), 500

@app.route('/voice_control/clean_file', methods=['POST'])
def clean_voice_file():
    """Nettoie le fichier output.txt et le recrée en UTF-8 propre"""
    try:
        output_file = "output.txt"
        
        # Recréer le fichier en UTF-8 propre
        with open(output_file, "w", encoding='utf-8') as f:
            f.write("")
        
        # Remettre à zéro le pointeur du contrôleur vocal
        if voice_controller_instance:
            voice_controller_instance.file_position = 0
        
        print(f"?? Fichier {output_file} nettoyé et recrée en UTF-8")
        
        return jsonify({
            'status': 'success',
            'message': f'Fichier {output_file} nettoyé (UTF-8)'
        })
        
    except Exception as e:
        print(f"? Erreur nettoyage fichier: {e}")
        return jsonify({
            'status': 'error',
            'message': f'Erreur: {str(e)}'
        }), 500

# AJOUTEZ cette fonction de nettoyage dans votre fonction cleanup_led() existante :

def cleanup_led():
    global led_update_running, voice_controller_instance
    print("Extinction de la LED...")
    
    # Arrêter le contrôleur vocal
    if voice_controller_instance:
        try:
            voice_controller_instance.stop()
            print("? Contrôleur vocal arrêté")
        except Exception as e:
            print(f"? Erreur arrêt contrôleur vocal: {e}")
# ============================================================================
# NOUVELLES ROUTES POUR CONTR?LE DES FEUX ARRI?RE
# ============================================================================

@app.route('/back_light/status', methods=['GET'])
def back_light_status():
    """Retourne le statut des feux arri?re"""
    if not back_light_controller:
        return jsonify({'status': 'error', 'message': 'Contr?leur non initialis?'}), 500
    
    status = back_light_controller.get_status()
    return jsonify({
        'status': 'success',
        'data': status
    })

@app.route('/back_light/test', methods=['POST'])
def back_light_test():
    """Test manuel des diff?rents ?tats des feux arri?re"""
    if not back_light_controller:
        return jsonify({'status': 'error', 'message': 'Contr?leur non initialis?'}), 500
    
    test_mode = request.form.get('mode', 'stop')
    
    try:
        if test_mode == 'forward':
            back_light_controller.on_move_forward()
        elif test_mode == 'backward':
            back_light_controller.on_move_backward()
        elif test_mode == 'left':
            back_light_controller.on_turn_left()
        elif test_mode == 'right':
            back_light_controller.on_turn_right()
        else:  # stop
            back_light_controller.on_stop()
        
        return jsonify({
            'status': 'success',
            'message': f'Test mode {test_mode} activ?'
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Erreur lors du test: {str(e)}'
        }), 500

@app.route('/back_light/emergency_stop', methods=['POST'])
def back_light_emergency_stop():
    """Arr?t d'urgence - ?teint tous les feux arri?re"""
    if not back_light_controller:
        return jsonify({'status': 'error', 'message': 'Contr?leur non initialis?'}), 500
    
    try:
        # Forcer l'arr?t de tous les effets
        back_light_controller._stop_blinkers()
        
        # ?teindre toutes les LEDs arri?re (2, 3, 4, 5, 6, 7)
        for led_id in [2, 3, 4, 5, 6, 7]:
            led_bar.set_ledpixel(led_id, 0, 0, 0)
        led_bar.show()
        
        return jsonify({
            'status': 'success',
            'message': 'Arr?t d\'urgence des feux arri?re effectu?'
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Erreur lors de l\'arr?t d\'urgence: {str(e)}'
        }), 500

# ============================================================================
# ROUTES CAMERA EXISTANTES
# ============================================================================

def gen():
    while True:
        frame = camera.get_frame()
        if frame:
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
  
@app.route('/video_feed')
def video():
    return Response(gen(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/take_photo', methods=['GET', 'POST'])
def take_photo():
    """Prendre une photo avec gestion amelioree"""
    import os
    from datetime import datetime
    
    try:
        # Creer le dossier Pictures s'il n'existe pas
        pictures_dir = "/home/pi/Pictures"
        if not os.path.exists(pictures_dir):
            os.makedirs(pictures_dir)
            print(f"Dossier {pictures_dir} cree")
        
        # Generer un nom de fichier unique avec timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"photo_{timestamp}.jpg"
        filepath = os.path.join(pictures_dir, filename)
        
        print(f"Prise de photo: {filepath}")
        
        # Prendre la photo avec la camera
        photo_path = camera.photo(filepath)
        
        # Verifier que le fichier a bien ete cree
        if os.path.exists(photo_path):
            file_size = os.path.getsize(photo_path)
            print(f"Photo sauvegardee: {photo_path} ({file_size} bytes)")
            
            # Determiner le type MIME en fonction de l'extension
            if photo_path.lower().endswith('.png'):
                mimetype = 'image/png'
            elif photo_path.lower().endswith(('.jpg', '.jpeg')):
                mimetype = 'image/jpeg'
            else:
                mimetype = 'image/jpeg'  # Par defaut
            
            # Retourner la photo avec les bons headers
            return send_file(
                photo_path, 
                mimetype=mimetype,
                as_attachment=True,
                download_name=filename
            )
        else:
            print(f"Erreur: fichier photo non trouve: {photo_path}")
            return jsonify({
                'status': 'error',
                'message': 'Erreur lors de la creation du fichier photo'
            }), 500
            
    except Exception as e:
        print(f"Erreur lors de la prise de photo: {e}")
        return jsonify({
            'status': 'error', 
            'message': f'Erreur lors de la prise de photo: {str(e)}'
        }), 500

@app.route('/list_photos', methods=['GET'])
def list_photos():
    """Lister toutes les photos prises"""
    import os
    from datetime import datetime
    
    try:
        pictures_dir = "/home/pi/Pictures"
        
        if not os.path.exists(pictures_dir):
            return jsonify({
                'photos': [],
                'count': 0,
                'message': 'Aucun dossier de photos trouve'
            })
        
        # Lister tous les fichiers images
        photo_files = []
        for filename in os.listdir(pictures_dir):
            if filename.lower().endswith(('.jpg', '.jpeg', '.png')):
                filepath = os.path.join(pictures_dir, filename)
                if os.path.isfile(filepath):
                    # Obtenir les informations du fichier
                    stat = os.stat(filepath)
                    size = stat.st_size
                    modified = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                    
                    photo_files.append({
                        'filename': filename,
                        'size': size,
                        'size_mb': round(size / (1024*1024), 2),
                        'modified': modified,
                        'url': f'/get_photo/{filename}'
                    })
        
        # Trier par date de modification (plus recent en premier)
        photo_files.sort(key=lambda x: x['modified'], reverse=True)
        
        return jsonify({
            'photos': photo_files,
            'count': len(photo_files),
            'total_size_mb': round(sum(p['size'] for p in photo_files) / (1024*1024), 2)
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Erreur lors du listage: {str(e)}'
        }), 500

@app.route('/get_photo/<filename>', methods=['GET'])
def get_photo(filename):
    """Recuperer une photo specifique"""
    import os
    
    try:
        # Securite: eviter les path traversal attacks
        if '..' in filename or '/' in filename:
            return jsonify({'status': 'error', 'message': 'Nom de fichier invalide'}), 400
        
        pictures_dir = "/home/pi/Pictures"
        filepath = os.path.join(pictures_dir, filename)
        
        if not os.path.exists(filepath):
            return jsonify({'status': 'error', 'message': 'Photo non trouvee'}), 404
        
        # Determiner le type MIME
        if filename.lower().endswith('.png'):
            mimetype = 'image/png'
        elif filename.lower().endswith(('.jpg', '.jpeg')):
            mimetype = 'image/jpeg'
        else:
            mimetype = 'image/jpeg'
        
        return send_file(filepath, mimetype=mimetype)
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Erreur lors de la recuperation: {str(e)}'
        }), 500

@app.route('/delete_photo/<filename>', methods=['DELETE'])
def delete_photo(filename):
    """Supprimer une photo specifique"""
    import os
    
    try:
        # Securite: eviter les path traversal attacks
        if '..' in filename or '/' in filename:
            return jsonify({'status': 'error', 'message': 'Nom de fichier invalide'}), 400
        
        pictures_dir = "/home/pi/Pictures"
        filepath = os.path.join(pictures_dir, filename)
        
        if not os.path.exists(filepath):
            return jsonify({'status': 'error', 'message': 'Photo non trouvee'}), 404
        
        # Supprimer le fichier
        os.remove(filepath)
        print(f"Photo supprimee: {filepath}")
        
        return jsonify({
            'status': 'success',
            'message': f'Photo {filename} supprimee avec succes'
        })
        
    except Exception as e:
        print(f"Erreur lors de la suppression: {e}")
        return jsonify({
            'status': 'error',
            'message': f'Erreur lors de la suppression: {str(e)}'
        }), 500

@app.route('/clear_photos', methods=['DELETE'])
def clear_photos():
    """Supprimer toutes les photos"""
    import os
    
    try:
        pictures_dir = "/home/pi/Pictures"
        
        if not os.path.exists(pictures_dir):
            return jsonify({
                'status': 'success',
                'message': 'Aucun dossier de photos a nettoyer',
                'deleted_count': 0
            })
        
        deleted_count = 0
        for filename in os.listdir(pictures_dir):
            if filename.lower().endswith(('.jpg', '.jpeg', '.png')):
                filepath = os.path.join(pictures_dir, filename)
                if os.path.isfile(filepath):
                    os.remove(filepath)
                    deleted_count += 1
                    print(f"Photo supprimee: {filepath}")
        
        return jsonify({
            'status': 'success',
            'message': f'{deleted_count} photos supprimees',
            'deleted_count': deleted_count
        })
        
    except Exception as e:
        print(f"Erreur lors du nettoyage: {e}")
        return jsonify({
            'status': 'error',
            'message': f'Erreur lors du nettoyage: {str(e)}'
        }), 500

# Routes pour le controle d'alimentation
@app.route('/power/shutdown', methods=['POST'])
def power_shutdown():
    """Arrete le Raspberry Pi"""
    try:
        shutdown()
        return jsonify({'status': 'success', 'message': 'Arret en cours...'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': f'Erreur: {str(e)}'})

@app.route('/power/reboot', methods=['POST'])
def power_reboot():
    """Redemarrer le Raspberry Pi"""
    try:
        reboot()
        return jsonify({'status': 'success', 'message': 'Redemarrage en cours...'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': f'Erreur: {str(e)}'})

@app.route('/power/restart_server', methods=['POST'])
def power_restart_server():
    """Redemarrer le serveur via systemctl restart - solution simple et fiable"""
    import subprocess
    import threading
    import os
    import time
    
    try:
        print("Redemarrage du serveur via systemd...")
        
        # Arrêter le suivi de ligne si actif
        if line_follower and line_follower.is_running():
            line_follower.stop()
        # Arrêter le Challenge 2 si actif
        if challenge2_follower and challenge2_follower.is_running():
            challenge2_follower.stop()
        # Arrêter le mode labyrinthe si actif
        if labyrinthe_mode and labyrinthe_mode.is_running():
            labyrinthe_mode.stop()
        
        # Programmer l'arret APRES avoir envoye la reponse
        def delayed_restart():
            time.sleep(0.5)  # Laisser le temps d'envoyer la reponse
            try:
                print("Execution de systemctl restart main.service...")
                result = subprocess.run(
                    ["sudo", "systemctl", "restart", "main.service"], 
                    check=True,
                    capture_output=True,
                    text=True,
                    timeout=15
                )
                print(f"systemctl restart execute avec succes: {result.returncode}")
                
                # Arreter ce serveur apres le restart
                time.sleep(2)
                print("Arret du serveur actuel - systemd prend le relais")
                os._exit(0)
                
            except subprocess.CalledProcessError as e:
                print(f"Erreur systemctl restart: {e}")
                print(f"stderr: {e.stderr}")
            except Exception as e:
                print(f"Erreur lors du restart delayed: {e}")
        
        # Lancer le redemarrage en arriere-plan
        threading.Thread(target=delayed_restart, daemon=True).start()
        
        # Envoyer la reponse IMMEDIATEMENT
        return jsonify({
            'status': 'restarting', 
            'message': 'Redemarrage en cours via systemd... Reconnexion dans 8 secondes.'
        })
        
    except Exception as e:
        print(f"Erreur generale dans power_restart_server: {e}")
        return jsonify({
            'status': 'error', 
            'message': f"Erreur generale: {e}"
        })

@app.route('/power/server_status', methods=['GET'])
def power_server_status():
    """Obtenir le statut du serveur"""
    import subprocess
    
    try:
        # Verifier le statut du service main.service
        result = subprocess.run(
            ["sudo", "systemctl", "is-active", "main.service"],
            capture_output=True, text=True, timeout=5
        )
        
        service_status = result.stdout.strip()
        
        return jsonify({
            'status': 'running',
            'service_status': service_status,
            'service_active': service_status == 'active'
        })
        
    except Exception as e:
        return jsonify({
            'status': 'running',
            'service_status': 'unknown',
            'service_active': False,
            'error': str(e)
        })

# Variable globale pour le thread de mise ? jour des LEDs
led_update_thread = None
led_update_running = True

# ============================================================================
# HOOK POUR MISE A JOUR AUTOMATIQUE DES LEDS SELON LA COULEUR D?TECT?E
# ============================================================================

def update_leds_from_color():
    """Thread pour mettre à jour les LEDs selon la couleur dominante"""
    global led_update_running
    while led_update_running:
        try:
            # Ne mettre à jour que si le Challenge 2 ou le labyrinthe ne sont pas actifs
            # (car ces modes gèrent leurs propres LEDs)
            if ((not challenge2_follower or not challenge2_follower.is_running()) and 
                (not labyrinthe_mode or not labyrinthe_mode.is_running())):
                if camera.show_color_detection:
                    dominant = camera.get_dominant_color()
                    if dominant:
                        led_controller_improved.set_color_by_name(dominant)
                    else:
                        # Si aucune couleur détectée, mettre en blanc
                        led_controller_improved.set_front_leds(255, 255, 255)
                else:
                    # Si la détection n'est pas active, LEDs en blanc
                    led_controller_improved.set_front_leds(255, 255, 255)
            elif labyrinthe_mode and labyrinthe_mode.is_running():
                # En mode labyrinthe, toujours LEDs en blanc
                led_controller_improved.set_front_leds(255, 255, 255)
            
            time.sleep(1)  # Mise ? jour chaque seconde
            
        except Exception as e:
            print(f"Erreur update LEDs: {e}")
            time.sleep(5)
            
@app.route('/peak_logo')
def peak_logo():
    """Servir le logo PEAK"""
    try:
        logo_path = '/home/pi/Pictures/peak_logo.png'
        if os.path.exists(logo_path):
            return send_file(logo_path, mimetype='image/png')
        else:
            print(f"Logo PEAK non trouve: {logo_path}")
            return '', 404
    except Exception as e:
        print(f"Erreur lors du chargement du logo: {e}")
        return '', 500

# D?marrer le thread de mise ? jour des LEDs
led_update_thread = threading.Thread(target=update_leds_from_color, daemon=True)
led_update_thread.start()
  
def webserver():
    app.run(host='192.168.12.1', port=8000)