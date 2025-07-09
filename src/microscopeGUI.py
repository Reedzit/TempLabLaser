import tkinter as tk
from tkinter import ttk
from instrumentManager import InstrumentInitialize
from src.gui_tabs import amplifierTab, hexapodTab, automationTab, instrumentsTab, automationHexapodTab


# import pymeasure.instruments.srs.sr830 as lia

class MicroscopeGUI:
    instruments = InstrumentInitialize()
    hexapod = None

    def __init__(self, manager):
        self.AutomationThread = None  # Thread for automation, If not in use, should be None
        self.GraphingThread = None  # Thread for updating the graph
        self.manager = manager
        window = tk.Tk()
        window.geometry("1000x1000")
        window.title("Microscope GUI")
        notebook = ttk.Notebook(window)

        laserAutomationFrame = tk.Frame(notebook)
        hexapodAutomationFrame = tk.Frame(notebook)

        notebook.add(laserAutomationFrame, text='Laser Automation')
        notebook.add(hexapodAutomationFrame, text='Hexapod Automation')
        notebook.pack(expand=1, fill='both')

        ### Automation Tab ###
        self.automationTabObject = automationTab.AutomationTab(laserAutomationFrame, self.instruments)
        self.automationTabObject.manager = manager

        self.hexapodTabObject = automationHexapodTab.HexapodAutomationTab(hexapodAutomationFrame, self.instruments)

        # This needs access to the main thread and that's why we call it here.
        window.after(100, self.automationTabObject.schedule_automation_update)
        window.mainloop()

    def __del__(self):
        print("Closing GUI")
        self.automationTabObject.graph.close_plotting_process()


if __name__ == '__main__':
    MicroscopeGUI()
