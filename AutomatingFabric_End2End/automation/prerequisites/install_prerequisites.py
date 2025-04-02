import subprocess
import sys, os

os.chdir(os.path.dirname(os.path.abspath(__file__)))

with open("requirements.txt", "r") as file:
    required_libraries = file.readlines()[1:]

required_libraries = [line.strip() for line in required_libraries]

def install_libraries():
    for lib in required_libraries:

        try:
            __import__(lib)
            print(f"{lib} already installed...")
        except ImportError:
            print(f"Installing {lib}...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", lib])

install_libraries()
