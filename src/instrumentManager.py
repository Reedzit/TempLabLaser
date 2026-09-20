import datetime

import pyvisa
try:
    from .spoofedLaserData import spoof_laser_data
    from .instrument_configurations.fgConfig import fgConfig
    from . import statAnalysis
except ImportError:
    from spoofedLaserData import spoof_laser_data
    from instrument_configurations.fgConfig import fgConfig
    import statAnalysis
import numpy as np
import pandas as pd
import queue
import os
import threading

"""
This is a giga script. I am so sorry for this, but I don't want to split it up into multiple files.
It is a bit of a mess, but it works.
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
        self.workflow_lock = threading.Lock()


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
            real = float(self.lia.query("OUTP? 1"))
            imag = float(self.lia.query("OUTP? 2"))
            amplitude = float(self.lia.query("OUTP? 3"))
            #query1_time = time.perf_counter() - start_time

            #start_time = time.perf_counter()
            phase = float(self.lia.query("OUTP? 4"))
           # query2_time = time.perf_counter() - start_time

            #print(f"Query 1 took: {query1_time * 1000:.2f}ms")
            #print(f"Query 2 took: {query2_time * 1000:.2f}ms")
            return amplitude, phase, real, imag

        else:
            #print("No lock in amplifier connected")
            #return random.randint(0, 100), random.randint(0, 360) # For debugging
            time_since_last_measurement = datetime.datetime.now() - self.time_at_last_measurement
            if self.freq_for_spoofing == None:
                return False
            amplitude = 4.8
            phase = spoof_laser_data(self.freq_for_spoofing, time_since_last_measurement.total_seconds())
            real = amplitude * np.cos(np.deg2rad(phase))
            imag = amplitude * np.sin(np.deg2rad(phase))
            return amplitude, phase, real, imag

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

    @staticmethod
    def build_measurement_ranges(settings):
        """Build frequency, amplitude, and offset values for a sweep."""
        freq, amp, offset, _time_step, step_count, _spot_distance, spacing = settings
        if step_count < 1:
            raise ValueError("Step count must be at least 1")

        initial_freq, final_freq = freq
        initial_amp, final_amp = amp
        initial_offset, final_offset = offset
        if spacing == "linspace":
            frequency_range = np.linspace(initial_freq, final_freq, step_count)
        elif spacing == "logspace":
            if initial_freq <= 0 or final_freq <= 0:
                raise ValueError("Logarithmic frequency bounds must be positive")
            frequency_range = np.logspace(np.log10(initial_freq), np.log10(final_freq), step_count)
        else:
            raise ValueError(f"Unsupported frequency spacing: {spacing}")

        return (
            frequency_range.tolist(),
            np.linspace(initial_amp, final_amp, step_count).tolist(),
            np.linspace(initial_offset, final_offset, step_count).tolist(),
        )

    def measure_frequency_sweep(
        self,
        settings,
        convergence_check=False,
        degree=None,
        cancel_event=None,
        should_cancel=None,
        progress_callback=None,
    ):
        """Run one blocking frequency sweep and return every acquired sample."""
        _freq, _amp, _offset, time_step, _step_count, _spot_distance, _spacing = settings
        if time_step < 0:
            raise ValueError("Time per frequency must not be negative")

        frequency_range, amplitude_range, offset_range = self.build_measurement_ranges(settings)
        columns = [
            "Time", "index", "FrequencyIn", "AmplitudeOut", "PhaseOut",
            "RealOut", "ImagOut", "Convergence", "Degrees of Rotation",
        ]
        data = pd.DataFrame(columns=columns)

        def cancelled():
            return (
                (cancel_event is not None and cancel_event.is_set())
                or (should_cancel is not None and should_cancel())
            )

        for index, frequency in enumerate(frequency_range):
            if cancelled():
                break

            self.update_configuration(
                freq=frequency,
                amp=amplitude_range[index],
                offset=offset_range[index],
            )
            frequency_started = datetime.datetime.now()
            self.time_at_last_measurement = frequency_started
            frequency_rows = []

            while not cancelled():
                measured_at = datetime.datetime.now()
                measurement = self.take_measurement()
                if not measurement:
                    raise RuntimeError("Lock-in amplifier did not return a measurement")
                amplitude, phase, real, imag = measurement
                frequency_rows.append(phase)
                converged = statAnalysis.check_for_convergence(
                    pd.DataFrame({"PhaseOut": frequency_rows}), "PhaseOut"
                )
                data.loc[len(data)] = [
                    measured_at,
                    index,
                    frequency,
                    amplitude,
                    phase,
                    real,
                    imag,
                    converged,
                    degree if degree is not None else 0,
                ]

                elapsed = (measured_at - frequency_started).total_seconds()
                if (
                    len(frequency_rows) >= 2
                    and elapsed >= time_step
                    and (not convergence_check or converged)
                ):
                    if progress_callback is not None:
                        progress_callback(data, index + 1, len(frequency_range))
                    break

        return data

    def automatic_measuring(self, settings, filepath, convergence_check, degree=None, plot_code="Default"):
        """Run and persist a standalone sweep while preserving the legacy GUI API."""
        print("Automation Beginning!")
        _freq, _amp, _offset, _time_step, _step_count, spot_distance, _spacing = settings
        if not self.workflow_lock.acquire(blocking=False):
            self.automation_status = "error: instruments are in use by another workflow"
            print("Automation could not start because the instruments are already in use.")
            return pd.DataFrame()
        self.automation_running = True
        self.automation_status = "running"
        data = pd.DataFrame()
        cancel_requested = False

        def should_cancel():
            nonlocal cancel_requested
            if not self.automation_running:
                cancel_requested = True
                return True
            if not self.q.empty():
                self.q.get()
                cancel_requested = True
                return True
            return False

        def publish_progress(current_data, _completed, _total):
            while not self.automationQueue.empty():
                try:
                    self.automationQueue.get_nowait()
                except queue.Empty:
                    break
            self.automationQueue.put_nowait(current_data.copy())

        try:
            data = self.measure_frequency_sweep(
                settings,
                convergence_check=convergence_check,
                degree=degree,
                should_cancel=should_cancel,
                progress_callback=publish_progress,
            )
            self.automation_status = "cancelled" if cancel_requested else "completed"
        except Exception as e:
            print(f"Error during automation: {str(e)}")
            self.automation_status = f"error: {str(e)}"
        finally:
            print("Automation Ended!")
            self.automation_running = False
            if not data.empty and filepath:
                if degree is None:
                    name = f"measurement_{datetime.datetime.now().strftime('%m-%d_%H-%M')}_{spot_distance}um.csv"
                else:
                    name = f"{round(degree, 1)}_degrees.csv"
                full_path = os.path.join(filepath, name)
                os.makedirs(os.path.dirname(full_path), exist_ok=True)
                data.to_csv(full_path, index=False)
                print(f"Data saved to {full_path}")
            self.workflow_lock.release()
        return data
                


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
