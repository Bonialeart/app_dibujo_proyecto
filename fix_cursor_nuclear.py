import os

path = r'd:/app_dibujo_proyecto/src/ui/canvas_item.py'
with open(path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# We need to find the hover handlers we inserted and replace them with the Nuclear Option (QGuiApplication)

# 1. Update Imports if needed (QGuiApplication is already there based on view_file, but let's be safe)
# It is in line 7.

# 2. Define the new Robust Event Handlers
new_methods = [
    '    def hoverEnterEvent(self, event):\n',
    '        self._is_hovering = True\n',
    '        # FORCE NULL CURSOR GLOBALLY (Nuclear Option)\n',
    '        if self._current_tool != "hand" and not getattr(self, "_cursor_overridden", False):\n',
    '            QGuiApplication.setOverrideCursor(QCursor(Qt.CursorShape.BlankCursor))\n',
    '            self._cursor_overridden = True\n',
    '        event.accept()\n',
    '\n',
    '    def hoverLeaveEvent(self, event):\n',
    '        self._is_hovering = False\n',
    '        # Restore cursor\n',
    '        if getattr(self, "_cursor_overridden", False):\n',
    '            QGuiApplication.restoreOverrideCursor()\n',
    '            self._cursor_overridden = False\n',
    '        self.update()\n',
    '        event.accept()\n',
    '\n',
    '    def hoverMoveEvent(self, event):\n',
    '        self._cursor_pos = event.position()\n',
    '        self._is_hovering = True\n',
    '        \n',
    '        # Ensure cursor remains dead\n',
    '        if self._current_tool != "hand" and not getattr(self, "_cursor_overridden", False):\n',
    '             QGuiApplication.setOverrideCursor(QCursor(Qt.CursorShape.BlankCursor))\n',
    '             self._cursor_overridden = True\n',
    '             \n',
    '        self.update() # Draw ghost\n',
    '        self.cursorPosChanged.emit(self._cursor_pos.x(), self._cursor_pos.y())\n',
    '        event.accept()\n',
    '\n'
]

# 3. HELPER TO REMOVE PREVIOUS VERSIONS
def remove_function(name):
    start = -1
    for i in range(len(lines)):
        if f'def {name}' in lines[i]:
            start = i
            break
    if start == -1: return
    
    end = len(lines)
    indent = len(lines[start]) - len(lines[start].lstrip())
    for i in range(start + 1, len(lines)):
        if lines[i].strip() == '': continue
        curr_indent = len(lines[i]) - len(lines[i].lstrip())
        if curr_indent <= indent:
            end = i
            break
    del lines[start:end]

# Remove existing (which we just added in v2)
remove_function('hoverEnterEvent')
remove_function('hoverLeaveEvent')
remove_function('hoverMoveEvent')

# 4. Insert New
insert_idx = -1
for i, line in enumerate(lines):
    if 'def mouseReleaseEvent' in line:
        insert_idx = i
        break
if insert_idx == -1: insert_idx = len(lines) - 1

lines[insert_idx:insert_idx] = new_methods

# 5. Fix _update_native_cursor to play nice with override
update_cursor_idx = -1
for i, line in enumerate(lines):
    if 'def _update_native_cursor' in line:
        update_cursor_idx = i
        break

if update_cursor_idx != -1:
    # Need to replace the whole function content
    # Find end
    end_uc = len(lines)
    indent = len(lines[update_cursor_idx]) - len(lines[update_cursor_idx].lstrip())
    for i in range(update_cursor_idx + 1, len(lines)):
         if lines[i].strip() == '': continue
         curr_indent = len(lines[i]) - len(lines[i].lstrip())
         if curr_indent <= indent:
             end_uc = i
             break
    
    new_update_cursor = [
        '    def _update_native_cursor(self):\n',
        '        """Updates cursor state (Nuclear Compatible)."""\n',
        '        if self._current_tool == "hand":\n',
        '            # Restore standard cursor if we were overriding\n',
        '            if getattr(self, "_cursor_overridden", False):\n',
        '                QGuiApplication.restoreOverrideCursor()\n',
        '                self._cursor_overridden = False\n',
        '            self.setCursor(QCursor(Qt.CursorShape.OpenHandCursor))\n',
        '        else:\n',
        '            # Enforce Blank Override\n',
        '            if self._is_hovering and not getattr(self, "_cursor_overridden", False):\n',
        '                 QGuiApplication.setOverrideCursor(QCursor(Qt.CursorShape.BlankCursor))\n',
        '                 self._cursor_overridden = True\n'
    ]
    lines[update_cursor_idx:end_uc] = new_update_cursor

# 6. Ensure __init__ initializes the flag
for i, line in enumerate(lines):
    if 'def __init__' in line:
        # Find end of init to append property
        # Actually easier to just invoke it in setCursor
        pass
    if 'self._is_hovering = False' in line:
        if 'self._cursor_overridden = False' not in lines[i+1]:
            lines.insert(i+1, '        self._cursor_overridden = False\n')
        break

with open(path, 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("NUCLEAR CURSOR FIX APPLIED")
