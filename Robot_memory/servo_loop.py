#!/usr/bin/env/python3
'''
 SPDX-FileCopyrightText: 2021 ladyada for Adafruit Industries
# SPDX-License-Identifier: MIT
# Import the PCA9685 module. Available in the bundle and here:
#   https://github.com/adafruit/Adafruit_CircuitPython_PCA9685
# sudo pip3 install adafruit-circuitpython-motor
# sudo pip3 install adafruit-circuitpython-pca9685
'''
import time
from board import SCL, SDA
import busio
from adafruit_motor import servo
from adafruit_pca9685 import PCA9685

i2c = busio.I2C(SCL, SDA)
# Create a simple PCA9685 class instance.
pca = PCA9685(i2c, address=0x5f) #default 0x40

pca.frequency = 50

# The pulse range is 750 - 2250 by default. This range typically gives 135 degrees of
# range, but the default is to use 180 degrees. You can specify the expected range if you wish:
# servo7 = servo.Servo(pca.channels[7], actuation_range=135)
def set_angle(ID, angle):
    servo_angle = servo.Servo(pca.channels[ID], min_pulse=500, max_pulse=2400,actuation_range=180)
    servo_angle.angle = angle
      
def slow_angle(channel, init, final):
    if(final > init): 
        for i in range(init, final): # The servo turns from 0 to 180 degrees.
            set_angle(channel, i)
            time.sleep(0.01)
        time.sleep(0.5)
        
    else:
        for i in range(init, final, -1): # The servo turns from 180 to 0 degre
            set_angle(channel, i)
            time.sleep(0.01)
        time.sleep(0.5)
    return final

if __name__ == "__main__":
    init = 90
    while True:
        set_angle(2,80)
        response = int(input("Servomoteur ? (0 moteur, 1 tete de gauche a droite, 2 tete de haut en bas) :  "))
        for i in range(5):
          angle = 30
          init = slow_angle(response,init,angle)
          angle = 160
          init = slow_angle(response,init,angle)
