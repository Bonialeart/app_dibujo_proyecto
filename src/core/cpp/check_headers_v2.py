
import os
from PyQt6.QtCore import QLibraryInfo

qt_headers = QLibraryInfo.path(QLibraryInfo.LibraryPath.HeadersPath)
print(f"Qt Headers Path: {qt_headers}")

if os.path.exists(qt_headers):
    print("Contents of include dir:")
    try:
        print(os.listdir(qt_headers))
    except:
        print("Error listing include dir")

    # Check subdirs
    for sub in ["QtGui", "QtOpenGL"]:
        p = os.path.join(qt_headers, sub)
        if os.path.exists(p):
            print(f"Contents of {sub}:")
            try:
                files = os.listdir(p)
                print([f for f in files if "OpenGL" in f or "gl" in f.lower()])
            except: pass
        else:
            print(f"{sub} not found at {p}")
