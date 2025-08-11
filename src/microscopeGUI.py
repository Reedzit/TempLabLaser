import tkinter as tk
from tkinter import ttk
from instrumentManager import InstrumentInitialize
from src.gui_tabs import amplifierTab, hexapodTab, automationLaserTab, instrumentsTab, automationHexapodTab, automationManagementTab


# import pymeasure.instruments.srs.sr830 as lia

class MicroscopeGUI:
    instruments = InstrumentInitialize()
    hexapod = None

    def __init__(self, manager):

        def on_closing():
            if self.AutomationThread is not None:
                self.AutomationThread.stop()
            if self.GraphingThread is not None:
                self.GraphingThread.stop()
            window.destroy()
            quit()

        self.AutomationThread = None
        self.GraphingThread = None
        self.manager = manager

        # GUI global variables remain the same
        self.laser_gain = None
        self.file_path = None
        self.convergence_check = False
        self.step_count = 0
        self.laser_settings = None

        window = tk.Tk()
        window.geometry("1000x1000")
        window.title("Microscope GUI")

        # Create centered container frame with fixed size
        main_container = ttk.Frame(window)
        main_container.pack(expand=True)  # This centers the frame without making it expand

        # Create notebook with fixed size
        notebook = ttk.Notebook(main_container, width=1000, height=1000)
        notebook.pack(padx=20, pady=20)

        # Create frames for each tab
        laserAutomationFrame = ttk.Frame(notebook)
        hexapodAutomationFrame = ttk.Frame(notebook)
        generalAutomationFrame = ttk.Frame(notebook)

        # Add frames to notebook
        notebook.add(laserAutomationFrame, text='Laser Automation')
        notebook.add(hexapodAutomationFrame, text='Hexapod Automation')
        notebook.add(generalAutomationFrame, text='Automation Finalization')

        # Create tab objects
        self.laserTabObject = automationLaserTab.AutomationTab(laserAutomationFrame, self.instruments, self)
        self.laserTabObject.manager = manager

        self.hexapodTabObject = automationHexapodTab.HexapodAutomationTab(hexapodAutomationFrame, self.instruments, self)

        self.automationTab = automationManagementTab.AutomationManagerTab(generalAutomationFrame, self.instruments, self)

        window.after(100, self.laserTabObject.schedule_automation_update)

        window.protocol("WM_DELETE_WINDOW", on_closing)
        window.mainloop()
    