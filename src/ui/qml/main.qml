import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import QtQuick.Window 2.15

ApplicationWindow {
    id: window
    visible: true
    width: 1280
    height: 800
    title: "ArtFlow Studio Pro"
    color: "transparent"
    flags: Qt.FramelessWindowHint | Qt.Window

    property color bgDark: "#0f0f12"
    property color bgPanel: "#1a1a20"
    property color accentColor: "#00d4aa"

    // Fondo principal
    Rectangle {
        id: mainBackground
        anchors.fill: parent
        color: bgDark
        radius: 16
        border.color: "#333344"
        
        // --- TITLE BAR ---
        Rectangle {
            id: titleBar
            height: 40; width: parent.width
            color: "transparent"
            
            Text {
                text: "ARTFLOW STUDIO (QML DEMO)"
                color: "#808090"
                font.bold: true
                anchors.centerIn: parent
            }
            
            Row {
                anchors.right: parent.right; anchors.rightMargin: 16
                anchors.verticalCenter: parent.verticalCenter
                spacing: 8
                Rectangle { width: 12; height: 12; radius: 6; color: "#ff5f56"; MouseArea { anchors.fill: parent; onClicked: Qt.quit() } }
                Rectangle { width: 12; height: 12; radius: 6; color: "#ffbd2e" }
                Rectangle { width: 12; height: 12; radius: 6; color: "#27c93f" }
            }
            
            MouseArea {
                anchors.fill: parent
                property point lastMousePos: Qt.point(0, 0)
                onPressed: { lastMousePos = Qt.point(mouseX,mouseY); }
                onPositionChanged: { if (pressed) { window.x += mouseX - lastMousePos.x; window.y += mouseY - lastMousePos.y } }
            }
        }

        // --- CONTENIDO ---
        RowLayout {
            anchors.top: titleBar.bottom; anchors.bottom: parent.bottom
            anchors.left: parent.left; anchors.right: parent.right
            anchors.margins: 20
            spacing: 20

            // SIDEBAR
            Rectangle {
                Layout.preferredWidth: 80; Layout.fillHeight: true
                color: bgPanel; radius: 16
                Column {
                    anchors.centerIn: parent; spacing: 30
                    Repeater {
                        model: ["🏠", "🎨", "📁", "⚙️"]
                        Text { 
                            text: modelData; font.pixelSize: 28; color: index===0?accentColor:"#666" 
                            anchors.horizontalCenter: parent.horizontalCenter
                        }
                    }
                }
            }

            // MAIN AREA
            ColumnLayout {
                Layout.fillWidth: true; Layout.fillHeight: true
                spacing: 20
                
                Text { text: "Bienvenido de nuevo"; color: "white"; font.pixelSize: 32 }
                
                // HERO
                RowLayout {
                    Layout.preferredHeight: 300; Layout.fillWidth: true
                    spacing: 20
                    
                    // NEW CANVAS
                    Rectangle {
                        Layout.preferredWidth: 300; Layout.fillHeight: true
                        color: "transparent"; radius: 20
                        border.color: accentColor; border.width: 1
                        
                        // Fake gradient background
                        Rectangle { anchors.fill: parent; radius: 20; color: accentColor; opacity: 0.05 }

                        Column {
                            anchors.centerIn: parent
                            Text { text: "+"; font.pixelSize: 60; color: accentColor; anchors.horizontalCenter: parent.horizontalCenter }
                            Text { text: "Nuevo Lienzo"; font.pixelSize: 18; color: "white"; font.bold: true; anchors.horizontalCenter: parent.horizontalCenter }
                        }
                    }
                    
                    // RECENT
                    Rectangle {
                        Layout.fillWidth: true; Layout.fillHeight: true
                        color: bgPanel; radius: 20
                        Text { text: "Recientes"; color: "#666"; anchors.margins: 20; anchors.top: parent.top; anchors.left: parent.left }
                        
                        Row {
                            anchors.centerIn: parent; spacing: 20
                            Repeater {
                                model: 3
                                Rectangle {
                                    width: 150; height: 120; color: "#252530"; radius: 12
                                    Rectangle { width: 150; height: 80; radius: 12; color: index==0?"#ff512f":index==1?"#8e2de2":"#10b981" }
                                }
                            }
                        }
                    }
                }
                
                // FOOTER
                Rectangle {
                    Layout.fillWidth: true; Layout.fillHeight: true
                    color: bgPanel; radius: 20
                }
            }
        }
    }
}
