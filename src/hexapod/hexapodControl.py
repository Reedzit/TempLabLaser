import src.hexapod.SYM_HexaPy as SYM_HexaPy
import tkinter as tk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import numpy as np

# TODO:
# - Research the API and how to use it
# - Move in Z direction (Z is the direciton of the lasers)
# - Move in X and Y for rastering
# - Rotation about a point


class HexapodControl():
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

    def _decode_command_answer(self, answer, command=None):
        try:
            code = int(str(answer).strip())
        except (TypeError, ValueError) as exc:
            raise RuntimeError(f"Hexapod API error during {command}: unparseable response {answer!r}") from exc

        if code == 0:
            return self.ssh_API.CommandReturns.get(code, "Success.")

        if code in self.ssh_API.CommandReturns:
            raise RuntimeError(f"Hexapod API error during {command}: {code} - {self.ssh_API.CommandReturns[code]}")

        if code in self.ssh_API.ErrorCodes:
            raise RuntimeError(f"Hexapod API error during {command}: {code} - {self.ssh_API.ErrorCodes[code]}")

        raise RuntimeError(f"Hexapod API error during {command}: unknown response code {code}")

    def _send_command(self, command, arguments=None):
        return self._decode_command_answer(self.ssh_API.SendCommand(command, arguments or []), command)
        

    def home(self):
        return self._send_command("HOME")
    
    def controlOn(self):
        return self._send_command("CONTROLON")

    def moveUp(self, step):
        return self._send_command("MOVE_PTP", [2.0, float(step), 0.0, 0.0, 0.0, 0.0, 0.0])
    def moveDown(self, step):
        return self._send_command("MOVE_PTP", [2.0, -float(step), 0.0, 0.0, 0.0, 0.0, 0.0])
    def moveLeft(self, step):
        return self._send_command("MOVE_PTP", [2.0, 0.0, float(step), 0.0, 0.0, 0.0, 0.0])
    def moveRight(self, step):
        return self._send_command("MOVE_PTP", [2.0, 0.0, -float(step), 0.0, 0.0, 0.0, 0.0]) 
    def moveOut(self, step):
        return self._send_command("MOVE_PTP", [2.0, 0.0, 0.0, float(step), 0.0, 0.0, 0.0])
    def moveIn(self, step):
        return self._send_command("MOVE_PTP", [2.0, 0.0, 0.0, -float(step), 0.0, 0.0, 0.0])
    def setSpeed(self, speed):
        return self._send_command("CFG_SPEED", [0.0, float(speed)]) #arguments: translationSpeed angularSpeed
    def resetPosition(self):
        return self._send_command("MOVE_SPECIFICPOS", [3.0]) 
        

  
