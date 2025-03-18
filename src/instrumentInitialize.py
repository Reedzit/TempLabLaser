import pyvisa
from instrument_configurations.fgConfig import fgConfig

class InstrumentInitialize:
  FgConfigs = {}
  fgConfigNames = []
  current_fg_config: fgConfig = None

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
      self.lia.write(f"OUTX 1")
    except Exception as e: 
      print("An error occurred connecting to the lock in amplifier: ", e)
      self.lia = None

  def update_configuration(self):
    if self.fg: 
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

# ##########This is for 1kHz wave##########
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

