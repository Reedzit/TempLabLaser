import datetime

import pyvisa
from spoofedLaserData import spoof_laser_data
from instrument_configurations.fgConfig import fgConfig
import statAnalysis
import numpy as np
import pandas as pd
import queue
import os

"""
This is a giga script. I am so sorry for this, but I don't want to split it up into multiple files.
It is a bit of a mess, but it works. I will try to refactor it in the future.
"""

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
        # First we need to initialize the queue for checking if we need to stop automation as well as one to update the GUI
        self.q = queue.Queue()
        self.time_at_last_measurement = datetime.datetime.now() # We need to use this both for automatic measuring,
        # but also for better data spoofing.

        # This one is LIFO because we want the GUI to only have up to date information about the most recent measurement
        self.automationQueue = queue.LifoQueue()
        self.automation_status = None
        self.automation_running = None
        self.freq_for_spoofing = None # This will only be used if debugging
        self.lia = None


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
            #start_time = time.perf_counter()
            amplitude = float(self.lia.query("OUTP? 3"))
            #query1_time = time.perf_counter() - start_time

            #start_time = time.perf_counter()
            phase = float(self.lia.query("OUTP? 4"))
           # query2_time = time.perf_counter() - start_time

            #print(f"Query 1 took: {query1_time * 1000:.2f}ms")
            #print(f"Query 2 took: {query2_time * 1000:.2f}ms")
            return amplitude, phase

        else:
            #print("No lock in amplifier connected")
            #return random.randint(0, 100), random.randint(0, 360) # For debugging
            time_since_last_measurement = datetime.datetime.now() - self.time_at_last_measurement
            if self.freq_for_spoofing == None:
                return False
            return 4.8, spoof_laser_data(self.freq_for_spoofing, time_since_last_measurement.total_seconds())

    def auto_gain(self):
        if self.lia:
            answer = self.lia.write("AGAN")
            if answer > 0:
                return "Auto gain successful"
            return None
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
                return None
        return None

    def increase_time_constant(self):
        if self.lia:
            current = int(self.lia.query("OFLT?"))
            current += 1  # increase the time constant by 1 step up
            value = self.time_constants[current]
            return value
        else:
            print("No lock in amplifier connected")
            return None

    def decrease_time_constant(self):
        if self.lia:
            current = int(self.lia.query("OFLT?"))
            current -= 1
            value = self.time_constants[current]
            return value
        else:
            print("No lock in amplifier connected")
            return None

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
                return None
        return None

    def increase_gain(self):
        if self.lia:
            current = int(self.lia.query("SENS?"))
            current += 1
            value = self.sensitivities[current]
            return value
        else:
            print("No lock in amplifier connected")
            return None

    def decrease_gain(self):
        if self.lia:
            current = int(self.lia.query("SENS?"))
            current -= 1
            value = self.sensitivities[current]
            return value
        else:
            print("No lock in amplifier connected")
            return None

    def update_configuration(self, freq = None, amp = None, offset = None):
        if freq:
            print("Using dynamic values")
            self.freq_for_spoofing = freq
            if self.fg:
                self.fg.write(f"C2:BSWV WVTP,SINE,FRQ,{freq},AMP,4,OFST,0,DUTY,50")
                self.fg.write("C2:OUTP ON")
                if amp and offset:
                    self.fg.write(
                        f"C1:BSWV WVTP,SINE,FRQ,{freq},AMP,{amp},OFST,{offset}")
                    self.fg.write("C1:OUTP ON")
            else:
                print("No function generator connected!\nYou were using Dynamic Values, so there is no configuration to show")
        elif self.fg:
            print("Using static values from config file")
            print(f"Setting fg channel 2 to be frequency {self.current_fg_config.frequency}")
            self.fg.write(f"C2:BSWV WVTP,SINE,FRQ,{self.current_fg_config.frequency},AMP,4,OFST,0,DUTY,50")
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

    def automatic_measuring(self, settings, filepath, convergence_check, degree = None, plot_code="Default"):
        print("Automation Beginning!")
        """
        This is the main culprit of the bad factoring. I probably won't ever fix it. If you are reading this, I am sorry.
        if you have questions. Feel free to reach out to me.
        This function will run the laser through all the frequencies and take measurements. I thought that would be smaller than it is.
        """


        #print(f"Waiting for convergence? {convergence_check}")
        self.automation_running = True
        self.automation_status = "running"
        measurements_per_config = 3
        freq, amp, offset, time_step, step_count, spot_distance, spacing = settings
        convergence = False

        # Initialize DataFrame
        data = pd.DataFrame(columns=["Time","index", "FrequencyIn", "AmplitudeOut", "PhaseOut", "Convergence", "Degrees of Rotation"])
        
        current_Step = 1
        try:
            initial_freq, final_freq = freq
            initial_amp, final_amp = amp
            initial_offset, final_offset = offset

            # Here is where we check if we're in logspace or linspace:
            if spacing == "linspace":
                freqRange = np.linspace(initial_freq, final_freq, step_count).tolist()
            elif spacing == "logspace":
                freqRange = np.logspace(np.log10(initial_freq), np.log10(final_freq), step_count).tolist()
            else:
                # If for some reason a broken spacing code is given, we'll default to linspace.
                print("Invalid spacing value. Using linspace instead.")
                freqRange = np.linspace(initial_freq, final_freq, step_count).tolist()
            ampRange = np.linspace(initial_amp, final_amp, step_count).tolist()
            offsetRange = np.linspace(initial_offset, final_offset, step_count).tolist()

            print(f"Number of steps planned: {step_count}")
            print(f"Frequency range: {freqRange}")
            idx = 0
            self.update_configuration(
                freq=freqRange[idx],
                amp=ampRange[idx],
                offset=offsetRange[idx]
            )
            self.time_at_last_measurement = datetime.datetime.now()
            while self.automation_running and idx < len(freqRange):
                if not self.q.empty():
                    print("Stop command received")
                    self.q.get()
                    break

                # If there's been no command to stop, we can continue with the loop as usual
                current_time = datetime.datetime.now()
                delta = current_time - self.time_at_last_measurement

                try:
                    amplitude, phase = self.take_measurement()
                except Exception as e:
                    print(f"Error during measurement: {str(e)}")
                    continue
                #print(f"Measurement {idx}: freq={freqRange[idx]}, amplitude={amplitude}, phase={phase}")

                # "Time","index", "FrequencyIn", "AmplitudeOut", "PhaseOut", "Convergence", "Degrees of Rotation"
                
                # Add data to DataFrame
                data.loc[len(data)] = [
                    current_time,
                    idx,
                    freqRange[idx],
                    amplitude,
                    phase,
                    convergence,
                    degree if degree is not None else 0  # Degrees of rotation, defaults to 0
                    ]

                convergence = statAnalysis.check_for_convergence(data, "PhaseOut")
                #print(
            #f"Debug values: delta={delta.total_seconds()}, time_step={time_step}, convergence_check={convergence_check}, convergence={convergence}")

                if ((delta.total_seconds() >= time_step and not convergence_check) or
                        (convergence_check and convergence and delta.total_seconds() >= time_step)):
                    print(f"Moving to next frequency. Current idx: {idx}")
                    self.automationQueue.put_nowait(data)
                    try:
                        # Update configuration for next frequency
                        self.update_configuration(
                            freq=freqRange[idx + 1],
                            amp=ampRange[idx + 1],
                            offset=offsetRange[idx + 1]
                        )
                    except IndexError as e:
                        print(f"Index error when trying to update configuration: {e}")
                        break

                    idx += 1
                    self.time_at_last_measurement = current_time
                    convergence = False
                    #diffusivityEstimate = statAnalysis.estimate_diffusivity(data, spot_distance)
                    #print(diffusivityEstimate)
                    #data.iloc[-1, data.columns.get_loc("DiffusivityEstimate")] = diffusivityEstimate

                    print(f"Updated idx: {idx}, total steps: {len(freqRange)}")

        except Exception as e:
            print(f"Error during automation: {str(e)}")
            self.automation_status = f"error: {str(e)}"
        finally:
            print("Automation Ended!")
            self.automation_running = False
            self.automation_status = "completed"
            # Save data to CSV
            if not data.empty and filepath:
                if degree is None:
                    name = f"measurement_data_{datetime.datetime.now}" + ".csv"
                else:
                    name = f"{degree}" + ".csv"
                full_path = os.path.join(filepath, name)
                os.makedirs(os.path.dirname(full_path), exist_ok=True)
                data.to_csv(full_path, index=False)
                print(f"Data saved to {full_path}")
                


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