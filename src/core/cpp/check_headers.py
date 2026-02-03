
import os
from PyQt6.QtCore import QLibraryInfo

qt_headers = QLibraryInfo.path(QLibraryInfo.LibraryPath.HeadersPath)
print(f"Qt Headers Path: {qt_headers}")

modules = ["QtGui", "QtOpenGL"]
for mod in modules:
    path = os.path.join(qt_headers, mod)
    if os.path.exists(path):
        print(f"Listing {path}:")
        try:
            files = os.listdir(path)
            # Filter for gl functions
            gl_files = [f for f in files if "glfunctions" in f.lower() or "openglfunctions" in f.lower()]
            for f in gl_files:
                print(f"  {f}")
        except Exception as e:
            print(f"Error listing {path}: {e}")
    else:
        print(f"Path not found: {path}")
