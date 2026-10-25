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
from src.measurementWorkflow import (
    coordinate_directory,
    generate_centered_angles,
    publish_latest,
    run_angle_sweeps,
    save_angle_sweep,
)


class AutomationManager:
    def __init__(self, parent, instruments, hexapod, main_gui):
        self.instruments = instruments
        self.hexapod = hexapod
        self.parent = parent
        self.main_gui = main_gui
        self.AutomationThread = None
        self.running = False
        self.cancel_event = threading.Event()
        self.laserGUI = self.main_gui.laserTabObject
        self.hexapodGUI = self.main_gui.hexapodTabObject

    def beginAutomation(self):
        if self.running or self.instruments.workflow_lock.locked():
            print("Automation could not start because another workflow is running.")
            return
        if not self.hexapod:
            self.hexapod = self.main_gui.hexapodTabObject.hexapod
        if not self.hexapod:
            print("Automation could not start because the hexapod is not connected.")
            return
        if getattr(self.hexapod, "laser_position", None) is None:
            print("Automation could not start until the laser position is calibrated.")
            return

        if not self.instruments.workflow_lock.acquire(blocking=False):
            print("Automation could not start because another workflow is running.")
            return

        try:
            measurement_directory = self.laserGUI.prepare_measurement_run()
            angles = generate_centered_angles(
                float(self.hexapodGUI.degrees_of_sweep.get()),
                int(self.hexapodGUI.stepCount.get()),
            )
            convergence_check = bool(self.laserGUI.wait_for_convergence.get())
            settings = self.laserGUI.laser_settings
            self.hexapod.getState()
            status = self.hexapod.status_dict or {}
            x_position = round(status.get("s_mtp_tx", 0), 3)
            y_position = round(status.get("s_mtp_ty", 0), 3)
        except Exception as exc:
            self.instruments.workflow_lock.release()
            print(f"Automation could not start: {exc}")
            return

        self.running = True
        self.cancel_event.clear()
        self.laserGUI.begin_shared_workflow(
            "Angle automation started. Live sweeps will appear here."
        )
        context = {
            "measurement_directory": measurement_directory,
            "settings": settings,
            "angles": angles,
            "convergence_check": convergence_check,
            "x_position": x_position,
            "y_position": y_position,
            "workflow_lock_acquired": True,
        }

        def run():
            try:
                self.runAutomationCycle(False, context)
            finally:
                self.running = False

        try:
            self.AutomationThread = threading.Thread(target=run)
            self.AutomationThread.start()
        except Exception:
            self.running = False
            self.instruments.workflow_lock.release()
            self.laserGUI.finish_shared_workflow("error: failed to start workflow thread")
            raise
        print("Automation started in the background. You can continue using the GUI.")

    def endAutomation(self):
        if self.AutomationThread and self.AutomationThread.is_alive():
            print("Stopping automation...")
            self.cancel_event.set()
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

    def runAutomationCycle(self, DEBUG_MODE=False, context=None):
        """Run the shared centered angle workflow at the current XY position."""
        if DEBUG_MODE:
            raise ValueError("Debug-only movement is not supported by the shared workflow")
        if context is None:
            raise ValueError("Automation context was not prepared")

        measurement_directory = context["measurement_directory"]
        x_position = context["x_position"]
        y_position = context["y_position"]
        coordinate_directory(measurement_directory, x_position, y_position)
        final_status = "completed"

        def display_data(data):
            publish_latest(self.instruments.automationQueue, data)

        def save_sweep(_angle_index, angle, sweep):
            save_angle_sweep(
                measurement_directory,
                x_position,
                y_position,
                angle,
                sweep,
            )

        try:
            run_angle_sweeps(
                self.hexapod,
                self.instruments,
                context["settings"],
                context["angles"],
                convergence_check=context["convergence_check"],
                cancel_event=self.cancel_event,
                on_sweep=save_sweep,
                on_data=display_data,
            )
            if self.cancel_event.is_set():
                final_status = "cancelled"
        except InterruptedError:
            final_status = "cancelled"
        except Exception as exc:
            final_status = f"error: {exc}"
            print(f"Angle automation failed: {exc}")
        finally:
            if context.get("workflow_lock_acquired"):
                self.instruments.workflow_lock.release()
            self.laserGUI.finish_shared_workflow(final_status)
