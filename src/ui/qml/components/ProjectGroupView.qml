import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Effects

Item {
    id: insideRoot
    property string currentSketchbookPath: ""
    property string sketchbookTitle: "Untitled Sketchbook"
    
    signal backRequested()
    signal pageSelected(string path)
    
    property bool isSketchbook: currentSketchbookPath.indexOf("Sketchbook") !== -1 // Simple heuristic
    
    // Background
    Rectangle {
        anchors.fill: parent
        color: "#0f0f11" 
    }
    
    // Header
    RowLayout {
        id: header
        anchors.top: parent.top; anchors.topMargin: 50
        anchors.left: parent.left; anchors.leftMargin: 50
        anchors.right: parent.right; anchors.rightMargin: 50
        height: 80
        spacing: 25
        
        Rectangle {
            width: 50; height: 50; radius: 25; color: "#1c1c1e"
            border.color: "#333"; border.width: 1
            Text { text: "✕"; color: "white"; anchors.centerIn: parent; font.pixelSize: 20 }
            MouseArea { 
                anchors.fill: parent
                cursorShape: Qt.PointingHandCursor 
                onClicked: insideRoot.backRequested() 
                onEntered: parent.color = "#2c2c2e"
                onExited: parent.color = "#1c1c1e"
                hoverEnabled: true
            }
        }
        
        Column {
            Layout.fillWidth: true
            Text { 
                text: insideRoot.sketchbookTitle; color: "white"
                font.pixelSize: 32; font.weight: Font.Bold
                font.family: "Outfit" 
            }
            Text { 
                text: pagesModel.count + (insideRoot.isSketchbook ? " Pages" : " Artworks")
                color: "#666"
                font.pixelSize: 14; font.family: "Outfit" 
            }
        }
        
        // Add Page/Artwork Button
        Rectangle {
            width: 170; height: 50; radius: 12; color: colorAccent
            Text { 
                text: insideRoot.isSketchbook ? "+ New Page" : "+ New Artwork" 
                color: "white"; font.bold: true; anchors.centerIn: parent; font.pixelSize: 15
            }
            MouseArea { 
                anchors.fill: parent
                cursorShape: Qt.PointingHandCursor
                onClicked: {
                     var newPageName = insideRoot.isSketchbook ? "Page" : "Artwork"
                     mainCanvas.create_new_page(currentSketchbookPath, newPageName)
                     refreshPages()
                }
            }
        }
    }
    
    GridView {
        id: pagesGrid
        anchors.top: header.bottom; anchors.topMargin: 40
        anchors.bottom: parent.bottom; anchors.bottomMargin: 20
        anchors.left: parent.left; anchors.leftMargin: 50
        anchors.right: parent.right; anchors.rightMargin: 50
        cellWidth: 280; cellHeight: 240
        clip: true
        
        model: ListModel { id: pagesModel }
        
        delegate: Item {
            width: 260; height: 220
            
            Rectangle {
                id: pageCard
                anchors.fill: parent; anchors.bottomMargin: 40
                color: "#1c1c1e"
                radius: 12
                border.color: "#333"; border.width: 1
                clip: true
                
                Image {
                    anchors.fill: parent
                    source: model.path
                    fillMode: Image.PreserveAspectCrop
                    asynchronous: true
                }
                
                // Overlay for selection/hover effect
                Rectangle {
                    anchors.fill: parent; color: "white"; opacity: 0.1; visible: mouseArea.containsMouse
                }

                MouseArea {
                    id: mouseArea
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    onClicked: insideRoot.pageSelected(model.realPath || model.path)
                    hoverEnabled: true
                    onEntered: pageCard.scale = 1.02
                    onExited: pageCard.scale = 1.0
                }

                // Delete Button
                Rectangle {
                    width: 28; height: 28; radius: 14; z: 10
                    color: deleteMouse.containsMouse ? "#ef4444" : "#aa1c1c1e"
                    anchors.top: parent.top; anchors.right: parent.right; anchors.margins: 12
                    visible: mouseArea.containsMouse
                    Text { text: "✕"; color: "white"; font.pixelSize: 14; anchors.centerIn: parent }
                    MouseArea {
                        id: deleteMouse
                        anchors.fill: parent; hoverEnabled: true
                        onClicked: {
                            var targetPath = model.realPath || model.path
                            if (mainCanvas.deleteProject(targetPath)) {
                                pagesModel.remove(index)
                            }
                        }
                    }
                }
            }
            
            Text {
                anchors.top: pageCard.bottom; anchors.topMargin: 10
                anchors.left: pageCard.left; anchors.right: pageCard.right
                text: model.name ? model.name.replace(".png", "").replace(".aflow", "") : "Item"
                color: "white"; font.pixelSize: 14; font.weight: Font.Medium
                elide: Text.ElideRight; horizontalAlignment: Text.AlignHCenter
            }
        }
    }
    
    function refreshPages() {
        pagesModel.clear()
        if (currentSketchbookPath === "") return
        
        var pages = mainCanvas.get_sketchbook_pages(currentSketchbookPath)
        for(var i=0; i<pages.length; i++) {
            pagesModel.append(pages[i])
        }
    }
    
    Component.onCompleted: refreshPages()
    onCurrentSketchbookPathChanged: refreshPages()
}
