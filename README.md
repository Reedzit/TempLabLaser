# TEMP Lab Microscope 
This is a GUI that integrates function generators, a hexapod and in the future a lock in camera to automate the workflow for our setup. 

### Installation Instructions
1. Download the required modules using pip or conda. Run the following commands in your terminal
~~~
# for pip
pip install pyvisa matplotlib numpy tk subprocess paramiko
~~~
2.  To install Matlab Engine API you need to have Matlab installed on your machine. If it is installed on your machine run the following commands in your terminal:
~~~
# navigate to your matlab directory in the terminal
cd "matlabroot\extern\engines\python"
python -m pip install .
# if you run into issues with this there are troubleshooting steps here: https://www.mathworks.com/help/matlab/matlab_external/install-the-matlab-engine-for-python.html
~~~
3. To start the program, run "main.py" by pressing the play button if you are using VSCode or if you would like to run it from the terminal:
~~~
# navigate to the templablaser directory
cd "path to templablaser directory"
# it should say templablaser at the end of the current path like the following
PS C:\...\templablaser>
# run this command
python main.py
~~~

### Instruments Instructions
1. If you have run this program before and have a desired configuration saved, you can skip to step 4. Otherwise continue to step 2.
2. Under "Create Configuration", type in a good name for the function generator configuration you would like to set followed by the corresponding frequency, amplitude, and offset.
3. Click "Create Configuration".
4. Click the drop down box and select your desired configuration.
5. Click "Update Configuration".

### Hexapod Instructions
1. Connect to the hexapod
2. If you are turning on the controller for the first time, run the homing sequence, otherwise skip this step. (When the hexapod is homing you must wait for the stage to move all the way in (-z direction) and back out (+z direction). It will move back to the neutral position when it is finished.)
3. Turn on control.
4. Specify the step size (mm) and choose which direction you would like the stage to move.

### Lock In Amplifier Instructions
1. 
