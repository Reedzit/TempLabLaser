# TempLab Laser

Microscope and hardware automation GUI for the TempLab setup. The application coordinates the laser, function generators, hexapod, and measurement logging.

## Repository layout

- `main.py` - application entry point
- `src/` - GUI tabs, instrument managers, and automation logic
- `res/` - sample metadata and other shared resources
- `src/matlab/` - MATLAB analysis helpers and example data

## Run

```bash
python main.py
```

## Installation

Install the Python dependencies first:

```bash
pip install pyvisa pyvisa-py matplotlib numpy tk subprocess paramiko zeroconf psutil pandas fonttools
```

For the camera tab, install the camera display dependencies:

```bash
pip install opencv-python pillow
```

If you use MATLAB analysis, install the MATLAB Engine API from your MATLAB installation:

```bash
cd "matlabroot\extern\engines\python"
python -m pip install .
```

## Measurement workflow

1. Configure the instruments.
2. Connect and home the hexapod if needed.
3. Select the sample and measurement parameters.
4. Start automation from the laser tab.

Each measurement run writes its data into a dedicated folder and generates a measurement README alongside the collected files.

## Notes

- Python cache files and local data artifacts are ignored by default.
- The generated measurement README now mirrors the simpler, structured style used in the sister unified codebase.
