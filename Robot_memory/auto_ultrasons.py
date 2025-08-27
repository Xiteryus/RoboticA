from motor import *
from radar import *
import asyncio

def initialisation_servos():
    initialisation_direction()
    initialisation_radar()


def initialisation_radar():
    #cou (gauche/dorite)
    set_angle(1, 90)
    #cou (haut/bas)
    set_angle(2, 90)


def initialisation_direction():
    set_angle(0, 90)


async def radar():
    initialisation_radar()
    try :
        detection_map = [0]*18
        direction = 1
        angle = 90
        while True: 
            for i in range(len(detection_map)):
                # mise a jour de la map de detection
                detection_map[(angle//10)-1] = detection(angle)
                #print("\n", detection_map)

                # mise a jour du sens de direction
                if angle >= 180 and direction == 1:
                    direction = 0
                elif angle <= 10 and direction == 0:
                    direction = 1

                # mise a jour de l'angle
                if direction:
                    angle += 10
                else:
                    angle -= 10

            yield detection_map
    except KeyboardInterrupt:
        print("\nArret du radar")
        #queue.put(None)
    finally:
        print("\nReinitialisation des servomoteurs")
        set_angle(1, 90)
        set_angle(2, 90)


async def cast_stop_warning():
    async for result in radar():
        if result[9] <= 100:
            return True
        elif result[8] <= 51.8 or result[10] <= 51.8:
            return True
        elif result[7] <= 26.3 or result[11] <= 26.3:
            return True
        elif result[6] <= 18 or result[12] <= 18:
            return True
        elif result[5] <= 14 or result[13] <= 14:
            return True
        elif result[4] <= 11.7 or result[14] <= 11.7:
            return True
        else:
            return False


async def stopRobot():
    async for result in cast_stop_warning():
        if result:
            motorStop()
        else:
            motor_drive(25, 1, 1)


if __name__ == "__main__":
    initialisation_direction()
    try:
        asyncio.run(stopRobot())
    except KeyboardInterrupt:
        print("\nArret du programme")
    finally:
        print("\nReinitialisation des servo moteurs")