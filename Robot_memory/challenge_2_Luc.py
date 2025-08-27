import motor
from gpiozero import InputDevice
import servo_controller


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


def initialize_servos():
    servo_controller.set_angle(0, 90)
    servo_controller.set_angle(1, 90)
    servo_controller.set_angle(2, 90)

# fonction de recuperation des valeurs des capteurs
def convertIRtoList():
    return [left.value, middle.value, right.value]


# fonction de detection de position de la ligne par rapport au capteur
def line_awareness():
    censor = convertIRtoList
    if censor == [0, 0, 1] or censor == [0, 1, 1]:
        return 1, censor
    elif censor == [1, 0, 0] or censor == [1, 1, 0]:
        return -1, censor
    elif censor == [0, 1, 0] or censor == [1, 1, 1]:
        return 0, censor
    elif censor == [0, 0, 0]:
        return None, censor
    else:
        return 2, censor


# fonction de prise de decision
def tracking(previous_action, previous_line_position):
    line, IRcaptor = line_awareness()
    match previous_action: # switch case avec l'action en cours d'execution comme reference
        case 1: # virage a droite
            if line == 1:
                servo_controller.set_angle(0, ANGLE_SHARP_RIGHT)
                motor.motor_drive(MOTOR_SPEED_SEARCH, 1, 5)
                return 1, IRcaptor
            elif line == -1:
                servo_controller.set_angle(0, ANGLE_SHARP_LEFT)
                motor.motor_drive(MOTOR_SPEED_SEARCH, 1, 5)
                return -1, IRcaptor
            elif line == 0:
                servo_controller.set_angle(0, ANGLE_CENTER)
                motor.motor_drive(MOTOR_SPEED_NORMAL, 1, 5)
                return 0, IRcaptor
            elif line == None:
                if previous_line_position == [0, 0, 0] or previous_line_position == [0, 0, 1] or previous_line_position == [0, 1, 1]:
                    servo_controller.set_angle(0, ANGLE_SHARP_RIGHT)
                    motor.motor_drive(MOTOR_SPEED_SEARCH, 1, 5)
                    return 1, IRcaptor

        case -1: # virage a gauche
            if line == 1:
                servo_controller.set_angle(0, ANGLE_SHARP_RIGHT)
                motor.motor_drive(MOTOR_SPEED_SEARCH, 1, 5)
                return 1, IRcaptor
            elif line == -1:
                servo_controller.set_angle(0, ANGLE_SHARP_LEFT)
                motor.motor_drive(MOTOR_SPEED_SEARCH, 1, 5)
                return -1, IRcaptor
            elif line == 0:
                servo_controller.set_angle(0, ANGLE_CENTER)
                motor.motor_drive(MOTOR_SPEED_NORMAL, 1, 5)
                return 0, IRcaptor
            elif line == None:
                if previous_line_position == [0, 0, 0] or previous_line_position == [1, 0, 0] or previous_line_position == [1, 1, 0]:
                    servo_controller.set_angle(0, ANGLE_SHARP_LEFT)
                    motor.motor_drive(MOTOR_SPEED_SEARCH, 1, 5)
                    return -1, IRcaptor

        case 0: # ligne droite
            if line == 0: # la capteur est entierement sur la ligne
                servo_controller.set_angle(0, ANGLE_CENTER)
                motor.motor_drive(MOTOR_SPEED_NORMAL, 1, 5)
                return 0, IRcaptor
            elif line == 1: # la ligne est sur la droite du capteur
                servo_controller.set_angle(0, ANGLE_SHARP_RIGHT)
                motor.motor_drive(MOTOR_SPEED_SEARCH, 1, 5)
                return 1, IRcaptor
            elif line == -1: # la ligne est sur la gauche du capteur
                servo_controller.set_angle(0, ANGLE_SHARP_LEFT)
                motor.motor_drive(MOTOR_SPEED_SEARCH, 1, 5)
                return -1, IRcaptor
            elif line == None: # la ligne n'est pas captee par le capteur
                if previous_line_position == [0, 0, 1] or previous_line_position == [0, 1, 1]: # la ligne se trouvait a l'extremite droite du capteur avant de perdre le signal
                    servo_controller.set_angle(0, ANGLE_SHARP_RIGHT)
                    motor.motor_drive(MOTOR_SPEED_SEARCH, 1, 5)
                    return 1, IRcaptor
                elif previous_line_position == [1, 0, 0] or previous_line_position == [1, 1, 0]: # la ligne se trouvait a l'extremite gauche du capteur avant de perdre le signal
                    servo_controller.set_angle(0, ANGLE_SHARP_LEFT)
                    motor.motor_drive(MOTOR_SPEED_SEARCH, 1, 5)
                    return -1, IRcaptor
  
        case _: # cas impossible
            print("\nCette action n'est pas effectuable par le robot")
            servo_controller.set_angle(0, ANGLE_CENTER)
            motor.motor_drive(0, 1, 2)


if __name__ == "__main__":
    
    initialize_servos()
    
    previous_line_position = convertIRtoList
    previous_action = 0
    
    try:
        while True :
            tracking(previous_action, previous_line_position)
    except KeyboardInterrupt:
        print("\nArret du programme")
        initialize_servos()
        motor.motor_drive(0, 1, 2)