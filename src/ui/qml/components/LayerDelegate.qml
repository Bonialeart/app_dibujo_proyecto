import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15


Item {
    id: layerDelegate
    
    // Properties passed from the main list
    property int listIndex: index // The special 'index' variable from Delegate
    property var listModel: model // THe special 'model' variable from Delegate
    
    // External References
    property var layersListRef: ListView.view 
    
    // Layer Data (extracted from model for easier binding)
    property int layerIndex: listModel.layerId
    property string layerName: listModel.name
    property bool isVisible: listModel.visible
    property bool isActive: listModel.active
    property bool isLocked: listModel.locked
    property bool isClipped: listModel.clipped
    property bool isAlphaLocked: listModel.alpha_lock
    property bool isPrivate: listModel.is_private
    property string blendMode: listModel.blendMode || "Normal"
    property real layerOpacity: listModel.opacity !== undefined ? listModel.opacity : 1.0
    property string layerType: listModel.type
    property var thumbnailSource: listModel.thumbnail
    property int layerDepth: (typeof listModel.depth !== 'undefined' ? listModel.depth : 0)
    property bool isGroupExpanded: listModel.expanded
    
    width: layersListRef.width
    // Height changes if options are open
    height: layersListRef.optionsIndex === layerDelegate.layerIndex ? 320 : 64
    
    property bool isSwipedOpen: layersListRef.swipedIndex === layerDelegate.listIndex
    
    // Helper function for icon paths (assuming parent context has this or we need to pass it)
    function iconPath(name) {
        return "image://icons/" + name
    }

    // --- 1. BACKGROUND ACTIONS (Copy, Lock, Delete) ---
    // Revealed when swiping LEFT
    Row {
        anchors.right: parent.right
        anchors.rightMargin: 4
        anchors.verticalCenter: parent.verticalCenter
        anchors.verticalCenterOffset: (layersListRef.optionsIndex === layerDelegate.layerIndex) ? -128 : 0 // Align to top part if expanded
        height: 56 // Fixed height matching header
        spacing: 4
        
        visible: layerDelegate.isSwipedOpen
        opacity: layerDelegate.isSwipedOpen ? 1 : 0
        Behavior on opacity { NumberAnimation { duration: 200 } }
        
        // Copy
        Rectangle {
            width: 50; height: parent.height; radius: 10
            color: "#0a84ff"
            Column {
                anchors.centerIn: parent
                spacing: 2
                Image { source: iconPath("copy.svg"); width: 18; height: 18; anchors.horizontalCenter: parent.horizontalCenter }
                Text { text: "Copy"; color: "#fff"; font.pixelSize: 9; anchors.horizontalCenter: parent.horizontalCenter }
            }
            MouseArea {
                anchors.fill: parent; onClicked: { 
                    mainCanvas.duplicateLayer(layerIndex); 
                    layersListRef.swipedIndex = -1 
                }
            }
        }
        
        // Lock
        Rectangle {
            width: 50; height: parent.height; radius: 10
            color: isLocked ? "#ff9500" : "#34c759"
            Column {
                anchors.centerIn: parent
                spacing: 2
                Image { source: isLocked ? iconPath("unlock.svg") : iconPath("lock.svg"); width: 18; height: 18; anchors.horizontalCenter: parent.horizontalCenter }
                Text { text: isLocked ? "Unlock" : "Lock"; color: "#fff"; font.pixelSize: 9; anchors.horizontalCenter: parent.horizontalCenter }
            }
            MouseArea {
                anchors.fill: parent; onClicked: { 
                    mainCanvas.toggleLock(listIndex); 
                    layersListRef.swipedIndex = -1 
                }
            }
        }
        
        // Delete
        Rectangle {
            width: layerType !== "background" ? 50 : 0
            visible: layerType !== "background"
            height: parent.height; radius: 10
            color: "#ff453a"
            Column {
                anchors.centerIn: parent
                spacing: 2
                Image { source: iconPath("trash-2.svg"); width: 18; height: 18; anchors.horizontalCenter: parent.horizontalCenter }
                Text { text: "Delete"; color: "#fff"; font.pixelSize: 9; anchors.horizontalCenter: parent.horizontalCenter }
            }
            MouseArea {
                anchors.fill: parent; onClicked: { 
                    mainCanvas.removeLayer(listIndex); 
                    layersListRef.swipedIndex = -1 
                }
            }
        }
    }

    // --- 2. MAIN SWIPEABLE CONTENT ---
    Rectangle {
        id: layerContent
        width: parent.width - 4
        height: parent.height - 4
        // REMOVED anchors.horizontalCenter to allow X movements!
        anchors.verticalCenter: parent.verticalCenter
        
        // --- POSITION & ANIMATION ---
        // baseX logic: -140 when open, +40 displacement when clipped
        property real baseX: (layerDelegate.isSwipedOpen ? -150 : 0) + (isClipped ? 40 : 2)
        x: baseX // Bound to base, but overridden by drag
        
        radius: 12
        color: isClipped ? "#151517" : (isActive ? "#2c2c2e" : "#232325")
        border.width: (isActive || layersListRef.optionsIndex === layerIndex) ? 2 : 0.5
        border.color: (isActive || layersListRef.optionsIndex === layerIndex) ? colorAccent : (isClipped ? "#333" : "#3a3a3c")
        
        clip: true 
        
        Behavior on x { 
            enabled: !dragArea.drag.active
            NumberAnimation { duration: 300; easing.type: Easing.OutBack; easing.overshoot: 0.6 } 
        }

        // --- HEADER CONTENT (60px) ---
        Item {
            id: headerRow
            width: parent.width
            height: 60
            anchors.top: parent.top
            
            // --- MOUSE AREA (DRAG & CLICK) ---
            MouseArea {
                id: dragArea
                anchors.fill: parent
                property real startX: 0
                
                drag.target: layerContent
                drag.axis: Drag.XAxis
                drag.minimumX: -220
                drag.maximumX: 180
                drag.filterChildren: true 

                onPressed: { startX = mouseX }
                
                onClicked: {
                    if (layersListRef.swipedIndex !== -1 || layersListRef.optionsIndex !== -1) {
                        layersListRef.swipedIndex = -1
                        layersListRef.optionsIndex = -1
                        return
                    }
                    
                    // Activate Layer
                    mainCanvas.setActiveLayer(layerIndex)
                    
                    if (layerType === "background") {
                        bgColorDialog.open()
                    } else {
                        // Open Context Menu logic
                        var idx = layerIndex
                        layerContextMenu.targetLayerIndex = idx
                        layerContextMenu.targetLayerName = layerName || ""
                        layerContextMenu.targetAlphaLock = isAlphaLocked || false
                        
                        var rowRel = mapToItem(layersPanel, 0, 0)
                        layerContextMenu.y = rowRel.y
                        layerContextMenu.x = -layerContextMenu.width - 12
                        
                        var maxY = layersPanel.height - layerContextMenu.height
                        if (layerContextMenu.y > maxY) layerContextMenu.y = maxY
                        if (layerContextMenu.y < 0) layerContextMenu.y = 0
                        
                        layerContextMenu.visible = true
                    }
                }
                
                onReleased: {
                    var delta = mouseX - startX
                    var isOpen = layerDelegate.isSwipedOpen
                    
                    if (isOpen) {
                        // Easier to close if swiped
                        if (delta > 20) {
                            layersListRef.swipedIndex = -1
                        }
                    } else {
                        if (delta < -35) {
                            // Comfortably swipe left to show actions
                            layersListRef.swipedIndex = listIndex
                            layersListRef.optionsIndex = -1 // Close expanded settings when swiping
                        } else if (delta > 45) {
                            // Effortlessly swipe right to toggle clipping mask
                            mainCanvas.toggleClipping(layerIndex)
                        }
                    }
                    layerContent.x = Qt.binding(function() { return layerContent.baseX })
                }
            }
            
            // --- CONTENT ELEMENTS ---
            Row {
                anchors.fill: parent
                anchors.leftMargin: 8 + (layerDepth * 16)
                anchors.rightMargin: 8
                spacing: 8
                
                // Clipping Mask Arrow (Premium Indicator)
                Item {
                    width: isClipped ? 12 : 0
                    height: 20
                    visible: isClipped
                    anchors.verticalCenter: parent.verticalCenter
                    Image {
                        source: iconPath("arrow-down-left.svg") // Standard clipping icon
                        width: 12; height: 12
                        anchors.centerIn: parent
                        opacity: 0.6
                        rotation: -90 // Point down towards base layer
                    }
                    Behavior on width { NumberAnimation { duration: 200 } }
                }

                // Group Chevron
                Item {
                    width: layerType === "group" ? 22 : 0
                    height: 22
                    visible: layerType === "group"
                    anchors.verticalCenter: parent.verticalCenter
                    Image {
                        source: iconPath("chevron-down.svg")
                        width: 16; height: 16
                        anchors.centerIn: parent
                        rotation: isGroupExpanded ? 0 : -90
                        opacity: 0.7
                        Behavior on rotation { NumberAnimation { duration: 150 } }
                    }
                    MouseArea {
                        anchors.fill: parent
                        onClicked: mainCanvas.toggleGroupExpanded(layerIndex)
                    }
                }
                
                // Thumbnail Box
                Rectangle {
                    width: 52; height: 38; radius: 6
                    anchors.verticalCenter: parent.verticalCenter
                    color: layerType === "background" ? "white" : "#2a2a2c"
                    clip: true
                    border.color: isActive ? colorAccent : "#48484a"
                    border.width: isActive ? 2 : 1
                    
                    Image {
                         visible: layerType !== "background"
                         anchors.fill: parent
                         source: iconPath("grid_pattern.svg"); fillMode: Image.Tile; opacity: 0.1
                    }
                    Image {
                        visible: layerType !== "background" && layerType !== "group"
                        anchors.fill: parent; anchors.margins: 2
                        source: thumbnailSource || ""
                        fillMode: Image.PreserveAspectFit
                        cache: false
                    }
                    // Indicators
                    Image { 
                        visible: isAlphaLocked
                        source: iconPath("lock.svg"); width: 10; height: 10
                        anchors.right: parent.right; anchors.bottom: parent.bottom; anchors.margins: 2
                        z: 2
                    }
                    Rectangle {
                        visible: isLocked
                        width: 14; height: 14; radius: 7; color: "#ff9500"
                        anchors.right: parent.right; anchors.bottom: parent.bottom; anchors.margins: -2
                        Text { text: "🔒"; font.pixelSize: 8; anchors.centerIn: parent }
                    }
                }
                
                // Name & Blend Mode Info
                Column {
                    width: parent.width - 200 // Flexible width
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: 2
                    Text { 
                        text: layerName; color: isVisible ? "white" : "#666"
                        font.pixelSize: 13; font.weight: Font.Medium
                        elide: Text.ElideRight; width: parent.width 
                    }
                    Row {
                        spacing: 4
                        Rectangle {
                            color: "#1a2a1a"; radius: 4; width: 50; height: 16
                            Text { text: blendMode; color: "#aaa"; font.pixelSize: 9; anchors.centerIn: parent }
                        }
                    }
                }
                
                // Premium Settings Button
                Rectangle {
                    width: 30; height: 30; radius: 6
                    color: settingsMouse.containsMouse ? "#3a3a3c" : "transparent"
                    anchors.verticalCenter: parent.verticalCenter
                    Image { source: iconPath("sliders.svg"); width: 18; height: 18; anchors.centerIn: parent; opacity: 0.9 }
                    MouseArea {
                        id: settingsMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            if (layerType !== "background") {
                                var newIdx = (layersListRef.optionsIndex === layerIndex) ? -1 : layerIndex
                                layersListRef.optionsIndex = newIdx
                                layersListRef.swipedIndex = -1
                            }
                        }
                    }
                }
                
                // PREMIUM Visibility Eye
                Rectangle {
                    width: 34; height: 34; radius: 8
                    color: eyeMouse.containsMouse ? "#3a3a3c" : "transparent"
                    border.color: eyeMouse.containsMouse ? "#48484a" : "transparent"
                    border.width: 1
                    anchors.verticalCenter: parent.verticalCenter
                    Image { 
                        source: isVisible ? iconPath("eye.svg") : iconPath("eye-off.svg")
                        width: 18; height: 18
                        anchors.centerIn: parent
                        opacity: isVisible ? 0.9 : 0.4 
                    }
                    MouseArea { 
                        id: eyeMouse
                        anchors.fill: parent
                        hoverEnabled: true 
                        onClicked: mainCanvas.toggleVisibility(layerIndex) 
                    }
                }

                // GRIP HANDLE (For reordering)
                Item {
                    width: 30; height: 30
                    anchors.verticalCenter: parent.verticalCenter
                    Image { source: iconPath("grip.svg"); width: 14; height: 14; anchors.centerIn: parent; opacity: 0.3 }
                    
                    MouseArea {
                        id: gripMouse
                        anchors.fill: parent
                        cursorShape: Qt.SizeVerCursor
                        
                        onPressed: {
                            layersListRef.interactive = false
                            var pos = mapToItem(layersPanel, mouse.x, mouse.y)
                            // Note: dragGhost must be accessible in Parent scope (main_pro.qml)
                            if (typeof dragGhost !== 'undefined') {
                                dragGhost.y = pos.y - 20
                                dragGhost.targetDepth = layerDepth
                                dragGhost.x = 12 + dragGhost.targetDepth * 16
                                dragGhost.infoText = layerName
                                dragGhost.visible = true
                            }
                        }
                        onPositionChanged: {
                            var pos = mapToItem(layersPanel, mouse.x, mouse.y)
                            if (typeof dragGhost !== 'undefined') {
                                dragGhost.y = pos.y - 20
                                var relativeX = mouse.x
                                var depthShift = Math.floor(relativeX / 20)
                                var newTargetDepth = Math.max(0, layerDepth + depthShift)
                                dragGhost.targetDepth = Math.min(newTargetDepth, 4) 
                                dragGhost.x = 12 + dragGhost.targetDepth * 16
                            }
                        }
                        onReleased: {
                            layersListRef.interactive = true
                            if (typeof dragGhost !== 'undefined') {
                                dragGhost.visible = false
                                var pos = mapToItem(layersListRef, mouse.x, mouse.y)
                                var rowH = 68 // Standard row height
                                var dropIdx = Math.floor((pos.y + layersListRef.contentY) / rowH)
                                if (dropIdx < 0) dropIdx = 0
                                if (dropIdx >= layerModel.count) dropIdx = layerModel.count - 1
                                var targetItem = layerModel.get(dropIdx)
                                if (targetItem) {
                                    mainCanvas.moveLayer(layerIndex, targetItem.layerId, dragGhost.targetDepth)
                                }
                            }
                        }
                    }
                }
            } // End Content Row
            
        } // End Header Item

        // --- 3. OPTIONS PANEL (Expanded) ---
        // Visible only when expanded. Pushed down below header.
        Rectangle {
            id: optionsPanel
            anchors.top: headerRow.bottom
            width: parent.width
            height: parent.height - 60
            color: "#1c1c1e" // SOLID BACKGROUND to fix transparency/overlap issues!
            visible: layersListRef.optionsIndex === layerIndex
            opacity: visible ? 1 : 0
            
            // Eat clicks to prevent passing to canvas!
            MouseArea {
                anchors.fill: parent
                preventStealing: true
                onWheel: wheel.accepted = true // Stop scroll propagation
            }

            Column {
                anchors.fill: parent
                anchors.margins: 12
                spacing: 12
                
                // Divider
                Rectangle { width: parent.width; height: 1; color: "#333" }
                
                // Opacity Slider
                RowLayout {
                    width: parent.width
                    Text { text: "Opacity"; color: "#aaa"; font.pixelSize: 11 }
                    Slider {
                        Layout.fillWidth: true
                        from: 0; to: 1
                        value: layerOpacity
                        onMoved: mainCanvas.setLayerOpacity(layerIndex, value)
                    }
                    Text { text: Math.round(layerOpacity * 100) + "%"; color: "#fff"; font.pixelSize: 11; width: 30 }
                }

                // Private Layer Toggle
                RowLayout {
                    width: parent.width
                    spacing: 10
                    Image { 
                        source: iconPath(isPrivate ? "eye-off.svg" : "eye.svg"); 
                        width: 14; height: 14; opacity: 0.7 
                    }
                    Text { 
                        text: "Private Layer (Hidden in Timelapse)"; 
                        color: isPrivate ? "#ff453a" : "#aaa"; 
                        font.pixelSize: 11; Layout.fillWidth: true 
                    }
                    Switch {
                        checked: isPrivate
                        scale: 0.7
                        onToggled: mainCanvas.setLayerPrivate(layerIndex, checked)
                    }
                }
                
                // Blend Modes
                Text { text: "Blend Mode"; color: "#aaa"; font.pixelSize: 11 }
                
                ListView {
                    width: parent.width
                    height: 160
                    clip: true
                    model: ["Normal", "Multiply", "Screen", "Overlay", "Darken", "Lighten", "Color Dodge", "Color Burn", "Add", "Difference", "Exclusion", "Soft Light", "Hard Light"]
                    
                    // Specific scroll bar / handler to avoid canvas scroll
                    boundsBehavior: Flickable.StopAtBounds
                    
                    delegate: Rectangle {
                        width: parent.width
                        height: 32
                        color: "transparent"
                        
                        // Highlight current
                        Rectangle {
                            anchors.fill: parent
                            color: colorAccent
                            opacity: 0.1
                            visible: modelData === blendMode
                        }
                        
                        Row {
                            anchors.fill: parent; anchors.leftMargin: 8; spacing: 8
                            Text { text: modelData === blendMode ? "✓" : ""; color: colorAccent; width: 12 }
                            Text { text: modelData; color: "white"; font.pixelSize: 12; anchors.verticalCenter: parent.verticalCenter }
                        }
                        
                        MouseArea {
                            anchors.fill: parent
                            onClicked: mainCanvas.setLayerBlendMode(layerIndex, modelData)
                        }
                    }
                }
            }
        }
    } // End LayerContent Rectangle
}
