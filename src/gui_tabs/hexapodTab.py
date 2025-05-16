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

    def home_hexapod(self):
        if self.hexapod is None or not self.hexapod.ssh_API:
            print("Not connected to hexapod")
        else:
            response = self.hexapod.home()
            self.hexapodTextbox.insert(tk.END, f"Home: {response}\n")

    def control_on_hexapod(self):
        if self.hexapod is None or not self.hexapod.ssh_API:
            print("Not connected to hexapod")
        else:
            response = self.hexapod.controlOn()
            self.hexapodTextbox.insert(tk.END, f"Control on: {response}\n")

    def move_up(self):
        if self.hexapod is None or not self.hexapod.ssh_API:
            print("Not connected to hexapod")
        else:
            response = self.hexapod.moveUp(self.stepInput.get())
            self.hexapodTextbox.insert(tk.END, f"Move up: {response}\n")

    def move_down(self):
        if self.hexapod is None or not self.hexapod.ssh_API:
            print("Move Down")
        else:
            response = self.hexapod.moveDown(self.stepInput.get())
            self.hexapodTextbox.insert(tk.END, f"Move down: {response}\n")

    def move_left(self):
        if self.hexapod is None or not self.hexapod.ssh_API:
            print("Move Left")
        else:
            response = self.hexapod.moveLeft(self.stepInput.get())
            self.hexapodTextbox.insert(tk.END, f"Move left: {response}\n")

    def move_right(self):
        if self.hexapod is None or not self.hexapod.ssh_API:
            print("Move Right")
        else:
            response = self.hexapod.moveRight(self.stepInput.get())
            self.hexapodTextbox.insert(tk.END, f"Move right: {response}\n")

    def move_in(self):
        if self.hexapod is None or not self.hexapod.ssh_API:
            print("Move In")
        else:
            response = self.hexapod.moveIn(self.stepInput.get())
            self.hexapodTextbox.insert(tk.END, f"Move in: {response}\n")

    def move_out(self):
        if self.hexapod is None or not self.hexapod.ssh_API:
            print("Move Out")
        else:
            response = self.hexapod.moveOut(self.stepInput.get())
            self.hexapodTextbox.insert(tk.END, f"Move out: {response}\n")

    def reset_position(self):
        if self.hexapod is None or not self.hexapod.ssh_API:
            print("Reset Position")
        else:
            response = self.hexapod.resetPosition()
            self.hexapodTextbox.insert(tk.END, f"Reset Position: {response}\n")
