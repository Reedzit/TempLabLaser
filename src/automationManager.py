"""
Input: configuration information for the lasers and the hexapod
Output: None

The purpose of this is to sync up the laser and hexapod.
This should work as follows:
1. Verify connection to hexapod
# Beginning of automation main loop
2. Move the hexapod to the correct position
3. Run the laser through all the frequencies
4. Repeat
# End of automation main loop
5. Reset everything
6. Process Data
"""
import numpy as np
import threading


class AutomationManager:
    def __init__(self, parent, instruments, hexapod):
        self.AutomationThread = None
        try:
            if hexapod.status_dict:
                print(hexapod.status_dict)
            else:
                raise Exception("Hexapod not connected")
            self.hexapodGUI = parent.parent.hexapodTabObject
            self.laserGUI = parent.parent.laserTabObject

            self.instruments = instruments
            self.hexapod = hexapod
        except Exception as e:
            print("Error with general automation manager initialization: " + str(e))
            self.hexapod = None

    def runAutomationCycle(self, DEBUG_MODE=False):
        def setupAutomation():
            laser_settings = self.laserGUI.laser_settings
            hexapod_settings = (self.hexapodGUI.AUTOMATION_ROTATION_ANGLE, 
                                self.hexapodGUI.AUTOMATION_STEPS,
                                self.hexapodGUI.hexapodCenter, 
                                self.hexapodGUI.pumpLaser)
            collection_settings = self.laserGUI.filepath, self.laserGUI.convergence_check
            return hexapod_settings, laser_settings, collection_settings

        def runLaser():
            """
            Should run the laser through all the frequencies.
            """
            pass
        if not DEBUG_MODE:
            # Here we get all the variables ready to run through the automation tab.
            hexapodSettings, laserSettings, collectionSettings = setupAutomation()
            AUTOMATION_ROTATION_ANGLE, AUTOMATION_STEPS, hexapodCenter, pumpLaser = hexapodSettings
            freq, amp, offset, timeStep, stepCount, spot_distance, spacing = laserSettings
            filepath, convergence_check = collectionSettings
        else:
            print("DEBUG MODE ACTIVATED, ONLY HEXAPOD WILL MOVE")
            laserSettings = None
            filepath = None
            convergence_check = None
            AUTOMATION_ROTATION_ANGLE, AUTOMATION_STEPS, hexapodCenter, pumpLaser = (20, 10,
                                                                                     [np.array([0, 0, 0])],
                                                                                     [np.array([0, 0, 0])])
        hexapod_rotation_stepList = np.linspace(0, AUTOMATION_ROTATION_ANGLE, AUTOMATION_STEPS)
        # Offset the rotation by half the total distance so that we can keep moving in 1 direction the whole time
        self.hexapod.rotate(-AUTOMATION_ROTATION_ANGLE / 2, False)
        # Everything below here should be the main loop
        for i in range(len(hexapod_rotation_stepList)):
            theta = hexapod_rotation_stepList[i] - hexapod_rotation_stepList[i - 1]
            self.hexapod.rotate(theta)

            adjustment_vector = pumpLaser[-2][:2] - pumpLaser[-1][:2]
            self.hexapod.transform(adjustment_vector)
            self.hexapod.compoundMove()
            if not DEBUG_MODE:
                self.AutomationThread = threading.Thread(target=self.instruments.automatic_measuring,
                                                         args=(laserSettings, filepath,
                                                               convergence_check))
                self.AutomationThread.start()
            else:
                print("DEBUG MODE ACTIVATED, NO LASER IN USE")

        # Reset Rotation and transformation
        self.hexapod.rotate(-AUTOMATION_ROTATION_ANGLE / 2, False)

        vector_for_reset = hexapodCenter[0][:2] - hexapodCenter[-1][:2]
        self.hexapod.transform(vector_for_reset, False)
