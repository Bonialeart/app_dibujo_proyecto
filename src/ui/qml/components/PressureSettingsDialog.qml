import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import QtQuick.Shapes 1.15

Popup {
    id: root
    
    // Properties
    property var canvasItem: null
    property var currentCurveWithPoints: [0.25, 0.25, 0.75, 0.75] // Default Linear
    
    modal: true
    focus: true
    width: 600
    height: 420
    
    anchors.centerIn: parent
    
    background: Rectangle {
        color: "#252526"
        border.color: "#3e3e42"
        radius: 8
        
        // Shadow
        Rectangle { z: -1; anchors.fill: parent; anchors.margins: -4; opacity: 0.3; color: "black"; radius: 12 }
    }
    
    // --- Header ---
    Text {
        text: "Adjust Pen Pressure"
        color: "white"
        font.pixelSize: 16
        font.bold: true
        anchors.top: parent.top; anchors.left: parent.left; anchors.margins: 16
    }
    
    // --- Window Controls ---
    Button {
        text: "✕"
        background: Rectangle { color: "transparent" }
        contentItem: Text { text: "✕"; color: "#aaa"; font.pixelSize: 16; horizontalAlignment: Text.AlignHCenter }
        width: 30; height: 30
        anchors.top: parent.top; anchors.right: parent.right; anchors.margins: 12
        onClicked: root.close()
    }
    
    RowLayout {
        anchors.fill: parent; anchors.topMargin: 50; anchors.bottomMargin: 16; anchors.leftMargin: 20; anchors.rightMargin: 20
        spacing: 20
        
        // LEFT: Graph Editor
        Rectangle {
            width: 320; Layout.fillHeight: true
            color: "#1e1e1e"
            border.color: "#333"
            radius: 4
            clip: true
            
            // Grid Background
            Canvas {
                id: grid
                anchors.fill: parent
                onPaint: {
                    var ctx = getContext("2d")
                    ctx.strokeStyle = "#444"
                    ctx.lineWidth = 1
                    var w = width; var h = height;
                    
                    ctx.beginPath()
                    // Vertical Lines (0%, 25%, 50%, 75%, 100%)
                    for(var i=0; i<=4; i++) {
                         ctx.moveTo(w*i/4, 0); ctx.lineTo(w*i/4, h);
                    }
                    // Horizontal Lines
                    for(var j=0; j<=4; j++) {
                         ctx.moveTo(0, h*j/4); ctx.lineTo(w, h*j/4);
                    }
                    ctx.stroke()
                    
                    // Labels
                    ctx.fillStyle = "#888"
                    ctx.font = "10px sans-serif"
                    ctx.fillText("Output", 4, h/2)
                    ctx.fillText("Pressure", w/2, h-4)
                }
            }
            
            // Curve Draw
            Shape {
                id: curveShape
                anchors.fill: parent
                
                ShapePath {
                    strokeColor: "#6366f1" // Accent
                    strokeWidth: 2
                    fillColor: "transparent"
                    
                    // Bezier P0 -> P3
                    startX: 0
                    startY: parent.height
                    
                    PathCubic {
                        id: bezierCurve
                        x: parent.width; y: 0 // End (Top-Right)
                        control1X: root.currentCurveWithPoints[0] * parent.width
                        control1Y: (1.0 - root.currentCurveWithPoints[1]) * parent.height
                        control2X: root.currentCurveWithPoints[2] * parent.width
                        control2Y: (1.0 - root.currentCurveWithPoints[3]) * parent.height
                    }
                }
            }
            
            // Handles for P1 and P2
            // P1 Handle
            Rectangle {
                id: p1Handle
                width: 12; height: 12; radius: 6
                color: "white"
                border.color: "#6366f1"; border.width: 2
                
                x: (root.currentCurveWithPoints[0] * parent.width) - width/2
                y: ((1.0 - root.currentCurveWithPoints[1]) * parent.height) - height/2
                
                MouseArea {
                    anchors.fill: parent
                    drag.target: parent
                    drag.axis: Drag.XAndYAxis
                    drag.minimumX: 0; drag.maximumX: parent.parent.width
                    drag.minimumY: 0; drag.maximumY: parent.parent.height
                    
                    onPositionChanged: {
                         var nx = parent.x + parent.width/2
                         var ny = parent.y + parent.height/2
                         // Update Model
                         var arr = root.currentCurveWithPoints
                         arr[0] = nx / parent.parent.width
                         arr[1] = 1.0 - (ny / parent.parent.height)
                         root.currentCurveWithPoints = arr
                         curveShape.requestPaint() // Force redraw if needed
                         
                         // Auto-update canvas for real-time feel?
                         if (canvasItem) canvasItem.updatePressureCurve(root.currentCurveWithPoints)
                    }
                }
            }
            // Line to P1
            Shape { anchors.fill: parent; z: -1; ShapePath { strokeColor: "#555"; startX: 0; startY: parent.height; PathLine { x: p1Handle.x+6; y: p1Handle.y+6 } } }

            // P2 Handle
            Rectangle {
                id: p2Handle
                width: 12; height: 12; radius: 6
                color: "white"
                border.color: "#6366f1"; border.width: 2
                
                x: (root.currentCurveWithPoints[2] * parent.width) - width/2
                y: ((1.0 - root.currentCurveWithPoints[3]) * parent.height) - height/2
                 
                MouseArea {
                    anchors.fill: parent
                    drag.target: parent
                    drag.axis: Drag.XAndYAxis
                    drag.minimumX: 0; drag.maximumX: parent.parent.width
                    drag.minimumY: 0; drag.maximumY: parent.parent.height
                    
                    onPositionChanged: {
                         var nx = parent.x + parent.width/2
                         var ny = parent.y + parent.height/2
                         var arr = root.currentCurveWithPoints
                         arr[2] = nx / parent.parent.width
                         arr[3] = 1.0 - (ny / parent.parent.height)
                         root.currentCurveWithPoints = arr
                         
                         if (canvasItem) canvasItem.updatePressureCurve(root.currentCurveWithPoints)
                    }
                }
            }
             // Line to P2
            Shape { anchors.fill: parent; z: -1; ShapePath { strokeColor: "#555"; startX: parent.width; startY: 0; PathLine { x: p2Handle.x+6; y: p2Handle.y+6 } } }
        }
        
        // RIGHT: Controls & Test Area
        ColumnLayout {
            Layout.fillWidth: true; Layout.fillHeight: true
            spacing: 16
            
            Text {
                text: "Test Area"
                color: "#ccc"
                font.pixelSize: 12
            }
            
            // Testing Canvas (Dummy for now, just visual placeholder or functional if we link it)
            // Ideally this would be a mini canvas where strokes use the CURRENT settings.
            Rectangle {
                Layout.fillWidth: true; Layout.fillHeight: true
                color: "#121214"
                border.color: "#444"
                radius: 4
                
                Text {
                    text: "Scribble here to test..."
                    anchors.centerIn: parent
                    color: "#555"
                }
                
                // Since our main Canvas is separate, we can't easily duplicate it here without creating another QCanvasItem instance.
                // But we can just direct the user to "Test on Canvas" behind the dialog, since it's modal but transparent?
                // Or just use the main canvas.
                // For now, let's keep it simple.
            }
            
            RowLayout {
                Layout.fillWidth: true
                Button {
                    text: "Reset to Default"
                    Layout.fillWidth: true
                    onClicked: {
                        root.currentCurveWithPoints = [0.25, 0.25, 0.75, 0.75]
                        if (canvasItem) canvasItem.updatePressureCurve(root.currentCurveWithPoints)
                    }
                    background: Rectangle { color: "#333"; radius: 4; border.color: "#555" }
                    contentItem: Text { text: parent.text; color: "white"; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                }
                
                Button {
                    text: "Done"
                    Layout.fillWidth: true
                    onClicked: root.close()
                    background: Rectangle { color: "#6366f1"; radius: 4 }
                    contentItem: Text { text: parent.text; color: "white"; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter; font.bold: true }
                }
            }
        }
    }
}
