
import os
from PyQt6.QtCore import QLibraryInfo
import PyQt6

output_file = "gl_headers_debug_v2.txt"

with open(output_file, "w") as f:
    pyqt_dir = os.path.dirname(PyQt6.__file__)
    f.write(f"PyQt6 Dir: {pyqt_dir}\n")
    
    if os.path.exists(pyqt_dir):
        f.write("Contents of PyQt6 dir:\n")
        try:
            for item in os.listdir(pyqt_dir):
                f.write(f" - {item}\n")
        except:
            f.write("Error listing PyQt6 dir\n")
            
        # Check Qt6 inside
        qt6_dir = os.path.join(pyqt_dir, "Qt6")
        if os.path.exists(qt6_dir):
             f.write("Contents of Qt6:\n")
             for item in os.listdir(qt6_dir):
                f.write(f" - {item}\n")
             
             # Check include in Qt6
             inc = os.path.join(qt6_dir, "include")
             if os.path.exists(inc):
                 f.write("Contents of Qt6/include: (EXISTS)\n")
                 # List it if not empty
                 try:
                     f.write(str(os.listdir(inc)) + "\n")
                 except: pass
             else:
                 f.write("Qt6/include does NOT exist.\n")

    else:
        f.write("PyQt6 dir does not exist.\n")
