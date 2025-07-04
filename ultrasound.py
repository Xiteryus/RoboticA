from gpiozero import DistanceSensor
from time import sleep

Tr = 23
Ec = 24
sensor = DistanceSensor(echo=Ec, trigger=Tr,max_distance=2) # Maximum detection distance 2m.

# Get the distance of ultrasonic detection.
def checkdist():
    return (sensor.distance) *10 # Unit: mm

if __name__ == "__main__":
    while True:
        distance = checkdist() 
        print("%.2f mm" %distance)
        sleep(0.05)
