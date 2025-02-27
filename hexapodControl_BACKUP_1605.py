import SYM_HexaPy
import tkinter as tk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import numpy as np
from lasergui import LaserGUI


class HexapodControl(LaserGUI):
    ssh_API = None

    def __init__(self):
        self.connectHexapod()
    
    def connectHexapod(self):
        

        # ip = "192.168.56.101"
        ip = "192.168.16.220"

        SEQ_file_path = "Gamme_PUNA.txt"
        SEQ_pause_stab = 0.1
        SEQ_pause_mes = 0.2
        SEQ_dec_nb = 1
        SEQ_cycle_nb = 2

        verbose = False
        log = True

        # Connect the SSH client
        self.ssh_API = SYM_HexaPy.API()
        self.ssh_API.connect(ip, verbose, log)
        if self.ssh_API.ssh_obj.connected is True:
            print("Connected to the Hexapod")
            self.ssh_API.CommandReturns

    def home(self):
        answer = self.ssh_API.SendCommand("HOME")
        return answer
    def controlOn(self):
<<<<<<< HEAD
        answer = self.ssh_API.SendCommand("CONTROLON")
        return answer
    def moveUp(self):
        answer = self.ssh_API.SendCommand("MOVE_PTP", [2.0, 10.0, 0.0, 0.0, 0.0, 0.0, 0.0])
        return answer
    def moveDown(self):
        answer = self.ssh_API.SendCommand("MOVE_PTP", [2.0, -10.0, 0.0, 0.0, 0.0, 0.0, 0.0])
        return answer
    def moveLeft(self):
        answer = self.ssh_API.SendCommand("MOVE_PTP", [2.0, 0.0, 10.0, 0.0, 0.0, 0.0, 0.0])
        return answer
    def moveRight(self):
        answer = self.ssh_API.SendCommand("MOVE_PTP", [2.0, 0.0, -10.0, 0.0, 0.0, 0.0, 0.0])
        return answer
    def moveOut(self):
        answer = self.ssh_API.SendCommand("MOVE_PTP", [2.0, 0.0, 0.0, 10.0, 0.0, 0.0, 0.0])
        return answer
    def moveIn(self):
        answer = self.ssh_API.SendCommand("MOVE_PTP", [2.0, 0.0, 0.0, -10.0, 0.0, 0.0, 0.0])
        return answer
=======
        self.ssh_API.SendCommand("CONTROLON")

    def moveUp(self, step):
        self.ssh_API.SendCommand("MOVE_PTP", [2.0, float(step), 0.0, 0.0, 0.0, 0.0, 0.0])
    def moveDown(self, step):
        self.ssh_API.SendCommand("MOVE_PTP", [2.0, -float(step), 0.0, 0.0, 0.0, 0.0, 0.0])
    def moveLeft(self, step):
        self.ssh_API.SendCommand("MOVE_PTP", [2.0, 0.0, float(step), 0.0, 0.0, 0.0, 0.0])
    def moveRight(self, step):
        self.ssh_API.SendCommand("MOVE_PTP", [2.0, 0.0, -float(step), 0.0, 0.0, 0.0, 0.0])
    def moveOut(self, step):
        self.ssh_API.SendCommand("MOVE_PTP", [2.0, 0.0, 0.0, float(step), 0.0, 0.0, 0.0])
    def moveIn(self, step):
        self.ssh_API.SendCommand("MOVE_PTP", [2.0, 0.0, 0.0, -float(step), 0.0, 0.0, 0.0])
>>>>>>> 7a2675da8b54631fa864ec713ba8b3822b2734b1
    def setSpeed(self, speed):
        answer = self.ssh_API.SendCommand("CFG_SPEED", [0.0, float(speed)]) #arguments: translationSpeed angularSpeed
        return answer
    def resetPosition(self):
        answer = self.ssh_API.SendCommand("MOVE_SPECIFICPOS", [3.0])
        return answer 
        

  