# -*- coding: Windows-1252 -*-
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
import spidev
import threading
import numpy


class Adeept_SPI_LedPixel(threading.Thread):
    def __init__(self, count=14, bright=255, sequence='GRB', bus=0, device=0):
        self.set_led_type(sequence)
        self.set_led_count(count)
        self.set_led_brightness(bright)
        self.led_begin(bus, device)
        self.set_all_led_color(0, 0, 0)
        super().__init__()
    def led_begin(self, bus, device):
        self.spi = spidev.SpiDev()
        try:
            self.spi.open(bus, device)
            self.spi.mode = 0
            self.led_init_state = 1
        except:
            self.led_init_state = 0
    def set_led_count(self, c):
        self.led_count = c
        self.led_color = [0]*3*self.led_count
    def set_led_type(self, t):
        types = ['RGB','RBG','GRB','GBR','BRG','BGR']
        offsets = [0x06,0x09,0x12,0x21,0x18,0x24]
        i = types.index(t) if t in types else 2
        o = offsets[i]
        self.led_offsets = [(o >> 4) & 3, (o >> 2) & 3, (o >> 0) & 3]
    def set_led_brightness(self, b):
        self.led_brightness = b
    def set_ledpixel(self, idx, r, g, b):
        p = [0,0,0]
        for col, ofs, val in zip((r,g,b), self.led_offsets, (r,g,b)):
            p[ofs] = round(col * self.led_brightness / 255)
        base = idx * 3
        self.led_color[base:base+3] = p
    def show(self):
        d = numpy.array(self.led_color, dtype=numpy.uint8)
        tx = numpy.zeros(len(d)*8, dtype=numpy.uint8)
        for bit in range(8):
            tx[7-bit::8] = ((d >> bit) & 1)*0x78 + 0x80
        if self.led_init_state:
            self.spi.xfer(tx.tolist(), int(8/1.25e-6))
    def led_close(self):
        self.set_all_led_color(0, 0, 0)
        self.show()
        if self.led_init_state:
            self.spi.close()
    def set_all_led_color(self, r, g, b):
        for i in range(self.led_count):
            self.set_ledpixel(i, r, g, b)
            

def voiture():
    bar = Adeept_SPI_LedPixel(count=14, bright=255, sequence='GRB', bus=0, device=0)
    
    while True:
      bar.set_ledpixel(2, 0, 0, 255)  # Bleu
      bar.show() 
      
      

if __name__ == "__main__":
    voiture()