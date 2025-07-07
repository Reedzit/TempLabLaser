import re

import matplotlib
import matplotlib.pyplot as plt
import numpy as np

from matplotlib.patches import Arc
from matplotlib.transforms import Bbox, IdentityTransform, TransformedBbox



matplotlib.use('macosx')

# Constants
MAXIMUM_DISTANCE = 30  # mm, This comes from the datasheet
MACHINE_SPEED = 3 # mm/s, from datasheet
MEASUREMENT_TIME = 300 # s, this is a rough estimate of time to sweep through frequencies

PUMP_DISTANCE_FROM_CENTER = 10  # mm, scaled as normal
PROBE_DISTANCE_FROM_PUMP = 5  # mm, should be scaled up so you can see it.

AUTOMATION_ROTATION_ANGLE = 40  # degrees, maximum sweep according to datasheet
AUTOMATION_STEPS = 150  # unitless and arbitrary

# Initialize position lists
pumpLaser = [np.array([PUMP_DISTANCE_FROM_CENTER, 0, 1])]
probeLaser = [np.array([PUMP_DISTANCE_FROM_CENTER + PROBE_DISTANCE_FROM_PUMP, 0, 1])]
hexapodCenter = [np.array([0, 0, 1])]  # This is constant

hexapod_points = [(46.19, 0),
                  (23.10, 40), (-23.10, 40),
                  (-46.19, 0), (-23.10, -40),
                  (23.10, -40), (46.19, 0)]  # These are also constant

# Create figure
plt.ion()
fig, ax = plt.subplots(figsize=(8, 8), dpi=100)


# Function to add new positions and update plot
def update_plot():
    ax.cla()  # Clear previous plot
    # Plot hexapod points
    if hexapodCenter:
        hexapodCenter_positions = np.array(hexapodCenter)
        ax.scatter(hexapodCenter_positions[:, 0], hexapodCenter_positions[:, 1],
                   c=hexapodCenter_positions[:, 2], cmap="Greys",
                   s=100, label="Hexapod Center", zorder=10)
        # Connect points with lines to show movement path
        ax.plot(hexapodCenter_positions[:, 0], hexapodCenter_positions[:, 1],
                '--', alpha=0.5, zorder=10)
        shape = matplotlib.patches.Polygon(hexapod_points, closed=True,
                                           color="grey", alpha=0.8)
        ax.add_patch(shape)

        circle_of_possibility = matplotlib.patches.Circle((0, 0), radius=MAXIMUM_DISTANCE, color="yellow", alpha=0.5)

        ax.add_patch(circle_of_possibility)


    # Plot pump laser positions
    if pumpLaser:
        pump_positions = np.array(pumpLaser)

        ax.scatter(pump_positions[:, 0], pump_positions[:, 1],
                   c=pump_positions[:, 2], cmap="Greens", s=10, label="Pump Laser")
        # Connect points with lines to show movement path
        ax.plot(pump_positions[:, 0], pump_positions[:, 1],
                'g--', alpha=0.25)

    # Plot probe laser positions
    if probeLaser:
        probe_positions = np.array(probeLaser)
        ax.scatter(probe_positions[:, 0], probe_positions[:, 1],
                   c=probe_positions[:, 2], cmap="Reds", s=10, label="Probe Laser")
        # Connect points with lines to show movement path
        ax.plot(probe_positions[:, 0], probe_positions[:, 1],
                'r--', alpha=0.25)

    # Set up the plot
    ax.set_xlim(-50, 50)
    ax.set_ylim(-50, 50)
    ax.spines[:].set_position('center')
    ax.grid(True, linestyle='--', alpha=0.3)

    # Add labels and legend
    ax.set_xlabel('X Position')
    ax.set_ylabel('Y Position')
    legend_elements = [matplotlib.lines.Line2D([0], [0], color='g', lw=4, label='Pump Laser'),
                       matplotlib.lines.Line2D([0], [0], color='r', lw=4, label='Probe Laser'),
                       matplotlib.patches.Patch(facecolor='yellow', edgecolor='yellow',
                                                label='possible platform positions'),
                       matplotlib.lines.Line2D([0], [0], marker='o', color='black', label='center of platform',
                                               markerfacecolor='black', markersize=10),
                       matplotlib.patches.Patch(facecolor='grey', edgecolor='black',
                                                label='hexapod platform')]
    ax.legend(handles=legend_elements, loc='upper left')

    plt.tight_layout()
    plt.draw()
    plt.pause(0.01)


