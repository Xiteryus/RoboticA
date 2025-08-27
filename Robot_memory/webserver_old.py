# -*- coding: Windows-1252 -*-
from flask import Flask, render_template, redirect, url_for, request, Response, send_file, jsonify
from temp import Adeept_SPI_LedPixel
import atexit  # Pour executer une fonction a l'arret du serveur
from led_controller import * 
from motor import * 
from led_techno import * 
from servo_reboot import *
from camera import *  # Version modifiee avec detection couleurs
from power_control import *  # Import du module de controle d'alimentation

camera = PiCameraStream()
app = Flask(__name__)

# Initialisation de la LED
led_bar = Adeept_SPI_LedPixel(count=14, bright=255, sequence='GRB', bus=0, device=0)
if led_bar.led_init_state:
    led_bar.set_ledpixel(0, 0, 255, 0)  # LED verte
    led_bar.show()
else:
    print("Erreur d'initialisation LED.")

# Fonction appelee a la fermeture du serveur
def cleanup_led():
    print("Extinction de la LED...")
    if led_bar.led_init_state:
        led_bar.led_close()
    try:
        camera.stop()
    except:
        pass

# Enregistrement de la fonction de nettoyage
atexit.register(cleanup_led)

@app.route('/')
def home():
    return render_template("index.html")
    
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
    direction = request.form.get("direction")
    if direction == "haut":
        forward()
    elif direction == "bas":
        backward()
    elif direction in ["gauche", "droite"]:
        left_right(direction)
    return '', 204  

@app.route('/moove', methods=['POST'])
def moove():
    direction = request.form.get("direction")
    if direction in ["gauche", "droite"]:
        left_right(direction)
    if direction == "stop":
        motorStop()
    return '', 204

@app.route('/moteur/stop', methods=['POST'])
def moteur_stop():
    motorStop()
    return '', 204
    
@app.route('/angle_reboot', methods=['POST'])
def angle_reboot():
    reboot()
    return redirect(url_for('home'))

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

# Camera routes existantes
def gen():
    while True:
        frame = camera.get_frame()
        if frame:
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
  
@app.route('/video_feed')
def video():
    return Response(gen(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/take_photo', methods=['GET'])
def take_photo():
    photo = camera.photo("Pictures/photo.png")
    return send_file(photo, mimetype='image/png')

# Nouvelles routes pour le controle d'alimentation
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
  
def webserver():
    app.run(host='192.168.12.1', port=8000)