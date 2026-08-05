import pyvisa

class PowerMeterManager:
    def __init__(self):
        self.resource_name = "USB0::0x1313::0x8078::P0024195::INSTR"
        self.rm = pyvisa.ResourceManager()
        self.instrument = None

    def connect(self):
        try:
            self.instrument = self.rm.open_resource(self.resource_name)
            print(f"Connected to power meter: {self.resource_name}")
            return True
        except Exception as e:
            print(f"Failed to connect to power meter: {e}")
            return False

    def disconnect(self):
        if self.instrument:
            self.instrument.close()
            print("Disconnected from power meter.")
            self.instrument = None
            return True
        return False

    def read_power(self):
        if not self.instrument:
            print("Instrument not connected.")
            return None
        try:
            power_value = self.instrument.query("MEAS:POW?")
            return float(power_value)
        except Exception as e:
            print(f"Failed to read power: {e}")
            return None



if __name__ == "__main__":
    power_meter_manager = PowerMeterManager()
    power_meter_manager.connect()

    power = power_meter_manager.read_power()
    if power is not None:
        print(f"Measured Power: {power} W")

    power_meter_manager.disconnect()
