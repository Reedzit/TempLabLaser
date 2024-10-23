import nidaqmx
import numpy as np
import matplotlib.pyplot as plt

with nidaqmx.Task() as task:
    # Add an analog input voltage channel
    task.ai_channels.add_ai_voltage_chan("Dev1/ai6")
    task.timing.cfg_samp_clk_timing(rate=200.0, sample_mode=nidaqmx.constants.AcquisitionType.CONTINUOUS, samps_per_chan=50)
    task.in_stream.input_buf_size = 100000
    try: 
      task.start()
      while True: 
        data = task.read(number_of_samples_per_channel=100)
        voltage_array = np.array(data)
        print(voltage_array)
        plt.plot(voltage_array)
        plt.ylabel('Voltage (mV)')
        plt.title('Thermistor Voltage')
        plt.pause(1)
        plt.close()
    except KeyboardInterrupt:
      print("aquisition stopped")
    finally:
      task.stop()