import os
import sys
import threading

# Add the src directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.microscopeGUI import MicroscopeGUI

if __name__ == '__main__':
    MicroscopeGUI()