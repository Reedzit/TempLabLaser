import tkinter as tk

from src.hexapod.hexapodControl import HexapodControl


class HexapodTab:
    def __init__(self, parent):
        self.parent = parent
        self.setup_ui()
        self.hexapod = None

    def setup_ui(self):
        hexapodTab = self.parent
        self.connectBtn = tk.Button(hexapodTab, text="Connect to Hexapod", command=self.connect_hexapod)
        self.connectBtn.pack(padx=10, pady=10)
        self.homeBtn = tk.Button(hexapodTab, text="Home Hexapod", command=self.home_hexapod)
        self.homeBtn.pack(padx=10, pady=10)
        self.controlOnBtn = tk.Button(hexapodTab, text="Turn on Control (Press this after homing)",
                                      command=self.control_on_hexapod)
        self.controlOnBtn.pack(padx=10, pady=10)
        self.stepLabel = tk.Label(hexapodTab, text="Step Size (mm)")
        self.stepLabel.pack(padx=10, pady=5)
        self.stepInput = tk.Entry(hexapodTab)
        self.stepInput.pack(padx=10, pady=10)
        self.resetBtn = tk.Button(hexapodTab, text="Reset Position", command=self.reset_position)
        self.resetBtn.pack(padx=10, pady=10)

        bfTranslation = tk.Frame(hexapodTab)
        bfTranslation.columnconfigure(0, weight=1)
        bfTranslation.columnconfigure(1, weight=1)
        bfTranslation.columnconfigure(2, weight=1)
        bfTranslation.rowconfigure(0, weight=1)
        bfTranslation.rowconfigure(1, weight=1)
        bfTranslation.rowconfigure(2, weight=1)

        btn_up = tk.Button(bfTranslation, text="Up", command=self.move_up, font=('Arial', 18))
        btn_up.grid(row=0, column=1, sticky=tk.W + tk.E)

        btn_left = tk.Button(bfTranslation, text="Left", command=self.move_left, font=('Arial', 18))
        btn_left.grid(row=1, column=0, sticky=tk.W + tk.E)

        btn_down = tk.Button(bfTranslation, text="Down", command=self.move_down, font=('Arial', 18))
        btn_down.grid(row=1, column=1, sticky=tk.W + tk.E)

        btn_right = tk.Button(bfTranslation, text="Right", command=self.move_right, font=('Arial', 18))
        btn_right.grid(row=1, column=2, sticky=tk.W + tk.E)

        btn_in = tk.Button(bfTranslation, text="In", command=self.move_in, font=('Arial', 18))
        btn_in.grid(row=2, column=1, sticky=tk.W + tk.E)

        btn_out = tk.Button(bfTranslation, text="Out", command=self.move_out, font=('Arial', 18))
        btn_out.grid(row=3, column=1, sticky=tk.W + tk.E)

        bfTranslation.pack(fill='x', padx=20, pady=20)

        self.hexapodTextbox = tk.Text(hexapodTab, height=8, font=('Arial', 16))
        self.hexapodTextbox.pack(padx=10, pady=10)

    def connect_hexapod(self):
        try:
            self.hexapod = HexapodControl()
        except Exception as e:
            self.hexapodTextbox.insert(tk.END, "Unable to connect to hexapod.\n Error: " + str(e) + "\n")

    def run_hexapod_command(self, command, success_label):
        if self.hexapod is None or not self.hexapod.ssh_API:
            print("Not connected to hexapod")
            return

        try:
            response = command()
            self.hexapodTextbox.insert(tk.END, f"{success_label}: {response}\n")
        except Exception as error:
            self.hexapodTextbox.insert(tk.END, f"{success_label} failed: {error}\n")

    def home_hexapod(self):
        self.run_hexapod_command(lambda: self.hexapod.home(), "Home")

    def control_on_hexapod(self):
        self.run_hexapod_command(lambda: self.hexapod.controlOn(), "Control on")

    def move_up(self):
        self.run_hexapod_command(lambda: self.hexapod.moveUp(self.stepInput.get()), "Move up")

    def move_down(self):
        self.run_hexapod_command(lambda: self.hexapod.moveDown(self.stepInput.get()), "Move down")

    def move_left(self):
        self.run_hexapod_command(lambda: self.hexapod.moveLeft(self.stepInput.get()), "Move left")

    def move_right(self):
        self.run_hexapod_command(lambda: self.hexapod.moveRight(self.stepInput.get()), "Move right")

    def move_in(self):
        self.run_hexapod_command(lambda: self.hexapod.moveIn(self.stepInput.get()), "Move in")

    def move_out(self):
        self.run_hexapod_command(lambda: self.hexapod.moveOut(self.stepInput.get()), "Move out")

    def reset_position(self):
        self.run_hexapod_command(lambda: self.hexapod.resetPosition(), "Reset Position")
