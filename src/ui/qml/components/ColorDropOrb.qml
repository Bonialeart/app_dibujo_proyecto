import QtQuick 2.15

Item {
    id: root
    property color dropColor: "blue"
    property bool active: false
    
    // Smaller, more precise size
    width: 32; height: 32
    visible: active
    z: 9999
    
    // Center logic
    transform: Translate { x: -width/2; y: -height/2 }

    // Animation scale
    scale: active ? 1.0 : 0.0
    Behavior on scale { NumberAnimation { duration: 250; easing.type: Easing.OutBack } }

    // 1. Premium Soft Shadow (Simpler & More Efficient)
    Rectangle {
        anchors.fill: parent
        anchors.margins: -4
        radius: height/2
        color: "black"
        opacity: 0.25
        z: -1
    }

    // 2. Main Orb
    Rectangle {
        id: mainCircle
        anchors.fill: parent
        radius: width/2
        color: root.dropColor
        border.color: "white"
        border.width: 2 // Thinner border for smaller size
        
        // --- Premium Details ---
        // Subtle Inner Glow (Glass effect)
        Rectangle {
            anchors.fill: parent
            anchors.margins: 2
            radius: width/2
            gradient: Gradient {
                GradientStop { position: 0.0; color: "#44ffffff" }
                GradientStop { position: 0.4; color: "transparent" }
                GradientStop { position: 1.0; color: "#22000000" }
            }
        }
    }
}
