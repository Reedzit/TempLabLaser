import pyvisa
from instrument_configurations.fgConfig import fgConfig

class InstrumentInitialize:
  FgConfigs: dict[str , fgConfig] = {}
  fgConfigNames = []
  current_fg_config: fgConfig = None
  time_constants: dict[str, int] = {
    "10us": 0,
    "30us": 1,
    "100us": 2,
    "300us": 3,
    "1ms": 4,
    "3ms": 5,
    "10ms": 6,
    "30ms": 7,
    "100ms": 8,
    "300ms": 9,
    "1s": 10,
    "3s": 11,
    "10s": 12,
    "30s": 13,
    "100s": 14,
    "300s": 15,
    "1ks": 16,
    "3ks": 17,
    "10ks": 18,
    "30ks": 19,
  }

  def __init__(self):
    self.rm = pyvisa.ResourceManager()
    try:
      # connect to function generator
      self.fg=self.rm.open_resource("TCPIP0::192.168.16.2::inst0::INSTR") #opens connection to function generator
      self.fg.encoding = 'latin-1'
    except Exception as e:
      print("An error occurred connecting to the function generator: ",e)
      self.fg = None
    try: 
      # connect to lock in amplifier
      self.lia = self.rm.open_resource('GPIB0::8::INSTR')   # opens connection on channel 8
      self.lia.encoding = 'latin-1'
      # set sampling rate
      self.lia.write("SRAT 0") # TODO: check if this is the correct sampling rate
      self.lia.write(f"OUTX 1")
    except Exception as e: 
      print("An error occurred connecting to the lock in amplifier: ", e)
      self.lia = None

  def take_measurement(self):
    if self.lia: 
      amplitude = self.lia.query("OUTP? 3")
      phase = self.lia.query("OUTP? 4")
      return amplitude, phase
    else: 
      print("No lock in amplifier connected")

  def stop_measurement(self):
    if self.lia: 
      self.lia.write("PAUS")
      # TODO: output data to file
    else: 
      print("No lock in amplifier connected")

  def auto_gain(self):
    if self.lia: 
      answer = self.lia.write("AGAN")
      if answer > 0:
        return "Auto gain successful"
    else: 
      return "No lock in amplifier connected"
    
  def set_time_constant(self, time_constant):
    index_val = self.time_constants.get(time_constant)
    if index_val: 
      if self.lia: 
        self.lia.write(f'OFLT {index_val}')

  def perform_measurement(self):
    if self.lia: 
      # take data for 10 seconds then stop 
      self.start_measurement()
      

  def update_configuration(self):
    if self.fg: 
      print(f"Setting fg channel 2 to be frequency {self.current_fg_config.frequency}")
      self.fg.write(f"C2:BSWV WVTP,SQUARE,FRQ,{self.current_fg_config.frequency},AMP,5,OFST,2.5,DUTY,50")
      self.fg.write("C2:OUTP ON")
      self.fg.write(f"C1:BSWV WVTP,SINE,FRQ,{self.current_fg_config.frequency},AMP,{self.current_fg_config.amplitude},OFST,{self.current_fg_config.offset}")
      self.fg.write("C1:OUTP ON")
    else: 
      print("No function generator connected. But this is the current configuration: ", self.current_fg_config)

  def create_fg_config(self, name, frequency, amplitude, offset):
    self.current_fg_config = fgConfig(name, frequency, amplitude, offset)
    self.fgConfigNames.append(name)
    self.FgConfigs[name] = self.current_fg_config
    return self.current_fg_config
  
  def set_current_fg_config(self, name):
    if self.FgConfigs[name]:
      self.current_fg_config = self.FgConfigs[name]
      print(f"Current FG config set to: Amplitude-{self.current_fg_config.amplitude}, Frequency-{self.current_fg_config.frequency}, Offset-{self.current_fg_config.offset}")
    else: 
      print("No Function Generator configuration with that name found")


##################### DEBUG #####################
# channel2 for fg will always be twice the frequency of channel1

# rm=pyvisa.ResourceManager()
# try:
#   fg=rm.open_resource("TCPIP0::192.168.16.2::inst0::INSTR") #opens connection to function generator
# except Exception as e:
#   print("An error occurred connecting to the function generator: ",e)
# fg.encoding = 'latin-1' #vi.write_raw called from the vi.write needs the encoding changed
# # print("Function generator identification: ", fg.query("*idn?"))
# # print("This is the test value: ",fg.query("*tst?")) # if output is 0 test is successful

# ##########This is for function generator 1kHz wave##########
# fg.write("C1:BSWV WVTP,SINE,FRQ,1000,AMP,2.480,OFST,2.519")
# fg.write("C2:BSWV WVTP,SQUARE,FRQ,2000,AMP,5,OFST,2.5,DUTY,50")
# fg.write("C1:OUTP ON")
# fg.write("C2:OUTP ON")
# print("Execution Finished")

########### test for lock in amplifier ###########
# rm = pyvisa.ResourceManager()
# try: 
#   lia = rm.open_resource('GPIB0::8::INSTR')   # opens connection on channel 8
# except Exception as e:
#   print("An error occurred connecting to the lock in amplifier: ", e)
# lia.encoding = 'latin-1'
# print("Lock in amplifier identification: ", lia.query("*idn?"))
## try sending a command 
# print(lia.read("OUTX?"))
# lia.write("OUTX 1")
# print(lia.read("OUTX?"))

