import QtQuick 2.15

Rectangle {
    id: root
    visible: false
    color: "#1c1c1e"
    border.color: "#6366f1" // colorAccent
    border.width: 1
    radius: 18
    z: 9999 // Always on Top

    property string imageSource: ""
    property var mainWindow: null // Reference to main window for dimensions
    
    // Explicitly expose functions we want to call
    function start(startRect, imgSource, projectPath, callback) {
        // 1. Setup Hero Initial State
        root.x = startRect.x
        root.y = startRect.y
        root.width = startRect.width
        root.height = startRect.height
        root.radius = 18
        root.imageSource = imgSource
        root.border.width = 1
        root.visible = true
        
        // 2. Perform callback (load project)
        if (callback(projectPath)) {
            // 3. Start Animation
            heroAnimOpen.start()
        } else {
             // Fail gracefully
             root.visible = false
        }
    }

    Image {
        id: heroImage
        source: root.imageSource
        anchors.fill: parent
        fillMode: Image.PreserveAspectCrop
        opacity: 1
    }
    
    SequentialAnimation {
        id: heroAnimOpen
        running: false
        
        // 1. Expansion Phase (Transform into Canvas)
        ParallelAnimation {
            NumberAnimation { target: root; property: "x"; to: 0; duration: 600; easing.type: Easing.OutQuint }
            NumberAnimation { target: root; property: "y"; to: 0; duration: 600; easing.type: Easing.OutQuint }
            NumberAnimation { target: root; property: "width"; to: (mainWindow ? mainWindow.width : 1440); duration: 600; easing.type: Easing.OutQuint }
            NumberAnimation { target: root; property: "height"; to: (mainWindow ? mainWindow.height : 900); duration: 600; easing.type: Easing.OutQuint }
            NumberAnimation { target: root; property: "radius"; to: 0; duration: 400; easing.type: Easing.OutQuint }
            NumberAnimation { target: root; property: "border.width"; to: 0; duration: 300 }
        }
        
        // 2. Seamless Dissolve (Reveal UI)
        NumberAnimation { target: root; property: "opacity"; to: 0; duration: 300; easing.type: Easing.InOutQuad }
        
        // 3. Cleanup
        ScriptAction {
            script: {
                root.visible = false
                root.opacity = 1.0 // Reset for next time
            }
        }
    }
}