def add_points(point_list, points, verbose=True):
    if verbose:
        index = len(point_list) + 1
    else:
        index = 0
    if isinstance(points, list):
        for point in points:
            x, y = point
            point = np.array([x, y, index])
            point_list.append(point)
            print(point)
    elif isinstance(points, (tuple, np.ndarray)):
        x, y = points
        point = np.array([x, y, index])
        point_list.append(point)
        print(point)
    else:
        print("Invalid input")
        return False
    return True


def rotate(theta, verbose=True):
    global hexapod_points
    theta = np.radians(theta)

    rotation_matrix = np.array([[np.cos(theta), -np.sin(theta)],
                                [np.sin(theta), np.cos(theta)]])

    old_pump_position = pumpLaser[-1][:2]
    new_pump_position = rotation_matrix @ old_pump_position

    old_probe_position = probeLaser[-1][:2]
    new_probe_position = rotation_matrix @ old_probe_position

    rotated_points = [rotation_matrix @ np.array(p) for p in hexapod_points]
    hexapod_points = rotated_points

    old_hexapod_center = hexapodCenter[-1][:2]
    new_hexapod_center = rotation_matrix @ old_hexapod_center

    add_points(pumpLaser, new_pump_position, verbose)
    add_points(probeLaser, new_probe_position, verbose)
    add_points(hexapodCenter, new_hexapod_center, verbose)

    return


def transform(vector, verbose=True):
    global hexapod_points
    x, y = vector
    new_pump_position = np.array([x, y]) + pumpLaser[-1][:2]
    new_probe_position = np.array([x, y]) + probeLaser[-1][:2]
    new_hexapod_center = np.array([x, y]) + hexapodCenter[-1][:2]

    add_points(pumpLaser, new_pump_position, verbose)
    add_points(probeLaser, new_probe_position, verbose)
    add_points(hexapodCenter, new_hexapod_center, verbose)

    translated_points = [np.array(p) for p in hexapod_points]
    translated_points = [(x + p[0], y + p[1]) for p in translated_points]
    hexapod_points = translated_points

    return


def automation():
    rotation_stepList = np.linspace(0, AUTOMATION_ROTATION_ANGLE, AUTOMATION_STEPS)
    # Offset the rotation by half the total distance so that we can keep moving in 1 direction the whole time
    rotate(-AUTOMATION_ROTATION_ANGLE / 2, False)
    for i in range(len(rotation_stepList)):
        theta = rotation_stepList[i] - rotation_stepList[i - 1]
        rotate(theta)

        adjustment_vector = pumpLaser[-2][:2] - pumpLaser[-1][:2]
        transform(adjustment_vector)

        update_plot()

    # Reset Rotation and transforma
    rotate(-AUTOMATION_ROTATION_ANGLE / 2, False)

    vector_for_reset = hexapodCenter[0][:2] - hexapodCenter[-1][:2]
    transform(vector_for_reset, False)
    update_plot()
    return


def calculate_total_machine_time():
    hexapodCenter_positions = np.array(hexapodCenter)
    time = 0
    for points in hexapodCenter_positions:
        x, y = points[:2]
        distance = np.sqrt(x ** 2 + y ** 2)
        split_time = distance / MACHINE_SPEED  # mm/s
        time += split_time
    time += MEASUREMENT_TIME*AUTOMATION_STEPS
    print(f"Total machine time: {time:.2f} s")


# Now here we can begin the logic loop
while True:
    user_input = input("Waiting for Command \n")

    rotate_regex = r"^R\s(-?\d+)$"
    transform_regex = r"^T\s(-?\d+)\s(-?\d+)$"

    rotate_match = re.search(rotate_regex, user_input)
    transform_match = re.search(transform_regex, user_input)

    try:
        if rotate_match:
            rotate_amount = int(rotate_match.group(1))
            print(rotate_amount)
            rotate(rotate_amount)
        elif transform_match:
            x_transform = int(transform_match.group(1))
            y_transform = int(transform_match.group(2))
            print(x_transform, y_transform)
            transform((x_transform, y_transform))
        elif user_input == "A":
            print("Automation Mode Beginning")
            automation()
        elif user_input.upper() == "Q":
            break
        elif user_input.upper() == "T":
            calculate_total_machine_time()
        else:
            print("Invalid command")
        update_plot()
    except Exception as e:
        print(f"Error: {e}")
        print("Invalid command")
