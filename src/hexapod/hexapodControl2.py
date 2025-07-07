import src.hexapod.SYM_HexaPy as SYM_HexaPy
import tkinter as tk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import numpy as np

class HexapodControl():

    def __init__(self):
        self.ssh_API = None
        self.connectHexapod()

    # Shout out to Reed Zittler for this code
    def connectHexapod(self):
        # ip = "192.168.56.101"
        ip = "192.168.16.220"

        SEQ_file_path = "Gamme_PUNA.txt"
        SEQ_pause_stab = 0.1
        SEQ_pause_mes = 0.2
        SEQ_dec_nb = 1
        SEQ_cycle_nb = 2

        self.verbose = False
        log = True

        # Connect the SSH client
        self.ssh_API = SYM_HexaPy.API()
        self.ssh_API.connect(ip, self.verbose, log)
        if self.ssh_API.ssh_obj.connected is True:
            print("Connected to the Hexapod")

    def home(self):
        answer = int(self.ssh_API.SendCommand("HOME").strip())
        print(f"This is the code for the home command: {self.ssh_API.CommandReturns[answer]}")
        return answer

    # API Documentation seems to have gone entirely missing, so I'm not entirely sure what this command does,
    # but some trial and error suggests it might be used to turn the hexapod on and off.

    def controlOn(self):
        answer = int(self.ssh_API.SendCommand("CONTROL ON").strip())
        print(f"This is the code for the control on command: {self.ssh_API.CommandReturns[answer]}")

    def controlOff(self):
        answer = int(self.ssh_API.SendCommand("CONTROL OFF").strip())
        print(f"This is the code for the control off command: {self.ssh_API.CommandReturns[answer]}")

    def translate(self, movement_vector=np.array([0.0, 0.0, 0.0]), magnitude=None):
        x, y, z = movement_vector
        if magnitude:
            normalizedMovementVector = (movement_vector / np.linalg.norm(movement_vector)) * magnitude
            x, y, z = normalizedMovementVector
        answer = self.ssh_API.SendCommand("MOVE_PTP", [2.0, x, y, z, 0.0, 0.0, 0.0])
        answer = int(answer.strip())
        if answer in self.ssh_API.CommandReturns.keys():
            answer = self.ssh_API.CommandReturns[answer]
        elif answer in self.ssh_API.ErrorCodes.keys():
            answer = self.ssh_API.ErrorCodes[answer]
        return answer

    def rotate(self, rotation_vector=np.array([0.0, 0.0, 0.0])):
        alpha, beta, tau = rotation_vector # naming conventions come from
        answer = self.ssh_API.SendCommand("MOVE_PTP", [2.0, 0.0, 0.0, 0.0, alpha, beta, tau])
        answer = int(answer.strip())
        if answer in self.ssh_API.CommandReturns.keys():
            answer = self.ssh_API.CommandReturns[answer]
        elif answer in self.ssh_API.ErrorCodes.keys():
            answer = self.ssh_API.ErrorCodes[answer]
        return answer

    def compoundMove(self, movement_vector=np.array([0.0, 0.0, 0.0]), rotation_vector=np.array([0.0, 0.0, 0.0]), magnitude=None):
        x, y, z = movement_vector
        alpha, beta, tau = rotation_vector
        if magnitude:
            normalizedMovementVector = (movement_vector / np.linalg.norm(movement_vector)) * magnitude
            x, y, z = normalizedMovementVector
        answer = self.ssh_API.SendCommand("MOVE_PTP", [2.0, x, y, z, alpha, beta, tau])
        answer = int(answer.strip())
        if answer in self.ssh_API.CommandReturns.keys():
            answer = self.ssh_API.CommandReturns[answer]
        elif answer in self.ssh_API.ErrorCodes.keys():
            answer = self.ssh_API.ErrorCodes[answer]
        return answer

    # Shout out to Reed Zittler for this code too
    def setSpeed(self, speed):
        answer = self.ssh_API.SendCommand("CFG_SPEED", [0.0, float(speed)]) #arguments: translationSpeed angularSpeed
        answer = int(answer.strip())
        if answer in self.ssh_API.CommandReturns.keys():
            answer = self.ssh_API.CommandReturns[answer]
        elif answer in self.ssh_API.ErrorCodes.keys():
            answer = self.ssh_API.ErrorCodes[answer]
        return answer

    def resetPosition(self):
        answer = self.ssh_API.SendCommand("MOVE_SPECIFICPOS", [3.0])
        answer = int(answer.strip())
        if answer in self.ssh_API.CommandReturns.keys():
            answer = self.ssh_API.CommandReturns[answer]
        elif answer in self.ssh_API.ErrorCodes.keys():
            answer = self.ssh_API.ErrorCodes[answer]
        return answer

    def waitForCommandResolution(self):
        answer = self.ssh_API.waitCommandExecuted()
        if answer in self.ssh_API.CommandReturns.keys():
            answer = self.ssh_API.CommandReturns[answer]
        elif answer in self.ssh_API.ErrorCodes.keys():
            answer = self.ssh_API.ErrorCodes[answer]
        return answer

    # no idea what this API command does but need to figure it out ig
    def getState(self):
        answer = self.ssh_API.STATE()
        if answer in self.ssh_API.CommandReturns.keys():
            answer = self.ssh_API.CommandReturns[answer]
        elif answer in self.ssh_API.ErrorCodes.keys():
            answer = self.ssh_API.ErrorCodes[answer]
        return answer



