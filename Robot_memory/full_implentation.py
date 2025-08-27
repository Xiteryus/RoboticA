import time
from time import sleep
import argparse
from gpiozero import InputDevice
import spidev
import threading
import numpy
import board
import adafruit_ads7830.ads7830 as ADC
from adafruit_ads7830.analog_in import AnalogIn
from servo_controller import *
from gpiozero import DistanceSensor
import RPi.GPIO as GPIO
from motor import *

#Line tracking
line_pin_left = 22
line_pin_middle = 27
line_pin_right = 17

left = InputDevice(pin=line_pin_right)
middle = InputDevice(pin=line_pin_middle)
right = InputDevice(pin=line_pin_left)

def run():
    status_right = right.value
    status_middle = middle.value
    status_left = left.value
    print('left: %d   middle: %d   right: %d' %(status_right,status_middle,status_left))

# Light tracking 
i2c = board.I2C()

adc = ADC.ADS7830(i2c,0x48)  #default is 0x48
chan1 = AnalogIn(adc, 1)
chan2 = AnalogIn(adc, 2)

chan3 = AnalogIn(adc, 3)
chan4 = AnalogIn(adc, 4)
chan5 = AnalogIn(adc, 5)
chan6 = AnalogIn(adc, 6)
chan7 = AnalogIn(adc, 7)
chan0 = AnalogIn(adc, 0)

#Ultrasound

Tr = 23
Ec = 24
sensor = DistanceSensor(echo=Ec, trigger=Tr,max_distance=2) # Maximum detection distance 2m.

# Get the distance of ultrasonic detection.
def checkdist():
    return (sensor.distance) *100 # Unit: cm

#LED control

def switchSetup(): # Python function designed to configure

  GPIO.setwarnings(False) # Disables GPIO warnings, which can be helpful
#carte
  GPIO.setmode(GPIO.BCM) # Sets the GPIO pin numbering mode to BCM

  GPIO.setup(9, GPIO.OUT) # Configures pin 5 as output pins.

  GPIO.setup(25, GPIO.OUT) # Configures pin 6 as output pins.

  GPIO.setup(11, GPIO.OUT) # Configures pin 13 as output pins.
#a gauche
  GPIO.setup(0, GPIO.OUT)

  GPIO.setup(19, GPIO.OUT)

  GPIO.setup(13, GPIO.OUT)
#a droite
  GPIO.setup(1, GPIO.OUT)

  GPIO.setup(5, GPIO.OUT)

  GPIO.setup(6, GPIO.OUT)
#ws
  GPIO.setup(12, GPIO.OUT)

def switch(port, status):
  if port == 1:
    if status == 1:
      GPIO.output(9, GPIO.HIGH)
    elif status == 0:
      GPIO.output(9,GPIO.LOW)
    else:
      pass # Do nothing
  elif port == 2:
    if status == 1:
      GPIO.output(25, GPIO.HIGH)
    elif status == 0:
      GPIO.output(25,GPIO.LOW)
    else:
      pass # Do nothing
  elif port == 3:
    if status == 1:
      GPIO.output(11, GPIO.HIGH)
    elif status == 0:
      GPIO.output(11,GPIO.LOW)
    else:
      pass # Do nothing
  elif port == 4:
    if status == 1:
      GPIO.output(0, GPIO.HIGH)
    elif status == 0:
      GPIO.output(0,GPIO.LOW)
    else:
      pass # Do nothing
  elif port == 5:
    if status == 1:
      GPIO.output(19, GPIO.HIGH)
    elif status == 0:
      GPIO.output(19,GPIO.LOW)
    else:
      pass # Do nothing
  elif port == 6:
    if status == 1:
      GPIO.output(13, GPIO.HIGH)
    elif status == 0:
      GPIO.output(13,GPIO.LOW)
    else:
      pass # Do nothing
  elif port == 7:
    if status == 1:
      GPIO.output(1, GPIO.HIGH)
    elif status == 0:
      GPIO.output(1,GPIO.LOW)
    else:
      pass # Do nothing
  elif port == 8:
    if status == 1:
      GPIO.output(5, GPIO.HIGH)
    elif status == 0:
      GPIO.output(5,GPIO.LOW)
    else:
      pass # Do nothing
  elif port == 9:
    if status == 1:
      GPIO.output(6, GPIO.HIGH)
    elif status == 0:
      GPIO.output(6,GPIO.LOW)
    else:
      pass # Do nothing
  elif port == 10:
    if status == 1:
      GPIO.output(12, GPIO.HIGH)
    elif status == 0:
      GPIO.output(12,GPIO.LOW)
    else:
      pass # Do nothing
  else:
    print('Wrong Command: Example--switch(3, 1)->to switch on port3')
    

