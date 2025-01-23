import SYM_HexaPy
import tkinter as tk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import numpy as np
from lasergui import LaserGUI


class HexapodTest(LaserGUI):
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
            self.textbox.insert(tk.END, "Connected to Hexapod\n")
            self.textbox.insert(tk.END, "Please wait for homing sequence to complete then turn on control functionality\n")
            # self.home()
            self.ssh_API.CommandReturns

    def home(self):
        self.ssh_API.SendCommand("HOME")
    def controlOn(self):
        self.ssh_API.SendCommand("CONTROLON")

    def moveUp(self):
        self.ssh_API.SendCommand("MOVE_PTP", [2.0, 10.0, 0.0, 0.0, 0.0, 0.0, 0.0])
    def moveDown(self):
        self.ssh_API.SendCommand("MOVE_PTP", [2.0, -10.0, 0.0, 0.0, 0.0, 0.0, 0.0])
    def moveLeft(self):
        self.ssh_API.SendCommand("MOVE_PTP", [2.0, 0.0, 10.0, 0.0, 0.0, 0.0, 0.0])
    def moveRight(self):
        self.ssh_API.SendCommand("MOVE_PTP", [2.0, 0.0, -10.0, 0.0, 0.0, 0.0, 0.0])
    def moveOut(self):
        self.ssh_API.SendCommand("MOVE_PTP", [2.0, 0.0, 0.0, 10.0, 0.0, 0.0, 0.0])
    def moveIn(self):
        self.ssh_API.SendCommand("MOVE_PTP", [2.0, 0.0, 0.0, -10.0, 0.0, 0.0, 0.0])
    def resetPosition(self):
        self.ssh_API.SendCommand("MOVE_SPECIFICPOS", [3.0])
        

  