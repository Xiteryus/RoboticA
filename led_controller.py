import RPi.GPIO as GPIO
import time

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
if __name__ == "__main__":
  switchSetup()
  set_all_switch_off()
  while 1:
    # led sur la carte : led 1 à 3 
    # led gauche avant : 4
    # led droite avant : 5 
    # led sur la carte à coté du bouton : 10 
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
          #----
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
