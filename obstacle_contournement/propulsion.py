# -*- coding: Windows-1252 -*-


#!/usr/bin/env python3
import time
from board import SCL, SDA
import busio
from adafruit_pca9685 import PCA9685
from adafruit_motor import motor
#from servo_controller import *


#initialisation du moteur
MOTOR_M1_IN1 = 15
MOTOR_M1_IN2 = 14

def map(x, in_min, in_max, out_min, out_max):
    return (x - in_min)/(in_max - in_min)*(out_max - out_min) + out_min

i2c = busio.I2C(SCL, SDA)
pwm_motor = PCA9685(i2c, address=0x5f)
pwm_motor.frequency = 50

motor1 = motor.DCMotor(pwm_motor.channels[MOTOR_M1_IN1], pwm_motor.channels[MOTOR_M1_IN2])
motor1.decay_mode = motor.SLOW_DECAY


init = 90


def Motor(channel,direction,motor_speed):
  if motor_speed > 100:
    motor_speed = 100
  elif motor_speed < 0:
    motor_speed = 0
  speed = map(motor_speed, 0, 100, 0, 1.0)
  if direction == -1:
    speed = -speed
  if channel == 1:
    motor1.throttle = speed
    # print("1111")


def motorStop():
    motor1.throttle = 0


def destroy():
    motorStop()
    pwm_motor.deinit()


def ramp(sens):
    steps = 20
    delay = 1.0 / steps #0.05s
    for i in range(steps):
      speed = (i / steps) * 100  #0 a 100 
      Motor(1, sens, speed)
      time.sleep(delay)
    time.sleep(2)
    motorStop()


def motor_drive(speed, sens, pente):
    steps = 30
    delay = pente / steps
    for i in range(steps):
      s = (i / steps) * speed 
      Motor(1, sens, s)
      time.sleep(delay)


def forward():
    motor_drive(25, 1, 1)
    time.sleep(2)
    motorStop()


def backward ():
    motor_drive(25, -1, 1)
    time.sleep(2)
    motorStop()