import RPi.GPIO as GPIO
import time

test_pins = [ 18, 22, 23, 24, 25, 26, 27]
GPIO.setmode(GPIO.BCM)

valid_pins = []

for pin in test_pins:
    try:
        GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        valid_pins.append(pin)
    except RuntimeError:
        print(f"GPIO{pin}")

print(f"{valid_pins}")

try:
    last_states = {pin: GPIO.input(pin) for pin in valid_pins}
    while True:
        for pin in valid_pins:
            current = GPIO.input(pin)
            if current != last_states[pin]:
                print(f"GPIO{pin} ? {current}")
                last_states[pin] = current
        time.sleep(0.005)
except KeyboardInterrupt:
    GPIO.cleanup()
