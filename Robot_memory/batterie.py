#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
import board
import busio
from adafruit_bus_device.i2c_device import I2CDevice
import spidev
import threading
import numpy

# ==== Classe de pilotage SPI WS2812 ====
class Adeept_SPI_LedPixel(threading.Thread):
    def __init__(self, count=2, bright=20, sequence='GRB', bus=0, device=0, *args, **kwargs):
        self.set_led_type(sequence)
        self.set_led_count(count)
        self.set_led_brightness(bright)
        self.led_begin(bus, device)
        self.lightMode = 'none'
        self.breathSteps = 10
        self.set_all_led_color(0, 0, 0)
        super(Adeept_SPI_LedPixel, self).__init__(*args, **kwargs)
        self.__flag = threading.Event()
        self.__flag.clear()

    def led_begin(self, bus, device):
        self.spi = spidev.SpiDev()
        try:
            self.spi.open(bus, device)
            self.spi.mode = 0
            self.led_init_state = 1
        except OSError:
            self.led_init_state = 0

    def check_spi_state(self):
        return self.led_init_state

    def set_led_count(self, count):
        self.led_count = count
        self.led_color = [0] * (3 * count)
        self.led_original_color = [0] * (3 * count)

    def set_led_type(self, rgb_type):
        types   = ['RGB','RBG','GRB','GBR','BRG','BGR']
        offsets = [0x06, 0x09, 0x12, 0x21, 0x18, 0x24]
        try:
            i = types.index(rgb_type)
        except ValueError:
            i = 2  # GRB par défaut
        o = offsets[i]
        self.led_red_offset   = (o >> 4) & 0x03
        self.led_green_offset = (o >> 2) & 0x03
        self.led_blue_offset  = (o >> 0) & 0x03

    def set_led_brightness(self, br):
        self.led_brightness = br

    def set_ledpixel(self, idx, r, g, b):
        p = [0, 0, 0]
        p[self.led_red_offset]   = round(r * self.led_brightness / 255)
        p[self.led_green_offset] = round(g * self.led_brightness / 255)
        p[self.led_blue_offset]  = round(b * self.led_brightness / 255)
        base = idx * 3
        self.led_original_color[base + 0] = r
        self.led_original_color[base + 1] = g
        self.led_original_color[base + 2] = b
        for i in range(3):
            self.led_color[base + i] = p[i]

    def set_all_led_color(self, r, g, b):
        for i in range(self.led_count):
            self.set_ledpixel(i, r, g, b)

    def show(self):
        d  = numpy.array(self.led_color, dtype=numpy.uint8)
        tx = numpy.zeros(len(d)*8, dtype=numpy.uint8)
        for bit in range(8):
            tx[7-bit::8] = ((d>>bit)&1)*0x78 + 0x80
        if self.led_init_state:
            self.spi.xfer(tx.tolist(), int(8/1.25e-6))

    def led_close(self):
        self.set_all_led_color(0, 0, 0)
        self.show()
        if self.led_init_state:
            self.spi.close()

# ==== Configuration ADC (ADS7830) ====
i2c = busio.I2C(board.SCL, board.SDA)
adc = I2CDevice(i2c, 0x48)
Vref             = 8.4
WarningThreshold = 6.75
R15, R17         = 3000, 1000
DivisionRatio    = R17 / (R15 + R17)

def read_adc(ch=0):
    cmd = 0x84 | (((ch << 2 | ch >> 1) & 0x07) << 4)
    buf = bytearray(1)
    with adc:
        adc.write_then_readinto(bytes([cmd]), buf)
    return buf[0]

# ==== Mise à jour des LED selon % de batterie ====
def update_leds(bar, pct):
    if pct > 50:
        bar.set_all_led_color(0, 255, 0)   # vert
    elif pct > 25:
        bar.set_all_led_color(255, 255, 0) # jaune
    elif pct > 5:
        bar.set_all_led_color(255, 0, 0)   # rouge fixe
    else:
        # clignotement rouge
        bar.set_all_led_color(255, 0, 0); bar.show(); time.sleep(0.3)
        bar.set_all_led_color(0, 0, 0);   bar.show(); time.sleep(0.3)
        return
    bar.show()

# ==== Boucle principale ====
def main():
    bar = Adeept_SPI_LedPixel(count=2, bright=20, sequence='GRB', bus=0, device=0)
    if not bar.check_spi_state():
        return

    try:
        while True:
            val  = read_adc(0)
            A0   = (val / 255) * 5.0
            batt = A0 / DivisionRatio
            pct  = (batt - WarningThreshold) / (Vref - WarningThreshold) * 100
            pct  = max(0.0, min(100.0, pct))

            update_leds(bar, pct)
            time.sleep(0.5)

    except KeyboardInterrupt:
        bar.led_close()

if __name__ == "__main__":
    main()