def set_all_switch_off(): 
  switch(1,0) 
  switch(2,0) 
  switch(3,0) 
  switch(4,1) 
  switch(5,1) 
  switch(6,1) 
  switch(7,1) 
  switch(8,1)
  switch(9,1)
  switch(10,1)  
  
#WS2812
class Adeept_SPI_LedPixel(threading.Thread):
    def __init__(self, count=14, bright=255, sequence='GRB', bus=0, device=0):
        self.set_led_type(sequence)
        self.set_led_count(count)
        self.set_led_brightness(bright)
        self.led_begin(bus, device)
        self.set_all_led_color(0, 0, 0)
        super().__init__()
    def led_begin(self, bus, device):
        self.spi = spidev.SpiDev()
        try:
            self.spi.open(bus, device)
            self.spi.mode = 0
            self.led_init_state = 1
        except:
            self.led_init_state = 0
    def set_led_count(self, c):
        self.led_count = c
        self.led_color = [0]*3*self.led_count
    def set_led_type(self, t):
        types = ['RGB','RBG','GRB','GBR','BRG','BGR']
        offsets = [0x06,0x09,0x12,0x21,0x18,0x24]
        i = types.index(t) if t in types else 2
        o = offsets[i]
        self.led_offsets = [(o >> 4) & 3, (o >> 2) & 3, (o >> 0) & 3]
    def set_led_brightness(self, b):
        self.led_brightness = b
    def set_ledpixel(self, idx, r, g, b):
        p = [0,0,0]
        for col, ofs, val in zip((r,g,b), self.led_offsets, (r,g,b)):
            p[ofs] = round(col * self.led_brightness / 255)
        base = idx * 3
        self.led_color[base:base+3] = p
    def show(self):
        d = numpy.array(self.led_color, dtype=numpy.uint8)
        tx = numpy.zeros(len(d)*8, dtype=numpy.uint8)
        for bit in range(8):
            tx[7-bit::8] = ((d >> bit) & 1)*0x78 + 0x80
        if self.led_init_state:
            self.spi.xfer(tx.tolist(), int(8/1.25e-6))
    def led_close(self):
        self.set_all_led_color(0, 0, 0)
        self.show()
        if self.led_init_state:
            self.spi.close()
    def set_all_led_color(self, r, g, b):
        for i in range(self.led_count):
            self.set_ledpixel(i, r, g, b)

# === Affichage de l'etat des LEDs ===
def afficher_etat(led_states, count):
    print("\nEtat actuel des LEDs :")
    for i in range(count):
        r, g, b = led_states.get(i, (0, 0, 0))
        etat = f"R={r} G={g} B={b}" if (r+g+b) > 0 else "ETEINTE"
        print(f"LED {i} : {etat}")
    print()

# === Commande utilisateur ===
def set_led_manuel(bar, num, couleur, intensite, led_states):
    if not (0 <= num < bar.led_count):
        print("Numero de LED invalide.")
        return
    if not (0 <= intensite <= 255):
        print("Intensite invalide. Doit etre entre 0 et 255.")
        return

    r = g = b = 0
    if couleur.upper() == 'R':
        r = intensite
    elif couleur.upper() == 'G':
        g = intensite
    elif couleur.upper() == 'B':
        b = intensite
    elif couleur.upper() == 'N':
        r = g = b = 0
    else:
        print("Couleur invalide. Utilisez R, G, B ou N.")
        return

    bar.set_ledpixel(num, r, g, b)
    led_states[num] = (r, g, b)
    bar.show()

