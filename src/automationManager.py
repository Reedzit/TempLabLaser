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
import os
import datetime
import pandas as pd


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

    def runFocussingCycle(self):
        print("Running focussing cycle... Autostopping is NOT supported yet. Please stop the cycle manually.", end='\r')

        if not self.hexapod:
            # If the hexapod is not passed in, we will try to get it from the main GUI
            self.hexapod = self.main_gui.hexapodTabObject.hexapod
            if not self.hexapod:
                raise RuntimeError("Hexapod is not connected. Please check the connection.")

        if self.AutomationThread and self.AutomationThread.is_alive():
            print("Automation Thread is in use. Clearing automation thread and starting new one...")
            self.AutomationThread.join(timeout=1)

            # The conical spiral search will be running on a seperate thread so that it can be shut off
            # from the GUI whenever it's reach the focussing point.

        def conical_spiral_search(num_steps):
            """
            This should perform the following loop until it no longer can.
            1. Increase the tilt angle.
            2. Generate a set of vectors that are tilted from normal axis along a range of axis.
            3. Align the hexapod to those vectors.
            4. Repeat until the hexapod has reached the focussing point.
            """
            TILT_CHANGE = 1

            n0 = np.array([0, 0, 1])
            # self.hexapod.home()
            while self.hexapod.ready_for_commands is False:
                time.sleep(0.1)

            def generate_tilted_vectors(n0, tilt_deg, num_steps):
                tilt_rad = np.deg2rad(tilt_deg)
                n0 = n0 / np.linalg.norm(n0)  # Ensure it's a unit vector

                # Find a vector orthogonal to n0
                if np.allclose(n0, [0, 0, 1]):
                    u = np.array([1, 0, 0])
                else:
                    u = np.cross(n0, [0, 0, 1])
                    u /= np.linalg.norm(u)

                # Rodrigues' rotation formula to sweep around n0
                vectors = []
                for phi in np.linspace(0, 2 * np.pi, num_steps, endpoint=False):
                    # Rotate u around n0 by phi
                    R = rotation_matrix(n0, phi)
                    dir = R @ (np.cos(tilt_rad) * n0 + np.sin(tilt_rad) * u)
                    vectors.append(dir)
                return vectors

            def rotation_matrix(axis, angle):
                # Rodrigues' rotation formula
                axis = axis / np.linalg.norm(axis)
                K = np.array([[0, -axis[2], axis[1]],
                              [axis[2], 0, -axis[0]],
                              [-axis[1], axis[0], 0]])
                return np.eye(3) + np.sin(angle) * K + (1 - np.cos(angle)) * (K @ K)

            def align_hexapod_normal(n0, n1):
                """
                Because the math on how we do the sweep is using the normal vectors,
                we now need to convert those vectors into euler angle that we can use to rotate the hexapod.

                The steps for that are going to be:
                1. Find the rotation matrix between the vector and the normal vector.
                2. Convert that rotation matrix into euler angles.
                3. Rotate the hexapod by those angles.
                """

                def rotation_to_align_normal(n0, n1):
                    z = n0
                    n_target = n1 / np.linalg.norm(n1)

                    axis = np.cross(z, n_target)
                    if np.linalg.norm(axis) < 1e-8:
                        # Already aligned (or opposite)
                        if np.dot(z, n_target) > 0:
                            return np.eye(3)  # No rotation
                        else:
                            # 180° rotation around X or Y (arbitrary axis perpendicular to z)
                            return rotation_matrix(np.array([1, 0, 0]), np.pi)

                    axis = axis / np.linalg.norm(axis)
                    angle = np.arccos(np.clip(np.dot(z, n_target), -1.0, 1.0))
                    return rotation_matrix(axis, angle)

                def rotation_matrix_to_euler_angles(R):
                    if abs(R[2, 0]) != 1:
                        y = -np.arcsin(R[2, 0])
                        x = np.arctan2(R[2, 1] / np.cos(y), R[2, 2] / np.cos(y))
                        z = np.arctan2(R[1, 0] / np.cos(y), R[0, 0] / np.cos(y))
                    else:
                        # Gimbal lock
                        z = 0
                        if R[2, 0] == -1:
                            y = np.pi / 2
                            x = z + np.arctan2(R[0, 1], R[0, 2])
                        else:
                            y = -np.pi / 2
                            x = -z + np.arctan2(-R[0, 1], -R[0, 2])
                    return np.rad2deg([x, y, z])

                R = rotation_to_align_normal(n0, n1)
                angles = rotation_matrix_to_euler_angles(R)
                x, y, z = angles
                rotation_vector = np.array([x, y, z])

                # wait until there is a signal for movement being ready.
                while self.hexapod.ready_for_commands is False:
                    time.sleep(0.1)
                self.hexapod.rotate(rotation_vector)

            # This is the main loop for the automation. Everything above basically just sets everthing up.
            current_angle = 0  # This is only used for the printout
            while True:
                tilted_vectors = generate_tilted_vectors(n0, TILT_CHANGE, num_steps)
                current_angle += TILT_CHANGE
                print("Tilt angle: ", current_angle)
                for vector in tilted_vectors:
                    print("Aligning to vector: ", vector)
                    print(f"This is step {tilted_vectors.index(vector) + 1} of {num_steps} for this angle")
                    align_hexapod_normal(n0, vector)
                    n0 = vector

        self.automationThread = threading.Thread(target=conical_spiral_search, args=(12,)).start()

    def endFocussing(self):
        if self.AutomationThread.is_alive():
            print("Stopping automation...")
            self.AutomationThread.join(timeout=1)
            self.AutomationThread = None
            print("Automation stopped.")
            print("Stopping Hexapod...")
            self.hexapod.stop()
            print("Hexapod stopped.")
        else:
            print("No focussing is running.")

    def runAutomationCycle(self, DEBUG_MODE=False):
        # First we need to load in the laser settings from begin automation
        self.laserGUI.begin_automation()  # This will load in the laser settings and check if the laser is connected        # We also need to make sure that the hexapod is connected
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

        def collectAutomationValues():
            laser_settings = self.laserGUI.laser_settings
            hexapod_settings = (float(self.hexapodGUI.degrees_of_sweep.get()),
                                int(self.hexapodGUI.stepCount.get()),
                                [np.array([0, 0, 0])],
                                # this should be the center, assuming that the hexapod is homed and calibrated.
                                [np.array([float(self.hexapodGUI.pumpLaser.get()), 0, 0])]
                                )
            collection_settings = self.laserGUI.fileStorageLocation.get(), self.laserGUI.wait_for_convergence.get()

            # Here we'll create the temporary folder where all the chunks will be stored
            file_location = collection_settings[0]
            #file_name = "automationBatches"
            #os.mkdir(os.path.join(file_location, file_name))

            #collection_settings = os.path.join(file_location, file_name), collection_settings[1]
            return hexapod_settings, laser_settings, collection_settings

        def cleanUpFiles(collection_tuple):
            # The main point here is to just stitch together the files
            print("cleaning files")

            # Step 1: get to the correct working directory
            working_directory = os.getcwd()  # We're saving this so we can go back to the original directory later
            file_location = collection_tuple[0]
            os.chdir(file_location)

            # Step 2: get all the files that we want to stitch together
            files = os.listdir(file_location)
            files = [file for file in files if
                     file.endswith(".csv")]  # This just removes anything that wasn't saved correctly
            files.sort(key=lambda x: os.path.getmtime(x),
                       reverse=True)  # We want to sort the files from newest to oldest
            print(files)

            # Step 3: take the newest file and add it onto the next newest to it. Delete the first file.
            # Then, repeat until all the files are done.
            print("Now stitching together the files...")
            while len(files) > 1:
                time.sleep(0.1)
                print(f"\rStitching... files left: {len(files) - 1}", end="")
                file1 = files.pop(0)  # This is the newest file
                file2 = files.pop(0)  # This is the next newest file

                d1 = pd.read_csv(file1)  # This is the dataframe corresponding to the newest file
                d2 = pd.read_csv(file2)  # This is the dataframe corresponding to the next newest file

                os.remove(file1)  # Here we remove the files
                os.remove(file2)  # Since we've read them, we no longer need them.

                d2 = pd.concat((d2, d1),
                               ignore_index=True)  # now we add the newest file at the bottom of the second-newest file
                d2.to_csv(str(datetime.datetime.now()) + ".csv", index=False)  # This will be the new newest file.

                # Now we need to update the list of files.
                files = os.listdir(file_location)
                files = [file for file in files if
                         file.endswith(".csv")]  # This just removes anything that wasn't saved correctly
                files.sort(key=lambda x: os.path.getmtime(x),
                           reverse=True)  # We want to sort the files from newest to oldest

            # Step 4: We now need to move the file to the originally requested location and delete the temp folder
            name = "../automation_data" + datetime.datetime.now().strftime('%Y-%m-%d_%H-%M') + ".csv"
            os.rename(files[0], name)  # we move the file up by 1 folder
            # Step 5: Go back to the original working directory
            os.chdir(working_directory)
            # Step 6: Delete the temp folder
            time.sleep(1)
            os.rmdir(os.path.join(file_location))
            print("Stitching complete.")

        def runLaser(degree):
            """
            Should run the laser through all the frequencies.
            """
            self.AutomationThread = threading.Thread(target=self.instruments.automatic_measuring,
                                                     args=(laserSettings, filepath,
                                                           convergence_check, degree))
            self.AutomationThread.start()
            while self.AutomationThread.is_alive():
                time.sleep(0.1)
                print("Laser is currently measuring...", end='\r')
            pass

        if not DEBUG_MODE:
            # Here we get all the variables ready to run through the automation tab.
            hexapodSettings, laserSettings, collectionSettings = collectAutomationValues()
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
        pumpLaser.append(rotate_point(pumpLaser[-1], np.array(
            [0, 0, -AUTOMATION_ROTATION_ANGLE / 2])))  # this is so that we can keep track of the laser position

        # Everything below here should be the main loop
        for i in range(len(hexapod_rotation_stepList)):
            self.parent.automation_progress_bar = (i / len(hexapod_rotation_stepList)) * 100  # Update the progress bar
            theta = hexapod_rotation_stepList[i] - hexapod_rotation_stepList[i - 1]
            rotation_vector = np.array([0, 0, theta])
            self.hexapod.rotate(rotation_vector)
            pumpLaser.append(rotate_point(pumpLaser[-1], rotation_vector))

            adjustment_vector = pumpLaser[-2] - pumpLaser[-1]
            self.hexapod.translate(adjustment_vector)
            pumpLaser.append(pumpLaser[-1] + adjustment_vector)

            if not DEBUG_MODE:
                runLaser(degree=hexapod_rotation_stepList[i])
            else:
                print("DEBUG MODE ACTIVATED, NO LASER IN USE")

        #hexapod_settings, laser_settings, collection_settings = collectAutomationValues()  # We need to collect the values here as well
        #cleanUpFiles(collection_settings)

        # Reset Rotation and transformation
        self.hexapod.rotate([0, 0, -AUTOMATION_ROTATION_ANGLE / 2])
        pumpLaser.append(rotate_point(pumpLaser[-1], np.array([0, 0, -AUTOMATION_ROTATION_ANGLE / 2])))

        vector_for_reset = hexapodCenter[0] - hexapodCenter[-1]
        self.hexapod.translate(vector_for_reset, False)
