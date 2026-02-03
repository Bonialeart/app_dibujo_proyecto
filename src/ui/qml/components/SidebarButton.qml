import QtQuick 2.15
import QtQuick.Layouts 1.15

Rectangle {
    id: root
    
    property string iconName: ""
    property string label: ""
    property bool active: false
    
    signal clicked()
    
    Layout.fillWidth: true
    Layout.preferredHeight: 50
    
    color: active ? "#1e1e1e" : "transparent"
    
    // Left active indicator
    Rectangle {
        width: 3; height: parent.height
        color: "#6366f1"
        visible: active
    }
    
    Column {
        anchors.centerIn: parent
        spacing: 4
        
        Image {
            // Try to use iconsUrl if available in context, else fallback (or fail gracefully)
            // Since we can't be sure of iconsUrl availability here without context property:
            // We'll rely on global iconsUrl. If strictly not allowed, this will print error but not crash.
            source: (typeof iconsUrl !== "undefined" ? iconsUrl : "") + root.iconName
            width: 24; height: 24
            anchors.horizontalCenter: parent.horizontalCenter
            opacity: root.active ? 1.0 : 0.5
            mipmap: true
            fillMode: Image.PreserveAspectFit
        }
        
        Text {
            text: root.label
            color: root.active ? "white" : "#777"
            font.pixelSize: 10
            anchors.horizontalCenter: parent.horizontalCenter
        }
    }
    
    MouseArea {
        anchors.fill: parent
        cursorShape: Qt.PointingHandCursor
        onClicked: root.clicked()
    }
}
