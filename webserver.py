# -*- coding: Windows-1252 -*-
from flask import Flask, render_template, redirect, url_for, request
from temp import Adeept_SPI_LedPixel
import atexit  # Pour exécuter une fonction à l'arrêt du serveur

from led_controller import * 
from motor import * 
from led_techno import * 

#init = 90

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
    elif direction == "gauche": 
        init = left(init)
    elif direction == "droite":
        init = right(init)
    return redirect(url_for('home'))

def webserver():
    app.run(host='192.168.12.1', port=8000)
