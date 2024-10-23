#initialize the function generator
import pyvisa

rm=pyvisa.ResourceManager()
try:
  fg=rm.open_resource("TCPIP0::192.168.1.2::inst0::INSTR") #opens connection to function generator
except Exception as e:
  print("An error occurred connecting to the function generator: ",e)
try:
  psu = rm.open_resource("TCPIP0::192.168.1.3::9221::SOCKET") #opens connection to power supply
except Exception as e:
  print("An error occurred connecting to the power supply: ", e)
psu.encoding = 'UTF-8'
print("this is psu output: ", psu.write("V1 12;I1 1.0"))
fg.encoding = 'latin-1' #vi.write_raw called from the vi.write needs the encoding changed
# print("Function generator identification: ", fg.query("*idn?"))
# print("This is the test value: ",fg.query("*tst?")) # if output is 0 test is successful

##########This is for 1kHz wave##########
fg.write("C1:BSWV WVTP,SINE,FRQ,1000,AMP,2.480,OFST,2.519")
fg.write("C2:BSWV WVTP,SQUARE,FRQ,2000,AMP,5,OFST,2.5,DUTY,50")
fg.write("C1:OUTP ON")
fg.write("C2:OUTP ON")
print("Execution Finished")
