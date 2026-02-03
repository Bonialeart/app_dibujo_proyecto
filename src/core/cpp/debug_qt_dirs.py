
import os
from PyQt6.QtCore import QLibraryInfo

output_file = "gl_headers_debug.txt"

with open(output_file, "w") as f:
    qt_headers = QLibraryInfo.path(QLibraryInfo.LibraryPath.HeadersPath)
    f.write(f"Qt Headers Path: {qt_headers}\n")
    
    if os.path.exists(qt_headers):
        f.write("Contents of include dir:\n")
        try:
            for item in os.listdir(qt_headers):
                f.write(f" - {item}\n")
        except Exception as e:
            f.write(f"Error listing include: {e}\n")
            
        # Check QtGui and QtOpenGL
        for sub in ["QtGui", "QtOpenGL", "Qt6Gui", "Qt6OpenGL"]: # Checking variants
            p = os.path.join(qt_headers, sub)
            if os.path.exists(p):
                f.write(f"\nContents of {sub}:\n")
                try:
                    files = os.listdir(p)
                    # Filter relevant
                    for file in files:
                        if "gl" in file.lower():
                            f.write(f"   {file}\n")
                except Exception as e:
                    f.write(f"Error listing {sub}: {e}\n")
            else:
                f.write(f"\n{sub} NOT found at {p}\n")
    else:
        f.write("Qt Headers dir does not exist.\n")

print("Done writing debug info.")
