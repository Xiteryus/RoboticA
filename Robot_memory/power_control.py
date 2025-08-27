# -*- coding: Windows-1252 -*-
import sys
import subprocess

def shutdown():
   
    subprocess.run(["sudo", "shutdown", "-h", "now"], check=False)

def reboot():
    
    subprocess.run(["sudo", "reboot"], check=False)

def usage():
    print("Usage : power_control.py [shutdown|reboot]")

def main():
    if len(sys.argv) != 2:
        usage()
        return

    cmd = sys.argv[1].lower()
    if cmd == "shutdown":
        shutdown()
    elif cmd == "reboot":
        reboot()
    else:
        usage()

if __name__ == "__main__":
    main()
