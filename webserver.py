# -*- coding: Windows-1252 -*-
from flask import Flask, render_template, redirect, url_for, request, Response, send_file
from temp import Adeept_SPI_LedPixel
import atexit  # Pour exécuter une fonction à l'arrêt du serveur

from led_controller import * 
from motor import * 
from led_techno import * 
from servo_reboot import *
from camera import *

camera = PiCameraStream()


app = Flask(__name__)

# Initialisation de la LED
led_bar = Adeept_SPI_LedPixel(count=14, bright=255, sequence='GRB', bus=0, device=0)

if led_bar.led_init_state:
    led_bar.set_ledpixel(0, 0, 255, 0)  # LED verte
    led_bar.show()
else:
    print("Erreur d'initialisation LED.")

# Fonction appelée à la fermeture du serveur
def cleanup_led():
    print("Extinction de la LED...")
    if led_bar.led_init_state:
        led_bar.led_close()

# Enregistrement de la fonction de nettoyage
atexit.register(cleanup_led)

@app.route('/')
def home():
    return render_template("index.html")  # Assure-toi que ce fichier existe dans /templates/
    
@app.route('/led-gauche', methods=['POST'])
def led_gauche():
    allumer_leds_gauche()
    return redirect(url_for('home'))
    
@app.route('/leds', methods=['POST'])
def leds():
  man()
  return redirect(url_for('home'))
    
@app.route('/moteur', methods=['POST'])
def controle_moteur(): 
    direction = request.form.get("direction")
    if direction == "haut":
        
        forward()
    elif direction == "bas":
        backward()
    elif direction in ["gauche","droite"]: 
        left_right(direction)
    elif direction == "stop":
        motorStop()
    return redirect(url_for('home'))
    
@app.route('/angle_reboot', methods=['POST'])
def angle_reboot():
  reboot()
  return redirect(url_for('home'))
  
#camera 
def gen():
        while True:
            frame = camera.get_frame()
            if frame:
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
  
@app.route('/video_feed')
def video():
    return Response(gen(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/take_photo',methods=['GET'])
def take_photo():
  photo = camera.photo("Pictures/photo.png")
  return send_file(photo, mimetype='image.png')
  

def webserver():
    app.run(host='192.168.12.1', port=8000)




