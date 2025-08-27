import servo_controller
from motor import *
from gpiozero import InputDevice


# Configuration des pins des capteurs de ligne
line_pin_left = 22
line_pin_middle = 27
line_pin_right = 17

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

# 1 = ligne, 0 = pas de ligne


def tracking(previous_status):

   current_status = [left.value, middle.value, right.value]

   current_converted = int(str(current_status), 2)

   print("Current : ", captor_status[0], " +", captor_status[1], " + ", captor_status[2],"\n")
  
   if previous_status != current_status:
     match current_converted:
       case 0:
         print("\nrechercher")
       case 1:
         print("\na droite")
         servo_controller.set_angle(0, ANGLE_RIGHT)
         motor_drive(MOTOR_SPEED_SLOW, 1, 30)
       case 2:
         print("\ntout droit")
         servo_controller.set_angle(0, ANGLE_CENTER)
         motor_drive(MOTOR_SPEED_NORMAL, 1, 30)
       case 3:
         print("\na droite")
         servo_controller.set_angle(0, ANGLE_RIGHT)
         motor_drive(MOTOR_SPEED_SLOW, 1, 30)
       case 4:
         print("\na gauche")
         servo_controller.set_angle(0, ANGLE_LEFT)
         motor_drive(MOTOR_SPEED_SLOW, 1, 30)
       case 5:
         print("\nJe ne sais pas")
       case 6:
         print("\na gauche")
         servo_controller.set_angle(0, ANGLE_LEFT)
         motor_drive(MOTOR_SPEED_SLOW, 1, 30)
       case 7:
         print("\ntout droit")
         servo_controller.set_angle(0, ANGLE_CENTER)
         motor_drive(MOTOR_SPEED_NORMAL, 1, 30)
       case _:
         print("\nError: impossible reading on the IR sensor")
         
   else:
     print("\ntout droit")
     servo_controller.set_angle(0, ANGLE_CENTER)
     motor_drive(MOTOR_SPEED_NORMAL, 1, 30)
     
   return current_status
   


if __name__ == "__main__":

  captor_status = [left.value, middle.value, right.value]
  print(captor_status)
  servo_controller.set_angle(0, ANGLE_CENTER)
  
  try:
    while True:
      captor_status = tracking(captor_status)
  except KeyboardInterrupt:
    print("\nArret du programme")