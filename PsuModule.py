import pyvisa

class PowerSupply():
  voltage: float = 12
  current: float = 0.9
  psu = None
  
  def __init__(self) -> None:
    rm=pyvisa.ResourceManager()
    self.psu = rm.open_resource("TCPIP0::192.168.1.3::9221::SOCKET") #opens connection to power supply
    self.psu.encoding = 'UTF-8'
    self.psu.write(f"V1 {self.voltage};I1 {self.current};")

  def increase_voltage(self, increment: float):
    voltage = voltage + increment
    self.psu.write(f"V1 {voltage}")
  def decrease_voltage(self, decrement: float):
    voltage = voltage - decrement
    self.psu.write(f"V1 {voltage}")
  
    
