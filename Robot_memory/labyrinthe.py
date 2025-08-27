# -*- coding: Windows-1252 -*-

from servo_controller_improved import *
from motor import *
from servo_controller_improved import servo_controller
from gpiozero import InputDevice
from servo_controller import *

from ultrasound import*

from arrow_detection import *
from camera import * 


ANGLE_CENTER = 90     # Position centrale
ANGLE_LEFT = 120      # Virage a gauche (augmente pour plus de braquage)
ANGLE_RIGHT = 60      # Virage a droite (diminue pour plus de braquage)
ANGLE_SHARP_LEFT = 130   # Virage serre a gauche
ANGLE_SHARP_RIGHT = 50   # Virage serre a droite

RIGHT_ANGLE_LEFT = 180
RIGHT_ANGLE_RIGHT = 0

camera = PiCameraStream()
camera.toggle_arrow_detection()


def get_direction():
    camera.get_frame()
    
    direction = camera.get_arrow_direction()
    return direction
    
    
def chose():
    
   
    
    t = []; l=0;r=0;n=0
    
    
    for j in range(5):
        non = get_direction()
        print(non)
        sleep(1)
        if non == "left":
            l+=1
        if non == "none":
            n+=1
        if non == "right":
            r+=1
    
    if max(l,n,r) == l:
        return "left"
    elif max(l,n,r) == r :
        return "right"
    else:
        return "none"
  
def moov():
    set_angle(1,100)
    set_angle(2,100)
    while checkdist() > 300:
      drive()
    motorStop()
    sleep(1)
    direction = chose()
    
    if direction == "none":
      backward()
      sleep(2)
      motorStop()    
    
    elif direction == "left":
      set_angle(0,ANGLE_SHARP_RIGHT)
      backward()
      sleep(0.5)
      motorStop()
      #-----
      set_angle(0,ANGLE_SHARP_LEFT)
      drive()
      sleep(4)
      motorStop()
      #-----
      set_angle(0,ANGLE_CENTER)
      drive()
      
       
   
      
      
    elif direction =="right":
        set_angle(0,ANGLE_SHARP_LEFT)
        backward()
        sleep(0.5)
        motorStop()
        #-----
        set_angle(0,ANGLE_SHARP_RIGHT)
        drive()
        sleep(4)
        motorStop()
        #-----
        set_angle(0,ANGLE_CENTER)
        drive()
    
      
      
      
if __name__ == "__main__":

      
      
      while True:
          # Met à jour la frame + effectue la détection
          
          
          moov()
          
          
           