import os
import sys
import multiprocessing

# Add the src directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.microscopeGUI import MicroscopeGUI

if __name__ == '__main__':
    manager = multiprocessing.Manager()
    MicroscopeGUI(manager).run.gui