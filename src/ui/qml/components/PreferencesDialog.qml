import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs
import "../Translations.js" as Trans

Popup {
    id: root
    width: 900
    height: 650
    modal: true
    focus: true
    closePolicy: Popup.CloseOnEscape
    
    // Position center of parent/window
    x: (parent.width - width) / 2
    y: (parent.height - height) / 2
    
    // --- PROPERTIES & SIGNALS ---
    signal settingsChanged()
    
    // Theme Colors - Bound to PreferencesManager if available, else fallback
    property string themeMode: (typeof preferencesManager !== "undefined") ? preferencesManager.themeMode : "Dark"
    property color themeAccent: (typeof preferencesManager !== "undefined") ? preferencesManager.themeAccent : "#6366f1"
    
    // Computed based on Mode
    readonly property bool isDark: themeMode === "Dark" || themeMode === "Midnight" || themeMode === "Blue-Grey"
    
    readonly property color colorBg: isDark ? (themeMode === "Midnight" ? "#0f172a" : (themeMode === "Blue-Grey" ? "#1e293b" : "#1e1e20")) : "#f3f4f6"
    readonly property color colorPanel: isDark ? (themeMode === "Midnight" ? "#1e293b" : (themeMode === "Blue-Grey" ? "#334155" : "#252526")) : "#ffffff"
    readonly property color colorAccent: themeAccent
    readonly property color colorText: isDark ? "#ffffff" : "#1f2937"
    readonly property color colorTextMuted: isDark ? "#a1a1aa" : "#6b7280"
    readonly property color colorBorder: isDark ? "#3f3f46" : "#e5e7eb"
    readonly property color colorInput: isDark ? "#18181b" : "#f9fafb"
    
    property int currentCategoryIndex: 0

    // --- TEMP STATE (Buffer for Cancel) ---
    // Initialize with safe defaults, overwritten on Open
    property bool tempGpuEnabled: true
    property int tempUndoLevels: 50
    property int tempMemLimit: 70
    property bool tempSwitchTool: true
    property int tempSwitchDelay: 500
    property string tempLanguage: "en"

    readonly property string lang: (typeof preferencesManager !== "undefined") ? preferencesManager.language : "en"
    function qs(key) { return Trans.get(key, lang); }
    
    onOpened: {
        // Load fresh values from Manager
        if (typeof preferencesManager !== "undefined") {
            tempGpuEnabled = preferencesManager.gpuAcceleration
            tempUndoLevels = preferencesManager.undoLevels
            tempLanguage = preferencesManager.language
            // tempMemLimit = preferencesManager.get("memory_limit")
        }
    }
    
    function saveSettings() {
        if (typeof preferencesManager !== "undefined") {
            preferencesManager.gpuAcceleration = tempGpuEnabled
            preferencesManager.undoLevels = tempUndoLevels
            preferencesManager.language = tempLanguage
            
            toastManager.show(root.qs("saved"), "success")
        }
    }


    
    // --- BACKGROUND ---
    background: Rectangle {
        color: colorBg
        border.color: "#444"
        border.width: 1
        radius: 8
        
        // Shadow effect
        layer.enabled: true
        // Note: Effects might need specific import or fallback, keeping simple for now
    }
    
    contentItem: ColumnLayout {
        spacing: 0
        
        // TITLE BAR
        Rectangle {
            Layout.fillWidth: true; Layout.preferredHeight: 40
            color: "transparent"
            
            Text {
                text: root.qs("preferences")
                color: colorText
                font.pixelSize: 14; font.bold: true
                anchors.centerIn: parent
            }
            
            // X Button
            Button {
                text: "✕"
                anchors.right: parent.right; anchors.rightMargin: 8
                anchors.verticalCenter: parent.verticalCenter
                width: 30; height: 30
                background: Rectangle { color: "transparent" }
                contentItem: Text { 
                    text: parent.text; color: colorTextMuted; font.pixelSize: 14; 
                    horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter 
                }
                onClicked: root.close()
            }
            
            Rectangle { width: parent.width; height: 1; color: colorBorder; anchors.bottom: parent.bottom }
        }
        
        // MAIN CONTENT AREA
        RowLayout {
            Layout.fillWidth: true; Layout.fillHeight: true
            spacing: 0
            
            // --- SIDEBAR ---
            Rectangle {
                Layout.preferredWidth: 220
                Layout.fillHeight: true
                color: "#18181b" // Darker sidebar
                
                Rectangle { width: 1; height: parent.height; color: colorBorder; anchors.right: parent.right }
                
                ListView {
                    id: categoryList
                    anchors.fill: parent
                    anchors.margins: 8
                    spacing: 2
                    model: [
                        { name: root.qs("appearance"), icon: "layout.svg" },
                        { name: root.qs("performance"), icon: "cpu.svg" }, 
                        { name: root.qs("cursor"), icon: "mouse-pointer.svg" },
                        { name: root.qs("tablet"), icon: "tablet.svg" },
                        { name: root.qs("shortcuts"), icon: "keyboard.svg" }, 
                        { name: root.qs("tools"), icon: "tool.svg" },      
                        { name: root.qs("file"), icon: "file.svg" },
                        { name: root.qs("color"), icon: "palette.svg" }
                    ]
                    
                    delegate: Rectangle {
                        width: parent.width
                        height: 32
                        color: index === root.currentCategoryIndex ? colorAccent : "transparent"
                        radius: 4
                        
                        property bool isHovered: hoverMa.containsMouse
                        
                        Rectangle {
                            anchors.fill: parent
                            color: "white"
                            opacity: parent.isHovered && index !== root.currentCategoryIndex ? 0.05 : 0
                            radius: 4
                        }
                        
                        RowLayout {
                            anchors.fill: parent; anchors.leftMargin: 10
                            spacing: 10
                            
                            Rectangle {
                                width: 16; height: 16; radius: 8
                                color: "transparent" // Transparent if icon is present
                                
                                Image { 
                                    anchors.fill: parent
                                    source: (typeof iconsUrl !== "undefined" ? iconsUrl : "") + model.icon
                                    visible: status === Image.Ready
                                    sourceSize.width: 16; sourceSize.height: 16
                                    opacity: index === root.currentCategoryIndex ? 1.0 : 0.6
                                    
                                    // Fallback circle if icon missing
                                    onStatusChanged: if (status === Image.Error) parent.color = (index === root.currentCategoryIndex ? "white" : "#555")
                                }
                                
                                // Default circle coloring if image not loaded initially
                                Component.onCompleted: if (source == "") color = (index === root.currentCategoryIndex ? "white" : "#555")
                            }
                            
                            Text {
                                text: modelData.name
                                color: index === root.currentCategoryIndex ? "white" : (parent.parent.isHovered ? colorText : colorTextMuted)
                                font.pixelSize: 13
                                font.weight: index === root.currentCategoryIndex ? Font.Bold : Font.Normal
                                Layout.fillWidth: true
                            }
                        }
                        
                        MouseArea {
                            id: hoverMa
                            anchors.fill: parent
                            hoverEnabled: true
                            onClicked: root.currentCategoryIndex = index
                        }
                    }
                }
            }
            
            // --- SETTINGS PAGES ---
            Rectangle {
                Layout.fillWidth: true
                Layout.fillHeight: true
                color: "transparent"
                clip: true
                
                StackLayout {
                    anchors.fill: parent
                    anchors.margins: 20
                    currentIndex: root.currentCategoryIndex
                    
                    // 0. APPEARANCE
                    ScrollView {
                        contentHeight: interfaceCol.height
                        ColumnLayout {
                            id: interfaceCol
                            width: parent.width
                            spacing: 20
                            
                            SettingsGroup {
                                title: root.qs("theme_mode")
                                description: root.qs("theme_desc")
                                
                                Flow {
                                    Layout.fillWidth: true
                                    spacing: 12
                                    
                                    Repeater {
                                        model: ["Dark", "Light", "Midnight", "Blue-Grey"]
                                        delegate: Rectangle {
                                            width: 100; height: 60
                                            color: (preferencesManager.themeMode === modelData) ? colorAccent : colorPanel
                                            radius: 6
                                            border.color: colorBorder
                                            border.width: 1
                                            
                                            Text {
                                                text: modelData
                                                anchors.centerIn: parent
                                                color: (preferencesManager.themeMode === modelData) ? "white" : colorText
                                                font.bold: true
                                            }
                                            
                                            MouseArea {
                                                anchors.fill: parent
                                                cursorShape: Qt.PointingHandCursor
                                                onClicked: preferencesManager.themeMode = modelData
                                            }
                                        }
                                    }
                                }
                            }

                            SettingsGroup {
                                title: root.qs("accent_color")
                                description: root.qs("accent_desc")
                                
                                Flow {
                                    Layout.fillWidth: true
                                    spacing: 12
                                    
                                    Repeater {
                                        model: ["#6366f1", "#ef4444", "#f59e0b", "#10b981", "#3b82f6", "#ec4899", "#8b5cf6", "#64748b"]
                                        delegate: Rectangle {
                                            width: 32; height: 32
                                            radius: 16
                                            color: modelData
                                            border.color: "white"
                                            border.width: (preferencesManager.themeAccent === modelData) ? 2 : 0
                                            
                                            MouseArea {
                                                anchors.fill: parent
                                                cursorShape: Qt.PointingHandCursor
                                                onClicked: preferencesManager.themeAccent = modelData
                                            }
                                        }
                                    }
                                }
                            }

                            SettingsGroup {
                                title: root.qs("language")
                                description: root.qs("language_desc")
                                
                                Flow { // Changed to Flow for many languages
                                    Layout.fillWidth: true; spacing: 12
                                    Repeater {
                                        model: [
                                            { name: "Español", code: "es" },
                                            { name: "English", code: "en" },
                                            { name: "日本語", code: "ja" },
                                            { name: "Français", code: "fr" },
                                            { name: "Português", code: "pt" },
                                            { name: "中文", code: "zh" },
                                            { name: "한국어", code: "ko" }
                                        ]
                                        delegate: Rectangle {
                                            width: 100; height: 36; radius: 6
                                            color: (root.tempLanguage === modelData.code) ? colorAccent : colorPanel
                                            border.color: colorBorder; border.width: 1
                                            
                                            Text {
                                                text: modelData.name
                                                anchors.centerIn: parent
                                                color: (root.tempLanguage === modelData.code) ? "white" : colorText
                                                font.pixelSize: 12; font.bold: true
                                            }
                                            
                                            MouseArea {
                                                anchors.fill: parent; cursorShape: Qt.PointingHandCursor
                                                onClicked: root.tempLanguage = modelData.code
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                    
                    // 1. PERFORMANCE (USER REQUEST)
                    ScrollView {
                        contentHeight: perfCol.height
                        ColumnLayout {
                            id: perfCol
                            width: parent.width
                            spacing: 20
                            
                            SettingsGroup {
                                title: "Graphic Processor"
                                description: "Configure how the application uses your hardware."
                                
                                RowLayout {
                                    spacing: 12
                                    Button {
                                        text: "GPU Acceleration (Recommended)"
                                        checkable: true
                                        checked: root.tempGpuEnabled
                                        Layout.fillWidth: true
                                        palette.button: checked ? colorAccent : "#333"
                                        palette.buttonText: "white"
                                        onClicked: root.tempGpuEnabled = true
                                    }
                                    Button {
                                        text: "CPU Only"
                                        checkable: true
                                        checked: !root.tempGpuEnabled
                                        Layout.fillWidth: true
                                        onClicked: root.tempGpuEnabled = false
                                    }
                                }
                                Text { 
                                    text: "Use GPU for rendering canvas and effects. Provides smoother zooming and rotating."
                                    color: colorTextMuted; font.pixelSize: 11; wrapMode: Text.WordWrap
                                    Layout.fillWidth: true
                                }
                            }
                            
                            SettingsGroup {
                                title: "Memory"
                                
                                Label { text: "Undo Levels: " + undoSlider.value; color: colorText }
                                Slider {
                                    id: undoSlider
                                    from: 10; to: 200; stepSize: 1
                                    value: root.tempUndoLevels
                                    Layout.fillWidth: true
                                    onMoved: root.tempUndoLevels = value
                                }
                                
                                Label { text: "Memory Usage Limit: " + memSlider.value + "%"; color: colorText }
                                Slider {
                                    id: memSlider
                                    from: 20; to: 90; value: root.tempMemLimit
                                    stepSize: 5
                                    Layout.fillWidth: true
                                    onMoved: root.tempMemLimit = value
                                }
                            }
                        }
                    }
                    
                    // 2. CURSOR
                    ScrollView {
                         contentHeight: cursorCol.height
                         ColumnLayout {
                            id: cursorCol
                            width: parent.width
                            SettingsGroup {
                                title: "Cursor Shape"
                                CheckBoxOption { text: "Brush Size Outline"; checked: true }
                                CheckBoxOption { text: "Crosshair in Center"; checked: true }
                            }
                         }
                    }
                    
                    // 3. TABLET
                    ScrollView {
                        contentHeight: tabletCol.height
                        ColumnLayout {
                            id: tabletCol; width: parent.width
                            SettingsGroup {
                                title: "Input Mode"
                                CheckBoxOption { text: "Use Windows Ink"; checked: true }
                                CheckBoxOption { text: "Wintab (Legacy)"; checked: false }
                            }
                        }
                    }
                    
                    // 4. SHORTCUTS (USER REQUEST)
                    ScrollView {
                        contentHeight: shortcutCol.height
                        ColumnLayout {
                            id: shortcutCol
                            width: parent.width
                            spacing: 16
                            
                            Text { text: "Keyboard Shortcuts"; color: colorText; font.pixelSize: 18; font.bold: true }
                            
                            // Search
                            Rectangle {
                                Layout.fillWidth: true; Layout.preferredHeight: 32
                                color: colorInput; radius: 4; border.color: colorBorder
                                TextInput {
                                    anchors.fill: parent; anchors.leftMargin: 8; verticalAlignment: Text.AlignVCenter
                                    color: "white"; font.pixelSize: 13
                                    text: "Search command..."
                                }
                            }
                            
                            // Shortcut List Header
                            RowLayout {
                                Layout.fillWidth: true
                                Text { text: "Command"; color: colorTextMuted; font.pixelSize: 12; Layout.fillWidth: true }
                                Text { text: "Key"; color: colorTextMuted; font.pixelSize: 12; Layout.preferredWidth: 100 }
                            }
                            
                            Rectangle { Layout.fillWidth: true; height: 1; color: colorBorder }
                            

                            // Shortcuts Data
                            Repeater {
                                model: [
                                    { cmd: "New Project", key: "Ctrl+N" },
                                    { cmd: "Open Project", key: "Ctrl+O" },
                                    { cmd: "Save", key: "Ctrl+S" },
                                    { cmd: "Undo", key: "Ctrl+Z" },
                                    { cmd: "Redo", key: "Ctrl+Y" },
                                    { cmd: "New Layer", key: "Ctrl+Shift+N" },
                                    { cmd: "Pen Tool", key: "P" },
                                    { cmd: "Pencil Tool", key: "Shift+P" },
                                    { cmd: "Brush Tool", key: "B" },
                                    { cmd: "Eraser Tool", key: "E" },
                                    { cmd: "Move (Hand)", key: "H / Space" }
                                ]
                                delegate: RowLayout {
                                    width: parent.width
                                    height: 30
                                    Text { text: modelData.cmd; color: colorText; font.pixelSize: 13; Layout.fillWidth: true }
                                    
                                    Rectangle {
                                        Layout.preferredWidth: 100; Layout.preferredHeight: 24
                                        color: "#2c2c2e"; radius: 4
                                        border.color: "#3f3f46"
                                        Text { 
                                            text: modelData.key; color: "white"; font.pixelSize: 12 
                                            anchors.centerIn: parent
                                        }
                                        MouseArea {
                                            anchors.fill: parent; cursorShape: Qt.PointingHandCursor
                                            onClicked: {
                                                // Logic to change shortcut would go here
                                                parent.border.color = colorAccent
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                    
                    // 5. TOOLS (USER REQUEST + CLIP STUDIO REFERENCE)
                    ScrollView {
                        contentHeight: toolsCol.height
                        ColumnLayout {
                            id: toolsCol
                            width: parent.width
                            spacing: 20
                            
                            SettingsGroup {
                                title: "Switch Tool Temporarily"
                                CheckBoxOption { text: "Switch tool temporarily by pressing and holding shortcut key"; checked: root.tempSwitchTool }
                                RowLayout {
                                    Layout.leftMargin: 24
                                    Text { text: "Length of keypress to switch tools:"; color: colorTextMuted }
                                    TextField { 
                                        text: "500"; palette.text: "white"; palette.base: colorInput
                                        Layout.preferredWidth: 60
                                        background: Rectangle { color: colorInput; border.color: colorBorder; radius: 4 }
                                    }
                                    Text { text: "ms"; color: colorTextMuted }
                                }
                            }
                            
                            SettingsGroup {
                                title: "Options"
                                RowLayout {
                                    Text { text: "Minimum drag distance:"; color: colorTextMuted; Layout.preferredWidth: 150 }
                                    TextField { text: "3"; Layout.preferredWidth: 60; color: "white"
                                        background: Rectangle { color: colorInput; border.color: colorBorder; radius: 4 }
                                    }
                                }
                                CheckBoxOption { text: "Use fast view while navigating canvas"; checked: false }
                            }
                            
                            SettingsGroup {
                                title: "Brush / Line"
                                CheckBoxOption { text: "Start from current size when changing brush size"; checked: true }
                                CheckBoxOption { text: "Display brush size adjustment on canvas"; checked: true }
                            }
                        }
                    }
                    
                    // 6. FILE
                    Item { Text { text: "File Settings"; color: "white"; anchors.centerIn: parent } }
                    
                    // 7. COLOR
                    Item { Text { text: "Color Settings"; color: "white"; anchors.centerIn: parent } }
                }
            }
        }
        
        // BUTTON BAR
        Rectangle {
            Layout.fillWidth: true; Layout.preferredHeight: 60
            color: colorPanel
            border.color: colorBorder
            border.width: 1
            
            RowLayout {
                anchors.fill: parent; anchors.margins: 12
                Layout.alignment: Qt.AlignRight
                
                Button {
                    text: "Restore Defaults"
                    flat: true
                    palette.buttonText: colorTextMuted
                }
                
                Item { Layout.fillWidth: true }
                
                Button {
                    text: root.qs("cancel")
                    onClicked: root.close()
                    background: Rectangle { color: "#333"; radius: 4 }
                    contentItem: Text { text: parent.text; color: "white"; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                    Layout.preferredWidth: 80; Layout.preferredHeight: 32
                }
                
                Button {
                    text: root.qs("ok")
                    onClicked: { 
                        root.saveSettings(); 
                        root.settingsChanged(); 
                        root.close() 
                    }
                    background: Rectangle { color: colorAccent; radius: 4 }
                    contentItem: Text { text: parent.text; color: "white"; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                    Layout.preferredWidth: 80; Layout.preferredHeight: 32
                }
            }
        }
    }
    
    // --- HELPER COMPONENTS ---
    
    component SettingsGroup : ColumnLayout {
        property string title
        property string description: ""
        
        spacing: 12
        Layout.fillWidth: true
        
        Text { text: title; color: colorText; font.bold: true; font.pixelSize: 15 }
        
        Rectangle { Layout.fillWidth: true; height: 1; color: "#33ffffff" }
        
        Text { 
            text: description; visible: description !== ""
            color: colorTextMuted; font.pixelSize: 12 
            Layout.fillWidth: true; wrapMode: Text.WordWrap
        }
    }
    
    component CheckBoxOption : CheckBox {
        text: ""
        contentItem: Text {
            text: parent.text
            color: colorText
            font.pixelSize: 13
            verticalAlignment: Text.AlignVCenter
            leftPadding: parent.indicator.width + 12
        }
        indicator: Rectangle {
            implicitWidth: 18; implicitHeight: 18
            x: parent.leftPadding; y: parent.height / 2 - height / 2
            radius: 4
            color: parent.checked ? colorAccent : "transparent"
            border.color: parent.checked ? colorAccent : "#777"
            
            Text {
                visible: parent.parent.checked
                text: "✓"; color: "white"; font.pixelSize: 12
                anchors.centerIn: parent
            }
        }
    }
}
