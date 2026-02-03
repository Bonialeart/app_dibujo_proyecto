import QtQuick 2.15
import QtQuick.Controls 2.15

Item {
    id: root
    
    property string label: ""
    property real value: 0.0
    property string previewType: "" // "size", "opacity"
    property bool previewOnRight: false
    
    // Usage implies it needs a height, typically inside a Column
    implicitWidth: 60
    implicitHeight: 200
    
    signal valueChanged(real value)
    
    Column {
        anchors.fill: parent
        spacing: 5
        
        // Slider Track
        Item {
            width: 40
            height: parent.height - 20
            anchors.horizontalCenter: parent.horizontalCenter
            
            // Background
            Rectangle {
                width: 4; height: parent.height
                anchors.centerIn: parent
                color: "#333"
                radius: 2
            }
            
            // Fill
            Rectangle {
                width: 4
                height: parent.height * root.value
                anchors.bottom: parent.bottom
                anchors.horizontalCenter: parent.horizontalCenter
                color: "#6366f1" // Accent
                radius: 2
            }
            
            // Handle
            Rectangle {
                width: 16; height: 16
                radius: 8
                color: "white"
                anchors.horizontalCenter: parent.horizontalCenter
                y: parent.height * (1.0 - root.value) - height/2
            }
            
            MouseArea {
                anchors.fill: parent
                onPositionChanged: {
                    if (pressed) {
                        var val = 1.0 - (mouseY / height)
                        val = Math.max(0.0, Math.min(1.0, val))
                        root.value = val
                        root.valueChanged(val)
                    }
                }
                onPressed: positionChanged(mouse)
            }
        }
        
        Text {
            text: root.label
            color: "#aaa"
            font.pixelSize: 10
            anchors.horizontalCenter: parent.horizontalCenter
        }
    }
}
