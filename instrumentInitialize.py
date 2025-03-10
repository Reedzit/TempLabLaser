#initialize the function generator
import pyvisa
from instrument_configurations.psuConfig import psuConfig
from instrument_configurations.fgConfig import fgConfig

class InstrumentInitialize:
  PSUConfigs = []
  FgConfigs = {}
  fgConfigNames = []
  current_psu_config: psuConfig = None
  current_fg_config: fgConfig = None
  def __init__(self):
    self.rm = pyvisa.ResourceManager()
    try:
      self.fg=self.rm.open_resource("TCPIP0::192.168.16.2::inst0::INSTR") #opens connection to function generator
      self.fg.encoding = 'latin-1'
    except Exception as e:
      print("An error occurred connecting to the function generator: ",e)
      self.fg = None
    #Not using a PSU for now
    # try:
    #   self.psu = self.rm.open_resource("TCPIP0::192.168.16.3::9221::SOCKET") #opens connection to power supply
    #   self.psu.encoding = 'UTF-8'
    # except Exception as e:
    #   print("An error occurred connecting to the power supply: ", e)
    #   self.psu = None

  def update_configuration(self):
    if self.psu: 
      self.psu.write(f"V1 {self.current_psu_config.voltage};I1 {self.current_psu_config.current}")
    else:
      print("No power supply connected. But this is the current configuration: ", self.current_psu_config)
    if self.fg: 
      self.fg.write(f"C2:BSWV WVTP,SQUARE,FRQ,{self.current_fg_config.frequency},AMP,5,OFST,2.5,DUTY,50")
      self.fg.write("C2:OUTP ON")
      self.fg.write(f"C1:BSWV WVTP,SINE,FRQ,{self.current_fg_config.frequency},AMP,{self.current_fg_config.amplitude},OFST,{self.current_fg_config.offset}")
      self.fg.write("C1:OUTP ON")
    else: 
      print("No function generator connected. But this is the current configuration: ", self.current_fg_config)

  def create_psu_config(self, name, voltage, current):
    self.current_psu_config = psuConfig(name, voltage, current)
    self.PSUConfigs.append(self.current_psu_config)

  def create_fg_config(self, name, frequency, amplitude, offset):
    self.current_fg_config = fgConfig(name, frequency, amplitude, offset)
    self.fgConfigNames.append(name)
    self.FgConfigs[name] = self.current_fg_config
    return self.current_fg_config
  
  def set_current_psu_config(self, name):
    for config in self.PSUConfigs:
      if config.name == name:
        self.current_psu_config = config
        break
      else: 
        print("No PSU configuration with that name found")
  
  def set_current_fg_config(self, name):
    if self.FgConfigs[name]:
      self.current_fg_config = self.FgConfigs[name]
      print(f"Current FG config set to: Amplitude-{self.current_fg_config.amplitude}, Frequency-{self.current_fg_config.frequency}, Offset-{self.current_fg_config.offset}")
    else: 
      print("No Function Generator configuration with that name found")



# channel2 for fg will always be twice the frequency of channel1

# rm=pyvisa.ResourceManager()
# try:
#   fg=rm.open_resource("TCPIP0::192.168.16.2::inst0::INSTR") #opens connection to function generator
# except Exception as e:
#   print("An error occurred connecting to the function generator: ",e)
# try:
#   psu = rm.open_resource("TCPIP0::192.168.16.3::9221::SOCKET") #opens connection to power supply
# except Exception as e:
#   print("An error occurred connecting to the power supply: ", e)
# psu.encoding = 'UTF-8'
# # print("this is psu output: ", psu.write("V1 12;I1 1.0"))
# print("this is psu output: ", psu.write("V1 2.9;I1 3.0"))
# fg.encoding = 'latin-1' #vi.write_raw called from the vi.write needs the encoding changed
# # print("Function generator identification: ", fg.query("*idn?"))
# # print("This is the test value: ",fg.query("*tst?")) # if output is 0 test is successful

# ##########This is for 1kHz wave##########
# fg.write("C1:BSWV WVTP,SINE,FRQ,1000,AMP,2.480,OFST,2.519")
# fg.write("C2:BSWV WVTP,SQUARE,FRQ,2000,AMP,5,OFST,2.5,DUTY,50")
# fg.write("C1:OUTP ON")
# fg.write("C2:OUTP ON")
# print("Execution Finished")
