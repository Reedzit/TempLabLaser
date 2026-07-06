import src.hexapod.SYM_HexaPy as SYM_HexaPy
import tkinter as tk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from time import sleep
import threading
from matplotlib.figure import Figure
import numpy as np
import re


class HexapodAPIError(RuntimeError):
    def __init__(self, code, message, command=None):
        self.code = code
        self.command = command
        command_text = f" during {command}" if command else ""
        super().__init__(f"Hexapod API error{command_text}: {code} - {message}")


class HexapodControl():

    def __init__(self):
        self.ssh_API = None
        self.status_dict = None
        self.ready_for_commands = True
        self.last_error = None
        self.commandResolutionThread = None # This Thread will be used to listen to the hexapod and update the ready for commands flag
        self.connectHexapod()

    def _decode_command_answer(self, answer, command=None):
        try:
            code = int(str(answer).strip())
        except (TypeError, ValueError) as exc:
            raise HexapodAPIError(answer, "Unparseable API response", command) from exc

        if code == 0:
            return self.ssh_API.CommandReturns.get(code, "Success.")

        if code in self.ssh_API.CommandReturns:
            raise HexapodAPIError(code, self.ssh_API.CommandReturns[code], command)

        if code in self.ssh_API.ErrorCodes:
            raise HexapodAPIError(code, self.ssh_API.ErrorCodes[code], command)

        raise HexapodAPIError(code, "Unknown API response code", command)

    def _send_command(self, command, arguments=None, wait_for_motion=False):
        arguments = arguments or []

        while not self.ready_for_commands:
            sleep(0.05)

        if self.last_error:
            error = self.last_error
            self.last_error = None
            raise error

        answer = self.ssh_API.SendCommand(command, arguments)
        message = self._decode_command_answer(answer, command)

        if wait_for_motion:
            self.ready_for_commands = False
            self.waitForCommandResolution()
        else:
            self.ready_for_commands = True

        return message

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
        try:
            answer = self.ssh_API.STATE()
            self.status_dict = parse_symetrie_state(answer)
            print(self.status_dict)
        finally:
            self.ssh_API.waiting_for_reply = False

        error_number = self.status_dict.get("s_err_nr", 0)
        if error_number:
            message = self.ssh_API.ErrorCodes.get(error_number, "Unknown controller error")
            raise HexapodAPIError(error_number, message, "STATE")

        return answer

    def stop(self):
        return self._send_command("STOP")

    def checkStatus(self):
        self.getState()
        if self.status_dict is not None:
            # Check if the hexapod is ready for commands
            if self.status_dict["s_hexa_bits"]["Motion task running"] is False:
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
            try:
                while not self.checkStatus():
                    print("Hexapod is still busy, waiting for it to finish...", end='\r')
                    self.getState()
                    sleep(0.25)
                print("Hexapod is now ready for new commands.")
                self.ready_for_commands = True
            except HexapodAPIError as error:
                self.last_error = error
                print(error)
                self.ready_for_commands = True
            finally:
                self.commandResolutionThread = None  # Reset thread reference
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
        answer = self._send_command("HOME", wait_for_motion=True)
        print("Hexapod is now homed and ready for commands.", end='\r')
        return answer

    # API Documentation seems to have gone entirely missing, so I'm not entirely sure what this command does,
    # but some trial and error suggests it might be used to turn the hexapod on and off.

    def controlOn(self):
        return self._send_command("CONTROL ON", wait_for_motion=True)

    def controlOff(self):
        return self._send_command("CONTROL OFF", wait_for_motion=True)

    def translate(self, movement_vector=np.array([0.0, 0.0, 0.0]), magnitude=None):
        x, y, z = movement_vector
        if magnitude:
            normalizedMovementVector = (movement_vector / np.linalg.norm(movement_vector)) * magnitude
            x, y, z = normalizedMovementVector
        return self._send_command("MOVE_PTP", [2.0, x, y, z, 0.0, 0.0, 0.0], wait_for_motion=True)

    def rotate(self, rotation_vector=np.array([0.0, 0.0, 0.0])):
        alpha, beta, tau = rotation_vector # naming conventions come from
        return self._send_command("MOVE_PTP", [2.0, 0.0, 0.0, 0.0, alpha, beta, tau], wait_for_motion=True)

    def compoundMove(self, movement_vector=np.array([0.0, 0.0, 0.0]), rotation_vector=np.array([0.0, 0.0, 0.0]), magnitude=None):
        x, y, z = movement_vector
        alpha, beta, tau = rotation_vector
        if magnitude:
            normalizedMovementVector = (movement_vector / np.linalg.norm(movement_vector)) * magnitude
            x, y, z = normalizedMovementVector
        return self._send_command("MOVE_PTP", [2.0, x, y, z, alpha, beta, tau], wait_for_motion=True)

    # Shout out to Reed Zittler for this code too
    def setSpeed(self, speed):
        return self._send_command("CFG_SPEED", [0.0, float(speed)]) #arguments: translationSpeed angularSpeed

    def resetPosition(self):
        return self._send_command("MOVE_SPECIFICPOS", [3.0], wait_for_motion=True)
