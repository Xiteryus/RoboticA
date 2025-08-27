import keyboard
import time

print("Appuie sur ..")

try:
    while True:
        if keyboard.is_pressed('z'):
            print("Touche Z ")
            break
        elif keyboard.is_pressed('a'):
            print("Touche A ")
        time.sleep(0.1)
except KeyboardInterrupt:
    pass
