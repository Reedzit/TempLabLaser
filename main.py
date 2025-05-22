import os
import sys
import threading
import multiprocessing as mp

# Add the src directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.microscopeGUI import MicroscopeGUI

if __name__ == '__main__':
    mp.set_start_method('spawn')
    MicroscopeGUI()