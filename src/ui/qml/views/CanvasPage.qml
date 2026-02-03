import QtQuick
import QtQuick.Window
import QtQuick.Controls
import QtQuick.Layouts 1.15
import QtQuick.Dialogs
import QtQuick.Effects

// import QtWebEngine
// import Qt5Compat.GraphicalEffects


import ArtFlow 1.0
import "components"

            Item {
                id: canvasPage
    property bool isProjectActive: mainWindow ? mainWindow.isProjectActive : false
    property color colorAccent: mainWindow ? mainWindow.colorAccent : '#6366f1'
    property var mainWindow
    property var mainCanvas
                Rectangle { anchors.fill: parent; color: "#121214" }

                // DRAWING CANVAS
                QCanvasItem {
                    id: mainCanvas
                    anchors.fill: parent
                    visible: isProjectActive
                    onVisibleChanged: if (visible) Qt.callLater(fitToView)
                    
                    // Sombra Dinámica que sigue al papel (y se escala)
                    Rectangle { 
                        z: -1; 
                        x: mainCanvas.viewOffset.x; y: mainCanvas.viewOffset.y
                        width: mainCanvas.canvasWidth * mainCanvas.zoomLevel
                        height: mainCanvas.canvasHeight * mainCanvas.zoomLevel
                        anchors.margins: -10; color: "black"; opacity: 0.3; radius: 10 
                    }

                    // --- TRANSFORM OVERLAY ---
                    Item {
                        id: transformOverlayContainer
                        visible: mainCanvas.isTransforming
                        x: mainCanvas.viewOffset.x
                        y: mainCanvas.viewOffset.y
                        scale: mainCanvas.zoomLevel
                        width: mainCanvas.canvasWidth
                        height: mainCanvas.canvasHeight
                        transformOrigin: Item.TopLeft
                        z: 100
                        
                        // The Manipulator Item (The selection bounding box)
                        Rectangle {
                            id: manipulator
                            // Initial pos 0,0 relative to container (Whole Canvas)
                            width: parent.width
                            height: parent.height
                            color: "transparent"
                            border.color: colorAccent
                            border.width: 2 / mainCanvas.zoomLevel
                            transformOrigin: Item.Center
                            
                            // Reset state when shown
                            onVisibleChanged: {
                                if (visible) {
                                    x = 0; y = 0
                                    scale = 1; rotation = 0
                                    mainCanvas.updateTransformProperties(x, y, scale, rotation, width, height)
                                }
                            }
                            
                            PinchHandler { target: manipulator }
                            DragHandler { target: manipulator }
                            
                            onXChanged: if (visible) updateTransform()
                            onYChanged: if (visible) updateTransform()
                            onScaleChanged: if (visible) updateTransform()
                            onRotationChanged: if (visible) updateTransform()
                            
                            function updateTransform() {
                                mainCanvas.updateTransformProperties(x, y, scale, rotation, width, height)
                            }
                            
                            // Visual Handles (Corners) - Just for show in Essential version
                            // Could implement interactive resize logic later
                            Repeater {
                                model: [
                                    {x: 0, y: 0}, {x: manipulator.width, y: 0},
                                    {x: 0, y: manipulator.height}, {x: manipulator.width, y: manipulator.height}
                                ]
                                delegate: Rectangle {
                                    width: 12 / mainCanvas.zoomLevel; height: 12 / mainCanvas.zoomLevel
                                    x: modelData.x - width/2; y: modelData.y - height/2
                                    color: "white"; border.color: colorAccent
                                    radius: width/2
                                }
                            }
                        }
                    }



                    // --- SMART CURSOR (Legacy - Now Handled in Python paint()) ---
                    /*
                    Image {
                        id: smartCursor
                        visible: false // Disabled in favor of Native Paint
                        enabled: false // Prevent event stealing
                        opacity: 0.5
                        mipmap: true
                        source: mainCanvas.brushTip 
                        
                        property real pixelSize: mainCanvas.brushSize * mainCanvas.zoomLevel
                        width: pixelSize
                        height: pixelSize
                        rotation: mainCanvas.brushAngle + mainCanvas.cursorRotation
                        
                        property real trackX: 0
                        property real trackY: 0
                        x: trackX - width/2
                        y: trackY - height/2
                        
                        cache: false 
                    }
                    */

                    // Handle Cursor Signal from C++
                    onCursorPosChanged: (x, y) => {
                         // smartCursor.trackX = x
                         // smartCursor.trackY = y
                    }

 

                    


                    // --- PREMIUM PRO LOUPE (EYEDROPPER) ---
                    Item {
                        id: loupe
                        visible: canvasPage.isSampling
                        // Float near the finger
                        x: canvasPage.samplePos.x - width/2
                        y: canvasPage.samplePos.y - height - 50 
                        width: 110; height: 110
                        z: 1000
    
                        scale: visible ? 1.0 : 0.4
                        opacity: visible ? 1.0 : 0.0
                        Behavior on scale { NumberAnimation { duration: 250; easing.type: Easing.OutBack } }
                        Behavior on opacity { NumberAnimation { duration: 150 } }
    
                        // Drop Shadow
                        Rectangle {
                            anchors.fill: parent; anchors.margins: 4
                            radius: width/2
                            color: "black"; opacity: 0.3
                            anchors.verticalCenterOffset: 4
                        }
    
                        // Outer Ring (Dark)
                        Rectangle {
                            anchors.fill: parent
                            radius: width/2
                            color: "transparent"
                            border.color: "#2c2c2e"
                            border.width: 6 
                        }
    
                        // Inner Content (Canvas for perfect circular masking)
                        Canvas {
                            id: loupeCanvas
                            anchors.fill: parent
                            anchors.margins: 6 // Inside the outer ring
                            property color topColor: canvasPage.samplingColor
                            property color bottomColor: mainCanvas.brushColor
    
                            onTopColorChanged: requestPaint()
                            onBottomColorChanged: requestPaint()
    
                            onPaint: {
                                var ctx = getContext("2d");
                                var w = width;
                                var h = height;
                                var cx = w/2;
                                var cy = h/2;
                                var r = w/2;
    
                                ctx.reset();
                                ctx.clearRect(0,0,w,h);
    
                                // Create Circular Clip
                                ctx.beginPath();
                                ctx.arc(cx, cy, r, 0, 2*Math.PI);
                                ctx.closePath();
                                ctx.clip();
    
                                // Draw Checkerboard (Transparency)
                                ctx.fillStyle = "#dddddd";
                                ctx.fillRect(0,0,w,h);
                                ctx.fillStyle = "#ffffff";
                                var box = 10;
                                for(var y=0; y<h; y+=box) {
                                    for(var x=0; x<w; x+=box) {
                                        if (((x+y)/box)%2 == 0) ctx.fillRect(x,y,box,box);
                                    }
                                }
    
                                // Top Half (New Color)
                                ctx.fillStyle = topColor;
                                ctx.fillRect(0, 0, w, h/2);
    
                                // Bottom Half (Old Color)
                                ctx.fillStyle = bottomColor;
                                ctx.fillRect(0, h/2, w, h/2);
    
                                // Divider Line
                                ctx.beginPath();
                                ctx.moveTo(0, h/2);
                                ctx.lineTo(w, h/2);
                                ctx.lineWidth = 1;
                                ctx.strokeStyle = "white";
                                ctx.stroke();
                            }
                        }
    
                        // Inner Ring (White - High Contrast)
                        Rectangle {
                            anchors.fill: parent
                            anchors.margins: 6
                            radius: width/2
                            color: "transparent"
                            border.color: "white"
                            border.width: 2
                            z: 2
                        }
    
                        // Central Reticle (Crosshair)
                        Item {
                            anchors.centerIn: parent
                            width: 14; height: 14
                            z: 5
    
                            // White box
                            Rectangle {
                                anchors.fill: parent; color: "transparent"
                                border.color: "white"; border.width: 2
                            }
                            // Black inner stroke
                            Rectangle {
                                anchors.fill: parent; anchors.margins: 2
                                color: "transparent"
                                border.color: "black"; border.width: 1
                                opacity: 0.5
                            }
                        }
                    }
                    
                    // Picker Mouse Interaction Overlay
                    MouseArea {
                        anchors.fill: parent
                        enabled: isProjectActive && canvasPage.activeToolIdx === 8
                        z: 900 // Over canvas
                        cursorShape: Qt.CrossCursor
                        
                        onPressed: {
                            canvasPage.isSampling = true
                            canvasPage.samplePos = Qt.point(mouseX, mouseY)
                            canvasPage.samplingColor = mainCanvas.sampleColor(mouseX, mouseY, canvasPage.samplingMode)
                        }
                        onPositionChanged: {
                            canvasPage.samplePos = Qt.point(mouseX, mouseY)
                            canvasPage.samplingColor = mainCanvas.sampleColor(mouseX, mouseY, canvasPage.samplingMode)
                        }
                        onReleased: {
                            canvasPage.isSampling = false
                            mainCanvas.brushColor = canvasPage.samplingColor
                            
                            // If it was a temporary Alt switch, revert tool
                            if (canvasPage.altPressed) {
                                canvasPage.activeToolIdx = canvasPage.lastToolIdx
                            }
                        }
                    } 
                }
                
                // --- CONTEXT BAR (APPLY/CANCEL TRANSFORM) ---
                Rectangle {
                    id: contextBar
                    anchors.bottom: parent.bottom; anchors.bottomMargin: 30
                    anchors.horizontalCenter: parent.horizontalCenter
                    width: 240; height: 48; radius: 24
                    color: "#222226"
                    border.color: "#3e3e42"
                    border.width: 1
                    visible: mainCanvas.isTransforming
                    z: 500
                    
                    Row {
                         anchors.centerIn: parent
                         spacing: 15
                         
                         // Cancel Button
                         Rectangle {
                             width: 90; height: 32; radius: 16; color: "#3a3a3c"
                             Text { text: "Cancel"; color: "white"; anchors.centerIn: parent; font.bold: true }
                             MouseArea { anchors.fill: parent; onClicked: mainCanvas.cancelTransform() }
                         }
                         
                         // Apply Button
                         Rectangle {
                             width: 90; height: 32; radius: 16; color: colorAccent
                             Text { text: "Apply"; color: "white"; anchors.centerIn: parent; font.bold: true }
                             MouseArea { anchors.fill: parent; onClicked: mainCanvas.applyTransform() }
                         }
                    }
                }
                
                // === ADVANCED PROFESSIONAL TOOLBAR MODEL ===
                ListModel {
                    id: toolsModel
                    ListElement { name: "selection"; icon: "selection.svg"; label: "Selection"; subTools: [
                        ListElement { name: "select_rect"; label: "Rectangle"; icon: "selection.svg" },
                        ListElement { name: "select_wand"; label: "Magic Wand"; icon: "wand.svg" }
                    ]}
                    ListElement { name: "shapes"; icon: "shapes.svg"; label: "Shapes"; subTools: [
                        ListElement { name: "rect"; label: "Rectangle"; icon: "shapes.svg" },
                        ListElement { name: "ellipse"; label: "Ellipse"; icon: "shapes.svg" },
                        ListElement { name: "line"; label: "Line"; icon: "shapes.svg" }
                    ]}
                    ListElement { name: "lasso"; icon: "lasso.svg"; label: "Lasso"; subTools: [] }
                    ListElement { name: "magnetic_lasso"; icon: "magnet.svg"; label: "Magnetic Lasso"; subTools: [] }
                    ListElement { name: "move"; icon: "move.svg"; label: "Transform & Move"; subTools: [] }
                    ListElement { name: "pen"; icon: "pen.svg"; label: "Pen"; subTools: [
                        ListElement { name: "INK"; label: "Ink Pen"; icon: "pen.svg" },
                        ListElement { name: "G-PEN"; label: "G-Pen"; icon: "pen.svg" },
                        ListElement { name: "MARU"; label: "Maru Pen"; icon: "pen.svg" }
                    ]}
                    ListElement { name: "pencil"; icon: "pencil.svg"; label: "Pencil"; subTools: [
                        ListElement { name: "HB"; label: "Pencil HB"; icon: "pencil.svg" },
                        ListElement { name: "6B"; label: "Pencil 6B"; icon: "pencil.svg" },
                        ListElement { name: "MECH"; label: "Mechanical"; icon: "pencil.svg" }
                    ]}
                    ListElement { name: "brush"; icon: "brush.svg"; label: "Brush"; subTools: [
                        ListElement { name: "WATER"; label: "Watercolor"; icon: "brush.svg" },
                        ListElement { name: "OIL"; label: "Oil Paint"; icon: "brush.svg" },
                        ListElement { name: "ACRY"; label: "Acrylic"; icon: "brush.svg" }
                    ]}
                    ListElement { name: "airbrush"; icon: "airbrush.svg"; label: "Airbrush"; subTools: [
                        ListElement { name: "SOFT"; label: "Soft"; icon: "airbrush.svg" },
                        ListElement { name: "HARD"; label: "Hard"; icon: "airbrush.svg" }
                    ]}
                    ListElement { name: "eraser"; icon: "eraser.svg"; label: "Eraser"; subTools: [
                        ListElement { name: "E_SOFT"; label: "Soft Eraser"; icon: "eraser.svg" },
                        ListElement { name: "E_HARD"; label: "Hard Eraser"; icon: "eraser.svg" }
                    ]}
                    ListElement { name: "fill"; icon: "fill.svg"; label: "Fill"; subTools: [
                        ListElement { name: "BUCKET"; label: "Bucket Fill"; icon: "fill.svg" },
                        ListElement { name: "LASSO_FILL"; label: "Lasso Fill"; icon: "selection.svg" },
                        ListElement { name: "GRAD"; label: "Gradient Tool"; icon: "gradient.svg" }
                    ]}

                    ListElement { name: "picker"; icon: "picker.svg"; label: "Eyedropper"; subTools: [] }
                    ListElement { name: "hand"; icon: "hand.svg"; label: "Hand"; subTools: [] }
                }

                property int activeToolIdx: 4 // Default to Pen
                
                onActiveToolIdxChanged: {
                    if (canvasPage.altPressed) return // Don't reset if switching via ALT
                    
                    var toolData = toolsModel.get(activeToolIdx)
                    if (toolData && toolData.subTools && toolData.subTools.count > 0) {
                        var subIdx = activeSubToolIdx
                        if (subIdx >= toolData.subTools.count) subIdx = 0
                        
                        // SPECIAL HANDLING FOR NON-BRUSH TOOLS
                        if (toolData.name === "shapes" || toolData.name === "selection" || toolData.name === "fill") {
                            var subName = toolData.subTools.get(subIdx).name
                            console.log("Switching Tool: " + subName)
                            mainCanvas.currentTool = subName
                        } else {
                            // Standard Presets (Pen, Pencil, Brush, Airbrush, Eraser)
                            var presetName = toolData.subTools.get(subIdx).label
                            console.log("Auto-applying Preset on Tool Change: " + presetName)
                            mainCanvas.usePreset(presetName)
                        }
                    } else if (toolData) {
                        // Handlers for tools without subtools
                        if (toolData.name === "eraser") mainCanvas.usePreset("Eraser Soft")
                        if (toolData.name === "lasso") mainCanvas.currentTool = "lasso"
                        if (toolData.name === "magnetic_lasso") mainCanvas.currentTool = "magnetic_lasso"
                        if (toolData.name === "selection") mainCanvas.currentTool = "selection"
                        if (toolData.name === "move") mainCanvas.currentTool = "move"
                    }
                    
                    // UX IMPROVEMENT: Close panels when picking a tool
                    // showBrush = false // Removed to allow library to stay open or open automatically
                    showColor = false
                    showLayers = false
                    
                    // Auto-open library for brush tools
                    if (activeToolIdx >= 4 && activeToolIdx <= 8) {
                        mainWindow.showBrush = true
                    } else {
                        mainWindow.showBrush = false
                    }
                }
                property int activeSubToolIdx: 0
                property bool showSubTools: false
                property bool showToolSettings: false
                property string selectedBrushCategory: "Sketching"
                
                // Eyedropper logic
                property int lastToolIdx: 4
                property int samplingMode: 0 // 0=Composite, 1=Current Layer
                property bool altPressed: false
                
                // Eyedropper (Picker) State
                property color samplingColor: "#ffffff"
                property bool isSampling: false
                property point samplePos: Qt.point(0,0)
                
                // Shortcuts
                Shortcut { sequence: "I"; onActivated: canvasPage.activeToolIdx = 10 }
                Shortcut { sequence: "B"; onActivated: canvasPage.activeToolIdx = 4 }
                Shortcut { sequence: "E"; onActivated: canvasPage.activeToolIdx = 8 }
                
                // Alt logic: Need to capture Alt press/release
                focus: isProjectActive
                Keys.onPressed: (event) => {
                    if (event.key === Qt.Key_Alt) {
                        if (!altPressed && activeToolIdx !== 8) {
                            lastToolIdx = activeToolIdx
                            activeToolIdx = 8
                            altPressed = true
                        }
                        event.accepted = true
                    }
                }
                Keys.onReleased: (event) => {
                    if (event.key === Qt.Key_Alt) {
                        // Restore tool first so the onActiveToolIdxChanged handler sees altPressed=true and ignores it
                        if (!isSampling) {
                            activeToolIdx = lastToolIdx
                        }
                        // Then clear flag
                        altPressed = false
                        event.accepted = true
                    }
                }

                // === SIDE PROFESSIONAL TOOLBAR (RIGHT SIDE - Compact Premium) ===
                Rectangle {
                    id: sideToolbar
                    width: 40
                    height: Math.min(toolsColumn.implicitHeight + 24, parent.height - 60)
                    anchors.right: parent.right
                    anchors.rightMargin: 12
                    anchors.verticalCenter: parent.verticalCenter
                    
                    // Compact Premium glassmorphism
                    color: "#e01a1a1e"
                    radius: 20
                    border.color: Qt.rgba(1, 1, 1, 0.08)
                    border.width: 1
                    visible: isProjectActive
                    z: 200

                    // Subtle inner glow
                    Rectangle { 
                        anchors.fill: parent
                        anchors.margins: 1
                        radius: parent.radius - 1
                        color: "transparent"
                        border.color: Qt.rgba(1, 1, 1, 0.03)
                        border.width: 1
                    }

                    // Shadow
                    Rectangle {
                        anchors.fill: parent
                        anchors.margins: -5
                        z: -1
                        radius: parent.radius + 5
                        color: "black"
                        opacity: 0.35
                    }

                    Column {
                        id: toolsColumn
                        anchors.centerIn: parent
                        spacing: 4
                        
                        Repeater {
                            model: toolsModel
                            delegate: Rectangle {
                                width: 34; height: 34
                                anchors.horizontalCenter: parent.horizontalCenter
                                radius: 12
                                color: (index === canvasPage.activeToolIdx) ? colorAccent : (toolHover.containsMouse ? "#22ffffff" : "transparent")
                                
                                Behavior on color { ColorAnimation { duration: 120 } }
                                
                                Image {
                                    id: toolImg
                                    source: iconPath(model.icon)
                                    width: 20; height: 20
                                    anchors.centerIn: parent
                                    opacity: (index === canvasPage.activeToolIdx) ? 1.0 : 0.6
                                    sourceSize: Qt.size(40, 40)
                                    smooth: true
                                    mipmap: true
                                    
                                    Behavior on opacity { NumberAnimation { duration: 120 } }
                                    
                                    onStatusChanged: if (status === Image.Error) console.log("Error loading icon:", source)
                                }
                                
                                // Fallback characters (Premium emojis/symbols)
                                Text {
                                    visible: toolImg.status !== Image.Ready
                                    text: {
                                        if (model.name === "selection") return "✥"
                                        if (model.name === "shapes") return "▢"
                                        if (model.name === "lasso") return "➰"
                                        if (model.name === "magnetic_lasso") return "🧲"
                                        if (model.name === "move") return "✣"
                                        if (model.name === "pen") return "✒"
                                        if (model.name === "pencil") return "✎"
                                        if (model.name === "brush") return "🖌"
                                        if (model.name === "airbrush") return "💨"
                                        if (model.name === "eraser") return "⌫"
                                        if (model.name === "fill") return "🪣"
                                        if (model.name === "picker") return "💉"
                                        if (model.name === "hand") return "✋"
                                        return "•"
                                    }
                                    color: "white"
                                    font.pixelSize: 18
                                    anchors.centerIn: parent
                                    opacity: toolImg.opacity
                                }
                                
                                MouseArea {
                                    id: toolHover
                                    anchors.fill: parent
                                    cursorShape: Qt.PointingHandCursor
                                    hoverEnabled: true
                                    
                                    Timer {
                                        id: longPressTimer
                                        interval: 500
                                        onTriggered: {
                                            canvasPage.activeToolIdx = index
                                            canvasPage.showSubTools = true
                                            // Position subtool bar next to this button
                                            subToolBar.yLevel = parent.mapToItem(canvasPage, 0, 0).y
                                        }
                                    }

                                    onPressed: longPressTimer.start()
                                    onReleased: {
                                        if (longPressTimer.running) {
                                            longPressTimer.stop()
                                            
                                            // UX: Close Panels on Tool Interaction
                                            mainWindow.showColor = false
                                            mainWindow.showLayers = false
                                            mainWindow.showBrush = false
                                            
                                            // Handle as Click
                                            if (canvasPage.activeToolIdx === index) {
                                                // Toggle Logic based on tool type
                                                if (index >= 4 && index <= 8) {
                                                    // Brushes/Eraser -> Open Brush Library (Gallery) instead of Settings
                                                    mainWindow.showBrush = !mainWindow.showBrush
                                                    if (mainWindow.showBrush) {
                                                        brushLibrary.autoSelectCategory(model.name)
                                                    }
                                                    canvasPage.showToolSettings = false 
                                                    mainWindow.showBrushSettings = false // Close Studio if open
                                                } else {
                                                    // Other tools -> Toggle their specific settings
                                                    canvasPage.showToolSettings = !canvasPage.showToolSettings
                                                }
                                            } else {
                                                canvasPage.activeToolIdx = index
                                                canvasPage.activeSubToolIdx = 0
                                                // Switch tool: Close all popovers initially
                                                canvasPage.showToolSettings = false
                                                canvasPage.showSubTools = false
                                                
                                                // If switching to a brush tool, Open Library automatically
                                                if (index >= 4 && index <= 8) {
                                                    mainWindow.showBrush = true
                                                    brushLibrary.autoSelectCategory(model.name)
                                                    mainWindow.showBrushSettings = false
                                                } else {
                                                    mainWindow.showBrush = false
                                                }
                                                
                                                // Backend Mapping
                                                // Backend Mapping - Pass EXACT names to Python for Filter Logic
                                                var toolName = model.name
                                                 if (toolName === "pen") mainCanvas.currentTool = "pen"
                                                 else if (toolName === "pencil") mainCanvas.currentTool = "pencil"
                                                 else if (toolName === "brush") mainCanvas.currentTool = "brush"
                                                 else if (toolName === "airbrush") mainCanvas.currentTool = "airbrush"
                                                 else if (toolName === "eraser") mainCanvas.currentTool = "eraser"
                                                 else if (toolName === "fill") mainCanvas.currentTool = "fill"
                                                 else if (toolName === "picker") mainCanvas.currentTool = "picker" 
                                                 else if (toolName === "hand") mainCanvas.currentTool = "hand"
                                                 else if (toolName === "selection") mainCanvas.currentTool = "selection"
                                                 else if (toolName === "lasso") mainCanvas.currentTool = "lasso"
                                                 else if (toolName === "magnetic_lasso") mainCanvas.currentTool = "magnetic_lasso"
                                                 else if (toolName === "move") mainCanvas.currentTool = "move"
                                                 else mainCanvas.currentTool = "hand"
                                            }
                                        }
                                    }
                                    onCanceled: longPressTimer.stop()

                                    ToolTip.visible: containsMouse
                                    ToolTip.text: model.label
                                    ToolTip.delay: 800
                                }
                            }
                        }
                    }
                }

                // === TOOL PROPERTIES PANEL (Brush Settings - Premium Floating Panel) ===
                Rectangle {
                    width: 250
                    height: brushPropsLayout.implicitHeight + 40
                    anchors.right: sideToolbar.left
                    anchors.rightMargin: 15
                    anchors.verticalCenter: sideToolbar.verticalCenter
                    
                    radius: 20
                    color: "#f21c1c1e" // Premium OLED
                    border.color: Qt.rgba(1, 1, 1, 0.12)
                    border.width: 1
                    visible: isProjectActive && canvasPage.showToolSettings && (canvasPage.activeToolIdx >= 2 && canvasPage.activeToolIdx <= 8)
                    
                    z: 500
                    
                    // Exit Animation
                    opacity: visible ? 1.0 : 0.0
                    scale: visible ? 1.0 : 0.95
                    Behavior on opacity { NumberAnimation { duration: 150 } }
                    Behavior on scale { NumberAnimation { duration: 200; easing.type: Easing.OutCubic } }
                    
                    /* layer.effect: DropShadow {
                        color: "#80000000"
                        radius: 15
                        samples: 30
                    } */

                    ColumnLayout {
                        id: brushPropsLayout
                        anchors.fill: parent
                        anchors.margins: 20
                        spacing: 15

                        RowLayout {
                            Layout.fillWidth: true
                            Label {
                                text: toolsModel.get(canvasPage.activeToolIdx).label + " Settings"
                                color: "white"; font.pixelSize: 15; font.bold: true
                                Layout.fillWidth: true
                            }
                            Text {
                                text: "×"; color: "#666"; font.pixelSize: 20
                                MouseArea { anchors.fill: parent; onClicked: canvasPage.showToolSettings = false }
                            }
                        }

                        // --- Brush Library (Icons only as requested) ---
                        ColumnLayout {
                            spacing: 8; Layout.fillWidth: true
                            visible: toolsModel.get(canvasPage.activeToolIdx).subTools.count > 0
                            
                            ListView {
                                id: brushLibList
                                Layout.fillWidth: true
                                Layout.preferredHeight: 300 // Prevent collapse
                                clip: true
                                spacing: 12
                                model: mainCanvas.brushFolders
                                
                                Connections {
                                    target: mainCanvas
                                    function onAvailableBrushesChanged() {
                                        console.log("QML: Refreshing Brush Library Model")
                                        brushLibList.model = 0 // Force clear
                                        brushLibList.model = mainCanvas.brushFolders // Re-bind
                                    }
                                }
                                function getBrushIcon(brushName) {
                                    // 1. Check Standard Tools
                                    for(var i = 0; i < toolsModel.count; i++) {
                                        var subs = toolsModel.get(i).subTools;
                                        if (subs) {
                                            for(var j=0; j < subs.count; j++) {
                                                if (subs.get(j).label === brushName) {
                                                    return iconPath(subs.get(j).icon);
                                                }
                                            }
                                        }
                                    }
                                    return iconPath("brush.svg");
                                }
                                
                                delegate: ColumnLayout {
                                    width: ListView.view.width - 10
                                    spacing: 8
                                    
                                    // Header removed as requested by user
                                    
                                    // Brushes Flow
                                    Flow {
                                        Layout.fillWidth: true
                                        spacing: 8
                                        
                                        Repeater {
                                            model: modelData.brushes
                                            delegate: Rectangle {
                                                width: 44; height: 44; radius: 10
                                                color: (mainCanvas.activeBrushName === modelData) ? colorAccent : (bhv.containsMouse ? "#22ffffff" : "#11ffffff")
                                                border.color: (mainCanvas.activeBrushName === modelData) ? "#ffffffff" : "transparent"
                                                border.width: 1
                                                
                                                Image {
                                                    source: brushLibList.getBrushIcon(modelData)
                                                    width: 20; height: 20; anchors.centerIn: parent
                                                    fillMode: Image.PreserveAspectFit
                                                    mipmap: true
                                                    opacity: 0.8
                                                }
                                                
                                                MouseArea {
                                                    id: bhv; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor
                                                    onClicked: mainCanvas.usePreset(modelData)
                                                }
                                                
                                                ToolTip.visible: bhv.containsMouse
                                                ToolTip.text: modelData
                                                ToolTip.delay: 200
                                            }
                                        }
                                    }
                                }
                            }
                            
                            // Import Button Footer
                            Rectangle {
                                width: 44; height: 44; radius: 10
                                color: impHover.containsMouse ? "#22ffffff" : "#11ffffff"
                                border.color: "#33ffffff"; border.width: 1
                                Layout.alignment: Qt.AlignLeft
                                
                                Text { text: "+"; color: "white"; font.pixelSize: 24; anchors.centerIn: parent; opacity: 0.8 }
                                
                                MouseArea {
                                    id: impHover; anchors.fill: parent; cursorShape: Qt.PointingHandCursor; hoverEnabled: true
                                    onClicked: importAbrDialog.open()
                                }
                                
                                ToolTip.visible: impHover.containsMouse
                                ToolTip.text: "Import .abr Brushes"
                            }
                        }


                        Rectangle { height: 1; Layout.fillWidth: true; color: "#1affffff" }

                        // --- SELECTION ACTIONS (Lasso Tools) ---
                        ColumnLayout {
                            spacing: 12; Layout.fillWidth: true
                            visible: (canvasPage.activeToolIdx <= 2) && !mainCanvas.selectionEmpty
                            
                            Rectangle {
                                Layout.fillWidth: true; height: 36; radius: 10
                                color: colorAccent
                                Text { text: "Transform Selection"; color: "white"; font.bold: true; anchors.centerIn: parent }
                                MouseArea { anchors.fill: parent; onClicked: mainCanvas.start_transformation() }
                            }
                            
                            Rectangle {
                                Layout.fillWidth: true; height: 36; radius: 10
                                color: "#1affffff"
                                Text { text: "Deselect"; color: "white"; anchors.centerIn: parent }
                                MouseArea { anchors.fill: parent; onClicked: mainCanvas.clear_selection() }
                            }
                        }

                        // --- Eyedropper Settings (Only if index 8) ---
                        ColumnLayout {
                            spacing: 12; Layout.fillWidth: true
                            visible: canvasPage.activeToolIdx === 8
                            
                            Label { text: "Sample Source"; color: "#888"; font.pixelSize: 11; font.bold: true }
                            
                            Row {
                                spacing: 4
                                Repeater {
                                    model: ["Full Image", "Current Layer"]
                                    delegate: Rectangle {
                                        width: 100; height: 32; radius: 8
                                        color: (index === canvasPage.samplingMode) ? colorAccent : "#1affffff"
                                        
                                        Text {
                                            text: modelData; color: "white"; font.pixelSize: 11; font.bold: index === canvasPage.samplingMode
                                            anchors.centerIn: parent
                                        }
                                        
                                        MouseArea {
                                            anchors.fill: parent; cursorShape: Qt.PointingHandCursor
                                            onClicked: canvasPage.samplingMode = index
                                        }
                                    }
                                }
                            }
                            
                            Label { 
                                text: "Tip: Hold Alt while drawing to pick colors quickly."
                                color: "#666"; font.pixelSize: 10; font.italic: true; 
                                Layout.topMargin: 5
                            }
                        }

                        // --- Brush Settings (Only for Indexes 2-6: Pen, Pencil, Brush, Air, Eraser) ---
                        ColumnLayout {
                            spacing: 15; Layout.fillWidth: true
                            visible: canvasPage.activeToolIdx >= 2 && canvasPage.activeToolIdx <= 6


                            // --- Brush Size ---
                            ColumnLayout {
                                spacing: 5; Layout.fillWidth: true
                                RowLayout {
                                    Label { text: "Size"; color: "#aaa"; font.pixelSize: 11 }
                                    Item { Layout.fillWidth: true }
                                    Label { text: Math.round(mainCanvas.brushSize) + " px"; color: colorAccent; font.pixelSize: 11; font.bold: true }
                                }
                                CustomSlider {
                                    id: sizeSlider; from: 1; to: 500; value: mainCanvas.brushSize
                                    Layout.fillWidth: true
                                    onMoved: mainCanvas.brushSize = value
                                }
                            }

                            // --- Brush Opacity ---
                            ColumnLayout {
                                spacing: 5; Layout.fillWidth: true
                                RowLayout {
                                    Label { text: "Opacity"; color: "#aaa"; font.pixelSize: 11 }
                                    Item { Layout.fillWidth: true }
                                    Label { text: Math.round(mainCanvas.brushOpacity * 100) + " %"; color: colorAccent; font.pixelSize: 11; font.bold: true }
                                }
                                CustomSlider {
                                    id: opacitySlider; from: 0; to: 1; value: mainCanvas.brushOpacity
                                    Layout.fillWidth: true
                                    onMoved: mainCanvas.brushOpacity = value
                                }
                            }

                            // --- Smoothing ---
                            ColumnLayout {
                                spacing: 5; Layout.fillWidth: true
                                RowLayout {
                                    Label { text: "Smoothing"; color: "#aaa"; font.pixelSize: 11 }
                                    Item { Layout.fillWidth: true }
                                    Label { text: Math.round(mainCanvas.brushSmoothing * 100) + " %"; color: colorAccent; font.pixelSize: 11; font.bold: true }
                                }
                                CustomSlider {
                                    from: 0; to: 0.95; value: mainCanvas.brushSmoothing
                                    Layout.fillWidth: true
                                    onMoved: mainCanvas.brushSmoothing = value
                                }
                            }

                            // --- Spacing ---
                            ColumnLayout {
                                spacing: 5; Layout.fillWidth: true
                                RowLayout {
                                    Label { text: "Spacing"; color: "#aaa"; font.pixelSize: 11 }
                                    Item { Layout.fillWidth: true }
                                    Label { text: Math.round(mainCanvas.brushSpacing * 100) + " %"; color: colorAccent; font.pixelSize: 11; font.bold: true }
                                }
                                CustomSlider {
                                    from: 0.01; to: 1.5; value: mainCanvas.brushSpacing
                                    Layout.fillWidth: true
                                    onMoved: mainCanvas.brushSpacing = value
                                }
                            }

                            // --- Hardness ---
                            ColumnLayout {
                                spacing: 5; Layout.fillWidth: true
                                RowLayout {
                                    Label { text: "Hardness"; color: "#aaa"; font.pixelSize: 11 }
                                    Item { Layout.fillWidth: true }
                                    Label { text: Math.round(mainCanvas.brushHardness * 100) + " %"; color: colorAccent; font.pixelSize: 11; font.bold: true }
                                }
                                CustomSlider {
                                    from: 0.01; to: 1.0; value: mainCanvas.brushHardness
                                    Layout.fillWidth: true
                                    onMoved: mainCanvas.brushHardness = value
                                }
                            }

                            // --- Grain / Texture (Graphite Effect) ---
                            ColumnLayout {
                                spacing: 5; Layout.fillWidth: true
                                visible: canvasPage.activeToolIdx === 3 // Only for pencil
                                RowLayout {
                                    Label { text: "Graphite Grain"; color: "#aaa"; font.pixelSize: 11 }
                                    Item { Layout.fillWidth: true }
                                    Label { text: Math.round(mainCanvas.brushGrain * 100) + " %"; color: colorAccent; font.pixelSize: 11; font.bold: true }
                                }
                                CustomSlider {
                                    from: 0; to: 1.0; value: mainCanvas.brushGrain
                                    Layout.fillWidth: true
                                    onMoved: mainCanvas.brushGrain = value
                                }
                            }

                            // --- WATERCOLOR PHYSICS (Premium) ---
                            ColumnLayout {
                                spacing: 15; Layout.fillWidth: true
                                visible: canvasPage.activeToolIdx === 4 || canvasPage.activeToolIdx === 2
                                
                                Rectangle { height: 1; Layout.fillWidth: true; color: "#333"; visible: true }
                                Text { text: "WATERCOLOR PHYSICS"; color: "#666"; font.pixelSize: 10; font.bold: true }

                                // 1. DIFFUSION
                                ColumnLayout {
                                    spacing: 5; Layout.fillWidth: true
                                    RowLayout {
                                        Label { text: "Diffusion"; color: "#aaa"; font.pixelSize: 11 }
                                        Item { Layout.fillWidth: true }
                                        Label { text: Math.round(mainCanvas.brushDiffusion * 100) + "%"; color: colorAccent; font.pixelSize: 11; font.bold: true }
                                    }
                                    Slider {
                                        from: 0; to: 1.0; value: mainCanvas.brushDiffusion
                                        Layout.fillWidth: true
                                        onMoved: mainCanvas.brushDiffusion = value
                                    }
                                }
                                
                                // 2. GRANULATION
                                ColumnLayout {
                                    spacing: 5; Layout.fillWidth: true
                                    RowLayout {
                                        Label { text: "Granulation"; color: "#aaa"; font.pixelSize: 11 }
                                        Item { Layout.fillWidth: true }
                                        Label { text: Math.round(mainCanvas.brushGranulation * 100) + "%"; color: colorAccent; font.pixelSize: 11; font.bold: true }
                                    }
                                    Slider {
                                        from: 0; to: 1.0; value: mainCanvas.brushGranulation
                                        Layout.fillWidth: true
                                        onMoved: mainCanvas.brushGranulation = value
                                    }
                                }
                            }
                        }

                        // --- FILL SETTINGS (Index 7) ---
                        ColumnLayout {
                            spacing: 15; Layout.fillWidth: true
                            visible: canvasPage.activeToolIdx === 7

                            Label { 
                                text: (mainCanvas.fillMode === "lasso") ? "Mode: Lasso Fill" : "Mode: Bucket Fill"
                                color: "#888"; font.pixelSize: 11; font.bold: true 
                            }
                            
                            // Tolerance Slider
                             ColumnLayout {
                                spacing: 5; Layout.fillWidth: true
                                RowLayout {
                                    Label { text: "Tolerance"; color: "#aaa"; font.pixelSize: 11 }
                                    Item { Layout.fillWidth: true }
                                    Label { text: mainCanvas.fillTolerance; color: colorAccent; font.pixelSize: 11; font.bold: true }
                                }
                                CustomSlider {
                                    from: 0; to: 100; value: mainCanvas.fillTolerance
                                    Layout.fillWidth: true
                                    onMoved: mainCanvas.fillTolerance = value
                                }
                            }
                            
                            // Expansion (Gap Close)
                            ColumnLayout {
                                spacing: 5; Layout.fillWidth: true
                                RowLayout {
                                    Label { text: "Expansion / Gap Close"; color: "#aaa"; font.pixelSize: 11 }
                                    Item { Layout.fillWidth: true }
                                    Label { text: mainCanvas.fillExpand + " px"; color: colorAccent; font.pixelSize: 11; font.bold: true }
                                }
                                CustomSlider {
                                    from: 0; to: 10; stepSize: 1; value: mainCanvas.fillExpand
                                    Layout.fillWidth: true
                                    onMoved: mainCanvas.fillExpand = value
                                }
                            }

                            // Sample All Layers
                             RowLayout {
                                CheckBox {
                                    text: "Sample All Layers"
                                    checked: mainCanvas.fillSampleAll
                                    onCheckedChanged: mainCanvas.fillSampleAll = checked
                                    font.pixelSize: 11
                                    palette.text: "#ddd"
                                }
                            }
                        }

                    }
                }

                // === NEW HORIZONTAL SUB-TOOL BAR (Premium Design - Pops out from Sidebar) ===
                Rectangle {
                    id: subToolBar
                    property real yLevel: 0
                    x: sideToolbar.x - width - 15
                    y: Math.max(10, Math.min(yLevel - 4, canvasPage.height - height - 10))
                    width: subToolRow.implicitWidth + 24
                    height: 48
                    radius: 24
                    color: "#f21c1c1e" // OLED Dark
                    border.color: Qt.rgba(1, 1, 1, 0.15)
                    border.width: 1
                    visible: isProjectActive && canvasPage.showSubTools && toolsModel.get(canvasPage.activeToolIdx).subTools.count > 0
                    z: 600
                    
                    // Glassmorphism shadow
                    layer.enabled: true
                    /* layer.effect: DropShadow {
                        transparentBorder: true
                        color: "#aa000000"
                        radius: 20
                        samples: 40
                    } */

                    opacity: visible ? 1.0 : 0.0
                    scale: visible ? 1.0 : 0.8
                    transformOrigin: Item.Right
                    Behavior on opacity { NumberAnimation { duration: 150 } }
                    Behavior on scale { NumberAnimation { duration: 250; easing.type: Easing.OutBack } }

                    Row {
                        id: subToolRow
                        anchors.centerIn: parent; spacing: 10
                        Repeater {
                            model: toolsModel.get(canvasPage.activeToolIdx).subTools
                            delegate: Rectangle {
                                width: 36; height: 36; radius: 18
                                color: (index === canvasPage.activeSubToolIdx) ? colorAccent : (subHover.containsMouse ? "#22ffffff" : "transparent")
                                
                                Behavior on color { ColorAnimation { duration: 150 } }

                                Image {
                                    id: subIcon
                                    source: iconPath(model.icon)
                                    width: 18; height: 18; anchors.centerIn: parent
                                    opacity: (index === canvasPage.activeSubToolIdx) ? 1.0 : 0.6
                                    smooth: true
                                }

                                // Fallback
                                Text {
                                    visible: subIcon.status !== Image.Ready
                                    text: model.label.substring(0, 1)
                                    color: "white"; font.pixelSize: 14; font.bold: true; anchors.centerIn: parent
                                    opacity: subIcon.opacity
                                }
                                
                                MouseArea {
                                    id: subHover; anchors.fill: parent; cursorShape: Qt.PointingHandCursor; hoverEnabled: true
                                    onClicked: {
                                        canvasPage.activeSubToolIdx = index
                                        canvasPage.showSubTools = false 
                                        
                                        // Auto-apply preset if it exists in backend
                                        mainCanvas.usePreset(model.label)
                                        
                                        // Update Selection Mode
                                        if (model.name === "LASSO") {
                                            mainCanvas.currentTool = "selection"
                                            mainCanvas.fillMode = "none" // Ensure not in lasso fill
                                        } else if (model.name === "MAGNETIC") {
                                            mainCanvas.currentTool = "magnetic_lasso"
                                        }
                                        
                                        // Update Fill Mode
                                        if (model.name === "LASSO_FILL") mainCanvas.fillMode = "lasso"
                                        else if (model.name === "BUCKET") mainCanvas.fillMode = "bucket"
                                    }

                                }
                                
                                ToolTip.visible: subHover.containsMouse
                                ToolTip.text: model.label
                                ToolTip.delay: 300
                            }
                        }
                    }
                }

                // Invisible overlay to dismiss settings when clicking outside
                MouseArea {
                    anchors.fill: parent
                    z: 50 // Above canvas but below bars
                    enabled: canvasPage.showSubTools || canvasPage.showToolSettings
                    onPressed: {
                        canvasPage.showSubTools = false
                        canvasPage.showToolSettings = false
                    }
                }


                // EMPTY STATE OVERLAY
                Rectangle {
                    anchors.fill: parent
                    color: "#050507"
                    visible: !isProjectActive
                    z: 1000
                    
                    Column {
                        anchors.centerIn: parent
                        spacing: 20
                        
                        Image {
                            source: iconPath("brush.svg")
                            width: 64; height: 64
                            anchors.horizontalCenter: parent.horizontalCenter
                            opacity: 0.2
                        }
                        
                        Text {
                            text: "No Project Active"
                            color: "#444"
                            font.pixelSize: 24
                            font.bold: true
                            anchors.horizontalCenter: parent.horizontalCenter
                        }
                        
                        Text {
                            text: "Please create a new canvas or open a recent\nproject from the Gallery to start drawing."
                            color: "#333"
                            font.pixelSize: 14
                            horizontalAlignment: Text.AlignHCenter
                            anchors.horizontalCenter: parent.horizontalCenter
                        }
                        
                        Rectangle {
                            width: 180; height: 44; radius: 22
                            color: colorAccent
                            anchors.horizontalCenter: parent.horizontalCenter
                            
                            Text { text: "Quick Draw"; color: "white"; anchors.centerIn: parent; font.bold: true }
                            
                            MouseArea {
                                anchors.fill: parent
                                cursorShape: Qt.PointingHandCursor
                                onClicked: {
                                    mainCanvas.resizeCanvas(1920, 1080)
                                    isProjectActive = true
                                    currentPage = 1
                                    mainCanvas.fitToView()
                                }
                            }
                        }

                        Text {
                            text: "or"
                            color: "#222"
                            font.pixelSize: 12
                            anchors.horizontalCenter: parent.horizontalCenter
                        }

                        Rectangle {
                            width: 180; height: 44; radius: 22
                            color: "transparent"
                            border.color: "#1a1a1c"
                            anchors.horizontalCenter: parent.horizontalCenter
                            
                            Text { text: "Go to Gallery"; color: "#666"; anchors.centerIn: parent; font.bold: true }
                            
                            MouseArea {
                                anchors.fill: parent
                                cursorShape: Qt.PointingHandCursor
                                onClicked: currentPage = 0
                            }
                        }
                    }
                }
                
                // ATAJOS DE TECLADO
                // ATAJOS DE TECLADO (Managed by Python handle_shortcuts now)
                /*
                Shortcut { sequences: ["Ctrl+Z"]; onActivated: mainCanvas.undo() }
                Shortcut { sequences: ["Ctrl+Y", "Ctrl+Shift+Z"]; onActivated: mainCanvas.redo() }
                Shortcut { sequences: ["Ctrl+S"]; onActivated: mainWindow.saveProjectAndRefresh() }
                Shortcut { sequences: ["Ctrl+0"]; onActivated: mainCanvas.fitToView() }
                Shortcut { sequences: ["B"]; onActivated: mainCanvas.currentTool = "brush" }
                Shortcut { sequences: ["E"]; onActivated: mainCanvas.currentTool = "eraser" }
                Shortcut { sequences: ["H"]; onActivated: mainCanvas.currentTool = "hand" }
                Shortcut { sequences: ["Tab"]; onActivated: isZenMode = !isZenMode }
                */

                // === MOVABLE PREMIUM SLIDERS TOOLBOX (Adaptive Orientation) ===
                Rectangle {
                    id: sliderToolbox
                    x: 20
                    y: 150 // Static initial Y to avoid startup loops
                    visible: isProjectActive && !isZenMode
                    opacity: visible ? 0.98 : 0.0
                    Behavior on opacity { NumberAnimation { duration: 300 } }
                    
                    // Adaptive dimensions based on orientation
                    property bool isHorizontal: false
                    
                    // Hysteresis logic to prevent flickering
                    onYChanged: {
                        var topDist = 100
                        var bottomDist = parent.height - 480
                        
                        if (y < topDist) {
                            if (!isHorizontal) isHorizontal = true
                        } else if (y > bottomDist) {
                            if (!isHorizontal) isHorizontal = true
                        } else {
                            if (isHorizontal) isHorizontal = false
                        }
                    }
                    
                    // Center vertically once parent is ready
                    Component.onCompleted: {
                        if (parent.height > 600) {
                            y = (parent.height - height) / 2
                        }
                    }                    
                    width: isHorizontal ? 420 : 46
                    height: isHorizontal ? 60 : 420
                    radius: isHorizontal ? 30 : 23
                    color: "#cc1c1c1e"
                    border.color: "#ffffff"
                    border.width: 0.5
                    opacity: 0.98
                    z: 90
                    
                    Behavior on width { NumberAnimation { duration: 200; easing.type: Easing.OutQuad } }
                    Behavior on height { NumberAnimation { duration: 200; easing.type: Easing.OutQuad } }
                    Behavior on radius { NumberAnimation { duration: 200 } }
                    
                    // Glass Background Blur Simulation
                    Rectangle { anchors.fill: parent; radius: parent.radius; color: "#ffffff"; opacity: 0.03 }
                    
                    // Shadow
                    Rectangle {
                        anchors.fill: parent; anchors.margins: -10
                        z: -1; radius: parent.radius + 10; color: "black"; opacity: 0.4
                    }

                    // Drag Handle (Only this area is draggable)
                    Rectangle {
                        id: toolboxHeader
                        width: sliderToolbox.isHorizontal ? 50 : parent.width
                        height: sliderToolbox.isHorizontal ? parent.height : 36
                        color: "transparent"
                        anchors.left: sliderToolbox.isHorizontal ? parent.left : undefined
                        anchors.top: sliderToolbox.isHorizontal ? parent.top : parent.top
                        anchors.horizontalCenter: sliderToolbox.isHorizontal ? undefined : parent.horizontalCenter
                        
                        // Drag Indicator
                        Row {
                            visible: sliderToolbox.isHorizontal
                            anchors.centerIn: parent
                            spacing: 3
                            Rectangle { width: 1.5; height: 14; radius: 1; color: "#666" }
                            Rectangle { width: 1.5; height: 14; radius: 1; color: "#666" }
                        }
                        Column {
                            visible: !sliderToolbox.isHorizontal
                            anchors.centerIn: parent
                            spacing: 3
                            Rectangle { width: 14; height: 1.5; radius: 1; color: "#666" }
                            Rectangle { width: 14; height: 1.5; radius: 1; color: "#666" }
                        }
                        
                        MouseArea {
                            id: toolboxDrag
                            anchors.fill: parent
                            drag.target: sliderToolbox
                            drag.axis: Drag.XAndYAxis
                            drag.minimumX: 10
                            drag.maximumX: mainWindow.width - sliderToolbox.width - 10
                            drag.minimumY: 50
                            drag.maximumY: mainWindow.height - sliderToolbox.height - 20
                            cursorShape: pressed ? Qt.ClosedHandCursor : Qt.OpenHandCursor
                            
                            onPressed: sliderToolbox.scale = 1.02
                            onReleased: sliderToolbox.scale = 1.0
                        }
                    }

                    // === VERTICAL LAYOUT (Left/Right edges) ===
                    Column {
                        visible: !sliderToolbox.isHorizontal
                        anchors.top: toolboxHeader.bottom
                        anchors.topMargin: 5
                        anchors.horizontalCenter: parent.horizontalCenter
                        spacing: 25
                        
                        ProSlider {
                            label: "Size"
                            value: mainCanvas.brushSize / 100.0
                            previewType: "size"
                            previewOnRight: (sliderToolbox.x < mainWindow.width / 2)
                            onValueChanged: { if (mainCanvas) mainCanvas.brushSize = value * 100 }
                        }
                        
                        ProSlider {
                            label: "Opac"
                            value: mainCanvas.brushOpacity
                            previewType: "opacity"
                            previewOnRight: (sliderToolbox.x < mainWindow.width / 2)
                            onValueChanged: { if (mainCanvas) mainCanvas.brushOpacity = value }
                        }
                    }

                    // === HORIZONTAL LAYOUT (Top/Bottom edges) ===
                    Row {
                        visible: sliderToolbox.isHorizontal
                        anchors.left: toolboxHeader.right
                        anchors.leftMargin: 10
                        anchors.verticalCenter: parent.verticalCenter
                        spacing: 30
                        
                        ProSliderHorizontal {
                            label: "Size"
                            value: mainCanvas.brushSize / 100.0
                            previewType: "size"
                            previewOnBottom: (sliderToolbox.y < mainWindow.height / 2)
                            onValueChanged: { if (mainCanvas) mainCanvas.brushSize = value * 100 }
                        }
                        
                        ProSliderHorizontal {
                            label: "Opac"
                            value: mainCanvas.brushOpacity
                            previewType: "opacity"
                            previewOnBottom: (sliderToolbox.y < mainWindow.height / 2)
                            onValueChanged: { if (mainCanvas) mainCanvas.brushOpacity = value }
                        }
                    }
                    
                    Behavior on scale { NumberAnimation { duration: 150; easing.type: Easing.OutBack } }
                }


                // === TRANSFORM CONTROLS (Floating Bar) ===
                Rectangle {
                    id: transformBar
                    width: 220; height: 56
                    anchors.bottom: parent.bottom; anchors.bottomMargin: 80
                    anchors.horizontalCenter: parent.horizontalCenter
                    color: "#f21c1c1e"
                    radius: 28
                    border.color: colorAccent
                    border.width: 1
                    visible: mainCanvas.isTransforming
                    z: 500 // Above canvas, below toolbars if needed, or above everything? 
                    
                    // Shadow
                    Rectangle { anchors.fill: parent; anchors.margins: -10; z: -1; radius: 38; color: "black"; opacity: 0.5 }

                    Row {
                        anchors.centerIn: parent
                        spacing: 25
                        
                        // Cancel
                        Rectangle {
                            width: 44; height: 44; radius: 22; color: "#1affffff"
                            Text { text: "✕"; color: "white"; anchors.centerIn: parent; font.pixelSize: 20 }
                            MouseArea { anchors.fill: parent; onClicked: mainCanvas.commit_transformation() }
                        }
                        
                        // Divider
                        Rectangle { width: 1; height: 30; color: "#33ffffff"; anchors.verticalCenter: parent.verticalCenter }

                        // Confirm
                        Rectangle {
                            width: 44; height: 44; radius: 22; color: colorAccent
                            Text { text: "✓"; color: "white"; anchors.centerIn: parent; font.pixelSize: 20; font.bold: true }
                            MouseArea { anchors.fill: parent; onClicked: mainCanvas.commit_transformation() }
                        }
                    }
                    
                    // Simple Entrance Animation
                    opacity: visible ? 1.0 : 0.0
                    scale: visible ? 1.0 : 0.8
                    Behavior on opacity { NumberAnimation { duration: 200 } }
                    Behavior on scale { NumberAnimation { duration: 300; easing.type: Easing.OutBack } }
                }

                // === TOP BAR (MINIMALIST PREMIUM REDESIGN V2) ===
                Rectangle {
                    id: topBar
                    width: parent.width; height: 42
                    color: "#e8101012"
                    visible: isProjectActive && !isZenMode
                    z: 50
                    
                    MouseArea { anchors.fill: parent; hoverEnabled: true; acceptedButtons: Qt.NoButton }
                    
                    // Subtle glass effect
                    Rectangle { anchors.fill: parent; color: "#ffffff"; opacity: 0.02 }
                    Rectangle { height: 1; width: parent.width; anchors.bottom: parent.bottom; color: "#1affffff" }
                    
                    RowLayout {
                        anchors.fill: parent; anchors.leftMargin: 12; anchors.rightMargin: 16
                        spacing: 10
                        
                        // === LEFT: NAVIGATION ===
                        
                        // Sidebar Toggle
                        Rectangle {
                            width: 28; height: 28; radius: 6
                            color: sidebarToggleMouse.containsMouse ? "#22ffffff" : "transparent"
                            
                            Column {
                                anchors.centerIn: parent; spacing: 3
                                Rectangle { width: 12; height: 1.5; radius: 1; color: showSidebar ? colorAccent : "#777" }
                                Rectangle { width: 8; height: 1.5; radius: 1; color: showSidebar ? colorAccent : "#777" }
                                Rectangle { width: 12; height: 1.5; radius: 1; color: showSidebar ? colorAccent : "#777" }
                            }
                            
                            MouseArea { 
                                id: sidebarToggleMouse
                                anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor
                                onClicked: showSidebar = !showSidebar
                            }
                        }
                        
                        // Back Arrow
                        Rectangle {
                            width: 28; height: 28; radius: 6
                            color: backMouse.containsMouse ? "#22ffffff" : "transparent"
                            Text { text: "←"; color: "#888"; font.pixelSize: 14; anchors.centerIn: parent }
                            MouseArea { id: backMouse; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: currentPage = 0 }
                        }
                        
                        // Project Name
                        Text { 
                            text: mainCanvas.currentProjectName === "Untitled" ? "Untitled" : mainCanvas.currentProjectName
                            color: "#777"; font.pixelSize: 11
                            elide: Text.ElideMiddle
                            Layout.maximumWidth: 100
                        }
                        
                        // Save Button
                        Rectangle {
                            width: 50; height: 24; radius: 12
                            color: saveMouse.containsMouse ? colorAccent : "#1affffff"
                            Text { text: "Save"; color: saveMouse.containsMouse ? "white" : "#aaa"; font.pixelSize: 10; font.weight: Font.Medium; anchors.centerIn: parent }
                            MouseArea { id: saveMouse; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: mainWindow.saveProjectAndRefresh() }
                        }
                        
                        // Separator
                        Rectangle { width: 1; height: 18; color: "#22ffffff"; Layout.alignment: Qt.AlignVCenter }
                        
                        // === CENTER: UNDO/REDO + SLIDERS (Together) ===
                        
                        // Undo
                        Rectangle {
                            width: 26; height: 26; radius: 6
                            color: undoMouse.containsMouse ? "#22ffffff" : "transparent"
                            Image { source: iconPath("undo.svg"); width: 12; height: 12; anchors.centerIn: parent; opacity: 0.7 }
                            MouseArea { id: undoMouse; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: mainCanvas.undo() }
                        }
                        
                        // Redo
                        Rectangle {
                            width: 26; height: 26; radius: 6
                            color: redoMouse.containsMouse ? "#22ffffff" : "transparent"
                            Image { source: iconPath("redo.svg"); width: 12; height: 12; anchors.centerIn: parent; opacity: 0.7 }
                            MouseArea { id: redoMouse; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: mainCanvas.redo() }
                        }
                        

                        
                        Item { Layout.fillWidth: true } // Spacer
                        
                        // === RIGHT: TOOLS & PANELS ===
                        
                        // Timelapse Indicator (Minimal)
                        Rectangle {
                            id: tlIndicator
                            property bool tlRecording: true
                            width: 22; height: 22; radius: 11
                            color: tlIndicatorMouse.containsMouse ? "#22ffffff" : "transparent"
                            
                            Rectangle {
                                width: 6; height: 6; radius: 3
                                anchors.centerIn: parent
                                color: parent.tlRecording ? "#ff3b30" : "#444"
                                
                                SequentialAnimation on opacity {
                                    running: tlIndicator.tlRecording
                                    loops: Animation.Infinite
                                    NumberAnimation { to: 0.3; duration: 800 }
                                    NumberAnimation { to: 1.0; duration: 800 }
                                }
                            }
                            
                            MouseArea {
                                id: tlIndicatorMouse
                                anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor
                                onClicked: tlMiniMenu.visible = !tlMiniMenu.visible
                            }
                            
                            // Mini Menu
                            Rectangle {
                                id: tlMiniMenu
                                visible: false
                                width: 130; height: 65
                                color: "#1c1c1e"
                                radius: 8
                                border.color: "#333"
                                anchors.top: parent.bottom; anchors.topMargin: 6
                                anchors.right: parent.right
                                z: 1000
                                
                                Column {
                                    anchors.centerIn: parent; spacing: 3
                                    
                                    Rectangle {
                                        width: 115; height: 26; radius: 5
                                        color: tlRecMouse.containsMouse ? "#333" : "transparent"
                                        Text { text: tlIndicator.tlRecording ? "Pause" : "Resume"; color: "white"; font.pixelSize: 10; anchors.centerIn: parent }
                                        MouseArea {
                                            id: tlRecMouse; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor
                                            onClicked: { tlIndicator.tlRecording = !tlIndicator.tlRecording; tlMiniMenu.visible = false }
                                        }
                                    }
                                    
                                    Rectangle {
                                        width: 115; height: 26; radius: 5
                                        color: tlExpMouse.containsMouse ? "#333" : "transparent"
                                        Text { text: "Export Video"; color: "white"; font.pixelSize: 10; anchors.centerIn: parent }
                                        MouseArea {
                                            id: tlExpMouse; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor
                                            onClicked: { tlMiniMenu.visible = false; videoConfigDialog.open() }
                                        }
                                    }
                                }
                            }
                        }
                        
                        // Separator
                        Rectangle { width: 1; height: 14; color: "#15ffffff"; Layout.alignment: Qt.AlignVCenter }
                        
                        // === PREMIUM REFERENCE BUTTON ===
                        Rectangle {
                            id: refBtn
                            width: 30; height: 30; radius: 8
                            // Glow effect on active/hover
                            color: refWindow.active ? Qt.rgba(colorAccent.r, colorAccent.g, colorAccent.b, 0.4) : (refBtnMouse.containsMouse ? "#22ffffff" : "transparent")
                            border.color: refWindow.active ? colorAccent : (refBtnMouse.containsMouse ? "#444" : "transparent")
                            border.width: 1
                            
                            // Subtle shadow for premium feel
                            Rectangle {
                                anchors.fill: parent; z: -1; radius: 8
                                color: colorAccent; opacity: (refBtnMouse.containsMouse || refWindow.active) ? 0.3 : 0
                                visible: opacity > 0
                                scale: 1.2; anchors.margins: -4
                            }
                            
                            Image {
                                source: iconPath("image.svg")
                                width: 14; height: 14; anchors.centerIn: parent
                                opacity: refWindow.active ? 1.0 : 0.7
                                Behavior on opacity { NumberAnimation { duration: 150 } }
                            }
                            
                            // Micro-animation indicator
                            Rectangle {
                                anchors.bottom: parent.bottom; anchors.bottomMargin: 2; anchors.horizontalCenter: parent.horizontalCenter
                                width: refWindow.active ? 4 : 0; height: 2; radius: 1; color: colorAccent
                                Behavior on width { NumberAnimation { duration: 200; easing.type: Easing.OutBack } }
                            }
                            
                            MouseArea {
                                id: refBtnMouse
                                anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor
                                onClicked: {
                                    refWindow.active = !refWindow.active
                                    // Feedback animation
                                    refBtnPulse.start()
                                }
                            }
                            
                            SequentialAnimation {
                                id: refBtnPulse
                                NumberAnimation { target: refBtn; property: "scale"; from: 1.0; to: 0.85; duration: 80 }
                                NumberAnimation { target: refBtn; property: "scale"; from: 0.85; to: 1.0; duration: 150; easing.type: Easing.OutBack }
                            }
                        }

                        // Separator
                        Rectangle { width: 1; height: 14; color: "#15ffffff"; Layout.alignment: Qt.AlignVCenter }
                        
                        // BRUSH SETTINGS BUTTON (Opens dedicated settings panel)
                        Rectangle {
                            width: 26; height: 26; radius: 6
                            color: showBrushSettings ? Qt.rgba(colorAccent.r, colorAccent.g, colorAccent.b, 0.3) : (brushSettingsMouse.containsMouse ? "#22ffffff" : "transparent")
                            border.color: showBrushSettings ? colorAccent : "transparent"
                            
                            Image { source: iconPath("sliders.svg"); width: 12; height: 12; anchors.centerIn: parent; opacity: showBrushSettings ? 1 : 0.6 }
                            
                            MouseArea { 
                                id: brushSettingsMouse
                                anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor
                                onClicked: { showBrushSettings = !showBrushSettings; showBrush = false; showLayers = false; showColor = false }
                            }
                        }
                        
                        // Layers Button
                        Rectangle {
                            width: 26; height: 26; radius: 6
                            color: showLayers ? Qt.rgba(colorAccent.r, colorAccent.g, colorAccent.b, 0.3) : (layersBtnMouse.containsMouse ? "#22ffffff" : "transparent")
                            border.color: showLayers ? colorAccent : "transparent"
                            
                            Image { source: iconPath("layers.svg"); width: 12; height: 12; anchors.centerIn: parent; opacity: showLayers ? 1 : 0.6 }
                            
                            MouseArea { 
                                id: layersBtnMouse
                                anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor
                                onClicked: { showLayers = !showLayers; showColor = false; showBrush = false; showBrushSettings = false }
                            }
                        }
                        
                        // Color Swatch
                        Rectangle {
                            width: 22; height: 22; radius: 11
                            color: mainCanvas.brushColor
                            border.color: showColor ? "white" : "#444"
                            border.width: 2
                            
                            MouseArea { 
                                id: colorBtnArea
                                anchors.fill: parent; cursorShape: Qt.PointingHandCursor
                                
                                property bool isDragging: false
                                property point startPos
                                
                                onPressed: (mouse) => {
                                    startPos = Qt.point(mouse.x, mouse.y)
                                    isDragging = false 
                                    dropOrb.dropColor = mainCanvas.brushColor
                                }
                                
                                onPositionChanged: (mouse) => {
                                    if (!pressed) return
                                    var dist = Math.sqrt(Math.pow(mouse.x - startPos.x, 2) + Math.pow(mouse.y - startPos.y, 2))
                                    if (dist > 8 && !isDragging) {
                                        isDragging = true
                                        dropOrb.active = true
                                    }
                                    if (isDragging) {
                                        var globalPos = mapToItem(canvasPage, mouse.x, mouse.y)
                                        dropOrb.x = globalPos.x
                                        dropOrb.y = globalPos.y
                                    }
                                }
                                
                                onReleased: (mouse) => {
                                    if (isDragging) {
                                        dropOrb.active = false
                                        var canvasPos = mapToItem(mainCanvas, mouse.x, mouse.y)
                                        mainCanvas.apply_color_drop(canvasPos.x, canvasPos.y, mainCanvas.brushColor)
                                    } else {
                                        showColor = !showColor; showLayers = false; showBrush = false; showBrushSettings = false
                                    }
                                    isDragging = false
                                }
                            }
                        }
                    }
                }
                
                // MASCARA LOCAL (Solo cubre el canvas y herramientas inferiores)
                MouseArea {
                    anchors.fill: parent
                    enabled: showLayers || showColor || showBrush || showBrushSettings
                    z: 90 // Debajo de los paneles (z=100) pero encima de canvas/herramientas
                    onClicked: {
                        if (showLayers && (layersList.swipedIndex !== -1 || layersList.optionsIndex !== -1 || layerContextMenu.visible)) {
                            // First priority: Close menus/swipes within layers modal
                            layersList.swipedIndex = -1
                            layersList.optionsIndex = -1
                            layerContextMenu.visible = false
                        } else {
                            // Standard: Close the modal
                            showLayers = false
                            showColor = false
                            showBrush = false
                            showBrushSettings = false
                        }
                    }
                }

                // === SUPER PREMIUM NAVIGATOR / REFERENCE PANEL ===
                Rectangle {
                    id: refWindow
                    
                    // State & Visibility
                    property bool active: false
                    visible: opacity > 0
                    opacity: active ? 1.0 : 0.0
                    scale: active ? 1.0 : 0.92
                    
                    onActiveChanged: if(active) mainCanvas.canvasPreviewChanged.emit()

                    // Size constraints
                    property real minW: 150; property real maxW: 500
                    property real minH: 120; property real maxH: 450
                    
                    width: 260; height: 200
                    x: parent.width - width - 16; y: 80
                    
                    // Super clean dark glass
                    color: "#f0101012"
                    radius: 12
                    z: 1500
                    clip: true
                    
                    // Subtle border only on hover
                    border.color: refHoverArea.containsMouse ? "#22ffffff" : "#0affffff"
                    border.width: 1
                    
                    // Transitions
                    Behavior on opacity { NumberAnimation { duration: 200; easing.type: Easing.OutCubic } }
                    Behavior on scale { NumberAnimation { duration: 280; easing.type: Easing.OutBack } }
                    Behavior on width { NumberAnimation { duration: 100 } }
                    Behavior on height { NumberAnimation { duration: 100 } }
                    
                    // Soft Shadow
                    Rectangle { 
                        z: -1; anchors.fill: parent; anchors.margins: -10
                        color: "#000"; opacity: 0.5; radius: 20 
                    }
                    
                    property string mode: "canvas" // "canvas" or "image"
                    property string refTool: "move" // "move" or "pick"
                    property string refSource: ""
                    property real navZoom: 1.0
                    property bool flipH: false
                    property point panOffset: Qt.point(0,0)
                    
                    // Main hover detector
                    MouseArea {
                        id: refHoverArea
                        anchors.fill: parent
                        hoverEnabled: true
                        acceptedButtons: Qt.NoButton
                        function onWheel(wheel) { wheel.accepted = true }
                    }
                    
                    // ===== HEADER (Minimal) =====
                    Item {
                        id: refHeader
                        width: parent.width; height: 28
                        z: 10

                        // Drag area (Background)
                        MouseArea {
                            anchors.fill: parent
                            drag.target: refWindow
                            drag.axis: Drag.XAndYAxis
                            drag.minimumX: 0; drag.maximumX: mainWindow.width - refWindow.width
                            drag.minimumY: 0; drag.maximumY: mainWindow.height - refWindow.height
                            cursorShape: Qt.OpenHandCursor
                            function onWheel(wheel) { wheel.accepted = true }
                        }
                        
                        // Title
                        Text { 
                            text: refWindow.mode === "canvas" ? "Navigator" : "Reference"
                            color: "#aaa"; font.pixelSize: 10; font.weight: Font.DemiBold
                            anchors.left: parent.left; anchors.leftMargin: 12
                            anchors.verticalCenter: parent.verticalCenter
                            font.letterSpacing: 0.3
                        }
                        
                        // Tab switcher (compact pills)
                        Row {
                            anchors.centerIn: parent
                            spacing: 2
                            
                            Rectangle {
                                width: 36; height: 18; radius: 9
                                color: refWindow.mode === "canvas" ? "#333" : "transparent"
                                Text { text: "Nav"; color: refWindow.mode === "canvas" ? "#fff" : "#555"; font.pixelSize: 8; font.weight: Font.Bold; anchors.centerIn: parent }
                                MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: refWindow.mode = "canvas" }
                            }
                            Rectangle {
                                width: 36; height: 18; radius: 9
                                color: refWindow.mode === "image" ? "#333" : "transparent"
                                Text { text: "Ref"; color: refWindow.mode === "image" ? "#fff" : "#555"; font.pixelSize: 8; font.weight: Font.Bold; anchors.centerIn: parent }
                                MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: refWindow.mode = "image" }
                            }
                        }
                        
                        // Close button
                        Rectangle {
                            width: 18; height: 18; radius: 9
                            color: closeRefMouse.containsMouse ? "#44ffffff" : "transparent"
                            anchors.right: parent.right; anchors.rightMargin: 8; anchors.verticalCenter: parent.verticalCenter
                            Text { text: "×"; color: "#666"; font.pixelSize: 12; anchors.centerIn: parent }
                            MouseArea { id: closeRefMouse; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: refWindow.active = false }
                        }
                    }
                    
                    // ===== CONTENT AREA (Full bleed, minimal padding) =====
                    Rectangle {
                        id: refContent
                        anchors.top: refHeader.bottom
                        anchors.left: parent.left; anchors.right: parent.right
                        anchors.bottom: refFooter.top
                        anchors.margins: 4
                        anchors.topMargin: 0
                        color: "#080809"
                        radius: 6
                        clip: true
                        
                        // Canvas/Image Preview with Pan & Zoom
                           // PROCRETE-STYLE GESTURES
                        MultiPointTouchArea {
                            anchors.fill: parent
                            mouseEnabled: false // Let mouse/pen pass through to QCanvasItem
                            z: 100 // Above canvas
                            
                            property point lastCentroid: Qt.point(0,0)
                            property bool isPanning: false

                            onPressed: (touchPoints) => {
                                if (touchPoints.length === 2) {
                                    // Start Pan
                                    isPanning = true
                                    var p1 = touchPoints[0]
                                    var p2 = touchPoints[1]
                                    lastCentroid = Qt.point((p1.x + p2.x)/2, (p1.y + p2.y)/2)
                                } else if (touchPoints.length === 3) {
                                    isPanning = false
                                }
                            }
                            
                            onUpdated: (touchPoints) => {
                                if (isPanning && touchPoints.length === 2) {
                                    var p1 = touchPoints[0]
                                    var p2 = touchPoints[1]
                                    var currentCentroid = Qt.point((p1.x + p2.x)/2, (p1.y + p2.y)/2)
                                    
                                    var dx = currentCentroid.x - lastCentroid.x
                                    var dy = currentCentroid.y - lastCentroid.y
                                    
                                    mainCanvas.pan_canvas(dx, dy)
                                    lastCentroid = currentCentroid
                                }
                            }
                            
                            onReleased: (touchPoints) => {
                                if (isPanning && touchPoints.length < 2) {
                                    // End Pan check - if it was a short tap, treat as Undo
                                    // Here we might need logic to distinguish tap vs drag.
                                    // For now, simpler: Tap logic was in onPressed previously, but that triggers immediately.
                                    // Undo on release is safer if no movement occurred.
                                    isPanning = false
                                }
                                
                                // Reset Tap Logic
                                // If we want 2-finger TAP for Undo, we should measure time or distance.
                                // Simple approach: If clean 2 finger press & release without much movement -> Undo.
                                // Current code has onPressed handling "Undo" immediately.
                                // That conflicts with Pan.
                                // Improved Logic: 
                                // On Press 2 fingers: Reset movement tracker.
                                // On Update: if moved > threshold, it's a pan.
                                // On Release: if not moved, it's undo.
                            }
                            
                            // To simplify, let's separate Tap (Undo) vs Drag (Pan).
                        } // End MultiPointTouchArea
                        
                        // (Touch logic handled by MultiPointTouchArea above)
                        
                        Item {
                            id: contentContainer
                            anchors.fill: parent
                            clip: true

                            // Image Item
                            Item {
                                id: imgHolder
                                width: parent.width
                                height: parent.height
                                
                                // Panning Transform
                                x: refWindow.panOffset.x
                                y: refWindow.panOffset.y
                                scale: refWindow.navZoom
                                
                                transformOrigin: Item.Center
                                
                                transform: Scale { 
                                    origin.x: imgHolder.width / 2
                                    origin.y: imgHolder.height / 2
                                    xScale: refWindow.flipH ? -1 : 1 
                                }

                                Image {
                                    id: refImage
                                    anchors.fill: parent
                                    fillMode: Image.PreserveAspectFit
                                    mipmap: true
                                    source: refWindow.mode === "canvas" ? mainCanvas.canvas_preview : refWindow.refSource
                                    asynchronous: true
                                    cache: false
                                    
                                    opacity: status === Image.Ready ? 1.0 : 0.0
                                    Behavior on opacity { NumberAnimation { duration: 200 } }
                                }
                            }
                        }
                        
                        // Floating toolbar (appears on hover)
                        Row {
                            anchors.top: parent.top; anchors.right: parent.right
                            anchors.margins: 6
                            spacing: 4
                            z: 20
                            // Fix: Keep visible when hovering buttons OR content
                            opacity: (refHoverArea.containsMouse || refContentMouse.containsMouse || flipBtnM.containsMouse || resetBtnM.containsMouse || (loadBtnM.visible && loadBtnM.containsMouse) || handBtnM.containsMouse || pickBtnM.containsMouse) ? 1.0 : 0.0
                            Behavior on opacity { NumberAnimation { duration: 120 } }
                            
                            // Flip button
                            Rectangle {
                                width: 22; height: 22; radius: 6
                                color: flipBtnM.containsMouse ? "#333" : "#222"
                                Image { source: iconPath("flip_horizontal.svg"); width: 14; height: 14; anchors.centerIn: parent }
                                MouseArea { id: flipBtnM; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: refWindow.flipH = !refWindow.flipH }
                            }
                            // Reset/Rotate button
                            Rectangle {
                                width: 22; height: 22; radius: 6
                                color: resetBtnM.containsMouse ? "#333" : "#222"
                                Image { source: iconPath("rotate.svg"); width: 14; height: 14; anchors.centerIn: parent }
                                MouseArea { id: resetBtnM; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: { refWindow.navZoom = 1.0; refWindow.panOffset = Qt.point(0,0); refWindow.flipH = false } }
                            }
                            // Hand Tool
                            Rectangle {
                                width: 22; height: 22; radius: 6
                                color: refWindow.refTool === "move" ? colorAccent : (handBtnM.containsMouse ? "#333" : "#222")
                                Image { source: iconPath("hand.svg"); width: 14; height: 14; anchors.centerIn: parent }
                                MouseArea { id: handBtnM; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: refWindow.refTool = "move" }
                            }
                            // Picker Tool (Only for Image Mode really useful, but allowed in canvas too)
                            Rectangle {
                                width: 22; height: 22; radius: 6
                                color: refWindow.refTool === "pick" ? colorAccent : (pickBtnM.containsMouse ? "#333" : "#222")
                                Image { source: iconPath("picker.svg"); width: 14; height: 14; anchors.centerIn: parent }
                                MouseArea { id: pickBtnM; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: refWindow.refTool = "pick" }
                            }
                            
                            // Load (only in Ref mode)
                            Rectangle {
                                visible: refWindow.mode === "image"
                                width: 22; height: 22; radius: 6
                                color: loadBtnM.containsMouse ? "#444" : "#222"
                                Image { source: iconPath("folder.svg"); width: 14; height: 14; anchors.centerIn: parent }
                                MouseArea { id: loadBtnM; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: referenceFileDialog.open() }
                            }
                        }
                        
                        // Interaction Handler (Zoom, Pan, Pick)
                        MouseArea {
                            id: refContentMouse
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: refWindow.refTool === "pick" ? Qt.CrossCursor : (pressed ? Qt.ClosedHandCursor : Qt.OpenHandCursor)
                            
                            property point lastPos
                            
                            onPressed: (mouse) => {
                                lastPos = Qt.point(mouse.x, mouse.y)
                                if (refWindow.refTool === "pick") {
                                    pickColor(mouse.x, mouse.y)
                                }
                            }
                            
                            onPositionChanged: (mouse) => {
                                if (pressed) {
                                    if (refWindow.refTool === "move") {
                                        var dx = mouse.x - lastPos.x
                                        var dy = mouse.y - lastPos.y
                                        refWindow.panOffset = Qt.point(refWindow.panOffset.x + dx, refWindow.panOffset.y + dy)
                                        lastPos = Qt.point(mouse.x, mouse.y)
                                    } else if (refWindow.refTool === "pick") {
                                        pickColor(mouse.x, mouse.y)
                                    }
                                }
                            }
                            
                            function pickColor(x, y) {
                                // Only works for local images currently handled by Python backend
                                if (refWindow.mode === "image" && refWindow.refSource !== "") {
                                    // 1. Map from RefContent (MouseArea) to RefImage (Local transformed space)
                                    //    This handles Pan, Zoom, and Flip automatically.
                                    var pt = refImage.mapFromItem(refContentMouse, x, y)
                                    
                                    // 2. Pass local coordinates + image source size to Python
                                    //    Python will map 'PreserveAspectFit' logic using the source constraints.
                                    //    We use refImage.width (which corresponds to the container width in local space)
                                    //    as the reference for aspect calculation.
                                    var c = mainCanvas.sampleColorFromImage(refWindow.refSource, pt.x, pt.y, refImage.width, refImage.height)
                                    
                                    if (c !== "#000000") {
                                        mainCanvas.brushColor = c
                                    }
                                }
                            }

                            function onWheel(wheel) {
                                if (wheel.angleDelta.y > 0) refWindow.navZoom = Math.min(5.0, refWindow.navZoom + 0.1)
                                else refWindow.navZoom = Math.max(0.1, refWindow.navZoom - 0.1)
                                wheel.accepted = true
                            }
                        }
                        
                        // Empty state for Ref mode
                        Column {
                            anchors.centerIn: parent; spacing: 8
                            visible: refWindow.mode === "image" && refWindow.refSource === ""
                            opacity: 0.4
                            Text { text: "📷"; font.pixelSize: 28; anchors.horizontalCenter: parent.horizontalCenter }
                            Text { text: "Drop or load image"; color: "#555"; font.pixelSize: 9; anchors.horizontalCenter: parent.horizontalCenter }
                        }
                    }
                    
                    // ===== FOOTER (Minimal zoom bar) =====
                    Item {
                        id: refFooter
                        anchors.bottom: parent.bottom
                        anchors.left: parent.left; anchors.right: parent.right
                        height: 24
                        
                        // Zoom slider track
                        Rectangle {
                            width: parent.width - 50; height: 3; radius: 1.5
                            anchors.centerIn: parent
                            color: "#1a1a1c"
                            
                            // Fill
                            Rectangle {
                                width: Math.max(0, (refWindow.navZoom - 0.3) / 2.7) * parent.width
                                height: parent.height; radius: parent.radius
                                color: colorAccent
                                opacity: 0.7
                            }
                            
                            // Thumb
                            Rectangle {
                                x: Math.max(0, (refWindow.navZoom - 0.3) / 2.7) * (parent.width - 10)
                                y: -3; width: 10; height: 10; radius: 5
                                color: zoomThumbM.containsMouse ? "#fff" : "#ccc"
                                
                                MouseArea {
                                    id: zoomThumbM
                                    anchors.fill: parent; anchors.margins: -8
                                    hoverEnabled: true
                                    drag.target: parent; drag.axis: Drag.XAxis
                                    drag.minimumX: 0; drag.maximumX: parent.parent.width - 10
                                    onPositionChanged: {
                                        if (drag.active) {
                                            var p = parent.x / (parent.parent.width - 10)
                                            refWindow.navZoom = 0.3 + (p * 2.7)
                                        }
                                    }
                                }
                            }
                        }
                        
                        // Zoom percentage
                        Text {
                            text: Math.round(refWindow.navZoom * 100) + "%"
                            color: "#444"; font.pixelSize: 8
                            anchors.right: parent.right; anchors.rightMargin: 8
                            anchors.verticalCenter: parent.verticalCenter
                        }
                    }
                    
                    // ===== CORNER RESIZE HANDLES =====
                    // Bottom-Right
                    MouseArea {
                        width: 14; height: 14
                        anchors.right: parent.right; anchors.bottom: parent.bottom
                        cursorShape: Qt.SizeFDiagCursor
                        property point sp; property size ss
                        onPressed: { sp = Qt.point(mouseX, mouseY); ss = Qt.size(refWindow.width, refWindow.height) }
                        onPositionChanged: {
                            refWindow.width = Math.min(refWindow.maxW, Math.max(refWindow.minW, ss.width + mouseX - sp.x))
                            refWindow.height = Math.min(refWindow.maxH, Math.max(refWindow.minH, ss.height + mouseY - sp.y))
                        }
                        Rectangle { anchors.fill: parent; color: "transparent" }
                    }
                    // Bottom-Left
                    MouseArea {
                        width: 14; height: 14
                        anchors.left: parent.left; anchors.bottom: parent.bottom
                        cursorShape: Qt.SizeBDiagCursor
                        property point sp; property size ss; property real sx
                        onPressed: { sp = Qt.point(mouseX, mouseY); ss = Qt.size(refWindow.width, refWindow.height); sx = refWindow.x }
                        onPositionChanged: {
                            var dw = sp.x - mouseX
                            var newW = Math.min(refWindow.maxW, Math.max(refWindow.minW, ss.width + dw))
                            refWindow.x = sx - (newW - ss.width)
                            refWindow.width = newW
                            refWindow.height = Math.min(refWindow.maxH, Math.max(refWindow.minH, ss.height + mouseY - sp.y))
                        }
                        Rectangle { anchors.fill: parent; color: "transparent" }
                    }
                    // Top-Right
                    MouseArea {
                        width: 14; height: 14
                        anchors.right: parent.right; anchors.top: parent.top
                        cursorShape: Qt.SizeBDiagCursor
                        property point sp; property size ss; property real sy
                        onPressed: { sp = Qt.point(mouseX, mouseY); ss = Qt.size(refWindow.width, refWindow.height); sy = refWindow.y }
                        onPositionChanged: {
                            var dh = sp.y - mouseY
                            var newH = Math.min(refWindow.maxH, Math.max(refWindow.minH, ss.height + dh))
                            refWindow.y = sy - (newH - ss.height)
                            refWindow.height = newH
                            refWindow.width = Math.min(refWindow.maxW, Math.max(refWindow.minW, ss.width + mouseX - sp.x))
                        }
                        Rectangle { anchors.fill: parent; color: "transparent" }
                    }
                    // Top-Left
                    MouseArea {
                        width: 14; height: 14
                        anchors.left: parent.left; anchors.top: parent.top
                        cursorShape: Qt.SizeFDiagCursor
                        property point sp; property size ss; property real sx; property real sy
                        onPressed: { sp = Qt.point(mouseX, mouseY); ss = Qt.size(refWindow.width, refWindow.height); sx = refWindow.x; sy = refWindow.y }
                        onPositionChanged: {
                            var dw = sp.x - mouseX
                            var dh = sp.y - mouseY
                            var newW = Math.min(refWindow.maxW, Math.max(refWindow.minW, ss.width + dw))
                            var newH = Math.min(refWindow.maxH, Math.max(refWindow.minH, ss.height + dh))
                            refWindow.x = sx - (newW - ss.width)
                            refWindow.y = sy - (newH - ss.height)
                            refWindow.width = newW
                            refWindow.height = newH
                        }
                        Rectangle { anchors.fill: parent; color: "transparent" }
                    }
                }
                
                // KeepFileDialog but update logic if needed
                FileDialog {
                    id: refFileDialog
                    title: "Open Reference Image"
                    nameFilters: ["Images (*.png *.jpg *.jpeg *.psd)"]
                    onAccepted: {
                        var path = refFileDialog.currentFile.toString()
                        var base64 = mainCanvas.loadReference(path)
                        refWindow.refSource = base64
                    }
                }

                // === PANELES DESPLEGABLES (POPOVERS) ===
                
                // 0. BRUSH STUDIO PANEL - PREMIUM DESIGN
                Rectangle {
                    id: brushSettingsPanel
                    visible: showBrushSettings
                    width: 300; height: 480
                    x: parent.width - width - 60
                    y: topBar.height + 12
                    color: "#1a1a1c"
                    radius: 18
                    border.color: "#2a2a2c"; border.width: 1
                    z: 2100
                    clip: true
                    
                    // Elegant Shadow
                    Rectangle { z: -1; anchors.fill: parent; anchors.margins: -12; color: "#000"; opacity: 0.6; radius: 26 }
                    
                    // Animation
                    scale: visible ? 1.0 : 0.95
                    opacity: visible ? 1.0 : 0.0
                    Behavior on scale { NumberAnimation { duration: 150; easing.type: Easing.OutBack } }
                    Behavior on opacity { NumberAnimation { duration: 150 } }
                    
                    MouseArea { 
                        anchors.fill: parent; hoverEnabled: true
                        function onWheel(wheel) { wheel.accepted = true }
                    } 
                    
                    // --- HEADER ---
                    Rectangle {
                        id: bsHeader
                        width: parent.width; height: 56
                        color: "transparent"
                        
                        Row {
                            anchors.left: parent.left; anchors.leftMargin: 18
                            anchors.verticalCenter: parent.verticalCenter
                            spacing: 14
                            
                            // Brush Icon
                            Rectangle {
                                width: 36; height: 36; radius: 12
                                gradient: Gradient {
                                    GradientStop { position: 0.0; color: "#2d2d30" }
                                    GradientStop { position: 1.0; color: "#232326" }
                                }
                                border.color: colorAccent; border.width: 1.5
                                
                                Text { text: "🖌️"; anchors.centerIn: parent; font.pixelSize: 16 }
                            }
                            
                            Column {
                                anchors.verticalCenter: parent.verticalCenter
                                spacing: 3
                                Text { text: "Brush Studio"; color: "#fff"; font.pixelSize: 15; font.weight: Font.DemiBold }
                                Text { 
                                    text: mainCanvas.activeBrushName || "No brush selected"
                                    color: colorAccent; font.pixelSize: 11
                                    width: 160; elide: Text.ElideRight
                                }
                            }
                        }
                        
                        // Close Button
                        Rectangle {
                            width: 30; height: 30; radius: 15
                            color: closeBtnMouse.containsMouse ? "#333" : "transparent"
                            anchors.right: parent.right; anchors.rightMargin: 14
                            anchors.verticalCenter: parent.verticalCenter
                            
                            Text { text: "✕"; color: closeBtnMouse.containsMouse ? "#fff" : "#666"; anchors.centerIn: parent; font.pixelSize: 12 }
                            MouseArea {
                                id: closeBtnMouse
                                anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor
                                onClicked: showBrushSettings = false 
                            }
                        }
                    }
                    
                    // Header Divider
                    Rectangle { 
                        id: headerDivider
                        width: parent.width - 36; height: 1; color: "#333"
                        anchors.horizontalCenter: parent.horizontalCenter
                        anchors.top: bsHeader.bottom 
                    }

                    // --- SCROLLABLE CONTENT AREA ---
                    Flickable {
                        id: bsFlickable
                        anchors.top: headerDivider.bottom; anchors.topMargin: 8
                        anchors.left: parent.left; anchors.right: parent.right
                        anchors.bottom: parent.bottom; anchors.bottomMargin: 12
                        contentHeight: bsContentColumn.height + 30
                        clip: true
                        flickableDirection: Flickable.VerticalFlick
                        boundsBehavior: Flickable.StopAtBounds
                        
                        MouseArea {
                            anchors.fill: parent; hoverEnabled: true;
                            onClicked: bsFlickable.contentY = 0
                            function onWheel(wheel) {
                                bsFlickable.contentY = Math.max(0, Math.min(bsFlickable.contentHeight - bsFlickable.height, bsFlickable.contentY - wheel.angleDelta.y * 0.5))
                                wheel.accepted = true
                            }
                        }
                        
                        Column {
                            id: bsContentColumn
                            width: parent.width - 40
                            x: 20
                            spacing: 22
                            
                            // === SECTION: BASIC ===
                            Column {
                                width: parent.width
                                spacing: 16
                                
                                // Section Header
                                Row {
                                    spacing: 8
                                    Rectangle { width: 3; height: 12; radius: 1; color: colorAccent; anchors.verticalCenter: parent.verticalCenter }
                                    Text { text: "BASIC"; color: "#777"; font.pixelSize: 11; font.weight: Font.Bold }
                                }
                                
                                // Size Slider
                                Column {
                                    width: parent.width
                                    spacing: 10
                                    Row {
                                        width: parent.width
                                        Text { text: "Size"; color: "#bbb"; font.pixelSize: 13 }
                                        Item { width: parent.width - 100; height: 1 }
                                        Text { text: Math.round(mainCanvas.brushSize) + " px"; color: colorAccent; font.pixelSize: 13; font.weight: Font.Medium }
                                    }
                                    Slider {
                                        id: sliderSize
                                        width: parent.width; height: 28
                                        from: 1; to: 200; value: mainCanvas.brushSize
                                        onValueChanged: mainCanvas.brushSize = value
                                        
                                        background: Rectangle {
                                            y: (parent.height - height) / 2
                                            width: parent.width; height: 8; radius: 4
                                            color: "#252528"
                                            border.color: "#333"; border.width: 1
                                            
                                            Rectangle {
                                                width: sliderSize.visualPosition * parent.width
                                                height: parent.height; radius: 4
                                                gradient: Gradient {
                                                    orientation: Gradient.Horizontal
                                                    GradientStop { position: 0.0; color: Qt.darker(colorAccent, 1.4) }
                                                    GradientStop { position: 1.0; color: colorAccent }
                                                }
                                            }
                                        }
                                        handle: Rectangle {
                                            x: sliderSize.visualPosition * (sliderSize.width - width)
                                            y: (sliderSize.height - height) / 2
                                            width: 22; height: 22; radius: 11
                                            color: sliderSize.pressed ? "#fff" : "#f0f0f0"
                                            border.color: "#1a1a1c"; border.width: 3
                                        }
                                    }
                                }
                                
                                // Opacity Slider
                                Column {
                                    width: parent.width
                                    spacing: 10
                                    Row {
                                        width: parent.width
                                        Text { text: "Opacity"; color: "#bbb"; font.pixelSize: 13 }
                                        Item { width: parent.width - 100; height: 1 }
                                        Text { text: Math.round(mainCanvas.brushOpacity * 100) + "%"; color: colorAccent; font.pixelSize: 13; font.weight: Font.Medium }
                                    }
                                    Slider {
                                        id: sliderOpacity
                                        width: parent.width; height: 28
                                        from: 0; to: 1; value: mainCanvas.brushOpacity
                                        onValueChanged: mainCanvas.brushOpacity = value
                                        
                                        background: Rectangle {
                                            y: (parent.height - height) / 2
                                            width: parent.width; height: 8; radius: 4
                                            color: "#252528"
                                            border.color: "#333"; border.width: 1
                                            Rectangle { width: sliderOpacity.visualPosition * parent.width; height: parent.height; radius: 4; color: colorAccent }
                                        }
                                        handle: Rectangle {
                                            x: sliderOpacity.visualPosition * (sliderOpacity.width - width)
                                            y: (sliderOpacity.height - height) / 2
                                            width: 22; height: 22; radius: 11
                                            color: sliderOpacity.pressed ? "#fff" : "#f0f0f0"
                                            border.color: "#1a1a1c"; border.width: 3
                                        }
                                    }
                                }
                            }
                            
                            // Divider
                            Rectangle { width: parent.width; height: 1; color: "#2a2a2c" }
                            
                            // === REFERENCE WINDOW TOGGLE ===
                            Row {
                                width: parent.width; height: 32
                                spacing: 10
                                Image { source: iconPath("image.svg"); width: 16; height: 16; opacity: 0.7; anchors.verticalCenter: parent.verticalCenter }
                                Text { text: "Reference View"; color: "#ddd"; font.pixelSize: 13; anchors.verticalCenter: parent.verticalCenter }
                                Item { width: 1; height: 1; Layout.fillWidth: true }
                                
                                Rectangle {
                                    width: 40; height: 22; radius: 11
                                    color: refWindow.visible ? colorAccent : "#333"
                                    Rectangle { x: refWindow.visible ? 20 : 2; y: 2; width: 18; height: 18; radius: 9; color: "#fff"; Behavior on x { NumberAnimation { duration: 150 } } }
                                    MouseArea { anchors.fill: parent; onClicked: refWindow.visible = !refWindow.visible }
                                }
                            }

                            // Divider
                            Rectangle { width: parent.width; height: 1; color: "#2a2a2c" }

                            // === SECTION: SHAPE ===
                            Column {
                                width: parent.width
                                spacing: 14
                                
                                Row {
                                    spacing: 8
                                    Rectangle { width: 3; height: 12; radius: 1; color: "#6c7aff"; anchors.verticalCenter: parent.verticalCenter }
                                    Text { text: "SHAPE"; color: "#777"; font.pixelSize: 11; font.weight: Font.Bold }
                                }
                                
                                // Hardness
                                Row {
                                    width: parent.width; height: 32
                                    Text { text: "Hardness"; color: "#aaa"; font.pixelSize: 12; width: 75; anchors.verticalCenter: parent.verticalCenter }
                                    Slider {
                                        id: sliderHardness
                                        width: parent.width - 120; height: parent.height
                                        from: 0; to: 1; value: mainCanvas.brushHardness
                                        onValueChanged: mainCanvas.brushHardness = value
                                        anchors.verticalCenter: parent.verticalCenter
                                        
                                        background: Rectangle { y: 12; width: parent.width; height: 8; radius: 4; color: "#252528"; border.color: "#333"; Rectangle { width: sliderHardness.visualPosition * parent.width; height: parent.height; radius: 4; color: colorAccent } }
                                        handle: Rectangle { x: sliderHardness.visualPosition * (sliderHardness.width - width); y: 5; width: 22; height: 22; radius: 11; color: "#f0f0f0"; border.color: "#1a1a1c"; border.width: 3 }
                                    }
                                    Text { text: Math.round(mainCanvas.brushHardness * 100) + "%"; color: "#666"; font.pixelSize: 12; width: 45; horizontalAlignment: Text.AlignRight; anchors.verticalCenter: parent.verticalCenter }
                                }
                                
                                // Roundness
                                Row {
                                    width: parent.width; height: 32
                                    Text { text: "Roundness"; color: "#aaa"; font.pixelSize: 12; width: 75; anchors.verticalCenter: parent.verticalCenter }
                                    Slider {
                                        id: sliderRoundness
                                        width: parent.width - 120; height: parent.height
                                        from: 0.1; to: 1; value: mainCanvas.brushRoundness
                                        onValueChanged: mainCanvas.brushRoundness = value
                                        anchors.verticalCenter: parent.verticalCenter
                                        
                                        background: Rectangle { y: 12; width: parent.width; height: 8; radius: 4; color: "#252528"; border.color: "#333"; Rectangle { width: sliderRoundness.visualPosition * parent.width; height: parent.height; radius: 4; color: colorAccent } }
                                        handle: Rectangle { x: sliderRoundness.visualPosition * (sliderRoundness.width - width); y: 5; width: 22; height: 22; radius: 11; color: "#f0f0f0"; border.color: "#1a1a1c"; border.width: 3 }
                                    }
                                    Text { text: Math.round(mainCanvas.brushRoundness * 100) + "%"; color: "#666"; font.pixelSize: 12; width: 45; horizontalAlignment: Text.AlignRight; anchors.verticalCenter: parent.verticalCenter }
                                }
                                
                                // Angle
                                Row {
                                    width: parent.width; height: 32
                                    Text { text: "Angle"; color: "#aaa"; font.pixelSize: 12; width: 75; anchors.verticalCenter: parent.verticalCenter }
                                    Slider {
                                        id: sliderAngle
                                        width: parent.width - 120; height: parent.height
                                        from: 0; to: 360; value: mainCanvas.brushAngle
                                        onValueChanged: mainCanvas.brushAngle = value
                                        anchors.verticalCenter: parent.verticalCenter
                                        
                                        background: Rectangle { y: 12; width: parent.width; height: 8; radius: 4; color: "#252528"; border.color: "#333"; Rectangle { width: sliderAngle.visualPosition * parent.width; height: parent.height; radius: 4; color: colorAccent } }
                                        handle: Rectangle { x: sliderAngle.visualPosition * (sliderAngle.width - width); y: 5; width: 22; height: 22; radius: 11; color: "#f0f0f0"; border.color: "#1a1a1c"; border.width: 3 }
                                    }
                                    Text { text: Math.round(mainCanvas.brushAngle) + "°"; color: "#666"; font.pixelSize: 12; width: 45; horizontalAlignment: Text.AlignRight; anchors.verticalCenter: parent.verticalCenter }
                                }
                            }
                            
                            // Divider
                            Rectangle { width: parent.width; height: 1; color: "#2a2a2c" }

                            // === SECTION: DYNAMICS ===
                            Column {
                                width: parent.width
                                spacing: 14
                                
                                Row {
                                    spacing: 8
                                    Rectangle { width: 3; height: 12; radius: 1; color: "#ff6b9d"; anchors.verticalCenter: parent.verticalCenter }
                                    Text { text: "DYNAMICS"; color: "#777"; font.pixelSize: 11; font.weight: Font.Bold }
                                }
                                
                                // Follow Direction Toggle
                                Rectangle {
                                    width: parent.width; height: 48
                                    color: "#222226"; radius: 10
                                    
                                    Row {
                                        anchors.fill: parent; anchors.margins: 12
                                        
                                        Column {
                                            anchors.verticalCenter: parent.verticalCenter
                                            Text { text: "Follow Direction"; color: "#ddd"; font.pixelSize: 12 }
                                            Text { text: "Rotate brush with stroke"; color: "#666"; font.pixelSize: 10 }
                                        }
                                        Item { width: parent.width - 180; height: 1 }
                                        
                                        // Toggle Switch
                                        Rectangle {
                                            width: 48; height: 26; radius: 13
                                            anchors.verticalCenter: parent.verticalCenter
                                            color: mainCanvas.brushDynamicAngle ? colorAccent : "#3a3a3e"
                                            border.color: mainCanvas.brushDynamicAngle ? Qt.lighter(colorAccent, 1.2) : "#555"
                                            
                                            Behavior on color { ColorAnimation { duration: 150 } }
                                            
                                            Rectangle {
                                                x: mainCanvas.brushDynamicAngle ? 24 : 2; y: 2
                                                width: 22; height: 22; radius: 11
                                                color: "#fff"
                                                Behavior on x { NumberAnimation { duration: 150; easing.type: Easing.OutQuad } }
                                            }
                                            MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: mainCanvas.brushDynamicAngle = !mainCanvas.brushDynamicAngle }
                                        }
                                    }
                                }

                                // Stamp Mode Toggle
                                Rectangle {
                                    width: parent.width; height: 48
                                    color: "#222226"; radius: 10
                                    
                                    Row {
                                        anchors.fill: parent; anchors.margins: 12
                                        
                                        Column {
                                            anchors.verticalCenter: parent.verticalCenter
                                            Text { text: "Stamp Mode"; color: "#ddd"; font.pixelSize: 12 }
                                            Text { text: "Place single dabs on click"; color: "#666"; font.pixelSize: 10 }
                                        }
                                        Item { width: parent.width - 180; height: 1 }
                                        
                                        // Toggle Switch
                                        Rectangle {
                                            width: 48; height: 26; radius: 13
                                            anchors.verticalCenter: parent.verticalCenter
                                            color: mainCanvas.brushStampMode ? colorAccent : "#3a3a3e"
                                            border.color: mainCanvas.brushStampMode ? Qt.lighter(colorAccent, 1.2) : "#555"
                                            
                                            Behavior on color { ColorAnimation { duration: 150 } }
                                            
                                            Rectangle {
                                                x: mainCanvas.brushStampMode ? 24 : 2; y: 2
                                                width: 22; height: 22; radius: 11
                                                color: "#fff"
                                                Behavior on x { NumberAnimation { duration: 150; easing.type: Easing.OutQuad } }
                                            }
                                            MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: mainCanvas.brushStampMode = !mainCanvas.brushStampMode }
                                        }
                                    }
                                }
                                
                                // Grain
                                Row {
                                    width: parent.width; height: 32
                                    Text { text: "Grain"; color: "#aaa"; font.pixelSize: 12; width: 75; anchors.verticalCenter: parent.verticalCenter }
                                    Slider {
                                        id: sliderGrain
                                        width: parent.width - 120; height: parent.height
                                        from: 0; to: 1; value: mainCanvas.brushGrain
                                        onValueChanged: mainCanvas.brushGrain = value
                                        anchors.verticalCenter: parent.verticalCenter
                                        
                                        background: Rectangle { y: 12; width: parent.width; height: 8; radius: 4; color: "#252528"; border.color: "#333"; Rectangle { width: sliderGrain.visualPosition * parent.width; height: parent.height; radius: 4; color: colorAccent } }
                                        handle: Rectangle { x: sliderGrain.visualPosition * (sliderGrain.width - width); y: 5; width: 22; height: 22; radius: 11; color: "#f0f0f0"; border.color: "#1a1a1c"; border.width: 3 }
                                    }
                                    Text { text: Math.round(mainCanvas.brushGrain * 100) + "%"; color: "#666"; font.pixelSize: 12; width: 45; horizontalAlignment: Text.AlignRight; anchors.verticalCenter: parent.verticalCenter }
                                }
                                
                                // Spacing
                                Row {
                                    width: parent.width; height: 32
                                    Text { text: "Spacing"; color: "#aaa"; font.pixelSize: 12; width: 75; anchors.verticalCenter: parent.verticalCenter }
                                    Slider {
                                        id: sliderSpacing
                                        width: parent.width - 120; height: parent.height
                                        from: 0.01; to: 1; value: mainCanvas.brushSpacing
                                        onValueChanged: mainCanvas.brushSpacing = value
                                        anchors.verticalCenter: parent.verticalCenter
                                        
                                        background: Rectangle { y: 12; width: parent.width; height: 8; radius: 4; color: "#252528"; border.color: "#333"; Rectangle { width: sliderSpacing.visualPosition * parent.width; height: parent.height; radius: 4; color: colorAccent } }
                                        handle: Rectangle { x: sliderSpacing.visualPosition * (sliderSpacing.width - width); y: 5; width: 22; height: 22; radius: 11; color: "#f0f0f0"; border.color: "#1a1a1c"; border.width: 3 }
                                    }
                                    Text { text: Math.round(mainCanvas.brushSpacing * 100) + "%"; color: "#666"; font.pixelSize: 12; width: 45; horizontalAlignment: Text.AlignRight; anchors.verticalCenter: parent.verticalCenter }
                                }

                                // Streamline (Stabilizer)
                                Row {
                                    width: parent.width; height: 32
                                    Text { text: "Streamline"; color: "#aaa"; font.pixelSize: 12; width: 75; anchors.verticalCenter: parent.verticalCenter }
                                    Slider {
                                        id: sliderStreamline
                                        width: parent.width - 120; height: parent.height
                                        from: 0; to: 20; stepSize: 1; value: mainCanvas.brushStreamline
                                        onValueChanged: mainCanvas.brushStreamline = value
                                        anchors.verticalCenter: parent.verticalCenter
                                        
                                        background: Rectangle { y: 12; width: parent.width; height: 8; radius: 4; color: "#252528"; border.color: "#333"; Rectangle { width: sliderStreamline.visualPosition * parent.width; height: parent.height; radius: 4; color: colorAccent } }
                                        handle: Rectangle { x: sliderStreamline.visualPosition * (sliderStreamline.width - width); y: 5; width: 22; height: 22; radius: 11; color: "#f0f0f0"; border.color: "#1a1a1c"; border.width: 3 }
                                    }
                                    Text { text: Math.round(mainCanvas.brushStreamline); color: "#666"; font.pixelSize: 12; width: 45; horizontalAlignment: Text.AlignRight; anchors.verticalCenter: parent.verticalCenter }
                                }
                            }
                            
                            // Bottom Padding
                            Item { width: 1; height: 15 }
                        }
                    }
                    
                    // Scroll Indicator (appears when content is scrollable)
                    Rectangle {
                        visible: bsFlickable.contentHeight > bsFlickable.height
                        width: 4; radius: 2
                        height: Math.max(30, bsFlickable.height * (bsFlickable.height / bsFlickable.contentHeight))
                        x: parent.width - 8
                        y: bsHeader.height + 10 + (bsFlickable.contentY / (bsFlickable.contentHeight - bsFlickable.height)) * (bsFlickable.height - height - 10)
                        color: "#444"
                        opacity: bsFlickable.moving ? 0.8 : 0.4
                        Behavior on opacity { NumberAnimation { duration: 200 } }
                    }
                }
                


                // 1. PANEL DE PINCELES (Librería - Izquierda)
                // 1. PANEL DE PINCELES (Librería - Premium Floating)
                BrushLibrary {
                    id: brushLibrary
                    z: 500
                    targetCanvas: mainCanvas
                    contextPage: canvasPage
                    
                    // Fixed constraints
                    visible: opacity > 0
                    opacity: mainWindow.showBrush ? 1.0 : 0.0
                    
                    // Smooth slide-in from right
                    anchors.right: sideToolbar.left
                    anchors.rightMargin: 15
                    anchors.verticalCenter: sideToolbar.verticalCenter
                    
                    // Visual offset for the "Slide" effect without breaking anchors
                    transform: Translate {
                        x: mainWindow.showBrush ? 0 : 50
                        Behavior on x { NumberAnimation { duration: 250; easing.type: Easing.OutCubic } }
                    }
                    
                    Behavior on opacity { NumberAnimation { duration: 200 } }
                    
                    onCloseRequested: mainWindow.showBrush = false
                    onImportRequested: importAbrDialog.open()
                }

                // Dimmer background for the modal
                Rectangle {
                    z: brushLibrary.z - 1
                    anchors.fill: parent
                    anchors.rightMargin: sideToolbar.width + sideToolbar.anchors.rightMargin + 10
                    color: "black"
                    opacity: mainWindow.showBrush ? 0.4 : 0.0
                    visible: opacity > 0
                    Behavior on opacity { NumberAnimation { duration: 200 } }
                    
                    MouseArea {
                        anchors.fill: parent
                        onClicked: mainWindow.showBrush = false
                    }
                }

                // 2. PANEL DE CAPAS - Diseño Premium
                Rectangle {
                    id: layersPanel
                    visible: showLayers
                    width: 280; height: 400
                    x: parent.width - width - 15
                    y: topBar.height + 8
                    color: "#1c1c1e"
                    radius: 14
                    border.color: "#3a3a3c"; border.width: 0.5
                    z: 2000 // High Z-index
                    clip: false // Allow menu to spill out to the left
                    
                    // Sombra suave
                    Rectangle { z: -1; anchors.fill: parent; anchors.margins: -8; color: "#000"; opacity: 0.5; radius: 18 }
                    
                    // Animación
                    scale: visible ? 1.0 : 0.95
                    opacity: visible ? 1.0 : 0.0
                    Behavior on scale { NumberAnimation { duration: 100; easing.type: Easing.OutQuad } }
                    Behavior on opacity { NumberAnimation { duration: 100 } }
                    
                    
                    // Reset on click background - Ensuring the whole modal is clickable
                    MouseArea {
                        id: modalBackgroundReset
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.ArrowCursor
                        // Should be the first child to stay behind interaction elements
                        function onWheel(wheel) { wheel.accepted = true }
                        onClicked: {
                            layersList.swipedIndex = -1
                            layersList.optionsIndex = -1
                            layerContextMenu.visible = false
                        }
                    }
                    
                    // --- CONTEXT MENU (NESTED) ---
                    Rectangle {
                        id: layerContextMenu
                        visible: false
                        width: 180
                        height: menuColumn.height + 16
                        z: 5000
                        radius: 12
                        // Ensure completely opaque background
                        color: "#1c1c1e" 
                        border.color: "#323232"
                        border.width: 1
                        
                        // Force rendering to texture to fix potential transparency glitches
                        layer.enabled: true
                        clip: true // Ensure content stays inside rounded corners

                        property int targetLayerIndex: -1
                        property string targetLayerName: ""
                        property bool targetAlphaLock: false
                        
                        // Drop Shadow explicitly
                        Rectangle {
                            z: -1
                            anchors.fill: parent
                            anchors.margins: -8
                            radius: 16
                            color: "#000000"
                            opacity: 0.8
                        }
                        
                        scale: visible ? 1.0 : 0.9
                        opacity: visible ? 1.0 : 0.0
                        transformOrigin: Item.TopRight
                        Behavior on scale { NumberAnimation { duration: 150; easing.type: Easing.OutBack } }
                        Behavior on opacity { NumberAnimation { duration: 100 } }
                        
                        Column {
                            id: menuColumn
                            anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top
                            anchors.margins: 8
                            spacing: 2
                            Text { text: layerContextMenu.targetLayerName; color: "#8e8e93"; font.pixelSize: 10; leftPadding: 8; topPadding: 4; bottomPadding: 6 }
                            Repeater {
                                model: ListModel {
                                    ListElement { label: "Alpha Lock"; iconName: "lock"; action: "alphaLock"; divider: true }
                                    ListElement { label: "Clipping Mask"; iconName: "arrow-down-left"; action: "clip"; divider: true }
                                    ListElement { label: "Rename"; iconName: "edit-3"; action: "rename"; divider: false }
                                    ListElement { label: "Select"; iconName: "mouse-pointer"; action: "select"; divider: false }
                                    ListElement { label: "Copy"; iconName: "copy"; action: "copy"; divider: false }
                                    ListElement { label: "Fill Layer"; iconName: "paint-bucket"; action: "fill"; divider: true }
                                    ListElement { label: "Clear"; iconName: "trash-2"; action: "clear"; divider: false }
                                    ListElement { label: "Merge Down"; iconName: "layers"; action: "mergeDown"; divider: false }
                                    ListElement { label: "Flatten"; iconName: "minimize-2"; action: "flatten"; divider: false }
                                }
                                Column {
                                    width: parent.width
                                    Rectangle {
                                        width: parent.width; height: 36; radius: 6
                                        color: ((model.action === "alphaLock" && layerContextMenu.targetAlphaLock) || (model.action === "clip" && mainCanvas.isLayerClipped(layerContextMenu.targetLayerIndex))) ? "#4a6366f1" : (meMouse.containsMouse ? "#3a3a3c" : "transparent")
                                        Row {
                                            anchors.fill: parent; anchors.margins: 10; spacing: 10
                                            Image { source: iconPath(model.iconName + ".svg"); width: 16; height: 16; anchors.verticalCenter: parent.verticalCenter; opacity: 0.8 }
                                            Text { text: model.label; color: "#fff"; font.pixelSize: 13; anchors.verticalCenter: parent.verticalCenter }
                                        }
                                        MouseArea {
                                            id: meMouse; anchors.fill: parent; hoverEnabled: true
                                            onClicked: {
                                                if (model.action === "alphaLock") mainCanvas.toggleAlphaLock(layerContextMenu.targetLayerIndex)
                                                else if (model.action === "clip") mainCanvas.toggleClipping(layerContextMenu.targetLayerIndex)
                                                else if (model.action === "rename") { renameDialog.targetIndex = layerContextMenu.targetLayerIndex; renameDialog.open() }
                                                else if (model.action === "clear") mainCanvas.clearLayer(layerContextMenu.targetLayerIndex)
                                                else if (model.action === "copy") mainCanvas.duplicateLayer(layerContextMenu.targetLayerIndex)
                                                else if (model.action === "mergeDown") mainCanvas.mergeDown(layerContextMenu.targetLayerIndex)
                                                else if (model.action === "flatten") mainCanvas.flattenCanvas()
                                                layerContextMenu.visible = false
                                            }
                                        }
                                    }
                                    Rectangle { width: parent.width; height: 1; color: "#2c2c2e"; visible: model.divider }
                                }
                            }
                        }
                    }
                    
                    // Drag Ghost
                    Rectangle {
                        id: dragGhost
                        visible: false
                        width: parent.width - 24
                        height: 40
                        x: 12
                        color: targetDepth > 0 ? "#1a8fff" : "#2c2c2e"
                        radius: 8
                        border.color: colorAccent
                        border.width: targetDepth > 0 ? 2 : 1
                        z: 1000
                        opacity: 0.9
                        property string infoText: "Moving Layer"
                        property int targetDepth: 0
                        
                        Row {
                            anchors.centerIn: parent
                            spacing: 8
                            Image { source: iconPath("grip.svg"); width: 14; height: 14; opacity: 0.5; visible: dragGhost.targetDepth > 0 }
                            Text { 
                                text: (dragGhost.targetDepth > 0 ? "Nest into... " : "") + dragGhost.infoText
                                color: "white" 
                                font.bold: true 
                            }
                        }
                        
                        Behavior on x { NumberAnimation { duration: 100 } }
                        
                        // Shadow
                        Rectangle { anchors.fill: parent; anchors.margins: -4; z: -1; color: "#000"; opacity: 0.3; radius: 12 }
                    }

                    // Modelo de Capas
                    ListModel { id: layerModel }
                    
                    // Conexión con Python
                    Connections {
                        target: mainCanvas
                        function onLayersChanged(layers) {
                            // save scroll position?
                            var oldY = layersList.contentY
                            layerModel.clear()
                            for (var i = 0; i < layers.length; i++) {
                                layerModel.append(layers[i])
                            }
                            // Restore scroll? Logic might be tricky if items change count.
                        }
                    }
                    
                    // Header Premium
                    Item {
                        id: layerHeader
                        width: parent.width; height: 52
                        
                        // Close swiped/options on header click
                        MouseArea {
                            anchors.fill: parent
                            onClicked: {
                                layersList.swipedIndex = -1
                                layersList.optionsIndex = -1
                                layerContextMenu.visible = false
                            }
                        }
                        
                        Row {
                            anchors.left: parent.left
                            anchors.leftMargin: 16
                            anchors.verticalCenter: parent.verticalCenter
                            spacing: 8
                            
                            // Icono de capas
                            Image {
                                source: iconPath("layers.svg")
                                width: 18; height: 18
                                anchors.verticalCenter: parent.verticalCenter
                                opacity: 0.8
                            }
                            
                            Text { 
                                text: "Layers"
                                color: "#fff"
                                font.pixelSize: 14
                                font.weight: Font.DemiBold
                                font.letterSpacing: 0.5
                                anchors.verticalCenter: parent.verticalCenter
                            }
                            
                            // Badge con número de capas
                            Rectangle {
                                width: 22; height: 18; radius: 9
                                color: "#3a3a3c"
                                anchors.verticalCenter: parent.verticalCenter
                                Text {
                                    text: layerModel.count
                                    color: "#8e8e93"
                                    font.pixelSize: 10
                                    font.weight: Font.Medium
                                    anchors.centerIn: parent
                                }
                            }
                        }
                        
                        // Botones de Acción (Grupo y Capa)
                        Row {
                            anchors.right: parent.right
                            anchors.rightMargin: 12
                            anchors.verticalCenter: parent.verticalCenter
                            spacing: 8

                            // Add Group
                            Rectangle {
                                width: 32; height: 32; radius: 8
                                color: grpMouse.containsMouse ? "#3a3a3c" : "#2c2c2e"
                                border.color: grpMouse.containsMouse ? colorAccent : "#48484a"
                                border.width: 1
                                
                                Image {
                                    source: iconPath("folder.svg")
                                    width: 16; height: 16
                                    anchors.centerIn: parent
                                    opacity: 0.9
                                }
                                
                                MouseArea {
                                    id: grpMouse
                                    anchors.fill: parent
                                    cursorShape: Qt.PointingHandCursor
                                    hoverEnabled: true
                                    onClicked: mainCanvas.addGroup()
                                }
                            }

                            // Add Layer
                            Rectangle {
                                width: 32; height: 32; radius: 8
                                color: addMouse.containsMouse ? "#3a3a3c" : "#2c2c2e"
                                border.color: addMouse.containsMouse ? colorAccent : "#48484a"
                                border.width: 1
                                
                                Text { 
                                    text: "+" 
                                    color: addMouse.containsMouse ? colorAccent : "#fff"
                                    font.pixelSize: 20
                                    font.weight: Font.Light
                                    anchors.centerIn: parent 
                                }
                                
                                MouseArea {
                                    id: addMouse
                                    anchors.fill: parent
                                    cursorShape: Qt.PointingHandCursor
                                    hoverEnabled: true
                                    onClicked: mainCanvas.addLayer()
                                }
                                
                                Behavior on color { ColorAnimation { duration: 150 } }
                                Behavior on border.color { ColorAnimation { duration: 150 } }
                            }
                        }
                        
                        // Separador con gradiente
                        Rectangle { 
                            width: parent.width - 24; height: 1
                            anchors.bottom: parent.bottom
                            anchors.horizontalCenter: parent.horizontalCenter
                            gradient: Gradient {
                                orientation: Gradient.Horizontal
                                GradientStop { position: 0.0; color: "transparent" }
                                GradientStop { position: 0.2; color: "#3a3a3c" }
                                GradientStop { position: 0.8; color: "#3a3a3c" }
                                GradientStop { position: 1.0; color: "transparent" }
                            }
                        }
                    }
                    
                    // Lista de Capas
                    ListView {
                        id: layersList
                        anchors.top: layerHeader.bottom
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.bottom: parent.bottom
                        anchors.margins: 8
                        anchors.topMargin: 4
                        spacing: 4
                        model: layerModel
                        clip: true
                        
                        // Track which layer is currently swiped open
                        property int swipedIndex: -1
                        property int optionsIndex: -1
                        property int draggedIndex: -1 // For tracking drag operations
                        
                        // Close any swiped layer when clicking on list background
                        MouseArea {
                            anchors.fill: parent
                            z: -1
                            onClicked: {
                                layersList.swipedIndex = -1
                                layersList.optionsIndex = -1
                                layerContextMenu.visible = false
                            }
                        }
                        
                        delegate: LayerDelegate {
                            // Delegate logic extracted to src/ui/qml/components/LayerDelegate.qml
                        }
                        
                        // Footer: Drop Zone for moving layers to bottom
                        footer: Item {
                            width: layersList.width
                            height: Math.max(60, layersList.height - layersList.contentHeight + 20) // Fill remaining space
                            
                            Rectangle {
                                id: dropZoneFooter
                                anchors.fill: parent
                                anchors.margins: 6
                                color: dropZoneMouse.containsMouse && layersList.draggedIndex >= 0 ? "#1a6366f1" : "transparent"
                                radius: 8
                                border.color: dropZoneMouse.containsMouse && layersList.draggedIndex >= 0 ? colorAccent : "#22ffffff"
                                border.width: dropZoneMouse.containsMouse && layersList.draggedIndex >= 0 ? 2 : 1
                                
                                visible: layerModel.count > 0
                                
                                Column {
                                    anchors.centerIn: parent
                                    spacing: 4
                                    opacity: dropZoneMouse.containsMouse && layersList.draggedIndex >= 0 ? 1.0 : 0.3
                                    
                                    Image {
                                        source: iconPath("arrow-down.svg")
                                        width: 16; height: 16
                                        anchors.horizontalCenter: parent.horizontalCenter
                                        opacity: 0.6
                                    }
                                    
                                    Text {
                                        text: layersList.draggedIndex >= 0 ? "Drop here" : "Move to bottom"
                                        color: "#666"
                                        font.pixelSize: 10
                                        anchors.horizontalCenter: parent.horizontalCenter
                                    }
                                }
                                
                                MouseArea {
                                    id: dropZoneMouse
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    
                                    onClicked: {
                                        layersList.swipedIndex = -1
                                        layersList.optionsIndex = -1
                                        layerContextMenu.visible = false
                                    }
                                }
                                
                                // For receiving drop
                                DropArea {
                                    anchors.fill: parent
                                    
                                    onEntered: (drag) => {
                                        console.log("Layer entered drop zone footer")
                                    }
                                    
                                    onDropped: (drop) => {
                                        if (layersList.draggedIndex >= 0) {
                                            // Move layer to the last position (before background)
                                            var targetIndex = layerModel.count - 1
                                            if (layersList.draggedIndex !== targetIndex) {
                                                mainCanvas.moveLayer(layersList.draggedIndex, targetIndex)
                                            }
                                            layersList.draggedIndex = -1
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
                



                // 3. PANEL DE COLOR - Multi-Modo (Wheel, Square, Sliders, Palettes)
                // 3. PANEL DE COLOR - PRO REDESIGN
                PopOverPanel {
                    id: colorPanel
                    visible: showColor
                    width: 250; height: 480 // Increased height for better layout
                    anchors.top: parent.top; anchors.topMargin: 56
                    anchors.right: parent.right; anchors.rightMargin: 16
                    title: "Color"
                    z: 300 // Fix: Ensure it appears above Side Toolbar
                    
                    property int colorMode: 0 // 0=Pro Ring, 1=Harmony, 2=Sliders, 3=Palettes
                    property real hue: 0
                    property real saturation: 0
                    property real brightness: 1
                    property color currentColor: Qt.hsva(hue, saturation, brightness, 1)
                    property bool isInternalUpdate: false
                    property int harmonyType: 0 // 0=Comp, 1=Triad, 2=Analog
                    
                    // --- SYNC ENGINE ---
                    Connections {
                        target: mainCanvas
                        function onBrushColorChanged() {
                             if (!colorPanel.isInternalUpdate && showColor) {
                                  var c = mainCanvas.brushColor
                                  colorPanel.hue = c.hsvHue
                                  colorPanel.saturation = c.hsvSaturation
                                  colorPanel.brightness = c.hsvValue
                             }
                        }
                    }
                    onVisibleChanged: {
                        if (visible) {
                             var c = mainCanvas.brushColor
                             colorPanel.hue = c.hsvHue
                             colorPanel.saturation = c.hsvSaturation
                             colorPanel.brightness = c.hsvValue
                        }
                    }

                    // --- HISTORY SYSTEM ---
                    ListModel { id: colorHistoryModel }
                    function addToHistory(c) {
                        for(var i=0; i<colorHistoryModel.count; i++) {
                            if (colorHistoryModel.get(i).color === c.toString()) {
                                colorHistoryModel.remove(i); break;
                            }
                        }
                        colorHistoryModel.insert(0, { "color": c.toString() })
                        if (colorHistoryModel.count > 8) colorHistoryModel.remove(8)
                    }

                    onCurrentColorChanged: {
                        isInternalUpdate = true
                        mainCanvas.brushColor = currentColor
                        isInternalUpdate = false
                    }
                    
                    Column {
                        anchors.fill: parent
                        anchors.margins: 12
                        anchors.topMargin: 35
                        spacing: 12
                        
                        // TAB SELECTOR
                        Rectangle {
                            width: parent.width; height: 28
                            radius: 8; color: "#2c2c2e"
                            
                            // Prevent scroll on tab bar
                            MouseArea {
                                anchors.fill: parent 
                                hoverEnabled: true
                                function onWheel(wheel) { wheel.accepted = true }
                                onPressed: { mouse.accepted = false }
                            }
                            
                            border.color: "#3e3e42"
                            Row {
                                anchors.fill: parent
                                Repeater {
                                    model: ["Ring", "Harm", "Sldr", "Pal"]
                                    Rectangle {
                                        width: parent.width / 4; height: parent.height
                                        radius: 6
                                        color: colorPanel.colorMode === index ? "#4a4a4c" : "transparent"
                                        Text { text: modelData; color: colorPanel.colorMode === index ? "white" : "#888"; anchors.centerIn: parent; font.pixelSize: 10 }
                                        MouseArea { anchors.fill: parent; onClicked: colorPanel.colorMode = index }
                                    }
                                }
                            }
                        }
                        
                        // === MODE 0: PRO RING (Hue Ring + SV Square) ===
                        Item {
                            visible: colorPanel.colorMode === 0
                            width: parent.width; height: 220
                            
                            // Hue Ring
                            Canvas {
                                anchors.fill: parent
                                onPaint: {
                                    var ctx = getContext("2d"); ctx.reset();
                                    var cx=width/2, cy=height/2, r=width/2, ir=width/2-25;
                                    for(var i=0; i<360; i+=2) {
                                        ctx.beginPath(); ctx.arc(cx,cy,r,(i-1.5)*Math.PI/180,(i+1.5)*Math.PI/180);
                                        ctx.arc(cx,cy,ir,(i+1.5)*Math.PI/180,(i-1.5)*Math.PI/180,true);
                                        ctx.fillStyle = Qt.hsva(i/360,1,1,1).toString(); ctx.fill();
                                    }
                                }
                                MouseArea {
                                    anchors.fill: parent
                                    onPositionChanged: {
                                        if(!pressed) return
                                        var dx=mouseX-width/2, dy=mouseY-height/2, ang=Math.atan2(dy,dx);
                                        if(ang<0) ang+=2*Math.PI;
                                        colorPanel.hue = ang/(2*Math.PI);
                                    }
                                    onPressed: positionChanged(mouse)
                                    onReleased: colorPanel.addToHistory(colorPanel.currentColor)
                                }
                                // Hue Indicator
                                Rectangle {
                                    width: 8; height: 8; radius: 4; border.width:1; border.color:"white"; color:"transparent"
                                    x: (parent.width/2) + (parent.width/2-12.5)*Math.cos(colorPanel.hue*2*Math.PI) - 4
                                    y: (parent.height/2) + (parent.width/2-12.5)*Math.sin(colorPanel.hue*2*Math.PI) - 4
                                }
                            }
                            
                            // SV Square (Inner)
                            Rectangle {
                                width: parent.width*0.55; height: width
                                anchors.centerIn: parent
                                border.color: "#555"; border.width: 1
                                Rectangle {
                                    anchors.fill: parent
                                    gradient: Gradient { orientation: Gradient.Horizontal; GradientStop { position: 0.0; color: "white" } GradientStop { position: 1.0; color: Qt.hsva(colorPanel.hue,1,1,1) } }
                                }
                                Rectangle {
                                    anchors.fill: parent
                                    gradient: Gradient { orientation: Gradient.Vertical; GradientStop { position: 0.0; color: "transparent" } GradientStop { position: 1.0; color: "black" } }
                                }
                                // Cursor
                                Rectangle {
                                    width: 10; height: 10; radius: 5; border.width:1; border.color: colorPanel.brightness > 0.5 ? "black" : "white"; color: "transparent"
                                    x: colorPanel.saturation * parent.width - 5
                                    y: (1-colorPanel.brightness) * parent.height - 5
                                }
                                MouseArea {
                                    anchors.fill: parent
                                    onPositionChanged: {
                                        if(!pressed) return
                                        colorPanel.saturation = Math.max(0,Math.min(1, mouseX/width))
                                        colorPanel.brightness = Math.max(0,Math.min(1, 1-mouseY/height))
                                    }
                                    onPressed: positionChanged(mouse)
                                    onReleased: colorPanel.addToHistory(colorPanel.currentColor)
                                }
                            }
                        }

                        // === MODE 1: HARMONY WHEEL ===
                        Item {
                            visible: colorPanel.colorMode === 1
                            width: parent.width; height: 220
                            
                            // Harmony Selector
                            Row { anchors.top: parent.top; anchors.horizontalCenter: parent.horizontalCenter; spacing: 10
                                Text { text: "Type:"; color: "#888"; font.pixelSize: 10; anchors.verticalCenter: parent.verticalCenter }
                                Repeater {
                                    model: ["Comp", "Triad", "Ana"]
                                    Rectangle {
                                        width: 40; height: 18; radius: 4; color: colorPanel.harmonyType === index ? "#555" : "#333"
                                        Text { text: modelData; anchors.centerIn: parent; color: "white"; font.pixelSize: 9 }
                                        MouseArea { anchors.fill: parent; onClicked: colorPanel.harmonyType = index }
                                    }
                                }
                            }

                            Canvas {
                                anchors.centerIn: parent; width: 170; height: 170
                                onPaint: {
                                    var ctx = getContext("2d"); ctx.reset();
                                    var w=width, h=height, cx=w/2, cy=h/2, r=w/2;
                                    
                                    // 1. Draw Conical Hue
                                    for(var i=0; i<360; i+=2) {
                                        ctx.beginPath(); ctx.moveTo(cx,cy);
                                        ctx.arc(cx,cy,r, i*Math.PI/180, (i+2.5)*Math.PI/180);
                                        ctx.fillStyle=Qt.hsva(i/360,1,1,1).toString(); ctx.fill();
                                    }
                                    
                                    // 2. Draw Radial Saturation (White center -> Transparent edge)
                                    var grad = ctx.createRadialGradient(cx,cy, 0, cx,cy, r);
                                    grad.addColorStop(0, "white");
                                    grad.addColorStop(1, "rgba(255,255,255,0)");
                                    ctx.fillStyle = grad;
                                    ctx.beginPath(); ctx.arc(cx,cy, r, 0, 2*Math.PI); ctx.fill();
                                }
                                MouseArea {
                                    anchors.fill: parent
                                    onPositionChanged: { if(pressed) {
                                        var dx=mouseX-85, dy=mouseY-85, ang=Math.atan2(dy,dx);
                                        var dist = Math.sqrt(dx*dx + dy*dy);
                                        if(ang<0) ang+=2*Math.PI; 
                                        colorPanel.hue=ang/(2*Math.PI);
                                        colorPanel.saturation=Math.min(1.0, dist/85.0);
                                        colorPanel.brightness = 1.0 // Ensure color is visible (not black)
                                    }}
                                    onPressed: positionChanged(mouse)
                                }
                                // Main Node
                                Rectangle {
                                    width: 14; height: 14; radius: 7; border.width: 2; border.color: "white"; color: colorPanel.currentColor
                                    x: 85 + (colorPanel.saturation*80)*Math.cos(colorPanel.hue*2*Math.PI) - 7
                                    y: 85 + (colorPanel.saturation*80)*Math.sin(colorPanel.hue*2*Math.PI) - 7
                                }
                                // Harmony Node 1
                                Rectangle {
                                    width: 10; height: 10; radius: 5; border.width: 1; border.color: "white"; color: Qt.hsva((colorPanel.hue + (colorPanel.harmonyType===0?0.5:(colorPanel.harmonyType===1?0.33:0.08)))%1.0, colorPanel.saturation, 1, 1)
                                    visible: true
                                    x: 85 + (colorPanel.saturation*80)*Math.cos(((colorPanel.hue + (colorPanel.harmonyType===0?0.5:(colorPanel.harmonyType===1?0.33:0.08)))%1.0)*2*Math.PI) - 5
                                    y: 85 + (colorPanel.saturation*80)*Math.sin(((colorPanel.hue + (colorPanel.harmonyType===0?0.5:(colorPanel.harmonyType===1?0.33:0.08)))%1.0)*2*Math.PI) - 5
                                    MouseArea { anchors.fill: parent; onClicked: mainCanvas.brushColor = parent.color }
                                }
                                // Harmony Node 2 (Triad/Analogous)
                                Rectangle {
                                    width: 10; height: 10; radius: 5; border.width: 1; border.color: "white"; color: Qt.hsva((colorPanel.hue + (colorPanel.harmonyType===1?0.66:0.92))%1.0, colorPanel.saturation, 1, 1)
                                    visible: colorPanel.harmonyType !== 0
                                    x: 85 + (colorPanel.saturation*80)*Math.cos(((colorPanel.hue + (colorPanel.harmonyType===1?0.66:0.92))%1.0)*2*Math.PI) - 5
                                    y: 85 + (colorPanel.saturation*80)*Math.sin(((colorPanel.hue + (colorPanel.harmonyType===1?0.66:0.92))%1.0)*2*Math.PI) - 5
                                    MouseArea { anchors.fill: parent; onClicked: mainCanvas.brushColor = parent.color }
                                }
                            }
                        }

                        // === MODE 2: PROFESSIONAL SLIDERS (HCL / RGB / HSV) ===
                        Item { 
                            id: slidersView
                            visible: colorPanel.colorMode === 2
                            width: parent.width; height: 230
                            
                            property string activeModel: "HCL"
                            property real hcl_h: 0
                            property real hcl_c: 0
                            property real hcl_l: 0
                            property bool internalUpdate: false

                            // Local storage for RGB values
                            property int rgb_r: 0
                            property int rgb_g: 0
                            property int rgb_b: 0
                            
                            // Sync from Main Color
                            Connections {
                                target: mainCanvas
                                function onBrushColorChanged() {
                                    if (slidersView.internalUpdate) return
                                    if (slidersView.visible) {
                                        if (slidersView.activeModel === "HCL") {
                                            var hcl = mainCanvas.hexToHcl(mainCanvas.brushColor)
                                            slidersView.hcl_h = hcl[0]; slidersView.hcl_c = hcl[1]; slidersView.hcl_l = hcl[2]
                                        } else if (slidersView.activeModel === "RGB") {
                                            var c = Qt.color(mainCanvas.brushColor)
                                            slidersView.rgb_r = Math.round(c.r * 255)
                                            slidersView.rgb_g = Math.round(c.g * 255)
                                            slidersView.rgb_b = Math.round(c.b * 255)
                                        }
                                    }
                                }
                            }
                            
                            // Initialize on visible or model change
                            onActiveModelChanged: updateSliders()
                            onVisibleChanged: if(visible) updateSliders()
                                
                            function updateSliders() {
                                if (activeModel === "HCL") {
                                    var hcl = mainCanvas.hexToHcl(mainCanvas.brushColor)
                                    hcl_h = hcl[0]; hcl_c = hcl[1]; hcl_l = hcl[2]
                                } else if (activeModel === "RGB") {
                                    var c = Qt.color(mainCanvas.brushColor)
                                    rgb_r = Math.round(c.r * 255)
                                    rgb_g = Math.round(c.g * 255)
                                    rgb_b = Math.round(c.b * 255)
                                }
                            }
                            
                            function applyRGB() {
                                slidersView.internalUpdate = true
                                var r = Math.round(slidersView.rgb_r)
                                var g = Math.round(slidersView.rgb_g)
                                var b = Math.round(slidersView.rgb_b)
                                // Clamp
                                r = Math.max(0, Math.min(255, r))
                                g = Math.max(0, Math.min(255, g))
                                b = Math.max(0, Math.min(255, b))
                                
                                var rs = ("0" + r.toString(16)).slice(-2)
                                var gs = ("0" + g.toString(16)).slice(-2)
                                var bs = ("0" + b.toString(16)).slice(-2)
                                
                                var hex = "#" + rs + gs + bs
                                // console.log("Applying RGB Hex:", hex)
                                mainCanvas.brushColor = hex
                                slidersView.internalUpdate = false
                            }

                            ColumnLayout {
                                anchors.fill: parent
                                spacing: 15
                                
                                // Model Tabs
                                RowLayout {
                                    Layout.alignment: Qt.AlignHCenter
                                    spacing: 4
                                    Repeater {
                                        model: ["HCL", "HSB", "RGB"]
                                        delegate: Rectangle {
                                            width: 50; height: 22; radius: 6
                                            color: slidersView.activeModel === modelData ? "#444" : "#222"
                                            Text { text: modelData; color: "white"; font.pixelSize: 10; font.bold: true; anchors.centerIn: parent }
                                            MouseArea { anchors.fill: parent; onClicked: slidersView.activeModel = modelData }
                                        }
                                    }
                                }
                                
                                // --- HCL SLIDERS ---
                                ColumnLayout {
                                    visible: slidersView.activeModel === "HCL"
                                    Layout.fillWidth: true
                                    spacing: 12
                                    
                                    CustomColorSlider {
                                        mode: "H"; labelText: "H"
                                        value: slidersView.hcl_h
                                        Layout.fillWidth: true
                                        onMoved: (val) => {
                                            slidersView.hcl_h = val
                                            slidersView.internalUpdate = true
                                            var hex = mainCanvas.hclToHex(slidersView.hcl_h, slidersView.hcl_c, slidersView.hcl_l)
                                            mainCanvas.brushColor = hex
                                            slidersView.internalUpdate = false
                                        }
                                    }
                                    CustomColorSlider {
                                        mode: "C"; labelText: "C"
                                        value: slidersView.hcl_c
                                        Layout.fillWidth: true
                                        onMoved: (val) => {
                                            slidersView.hcl_c = val
                                            slidersView.internalUpdate = true
                                            var hex = mainCanvas.hclToHex(slidersView.hcl_h, slidersView.hcl_c, slidersView.hcl_l)
                                            mainCanvas.brushColor = hex
                                            slidersView.internalUpdate = false
                                        }
                                    }
                                    CustomColorSlider {
                                        mode: "L"; labelText: "L"
                                        value: slidersView.hcl_l
                                        Layout.fillWidth: true
                                        onMoved: (val) => {
                                            slidersView.hcl_l = val
                                            slidersView.internalUpdate = true
                                            var hex = mainCanvas.hclToHex(slidersView.hcl_h, slidersView.hcl_c, slidersView.hcl_l)
                                            mainCanvas.brushColor = hex
                                            slidersView.internalUpdate = false
                                        }
                                    }
                                    
                                    Text {
                                        text: "Perceptual Color (Luminance)"
                                        color: "#555"; font.pixelSize: 9; Layout.alignment: Qt.AlignHCenter
                                    }
                                }

                                // --- HSB SLIDERS ---
                                ColumnLayout {
                                    visible: slidersView.activeModel === "HSB"
                                    Layout.fillWidth: true
                                    spacing: 12
                                    // H
                                    CustomColorSlider {
                                        mode: "H"; labelText: "H"
                                        value: colorPanel.hue * 360
                                        Layout.fillWidth: true
                                        onMoved: (val) => { colorPanel.hue = val / 360.0 }
                                    }
                                    // S
                                    CustomColorSlider {
                                        mode: "C"; labelText: "S" // Use C gradient logic but S label
                                        value: colorPanel.saturation * 100
                                        Layout.fillWidth: true
                                        onMoved: (val) => { colorPanel.saturation = val / 100.0 }
                                    }
                                    // B
                                    CustomColorSlider {
                                        mode: "L"; labelText: "B" // Use L gradient logic but B label
                                        value: colorPanel.brightness * 100
                                        Layout.fillWidth: true
                                        onMoved: (val) => { colorPanel.brightness = val / 100.0 }
                                    }
                                }
                                
                                // --- RGB SLIDERS ---
                                ColumnLayout {
                                    visible: slidersView.activeModel === "RGB"
                                    Layout.fillWidth: true
                                    spacing: 12
                                    
                                    CustomColorSlider {
                                        mode: "R"; labelText: "R"
                                        value: slidersView.rgb_r
                                        Layout.fillWidth: true
                                        onMoved: (val) => { slidersView.rgb_r = val; applyRGB() }
                                    }
                                    CustomColorSlider {
                                        mode: "G"; labelText: "G"
                                        value: slidersView.rgb_g
                                        Layout.fillWidth: true
                                        onMoved: (val) => { slidersView.rgb_g = val; applyRGB() }
                                    }
                                    CustomColorSlider {
                                        mode: "B_Blue"; labelText: "B"
                                        value: slidersView.rgb_b
                                        Layout.fillWidth: true
                                        onMoved: (val) => { slidersView.rgb_b = val; applyRGB() }
                                    }
                                }
                            }
                        }
                        
                        } // End slidersView
                        
                        // History Bar (Global)
                        Rectangle { width: parent.width; height: 1; color: "#444" }
                        Text { text: "History"; color: "#888"; font.pixelSize: 10 }
                        Row { spacing: 6
                            Repeater {
                                model: colorHistoryModel
                                Rectangle {
                                    width: 20; height: 20; radius: 10; color: model.color
                                    border.color: model.color === colorPanel.currentColor.toString() ? "white" : "transparent"; border.width: 1
                                    MouseArea { anchors.fill: parent; onClicked: mainCanvas.brushColor = model.color }
                                }
                            }
                        }
                    }
                }




                ColorDropOrb {
                    id: dropOrb
                    dropColor: mainCanvas.brushColor
                    active: false
                }
            } // Fin Item (Canvas Page)
