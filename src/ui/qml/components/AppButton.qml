import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Button {
    id: root
    property string iconSource: "" // Icon path
    property bool active: false
    property color colorAccent: "#0a84ff"
    property color backgroundColor: "transparent"
    
    width: 60; height: 60
    
    // Customize the button look to match original design
    background: Rectangle {
        color: root.active ? root.colorAccent : (root.hovered ? "#1affffff" : root.backgroundColor)
        radius: 12
        opacity: root.active ? 0.2 : 1.0
        
        Behavior on color { ColorAnimation { duration: 200 } }
    }
    
    contentItem: RowLayout {
        spacing: 8
        anchors.centerIn: parent
        
        Image {
            id: iconImage
            visible: root.iconSource !== ""
            source: (root.iconSource && (root.iconSource.startsWith("image://") ? root.iconSource : "image://icons/" + root.iconSource)) || ""
            Layout.preferredWidth: 24; Layout.preferredHeight: 24
            sourceSize.width: 48; sourceSize.height: 48
            opacity: root.active ? 1.0 : 0.6
        }
        
        Text {
            visible: root.text !== ""
            text: root.text
            color: root.active ? root.colorAccent : (root.hovered ? "#fff" : "#ddd")
            font.pixelSize: 13
            font.weight: Font.Medium
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
        }
    }
}
