import QtQuick 2.15
import QtQuick.Layouts 1.15
import QtQuick.Shapes 1.15

Item {
    id: root
    
    // Public API
    function show(message, type) {
        // Enforce max stack size, remove oldest if needed
        if (toastModel.count >= 3) {
            toastModel.remove(0)
        }
        
        toastModel.append({
            "message": message,
            "type": type || "info",
            "id": Date.now()
        })
    }
    
    anchors.fill: parent 
    z: 9999 
    visible: toastModel.count > 0
    
    ListModel { id: toastModel }
    
    ColumnLayout {
        anchors.bottom: parent.bottom
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottomMargin: 60 // Higher up for better visibility
        spacing: 12
        
        Repeater {
            model: toastModel
            delegate: ToastDelegate {
                message: model.message
                type: model.type
                onExpired: {
                    for(var i=0; i<toastModel.count; i++) {
                         if (toastModel.get(i).id === model.id) {
                             toastModel.remove(i)
                             break;
                         }
                    }
                }
            }
        }
    }
    
    component ToastDelegate : Item {
        id: toastItem
        property string message
        property string type
        signal expired()
        
        width: bg.width
        height: 52 // Slightly taller for elegance
        
        Timer {
            interval: 4000
            running: true
            onTriggered: exitAnim.start()
        }
        
        // Entrance & Exit State
        property real animY: 30
        property real animOp: 0
        property real animScale: 0.95
        
        transform: Translate { y: toastItem.animY }
        opacity: toastItem.animOp
        scale: toastItem.animScale
        
        Behavior on animY { NumberAnimation { duration: 500; easing.type: Easing.OutExpo } }
        Behavior on animOp { NumberAnimation { duration: 300 } }
        Behavior on animScale { NumberAnimation { duration: 400; easing.type: Easing.OutBack } }
        
        Component.onCompleted: {
            // Trigger Entrance
            animY = 0
            animOp = 1
            animScale = 1
        }
        
        SequentialAnimation {
            id: exitAnim
            ParallelAnimation {
                NumberAnimation { target: toastItem; property: "animY"; to: 15; duration: 300; easing.type: Easing.InCubic }
                NumberAnimation { target: toastItem; property: "animOp"; to: 0; duration: 200 }
                NumberAnimation { target: toastItem; property: "animScale"; to: 0.9; duration: 300 }
            }
            ScriptAction { script: toastItem.expired() }
        }
        
        // Shadow Layer (Soft diffusion)
        Rectangle {
            z: -1
            anchors.fill: parent; anchors.topMargin: 4
            color: "black"; opacity: 0.25; radius: 26
        }
        Rectangle {
            z: -2
            anchors.fill: parent; anchors.topMargin: 8; anchors.margins: 4
            color: "black"; opacity: 0.15; radius: 26
        }

        Rectangle {
            id: bg
            width: contentRow.width + 48
            height: 52
            radius: 26
            color: "#1e1e20" // Premium Dark Grey
            
            // Subtle premium stroke
            border.color: "#1affffff" 
            border.width: 1
            
            RowLayout {
                id: contentRow
                anchors.centerIn: parent
                spacing: 14
                
                // Icon Container
                Rectangle {
                    width: 24; height: 24; radius: 12
                    color: {
                        if (type === "success") return "#10b981"
                        if (type === "error") return "#ef4444" 
                        return "#6366f1"
                    }
                    
                    // Custom Icon Drawing for sharpness
                    Shape {
                        anchors.fill: parent
                        // Checkmark
                        ShapePath {
                            strokeWidth: 2
                            strokeColor: "white"
                            fillColor: "transparent"
                            capStyle: ShapePath.RoundCap
                            joinStyle: ShapePath.RoundJoin
                            
                            startX: 7; startY: 12
                            PathLine { x: 10; y: 15 }
                            PathLine { x: 17; y: 8 }
                        }
                        visible: type === "success"
                    }
                    
                    // Exclamation / Info
                    Text {
                        anchors.centerIn: parent
                        text: type === "error" ? "!" : "i"
                        color: "white"
                        font.bold: true
                        font.pixelSize: 14
                        visible: type !== "success"
                    }
                }
                
                Text {
                    text: message
                    color: "white"
                    font.family: "Segoe UI" // Or system font
                    font.pixelSize: 14
                    font.weight: Font.Medium
                    smooth: true
                }
            }
        }
    }
}
