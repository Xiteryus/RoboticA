import time
import board
import adafruit_ads7830.ads7830 as ADC
from adafruit_ads7830.analog_in import AnalogIn

i2c = board.I2C()

# Initialize ADS7830
adc = ADC.ADS7830(i2c,0x48)  #default is 0x48
chan1 = AnalogIn(adc, 1)
chan2 = AnalogIn(adc, 2)

chan3 = AnalogIn(adc, 3)
chan4 = AnalogIn(adc, 4)
chan5 = AnalogIn(adc, 5)
chan6 = AnalogIn(adc, 6)
chan7 = AnalogIn(adc, 7)
chan0 = AnalogIn(adc, 0)

if __name__ == "__main__":

    while True:
        LT_value = chan1.value
        print(f"Light Tracking Value: {LT_value}")
        print(f"ADC channel 2 = {chan2.value}")
        print(f"ADC channel 3 = {chan3.value}")
        print(f"ADC channel 4 = {chan4.value}")
        print(f"ADC channel 5 = {chan5.value}")
        print(f"ADC channel 6 = {chan6.value}")
        print(f"ADC channel 7 = {chan7.value}")
        print(f"ADC channel 0 = {chan0.value}")
        print("--------------------------------")
        time.sleep(0.5)

