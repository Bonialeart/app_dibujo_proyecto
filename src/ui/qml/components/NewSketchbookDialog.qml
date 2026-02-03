import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Effects

Dialog {
    id: root
    width: 450; height: 550
    modal: true
    anchors.centerIn: parent
    
    background: Rectangle {
        color: "#161618"
        radius: 20
        border.color: "#2c2c2e"
        border.width: 1
    }

    property string sketchbookTitle: "My Sketchbook"
    property color selectedColor: "#6366f1"
    
    onAboutToShow: {
        titleInput.text = "My Sketchbook " + (recentProjectsModel.count + 1)
        titleInput.forceActiveFocus()
    }

    contentItem: ColumnLayout {
        anchors.fill: parent
        anchors.margins: 30
        spacing: 25

        // HEADER
        Column {
            Layout.fillWidth: true
            spacing: 8
            Text {
                text: "Create New Sketchbook"
                color: "white"
                font.pixelSize: 24; font.bold: true
            }
            Text {
                text: "Organize your drawings in a beautiful digital collection."
                color: "#888"; font.pixelSize: 13
            }
        }

        // PREVIEW AREA
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 180
            color: "#0a0a0c"
            radius: 12
            
            // Reusing the cover look, manually styled here for preview
            Rectangle {
                id: previewCover
                width: 120; height: 160; radius: 4
                color: root.selectedColor
                anchors.centerIn: parent
                
                // Spine
                Rectangle {
                    width: 14; height: parent.height; anchors.left: parent.left
                    color: Qt.darker(parent.color, 1.2)
                }
                
                // Elastic band
                Rectangle {
                    width: 6; height: parent.height
                    anchors.right: parent.right; anchors.rightMargin: 15
                    color: "#1a1a1a"; opacity: 0.4
                }
                
                Text {
                    anchors.centerIn: parent
                    anchors.horizontalCenterOffset: 10
                    width: parent.width - 30
                    text: titleInput.text
                    color: "white"; font.bold: true; font.pixelSize: 11
                    wrapMode: Text.Wrap; horizontalAlignment: Text.AlignHCenter
                    opacity: 0.9
                }
            }
        }

        // TITLE INPUT
        Column {
            Layout.fillWidth: true; spacing: 10
            Text { text: "Title"; color: "#aaa"; font.pixelSize: 12; font.weight: Font.Medium }
            
            TextField {
                id: titleInput
                Layout.fillWidth: true
                placeholderText: "Enter sketchbook title..."
                color: "white"
                font.pixelSize: 15
                padding: 15
                
                background: Rectangle {
                    radius: 10
                    color: "#1e1e20"
                    border.color: titleInput.activeFocus ? colorAccent : "#2c2c2e"
                }
            }
        }

        // COLOR PICKER
        Column {
            Layout.fillWidth: true; spacing: 10
            Text { text: "Cover Color"; color: "#aaa"; font.pixelSize: 12; font.weight: Font.Medium }
            
            Row {
                spacing: 12
                Repeater {
                    model: ["#6366f1", "#ec4899", "#f59e0b", "#10b981", "#3b82f6", "#ef4444", "#8b5cf6", "#1c1c1e"]
                    Rectangle {
                        width: 34; height: 34; radius: 17
                        color: modelData
                        border.color: "white"; border.width: root.selectedColor === modelData ? 2 : 0
                        
                        MouseArea {
                            anchors.fill: parent; cursorShape: Qt.PointingHandCursor
                            onClicked: root.selectedColor = modelData
                        }
                    }
                }
            }
        }

        Item { Layout.fillHeight: true }

        // ACTIONS
        RowLayout {
            Layout.fillWidth: true; spacing: 15
            
            Button {
                id: cancelBtn
                Layout.fillWidth: true; height: 48
                contentItem: Text { text: "Cancel"; color: "white"; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter; font.bold: true }
                background: Rectangle { color: cancelMa.containsMouse ? "#2a2a2e" : "#212123"; radius: 12 }
                MouseArea { id: cancelMa; anchors.fill: parent; hoverEnabled: true; onClicked: root.close() }
            }
            
            Button {
                id: createBtn
                Layout.fillWidth: true; height: 48
                contentItem: Text { text: "Create Sketchbook"; color: "white"; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter; font.bold: true }
                background: Rectangle { color: createMa.containsMouse ? Qt.lighter(colorAccent, 1.1) : colorAccent; radius: 12 }
                MouseArea { 
                    id: createMa; 
                    anchors.fill: parent; 
                    hoverEnabled: true; 
                    onClicked: {
                        console.log("Attempting to create sketchbook: " + titleInput.text)
                        var newPath = mainCanvas.create_new_sketchbook(titleInput.text, root.selectedColor.toString())
                        if (newPath !== "") {
                            // Auto-open logic
                            mainCanvas.enter_folder(newPath)
                            mainWindow.currentPage = 3 // Go to Assets page
                            
                            // mainWindow.refreshGallery() // enter_folder already triggers refresh
                            toastManager.show("Sketchbook created!", "success")
                            root.close()
                        } else {
                            toastManager.show("Failed to create sketchbook", "error")
                        }
                    }
                }
            }
        }
    }
}
