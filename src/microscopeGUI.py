import tkinter as tk
from tkinter import ttk
from instrumentInitialize import InstrumentInitialize
from src.gui_tabs import amplifierTab, hexapodTab, automationTab, instrumentsTab


# import pymeasure.instruments.srs.sr830 as lia

class MicroscopeGUI():
    instruments = InstrumentInitialize()
    hexapod = None

    def __init__(self):
        self.AutomationThread = None  # Thread for automation, If not in use, should be None
        self.GraphingThread = None  # Thread for updating the graph

        window = tk.Tk()
        window.geometry("1000x1000")
        window.title("Microscope GUI")
        notebook = ttk.Notebook(window)

        instrumentsFrame = tk.Frame(notebook)
        hexapodFrame = tk.Frame(notebook)
        amplifierFrame  = tk.Frame(notebook)
        automationFrame = tk.Frame(notebook)

        # The notebook contains the rest of the frames and puts them in an easy to shuffle spot.
        notebook.add(instrumentsFrame, text='Instruments')
        notebook.add(hexapodFrame, text='Hexapod')
        notebook.add(amplifierFrame, text='Lock In Amplifier')
        notebook.add(automationFrame, text='🤖Automation🤖')
        notebook.pack(expand=1, fill='both')

        ### Instruments Tab ###
        self.instrumentsTabObject = instrumentsTab.InstrumentsTab(instrumentsFrame, self.instruments)
        ### Hexapod Tab ###
        self.hexapodTabObject = hexapodTab.HexapodTab(hexapodFrame)
        ### Lock In Amplifier Tab ###
        self.amplifierTabObject = amplifierTab.AmplifierTab(amplifierFrame, self.instruments)
        ### Automation Tab ###
        self.automationTabObject = automationTab.AutomationTab(automationFrame, self.instruments)

        # This needs access to the main thread and that's why we call it here.
        window.after(100, self.automationTabObject.schedule_automation_update)
        window.mainloop()

if __name__ == '__main__':
    MicroscopeGUI()
