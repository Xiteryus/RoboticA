from servo_controller_improved import *
from motor import *
from servo_controller_improved import servo_controller
from gpiozero import InputDevice
from servo_controller import *

# Configuration des pins des capteurs de ligne
line_pin_left = 17
line_pin_middle = 27
line_pin_right = 22

# Initialisation des capteurs (attention: assignation inversee dans le code original)
left = InputDevice(pin=line_pin_right)    # Capteur gauche sur pin droite
middle = InputDevice(pin=line_pin_middle) # Capteur milieu
right = InputDevice(pin=line_pin_left)    # Capteur droit sur pin gauche

# Configuration des angles du servo de direction
ANGLE_CENTER = 90     # Position centrale
ANGLE_LEFT = 120      # Virage a gauche (augmente pour plus de braquage)
ANGLE_RIGHT = 60      # Virage a droite (diminue pour plus de braquage)
ANGLE_SHARP_LEFT = 130   # Virage serre a gauche
ANGLE_SHARP_RIGHT = 50   # Virage serre a droite

# Configuration moteur
MOTOR_SPEED_NORMAL = 25   # Vitesse normale
MOTOR_SPEED_SLOW = 15     # Vitesse reduite en virage
MOTOR_SPEED_SEARCH = 10   # Vitesse de recherche




def tracking(virage):
    
    status_right = right.value
    status_middle = middle.value
    status_left = left.value

    print("Current : ",status_left," +", status_middle, " + ", status_right,"\n")

    if status_left == 0 and status_middle == 0 and status_right == 0: #1
      motorStop()
      print(virage)
      if virage == -1: 
        set_angle(0,ANGLE_SHARP_RIGHT) 
      elif virage == 1:
        set_angle(0,ANGLE_SHARP_LEFT) 
      """ 
      elif status_left_before == 1 and status_middle_before == 1 and status_right_before == 0: 
        set_angle(0,ANGLE_LEFT)

      elif status_left_before == 0 and status_middle_before == 1 and status_right_before == 1: 
        set_angle(0,ANGLE_RIGHT)"""
      
      sleep(0.5)

      #else:
      #motorStop()
      motor_25_negative()
      sleep(1.5)
      motorStop()
      if virage == -1:
        set_angle(0,ANGLE_SHARP_LEFT)
      elif virage == 1:
       set_angle(0, ANGLE_SHARP_RIGHT)
      sleep(0.5)
      motor_25()
      sleep(1.5)

    else :
      drive()
      if status_left == 0 and status_middle == 0 and status_right == 1: #2
        set_angle(0,ANGLE_SHARP_RIGHT)
        virage = -1
        
      elif status_left == 0 and status_middle == 1 and status_right == 0: #3
        set_angle(0,ANGLE_CENTER)
        virage = 0
        
      elif status_left == 0 and status_middle == 1 and status_right == 1: #4
        set_angle(0,ANGLE_RIGHT)
        virage = 1
        
      elif status_left == 1 and status_middle == 0 and status_right == 0: #5
        set_angle(0,ANGLE_SHARP_LEFT)
        virage = -1
        
      #elif status_left == 1 and status_middle == 0 and status_right == 1: #6
      
        #tracking(status_left_before, status_middle_before, status_right_before)
        #pass
      
      elif status_left == 1 and status_middle == 1 and status_right == 0: #7
        set_angle(0, ANGLE_LEFT)
        virage = -1
        
      elif status_left == 1 and status_middle == 1 and status_right == 1: #8
        #tracking(status_left_before, status_middle_before, status_right_before)
        set_angle(0,ANGLE_CENTER)
        virage = 0
      
    return status_left, status_middle, status_right, virage

if __name__ == "__main__":


    servo_controller.initialize_servos()
    
    status_right_before = 0
    status_middle_before = 1
    status_left_before = 0
    
    counter = 0
    virage = 0 # -1=gauche ; 0=toutdroit ; 1=droit
    
    while True :
        
        #if counter == 5:
          #status_left_before, status_middle_before, status_right_before = tracking(status_left_before, status_middle_before, status_right_before
          #counter = 0
        a,b,c,virage = tracking(virage)
        print("Past : ",status_left_before," +", status_middle_before, " + ", status_right_before)
        #counter = counter +1
        
        #if(status_left_before==0 and status_middle_before==0 and status_right_before==0 ):
        #  break
        
