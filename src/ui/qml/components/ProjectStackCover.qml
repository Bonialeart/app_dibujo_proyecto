import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Effects

Item {
    id: root
    width: 250; height: 290
    
    property string title: ""
    property var previews: []
    property color stackColor: "#34495e"
    property int itemCount: 0
    property bool isSketchbook: false

    // Bottom label (matches SketchbookCover style)
    Text {
        anchors.bottom: parent.bottom; anchors.bottomMargin: 0
        anchors.horizontalCenter: parent.horizontalCenter
        text: root.title
        color: "white"
        font.pixelSize: 14; font.weight: Font.Medium
        width: parent.width - 20; horizontalAlignment: Text.AlignHCenter
        elide: Text.ElideRight
    }
    
    Text {
        anchors.top: parent.bottom; anchors.topMargin: -20
        anchors.horizontalCenter: parent.horizontalCenter
        text: root.isSketchbook ? "Sketchbook" : (root.itemCount + " artworks")
        color: "#666"
        font.pixelSize: 11
    }

    // The Container for the "Stack"
    Item {
        id: stackContainer
        width: parent.width; height: parent.height - 40
        anchors.top: parent.top
        
        // Background shadow for the whole stack
        Rectangle {
            anchors.fill: stackContainer
            anchors.margins: 10
            anchors.topMargin: 20
            color: "black"; radius: 12; opacity: 0.2
        }

        // Draw the stack items in reverse (last on top)
        Repeater {
            model: Math.max(1, Math.min(3, root.previews.length))
            delegate: Item {
                width: stackContainer.width - 20; height: stackContainer.height - 20
                anchors.centerIn: parent
                
                // Offset and rotation for stack effect
                // Index 0 is the most recent (on top)
                // We want to show 2, 1, 0 (top)
                
                property int revIndex: (root.previews.length > 0) ? (Math.min(3, root.previews.length) - 1 - index) : 0
                
                z: revIndex 
                rotation: index * 4 - 4 // -4, 0, 4
                x: index * 6 - 6
                y: index * 4 - 8

                Rectangle {
                    anchors.fill: parent
                    color: "#1c1c1e"
                    radius: 12
                    border.color: "#333"
                    border.width: 1
                    clip: true
                    
                    // The thumbnail
                    Image {
                        anchors.fill: parent
                        source: root.previews[revIndex] || ""
                        fillMode: Image.PreserveAspectCrop
                        opacity: revIndex === (Math.min(3, root.previews.length) - 1) ? 1.0 : 0.7
                        visible: source != ""
                    }
                    
                    // If no image, show a placeholder
                    Rectangle {
                        anchors.fill: parent
                        color: root.stackColor
                        opacity: 0.4
                        visible: !root.previews[revIndex]
                        
                        Text {
                            anchors.centerIn: parent
                            text: "Empty"
                            color: "white"; opacity: 0.3; font.pixelSize: 14
                        }
                    }
                    
                    // Subtle shadow on each card
                    Rectangle {
                        anchors.fill: parent
                        color: "transparent"
                        border.color: Qt.rgba(0,0,0,0.2)
                        border.width: 1
                        radius: 12
                    }
                }
            }
        }
        
        // Folder tag (Premium detail)
        Rectangle {
            visible: !root.isSketchbook
            width: 70; height: 16; radius: 4
            color: root.stackColor
            anchors.bottom: stackContainer.top; anchors.left: stackContainer.left; anchors.leftMargin: 20
            anchors.bottomMargin: -4
            z: -1
        }
    }
}
