#!/usr/bin/env python3
import os
import sys

# Set Qt environment variables for better WSL2 performance
os.environ["QT_QPA_PLATFORM"] = "xcb"
os.environ["QT_X11_NO_MITSHM"] = "1"
os.environ["QT_QUICK_BACKEND"] = "software"
os.environ["QT_SCALE_FACTOR"] = "1"
os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "0"

# Disable hardware acceleration that can cause issues in WSL2
os.environ["LIBGL_ALWAYS_SOFTWARE"] = "1"

print("WSL2 Qt optimization environment set")
print("Starting desktop app...")

# Import and run the main app
from desktop_app import *

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = BudgetDesktopApp()
    window.show()
    sys.exit(app.exec())
