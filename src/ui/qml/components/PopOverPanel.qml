import QtQuick 2.15
import QtQuick.Controls 2.15

Rectangle {
    id: root
    
    // Block scroll propagation to canvas
    MouseArea { 
        anchors.fill: parent
        hoverEnabled: true
        function onWheel(wheel) { wheel.accepted = true }
    }
    
    // Properties
    property string title: "Panel"
    default property alias content: contentArea.data
    
    // Appearance
    color: "#1e1e1e"
    radius: 12
    border.color: "#333"
    border.width: 1
    
    // Shadow support (optional, requires specific import or implementation)
    // layer.enabled: true
    
    // Header
    Item {
        id: header
        width: parent.width
        height: 40
        anchors.top: parent.top
        
        Text {
            text: root.title
            color: "white"
            font.pixelSize: 14
            font.bold: true
            anchors.centerIn: parent
        }
        
        Rectangle {
            width: parent.width; height: 1
            color: "#333"
            anchors.bottom: parent.bottom
        }
    }
    
    // Content Container
    Item {
        id: contentArea
        anchors.top: header.bottom
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        clip: true
    }
}
