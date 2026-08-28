import src.hexapod.SYM_HexaPy as SYM_HexaPy
import tkinter as tk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from time import sleep
import threading
from matplotlib.figure import Figure
import numpy as np
import re

from src.hexapod.laserGeometry import rotation_compensation_for_face_spot
from src.hexapod.laserPositionStore import load_laser_position, save_laser_position

class HexapodControl():

    def __init__(self):
        self.ssh_API = None
        self.status_dict = None
        self.laser_position = load_laser_position()
        self.position = None
        self.ready_for_commands = False
        self.commandResolutionThread = None # This Thread will be used to listen to the hexapod and update the ready for commands flag
        self.connectHexapod()

    def set_laser_position(self, position):
        self.laser_position = save_laser_position(position)
        return self.laser_position

    def getState(self):
        if self.ssh_API.waiting_for_reply:
            print("Hexapod is currently busy, waiting for the current command to resolve.")
            while self.ssh_API.waiting_for_reply:
                print("API is still busy, waiting for it to finish...")
                sleep(0.25)
        self.ssh_API.waiting_for_reply = True
        """
        Hexapod status dictionary format:
        - 's_hexa': int — raw system status bits
        - 's_hexa_bits': dict — decoded bits from s_hexa:
            {'Error', 'System initialized', 'Control on', 'In position', 'Motion task running',
            'Home task running', 'Home complete', 'Home virtual', 'Phase found', 'Brake on',
            'Motion restricted', 'Power on encoders', 'Power on limit switches', 'Power on drives'}
        - 's_action': str — current action, e.g. '4:Stop'
        - 's_uto_tx', ..., 's_uto_rz': float — user target offsets (translations/rotations)
        - 's_mtp_tx', ..., 's_mtp_rz': float — motion target positions
        - 's_ax_1' to 's_ax_6': int — raw axis status bits for axes 1–6
        - 's_ax_1_bits' to 's_ax_6_bits': dict — decoded bits for each axis:
            {'Error', 'Control on', 'In position', 'Motion task running', 'Home task running',
            'Home complete', 'Phase found', 'Brake on', 'Home hardware input',
            'Negative hardware limit switch', 'Positive hardware limit switch',
            'Software limit reached', 'Following error', 'Drive fault'}
        - 's_pos_ax_1' to 's_pos_ax_6': str — position feedback per axis (may be 'nan')
        - 's_dio_1' to 's_dio_8': int — digital input/output values
        - 's_ai_1' to 's_ai_8': int — analog input values
        - 's_cycle': int — internal cycle counter
        - 's_index': int — internal index counter
        - 's_err_nr': int — error code (0 = no error)
        - 's_reserve_01' to 's_reserve_04': int — reserved fields (unknown purpose)
        """
        def parse_symetrie_state(state_str):
            status = {}

            # Split the data into lines
            lines = state_str.strip().split('\n')

            key = None
            bitfield_lines = []
            axis_state_prefix = 's_ax_' # this seems to just be hardcoded into the response
            current_axis = None

            for line in lines:
                line = line.strip()

                # Bitfield-style continuation (e.g., indented lines under s_hexa or s_ax_*)
                # Go through each line and identify if it follows the bitfield format
                if re.match(r'^\d+:\s', line):
                    bitfield_lines.append(line)
                    continue

                # Save the previous bitfield block
                if bitfield_lines:
                    if key:
                        status[key + '_bits'] = parse_bitfield(bitfield_lines)
                    bitfield_lines = []

                # Parse simple key=value
                if '=' in line:
                    key, val = line.split('=', 1)
                    key = key.strip()
                    val = val.strip()
                    # Try to parse as float or int
                    try:
                        if '.' in val or 'e' in val:
                            val = float(val)
                        else:
                            val = int(val)
                    except ValueError:
                        pass  # Leave as string

                    status[key] = val

            # Final bitfield block (e.g., last axis)
            if bitfield_lines and key:
                status[key + '_bits'] = parse_bitfield(bitfield_lines)

            return status

        def parse_bitfield(lines):
            """Parse lines like '0: Error' into a dict."""
            result = {}
            for line in lines:
                match = re.match(r'^(\d+):\s+(.*)', line.strip())
                if match:
                    val, label = match.groups()
                    result[label.strip()] = bool(int(val))
            return result
        answer = self.ssh_API.STATE()
        self.status_dict = parse_symetrie_state(answer)
        print(self.status_dict)
        self.ssh_API.waiting_for_reply = False
        if answer in self.ssh_API.CommandReturns.keys():
            answer = self.ssh_API.CommandReturns[answer]
        elif answer in self.ssh_API.ErrorCodes.keys():
            answer = self.ssh_API.ErrorCodes[answer]
        return answer

    def stop(self):
        self.ready_for_commands = False
        answer = self.ssh_API.SendCommand("C_STOP")
        self.waitForCommandResolution()
        answer = int(answer.strip())
        if answer in self.ssh_API.CommandReturns.keys():
            answer = self.ssh_API.CommandReturns[answer]
        return answer

    def checkStatus(self):
        self.getState()
        if self.status_dict is not None:
            # Check if the hexapod is ready for commands
            status_bits = self.status_dict["s_hexa_bits"]
            command_running = (
                status_bits.get("Motion task running", False)
                or status_bits.get("Home task running", False)
            )
            if not command_running:
                self.ready_for_commands = True
                return True
            else:
                self.ready_for_commands = False
                return False
        else:
            print("Status dictionary is empty. Please call getState() first.")
            return None

    def waitForCommandResolution(self):
        """
        Non-blocking: Starts a background thread that updates self.ready_for_commands
        when the hexapod is ready for new commands.
        The calling code should check self.ready_for_commands as needed.
        """
        print("Waiting for hexapod to finish executing the current command...")
        def loop():
            while not self.checkStatus():
                print("Hexapod is still busy, waiting for it to finish...", end='\r')
                self.getState()
                sleep(0.25)
            self.logPosition()
            print("Hexapod is now ready for new commands.")
            self.ready_for_commands = True
            self.commandResolutionThread = None  # Reset thread reference
            return
        if not self.commandResolutionThread or not self.commandResolutionThread.is_alive():
            self.commandResolutionThread = threading.Thread(target=loop, daemon=True)
            self.commandResolutionThread.start()
        else:
            print("A command resolution thread is already running.")
        

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
        self.ready_for_commands = False
        self.waitForCommandResolution()

    def home(self):
        print("Homing the hexapod, this may take a while...")

        self.ready_for_commands = False
        answer = int(self.ssh_API.SendCommand("HOME").strip())
        print(f"This is the code for the home command: {self.ssh_API.CommandReturns[answer]}")

        # Homing takes forever, so we need to wait for it to finish before we can send any more commands.
        self.waitForCommandResolution()
        print("Hexapod is now homed and ready for commands.", end='\r')
        self.logPosition() #in theory it's at 0,0,0 here, but we may as well log it
        return True

    # API Documentation seems to have gone entirely missing, so I'm not entirely sure what this command does,
    # but some trial and error suggests it might be used to turn the hexapod on and off.

    def controlOn(self):
        self.ready_for_commands = False
        answer = int(self.ssh_API.SendCommand("CONTROL ON").strip())
        self.waitForCommandResolution()
        print(f"This is the code for the control on command: {self.ssh_API.CommandReturns[answer]}")

    def controlOff(self):
        self.ready_for_commands = False
        answer = int(self.ssh_API.SendCommand("CONTROL OFF").strip())
        self.waitForCommandResolution()
        print(f"This is the code for the control off command: {self.ssh_API.CommandReturns[answer]}")

    def translate(self, movement_vector=np.array([0.0, 0.0, 0.0]), magnitude=None):
        self.ready_for_commands = False
        x, y, z = movement_vector
        if magnitude:
            normalizedMovementVector = (movement_vector / np.linalg.norm(movement_vector)) * magnitude
            x, y, z = normalizedMovementVector
        answer = self.ssh_API.SendCommand("MOVE_PTP", [2.0, x, y, z, 0.0, 0.0, 0.0])
        answer = int(answer.strip())
        self.waitForCommandResolution()

        if answer in self.ssh_API.CommandReturns.keys():
            answer = self.ssh_API.CommandReturns[answer]
        elif answer in self.ssh_API.ErrorCodes.keys():
            answer = self.ssh_API.ErrorCodes[answer]
        self.logPosition()  # Update the position after the move
        return answer

    def rotate(self, rotation_vector=np.array([0.0, 0.0, 0.0])):
        self.ready_for_commands = False
        alpha, beta, tau = rotation_vector # naming conventions come from
        answer = self.ssh_API.SendCommand("MOVE_PTP", [2.0, 0.0, 0.0, 0.0, alpha, beta, tau])
        answer = int(answer.strip())
        self.waitForCommandResolution()        
        if answer in self.ssh_API.CommandReturns.keys():
            answer = self.ssh_API.CommandReturns[answer]
        elif answer in self.ssh_API.ErrorCodes.keys():
            answer = self.ssh_API.ErrorCodes[answer]
        self.logPosition()  # Update the position after the move
        return answer

    def rotateAroundLaser(self, rotation_vector=np.array([0.0, 0.0, 0.0])):
        if self.laser_position is None:
            raise ValueError("The laser position has not been calibrated.")

        rotation_vector = np.asarray(rotation_vector, dtype=float)
        compensation = rotation_compensation_for_face_spot(
            self.laser_position,
            self.position,
            rotation_vector,
        )
        return self.compoundMove(compensation, rotation_vector)

    def compoundMove(self, movement_vector=np.array([0.0, 0.0, 0.0]), rotation_vector=np.array([0.0, 0.0, 0.0]), magnitude=None):
        self.ready_for_commands = False
        x, y, z = movement_vector
        alpha, beta, tau = rotation_vector
        if magnitude:
            normalizedMovementVector = (movement_vector / np.linalg.norm(movement_vector)) * magnitude
            x, y, z = normalizedMovementVector
        answer = self.ssh_API.SendCommand("MOVE_PTP", [2.0, x, y, z, alpha, beta, tau])
        answer = int(answer.strip())
        self.waitForCommandResolution()
        if answer in self.ssh_API.CommandReturns.keys():
            answer = self.ssh_API.CommandReturns[answer]
        elif answer in self.ssh_API.ErrorCodes.keys():
            answer = self.ssh_API.ErrorCodes[answer]
        self.logPosition()  # Update the position after the move
        return answer

    # Shout out to Reed Zittler for this code too
    def setSpeed(self, speed):
        self.ready_for_commands = False
        answer = self.ssh_API.SendCommand("CFG_SPEED", [0.0, float(speed)]) #arguments: translationSpeed angularSpeed
        answer = int(answer.strip())
        self.waitForCommandResolution()
        if answer in self.ssh_API.CommandReturns.keys():
            answer = self.ssh_API.CommandReturns[answer]
        elif answer in self.ssh_API.ErrorCodes.keys():
            answer = self.ssh_API.ErrorCodes[answer]
        return answer

    def resetPosition(self):
        self.ready_for_commands = False
        answer = self.ssh_API.SendCommand("MOVE_SPECIFICPOS", [3.0])
        answer = int(answer.strip())
        self.waitForCommandResolution()
        if answer in self.ssh_API.CommandReturns.keys():
            answer = self.ssh_API.CommandReturns[answer]
        elif answer in self.ssh_API.ErrorCodes.keys():
            answer = self.ssh_API.ErrorCodes[answer]
        return answer

    def logPosition(self):
        try:
            x = self.status_dict.get("s_mtp_tx", None)
            y = self.status_dict.get("s_mtp_ty", None)
            z = self.status_dict.get("s_mtp_tz", None)

            alpha = self.status_dict.get("s_mtp_rx", None)
            beta = self.status_dict.get("s_mtp_ry", None)
            tau = self.status_dict.get("s_mtp_rz", None)
            self.position = (x, y, z, alpha, beta, tau)
        except Exception as e:
            print(f"Error occurred while logging position: {e}")
            self.position = None
        return self.position
