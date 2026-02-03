import QtQuick
import QtQuick.Window
import ArtFlow 1.0

Window {
    visible: true
    width: 640
    height: 480
    title: "Debug Canvas"
    
    QCanvasItem {
        anchors.fill: parent
        // Just a basic canvas
    }
}