def eteindre_led(bar, num, led_states):
    if not (0 <= num < bar.led_count):
        print("Numero de LED invalide.")
        return
    bar.set_ledpixel(num, 0, 0, 0)
    led_states[num] = (0, 0, 0)
    bar.show()
    

#RADAR

# Get the distance of ultrasonic detection.
def checkdist():
    return (sensor.distance) *100 # Unit: cm

def servo_initialisation(angle):
    set_angle(2, 90)
    set_angle(1, angle)

def detection(angle):
    if angle >= 10 or angle <= 180:
        set_angle(1, angle)
        return round(checkdist(), 1)


if __name__ == '__main__':
    try:
      bar = Adeept_SPI_LedPixel(count=14, bright=255, sequence='GRB', bus=0, device=0)
      led_states = {}
      switchSetup()
      set_all_switch_off()
      angle = 90
      servo_initialisation(angle)
      while 1:
        init = input("Voir les valeurs (1), changer la couleur des LED (2), changer LED WS2812? (3) ou controler le robot (4) : ")
        if init=="1":
           detection_map = [0]*18
           direction = 1
           run()
           LT_value = chan1.value
           print(f"Light Tracking Value: {LT_value}")
           distance = checkdist() 
           print("%.2f cm" %distance)
           for i in range (0,27):
             # mise a jour de la map de detection
             detection_map[(angle//10)-1] = detection(angle)
             # mise a jour du sens de direction
             if angle >= 180 and direction == 1:
               direction = 0
             elif angle <= 10 and direction == 0:
               direction = 1
             sleep(0.1)
             # mise a jour de l'angle
             if direction:
               angle += 10
             else:
               angle -= 10
           print("\n", detection_map)
        elif init=="2":
          response = int(input("Quelle led modifier ?(1-3: Carte;  LED_G : 4; LED_D : 5; WS : 10): "))
          if (response>0 and response<4):
            status = int(input("Eteindre (0) ou Allumer (1) : "))
            if status == 0:  
              switch(response,0)
            elif status == 1:
      	      switch(response,1)
          if response == 10:
            status = int(input("Eteindre (0) ou Allumer (1) : "))
            if status == 0:
              switch(response,1)
            elif status == 1:
              switch(response,0)
          if response == 4 or response == 5:
            value = input("Quelle couleur ? (RGB) : ")
            #GAUCHE
            if response == 4:
              if value == "B":
                switch(5,1)
                switch(6,1)
                switch(4,0)
              if value == "R":	   
                switch(6,0)
                switch(5,1)
                switch(4,1)
              if value == "G":
                switch(5,0)
                switch(6,1)
                switch(4,1)
            #DROITE
            if response == 5:
              if value == "R":
                switch(8,1)
                switch(9,1)
                switch(7,0)
              if value == "B":	   
                switch(9,0)
                switch(8,1)
                switch(7,1)
              if value == "G":
                switch(8,0)
                switch(9,1)
                switch(7,1)
        elif init =="3":
          afficher_etat(led_states, bar.led_count)
          user_input = input("Entrez : <LED Couleur Intensite> ou 'off <LED>' ou 'exit' : ").strip()
          if user_input.lower() == "exit":
            break
          elif user_input.lower().startswith("off "):
            try:
              num = int(user_input.split()[1])
              eteindre_led(bar, num, led_states)
            except:
              print("Commande invalide. Format : off <num_led>")
          else:
            parts = user_input.split()
            if len(parts) != 3:
              print("Format invalide. Exemple : 2 R 128 ou off 1")
              continue  
            try:
              num = int(parts[0])
              couleur = parts[1].upper()
              intensite = int(parts[2])
              set_led_manuel(bar, num, couleur, intensite, led_states)
            except:
              print("Erreur de saisie. Verifiez vos valeurs.")
        elif init =="4":
          control()
    finally:
      bar.led_close()
      set_all_switch_off()
      servo_initialisation(100)
            

