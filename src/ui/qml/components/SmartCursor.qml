import QtQuick 2.15

Item {
    id: root
    
    // Properties to be bound from Main
    property real brushSize: 20
    property real zoomLevel: 1.0
    property bool isActive: true
    
    // New Advanced Cursor Properties
    property real rotationAngle: 0
    property real pressure: 1.0
    property real roundness: 1.0 // 1.0 = Circle, <1.0 = Ellipse
    
    // Calculate visual size based on pressure and zoom
    // We enforce a minimum size so it doesn't disappear completely
    property real actualSize: Math.max(5, brushSize * zoomLevel * pressure)
    property real actualHeight: actualSize * roundness
    
    // The Item size defines the bounding box for positioning
    width: Math.max(actualSize, actualHeight)
    height: width
    
    visible: isActive
    z: 1500 // High Z-order to stay on top
    
    // The actual brush tip shape
    Rectangle {
        id: tipShape
        anchors.centerIn: parent
        
        width: root.actualSize
        height: root.actualHeight
        radius: width / 2 // Fully rounded corners creates ellipse
        
        color: "transparent"
        border.color: "white"
        border.width: 1
        
        // Apply rotation
        rotation: root.rotationAngle
        
        // Better quality
        antialiasing: true
        
        // Inner contrast ring (for visibility on white backgrounds)
        Rectangle {
            anchors.fill: parent
            anchors.margins: 1
            radius: width / 2
            
            color: "transparent"
            border.color: "black"
            border.width: 1
            opacity: 0.5
        }
        
        // Direction indicator (Line) for very flat brushes (Calligraphic) to show angle
        Rectangle {
            anchors.centerIn: parent
            width: parent.width
            height: 1
            color: "white"
            visible: root.roundness < 0.5 // Only show "axis" if it's very distinct
            opacity: 0.5
        }
    }
    
    // Precision Crosshair (Center)
    // Only visible if the cursor is large enough to need a center point
    Item {
        anchors.centerIn: parent
        visible: root.actualSize > 15
        
        Rectangle {
            color: "#ffffff"
            width: 4; height: 1
            anchors.centerIn: parent
            Rectangle { anchors.centerIn: parent; width: 6; height: 3; color: "black"; opacity: 0.3; z: -1 }
        }
        Rectangle {
            color: "#ffffff"
            width: 1; height: 4
            anchors.centerIn: parent
            Rectangle { anchors.centerIn: parent; width: 3; height: 6; color: "black"; opacity: 0.3; z: -1 }
        }
    }
    
    // Smooth movement handled by external X/Y binding, but we can smooth rotation/size here
    Behavior on actualSize { NumberAnimation { duration: 50; easing.type: Easing.OutQuad } }
    Behavior on actualHeight { NumberAnimation { duration: 50; easing.type: Easing.OutQuad } }
    Behavior on rotationAngle { 
        // Use a short duration for rotation to avoid lag, but smooth out jitter
        NumberAnimation { duration: 60; easing.type: Easing.OutQuad } 
    }
}
