from tkinter import ttk
import tkinter as tk
import src.sampleMapper as sm
import threading



class SampleMappingTab:
    def __init__(self, parent, instruments, hexapodTab):
        self.parent = parent
        self.instruments = instruments
        self.hexapodTab = hexapodTab
        self.hexapod = self.hexapodTab.hexapod

        self.setup_ui()

    def setup_ui(self):
        SampleMappingTab = self.parent
    
        # Create a main frame to hold the canvas
        main_frame = tk.Frame(SampleMappingTab)
        main_frame.pack(fill=tk.BOTH, expand=1)
        
        # Create a canvas
        canvas = tk.Canvas(main_frame)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=1)
        
        # Add a scrollbar to the canvas
        scrollbar = tk.Scrollbar(main_frame, orient=tk.VERTICAL, command=canvas.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Configure the canvas
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Create a frame inside the canvas to hold the widgets
        inner_frame = tk.Frame(canvas)
        canvas.create_window((0, 0), window=inner_frame, anchor='nw')

        # Create LabelFrames for different sections
        control_frame = ttk.LabelFrame(inner_frame, text="Mapping Control")
        control_frame.grid(row=1, column=0, columnspan=4, padx=10, pady=5, sticky='nsew')

        output_frame = ttk.LabelFrame(inner_frame, text="Output and Status")
        output_frame.grid(row=2, column=0, columnspan=4, padx=10, pady=5, sticky='nsew')

        # Control section (in control_frame)
        self.startMapping = tk.Button(control_frame, text="Start Mapping", state="normal",
                                           command=lambda: self.begin_mapping())
        self.startMapping.grid(row=0, column=0, padx=10, pady=10)
        self.endMapping = tk.Button(control_frame, text="End Mapping", state="disabled",
                                         command=self.end_mapping())
        self.endMapping.grid(row=0, column=1, padx=10, pady=10)

        self.timePerStep = tk.IntVar(control_frame, 1)
        self.timePerStepLabel = tk.Label(control_frame, text="Time Per Step (s):")
        self.timePerStepInput = tk.Entry(control_frame, textvariable=self.timePerStep, state='disabled')
        self.timePerStepInput.grid(row=1, column=0, padx=10, pady=10)
        self.timePerStepLabel.grid(row=0, column=2, padx=10, pady=10)

        self.stepSize = tk.DoubleVar(control_frame, 0.1)
        self.stepSizeLabel = tk.Label(control_frame, text="Step Size (mm):")
        self.stepSizeInput = tk.Entry(control_frame, textvariable=self.stepSize, state='disabled')
        self.stepSizeInput.grid(row=1, column=1, padx=10, pady=10)
        self.stepSizeLabel.grid(row=0, column=3, padx=10, pady=10)

        # Output section (in output_frame)
        self.OutputLabel = tk.Label(output_frame, text="Status:")
        self.OutputLabel.grid(row=0, column=0)
        self.automationTxtBx = tk.Text(output_frame, height=8, font=('Arial', 16))
        self.automationTxtBx.grid(row=1, column=0, columnspan=4, padx=10, pady=10)

        self.fileStorageLocation = tk.StringVar(output_frame, "No Location Given")
        self.fileStorageLabel = tk.Label(output_frame, textvariable=self.fileStorageLocation)
        self.fileStorageButton = tk.Button(output_frame, text="Choose File Location", command=self.select_file_location)
        self.fileStorageLabel.grid(row=3, column=1, columnspan=2, padx=10, pady=10)
        self.fileStorageButton.grid(row=3, column=0, padx=10, pady=10)

        self.automationGraph = tk.Label(output_frame)
        self.automationGraph.grid(row=4, column=0, columnspan=4, padx=10, pady=10, sticky='nsew')

        # Update scrollregion when the size of the inner frame changes
        def _on_frame_configure(event):
            canvas.configure(scrollregion=canvas.bbox("all"))
        
        inner_frame.bind('<Configure>', _on_frame_configure)
        
        # Bind mouse wheel to scroll
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
    
    def update_hexapod(self):
        self.hexapod = self.hexapodTab.hexapod

    def select_file_location(self):
        from tkinter import filedialog
        file_path = filedialog.askdirectory()
        if file_path:
            self.fileStorageLocation.set(file_path)
            print(f"Selected file path: {file_path}")
        else:
            print("No file path selected.")
    
    def begin_mapping(self, begin=True):
        self.update_hexapod()
        if self.fileStorageLocation.get():
            print(f"File storage location: {self.fileStorageLocation.get()}")
            file_storage_location = self.fileStorageLocation.get()
        else:
            file_storage_location = None
        if self.hexapod is None:
            print("Hexapod not initialized.")
            return
        else:
            print("Starting sample mapping...")
            settings = (0.5, 0.02, file_storage_location) # TODO Gather settings from UI elements
            self.mapper = sm.SampleMapper(self.hexapod, self.instruments, None, settings) # This currently just uses the default settings.
            self.startMapping.config(state="disabled")
            self.endMapping.config(state="normal")
            self.timePerStepInput.config(state="normal")
            self.stepSizeInput.config(state="normal")
            self.automationTxtBx.insert(tk.END, "Sample mapping started...\n")

            self.mapper.debug_mode() # Blocking call for now, will run in thread later
    
    def end_mapping(self):
        pass # TODO Implement the logic to end sample mapping
    
    def update_mapping_status(self, message):
        self.automationTxtBx.insert(tk.END, message + "\n")
        self.automationTxtBx.see(tk.END)
        
