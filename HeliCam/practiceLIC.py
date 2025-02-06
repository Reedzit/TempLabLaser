import os, sys

prgPath = os.environ["PROGRAMFILES"]
sys.path.insert(0, prgPath + r'\\Heliotis\\heliCam\\Python\\wrapper')
from libHeLIC import * 
import subprocess
from Python.example.libHeLICTester import *

subprocess.run(['python', 'templablaser\\HeliCam\\Python\\example\\libHeLICTester.py'], check=True)
