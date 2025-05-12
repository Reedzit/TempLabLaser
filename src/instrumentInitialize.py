import pyvisa
from instrument_configurations.fgConfig import fgConfig


class InstrumentInitialize:
    FgConfigs: dict[str, fgConfig] = {}
    fgConfigNames = []
    current_fg_config: fgConfig = None
    time_constants: list = [
        "10us",
        "30us",
        "100us",
        "300us",
        "1ms",
        "3ms",
        "10ms",
        "30ms",
        "100ms",
        "300ms",
        "1s",
        "3s",
        "10s",
        "30s",
        "100s",
        "300s",
        "1ks",
        "3ks",
        "10ks",
        "30ks",
    ]
    sensitivities: list = [
        "2nV/fA",
        "5nV/fA",
        "10nV/fA",
        "20nV/fA",
        "50nV/fA",
        "100nV/fA",
        "200nV/fA",
        "500nV/fA",
        "1uV/fA",
        "2uV/fA",
        "5uV/fA",
        "10uV/fA",
        "20uV/fA",
        "50uV/fA",
        "100uV/fA",
        "200uV/fA",
        "500uV/fA",
        "1mV/fA",
        "2mV/fA",
        "5mV/fA",
        "10mV/fA",
        "20mV/fA",
        "50mV/fA",
        "100mV/fA",
        "200mV/fA",
        "500mV/fA",
        "1V/fA"
    ]

    def __init__(self):
        self.rm = pyvisa.ResourceManager()
        print(f"Available resources: {self.rm.list_resources()}")
        try:
            # connect to function generator
            self.fg = self.rm.open_resource(
                "TCPIP0::192.168.16.2::inst0::INSTR")  # opens connection to function generator
            self.fg.encoding = 'latin-1'
        except Exception as e:
            print("An error occurred connecting to the function generator: ", e)
            self.fg = None
        try:
            # connect to lock in amplifier
            self.lia = self.rm.open_resource('GPIB0::8::INSTR')  # opens connection on channel 8
            self.lia.encoding = 'latin-1'
            # set sampling rate
            self.lia.write("SRAT 0")  # TODO: check if this is the correct sampling rate
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
        index_val = self.time_constants.index(time_constant)
        if index_val:
            if self.lia:
                self.lia.write(f'OFLT {index_val}')
                current = int(self.lia.query("OFLT?"))
                current = self.time_constants[current]
                return current
            else:
                print("No lock in amplifier connected")

    def increase_time_constant(self):
        if self.lia:
            current = int(self.lia.query("OFLT?"))
            current += 1  # increase the time constant by 1 step up
            value = self.time_constants[current]
            return value
        else:
            print("No lock in amplifier connected")

    def decrease_time_constant(self):
        if self.lia:
            current = int(self.lia.query("OFLT?"))
            current -= 1
            value = self.time_constants[current]
            return value
        else:
            print("No lock in amplifier connected")

    def set_gain(self, gain):
        index_val = self.sensitivities.index(gain)
        if index_val:
            if self.lia:
                self.lia.write(f'SENS {index_val}')
                current = int(self.lia.query("SENS?"))
                current = self.sensitivities[current]
                return current
            else:
                print("No lock in amplifier connected")

    def increase_gain(self):
        if self.lia:
            current = int(self.lia.query("SENS?"))
            current += 1
            value = self.sensitivities[current]
            return value
        else:
            print("No lock in amplifier connected")

    def decrease_gain(self):
        if self.lia:
            current = int(self.lia.query("SENS?"))
            current -= 1
            value = self.sensitivities[current]
            return value
        else:
            print("No lock in amplifier connected")

    def perform_measurement(self):
        if self.lia:
            # take data for 10 seconds then stop
            self.start_measurement()

    def update_configuration(self, freq = None, amp = None, offset = None):
        if self.fg and freq:
            print("Using dynamic values")
            self.fg.write(f"C2:BSWV WVTP,SQUARE,FRQ,{freq},AMP,5,OFST,2.5,DUTY,50")
            self.fg.write("C2:OUTP ON")
            if amp and offset:
                self.fg.write(
                    f"C1:BSWV WVTP,SINE,FRQ,{freq},AMP,{amp},OFST,{offset}")
                self.fg.write("C1:OUTP ON")
        elif self.fg:
            print("Using static values from config file")
            print(f"Setting fg channel 2 to be frequency {self.current_fg_config.frequency}")
            self.fg.write(f"C2:BSWV WVTP,SQUARE,FRQ,{self.current_fg_config.frequency},AMP,5,OFST,2.5,DUTY,50")
            self.fg.write("C2:OUTP ON")
            self.fg.write(
                f"C1:BSWV WVTP,SINE,FRQ,{self.current_fg_config.frequency},AMP,{self.current_fg_config.amplitude},OFST,{self.current_fg_config.offset}")
            self.fg.write("C1:OUTP ON")
        else:
            print("No function generator connected. But this is the current configuration: ", self.current_fg_config)

    def delete_fg_config(self, name):
        if self.FgConfigs[name]:
            del self.FgConfigs[name]
            self.fgConfigNames.remove(name)
            print(f"Function generator configuration {name} deleted")
        else:
            print("No Function Generator configuration with that name found")

    def create_fg_config(self, name, frequency, amplitude, offset):
        self.current_fg_config = fgConfig(name, frequency, amplitude, offset)
        self.fgConfigNames.append(name)
        self.FgConfigs[name] = self.current_fg_config
        return self.current_fg_config

    def set_current_fg_config(self, name):
        if self.FgConfigs[name]:
            self.current_fg_config = self.FgConfigs[name]
            print(
                f"Current FG config set to: Amplitude-{self.current_fg_config.amplitude}, Frequency-{self.current_fg_config.frequency}, Offset-{self.current_fg_config.offset}")
        else:
            print("No Function Generator configuration with that name found")

    def set_phase(self, phase):
        if self.fg:
            # self.fg.write(f"C2:BSWV WVTP,SQUARE,FRQ,{self.current_fg_config.frequency},AMP,5,OFST,2.5,DUTY,50,PHSE,{phase}")
            self.fg.write(f"C2:BSWV PHSE,{phase}")
            self.fg.write("C1:OUTP ON")
            self.fg.write("C2:OUTP ON")
            return phase
        else:
            print("No function generator connected")

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
# fg.write("C2:BSWV WVTP,SQUARE,FRQ,2000,AMP,5,OFST,2.5,DUTY,50,PHSE,90")
# fg.write("C1:OUTP ON")
# fg.write("C2:OUTP ON")
# fg.write("C2:BSWV PHSE,45")
# print(fg.query("C2:BSWV?"))
# print(fg.query("C2:BSWV PHSE?"))
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
