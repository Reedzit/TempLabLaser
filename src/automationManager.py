"""
Input: configuration information for the lasers and the hexapod
Output: None

The purpose of this is to sync up the laser and hexapod.
This should work as follows:
1. Verify connection to hexapod
2. Verify connection to laser
3. Verify connection to instruments
4. Verify connection to Linkam
5. Load in the settings
# Beginning of automation main loop
6. Move the hexapod to the correct position
7. Run the laser through all the frequencies
8. Go back to Step 6 until the hexapod has moved through all the angles
# End of automation main loop
9. Reset everything
10. Process Data
"""
import numpy as np
import threading
import time


class AutomationManager:
    def __init__(self, parent, instruments, hexapod, main_gui):
        self.instruments = instruments
        self.hexapod = hexapod
        self.parent = parent
        self.main_gui = main_gui
        self.AutomationThread = None
        self.laserGUI = self.main_gui.laserTabObject
        self.hexapodGUI = self.main_gui.hexapodTabObject

    def beginAutomation(self):
        self.automationThread = threading.Thread(target=self.runAutomationCycle, args=(False,)).start()
        print("Automation started in the background. You can continue using the GUI.")
    
    def endAutomation(self):
        if self.AutomationThread and self.AutomationThread.is_alive():
            print("Stopping automation...")
            self.AutomationThread.join(timeout=1)


    def runAutomationCycle(self, DEBUG_MODE=False):
        # First we need to load in the laser settings from begin automation
        self.laserGUI.begin_automation() # This will load in the laser settings and check if the laser is connected
        
        # We also need to make sure that the hexapod is connected
        if not self.hexapod:
            # If the hexapod is not passed in, we will try to get it from the main GUI
            self.hexapod = self.main_gui.hexapodTabObject.hexapod
            if not self.hexapod:
                raise RuntimeError("Hexapod is not connected. Please check the connection.")
        def rotate_point(point, rotationVector):
            copy_of_point = np.copy(point)
            # Convert from degrees to radians
            rotationVector = np.radians(rotationVector)

            # Create rotation matrices for each axis
            X_ROTATION_MATRIX = np.array([[1, 0, 0],
                                            [0, np.cos(rotationVector[0]), -np.sin(rotationVector[0])],
                                            [0, np.sin(rotationVector[0]), np.cos(rotationVector[0])]])
            Y_ROTATION_MATRIX = np.array([[np.cos(rotationVector[1]), 0, np.sin(rotationVector[1])],
                                            [0, 1, 0],
                                            [-np.sin(rotationVector[1]), 0, np.cos(rotationVector[1])]])
            Z_ROTATION_MATRIX = np.array([[np.cos(rotationVector[2]), -np.sin(rotationVector[2]), 0],
                                            [np.sin(rotationVector[2]), np.cos(rotationVector[2]), 0],
                                            [0, 0, 1]])

            rotated_point = np.array(Z_ROTATION_MATRIX @ Y_ROTATION_MATRIX @ X_ROTATION_MATRIX @ copy_of_point)
            return rotated_point

        def setupAutomation():
            laser_settings = self.laserGUI.laser_settings
            hexapod_settings = (float(self.hexapodGUI.degrees_of_sweep.get()), 
                                int(self.hexapodGUI.stepCount.get()),
                                [np.array([0,0,0])], # this should be the center, assuming that the hexapod is homed and calibrated. 
                                [np.array([float(self.hexapodGUI.pumpLaser.get()), 0, 0])]
                                )
            collection_settings = self.laserGUI.fileStorageLocation.get(), self.laserGUI.wait_for_convergence.get()
            return hexapod_settings, laser_settings, collection_settings

        def runLaser():
            """
            Should run the laser through all the frequencies.
            """
            self.AutomationThread = threading.Thread(target=self.instruments.automatic_measuring,
                                                         args=(laserSettings, filepath,
                                                               convergence_check))
            self.AutomationThread.start()
            while self.AutomationThread.is_alive():
                time.sleep(0.1)
                print("Laser is currently measuring...", end='\r')
            pass
        if not DEBUG_MODE:
            # Here we get all the variables ready to run through the automation tab.
            hexapodSettings, laserSettings, collectionSettings = setupAutomation()
            AUTOMATION_ROTATION_ANGLE, AUTOMATION_STEPS, hexapodCenter, pumpLaser = hexapodSettings
            freq, amp, offset, timeStep, stepCount, spot_distance, spacing = laserSettings
            filepath, convergence_check = collectionSettings
        else:
            print("DEBUG MODE ACTIVATED, ONLY HEXAPOD WILL MOVE")
            time.sleep(5)  # Give the user a moment to read the message
            laserSettings = None
            filepath = None
            convergence_check = None
            AUTOMATION_ROTATION_ANGLE, AUTOMATION_STEPS, hexapodCenter, pumpLaser = (20, 10,
                                                                                     [np.array([0, 0, 0])],
                                                                                     [np.array([0, 0, 0])])
        hexapod_rotation_stepList = np.linspace(0, AUTOMATION_ROTATION_ANGLE, AUTOMATION_STEPS)
        # Offset the rotation by half the total distance so that we can keep moving in 1 direction the whole time
        self.hexapod.rotate(np.array([0, 0, -AUTOMATION_ROTATION_ANGLE / 2]))
        pumpLaser.append(rotate_point(pumpLaser[-1], np.array([0, 0, -AUTOMATION_ROTATION_ANGLE / 2]))) # this is so that we can keep track of the laser position
        
        # Everything below here should be the main loop
        for i in range(len(hexapod_rotation_stepList)):
            theta = hexapod_rotation_stepList[i] - hexapod_rotation_stepList[i - 1]
            rotation_vector = np.array([0, 0, theta])
            self.hexapod.rotate(rotation_vector)
            pumpLaser.append(rotate_point(pumpLaser[-1], rotation_vector))

            adjustment_vector = pumpLaser[-2] - pumpLaser[-1]
            self.hexapod.translate(adjustment_vector)
            pumpLaser.append(pumpLaser[-1] + adjustment_vector)

            if not DEBUG_MODE:
                runLaser()
            else:
                print("DEBUG MODE ACTIVATED, NO LASER IN USE")

        # Reset Rotation and transformation
        self.hexapod.rotate([0, 0, -AUTOMATION_ROTATION_ANGLE / 2])
        pumpLaser.append(rotate_point(pumpLaser[-1], np.array([0, 0, -AUTOMATION_ROTATION_ANGLE / 2])))

        vector_for_reset = hexapodCenter[0][:2] - hexapodCenter[-1][:2]
        self.hexapod.translate(vector_for_reset, False)
