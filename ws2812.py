# -*- coding: Windows-1252 -*-

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

# === Affichage de l’état des LEDs ===
def afficher_etat(led_states, count):
    print("\nEtat actuel des LEDs :")
    for i in range(count):
        r, g, b = led_states.get(i, (0, 0, 0))
        etat = f"R={r} G={g} B={b}" if (r+g+b) > 0 else "ETEINTE"
        print(f"LED {i} : {etat}")
    print()

# === Commande utilisateur ===
def set_led_manuel(bar, num, couleur, intensite, led_states):
    if not (0 <= num < bar.led_count):
        print("Numéro de LED invalide.")
        return
    if not (0 <= intensite <= 255):
        print("Intensite invalide. Doit etre entre 0 et 255.")
        return

    r = g = b = 0
    if couleur.upper() == 'R':
        r = intensite
    elif couleur.upper() == 'G':
        g = intensite
    elif couleur.upper() == 'B':
        b = intensite
    elif couleur.upper() == 'N':
        r = g = b = 0
    else:
        print("Couleur invalide. Utilisez R, G, B ou N.")
        return

    bar.set_ledpixel(num, r, g, b)
    led_states[num] = (r, g, b)
    bar.show()

def eteindre_led(bar, num, led_states):
    if not (0 <= num < bar.led_count):
        print("Numero de LED invalide.")
        return
    bar.set_ledpixel(num, 0, 0, 0)
    led_states[num] = (0, 0, 0)
    bar.show()

# === Main ===
def main():
    bar = Adeept_SPI_LedPixel(count=14, bright=255, sequence='GRB', bus=0, device=0)
    if not bar.led_init_state:
        print("Erreur d'initialisation SPI.")
        return

    led_states = {}

    try:
        while True:
            afficher_etat(led_states, bar.led_count)
            user_input = input("Entrez : <LED Couleur Intensite> ou 'off <LED>' ou 'exit' : ").strip()
            if user_input.lower() == "exit":
                break
            elif user_input.lower().startswith("off "):
                try:
                    num = int(user_input.split()[1])
                    eteindre_led(bar, num, led_states)
                except:
                    print("Commande invalide. Format : off <num_led>")
            else:
                parts = user_input.split()
                if len(parts) != 3:
                    print("Format invalide. Exemple : 2 R 128 ou off 1")
                    continue
                try:
                    num = int(parts[0])
                    couleur = parts[1].upper()
                    intensite = int(parts[2])
                    set_led_manuel(bar, num, couleur, intensite, led_states)
                except:
                    print("Erreur de saisie. Verifiez vos valeurs.")
    except KeyboardInterrupt:
        print("\nArrêt demandé.")
    finally:
        print("Extinction de toutes les LEDs...")
        bar.led_close()

if __name__ == "__main__":
    main()
