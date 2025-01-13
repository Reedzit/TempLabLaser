import SYM_HexaPy
import tkinter as tk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import numpy as np
from lasergui import LaserGUI


class HexapodControlWindow(LaserGUI):
    ssh_API = None

    def __init__(self):
        self.window = tk.Tk()
        self.window.geometry("1000x1000")
        self.window.title("Hexapod Control")
        label = tk.Label(self.window, text="Hexapod Control", font=('Arial', 18))
        label.pack(padx=20, pady=20)

        self.button = tk.Button(self.window, text="Connect to Hexapod", command=self.connectHexapod)
        self.button.pack(padx=10, pady=10)

        self.button = tk.Button(self.window, text="Turn on Control", command=self.controlOn)
        self.button.pack(padx=10, pady=10)

        self.button = tk.Button(self.window, text="Reset Position", command=self.resetPosition)
        self.button.pack(padx=10, pady=10)

        bfTranslation = tk.Frame(self.window)
        bfTranslation.columnconfigure(0, weight=1)
        bfTranslation.columnconfigure(1, weight=1)
        bfTranslation.columnconfigure(2, weight=1)
        bfTranslation.rowconfigure(0, weight=1)
        bfTranslation.rowconfigure(1, weight=1)
        bfTranslation.rowconfigure(2, weight=1)

        btn_up = tk.Button(bfTranslation, text="Up", command=self.moveUp, font=('Arial', 18))
        btn_up.grid(row=0, column=1, sticky=tk.W+tk.E)

        btn_left = tk.Button(bfTranslation, text="Left", command=self.moveLeft, font=('Arial', 18))
        btn_left.grid(row=1, column=0, sticky=tk.W+tk.E)

        btn_down = tk.Button(bfTranslation, text="Down", command=self.moveDown, font=('Arial', 18))
        btn_down.grid(row=1, column=1, sticky=tk.W+tk.E)

        btn_right = tk.Button(bfTranslation, text="Right", command=self.moveRight, font=('Arial', 18))
        btn_right.grid(row=1, column=2, sticky=tk.W+tk.E)

        btn_in = tk.Button(bfTranslation, text="In", command=self.moveIn, font=('Arial', 18))
        btn_in.grid(row=2, column=1, sticky=tk.W+tk.E)

        btn_out = tk.Button(bfTranslation, text="Out", command=self.moveOut, font=('Arial', 18))
        btn_out.grid(row=3, column=1, sticky=tk.W+tk.E)

        bfTranslation.pack(fill='x', padx=20, pady=20)

        self.textbox = tk.Text(self.window, height=8,  font=('Arial', 16))
        self.textbox.pack(padx=10, pady=10, side=tk.BOTTOM, fill=tk.X)

        self.window.mainloop()
    
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
            self.home()
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
        

  