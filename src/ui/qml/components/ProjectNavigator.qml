import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: navRoot
    anchors.fill: parent
    
    property var projectsModel: null
    
    signal openDrawing(string path)
    signal openSketchbook(string path, string title)
    signal createNewProject()
    signal createNewGroup()
    
    property alias stack: stack

    function pushGallery() {
        if (stack.currentItem.objectName !== "gallery") {
            stack.push(galleryComp)
        }
    }

    StackView {
        id: stack
        anchors.fill: parent
        initialItem: dashboardComp

        pushEnter: Transition {
            ParallelAnimation {
                NumberAnimation { property: "opacity"; from: 0; to: 1; duration: 300; easing.type: Easing.OutCubic }
                NumberAnimation { property: "scale"; from: 0.95; to: 1; duration: 400; easing.type: Easing.OutBack }
            }
        }
        pushExit: Transition {
            NumberAnimation { property: "opacity"; from: 1; to: 0; duration: 250 }
        }
        popEnter: Transition {
            ParallelAnimation {
                NumberAnimation { property: "opacity"; from: 0; to: 1; duration: 300 }
                NumberAnimation { property: "scale"; from: 1.05; to: 1; duration: 400; easing.type: Easing.OutBack }
            }
        }
        popExit: Transition {
            NumberAnimation { property: "opacity"; from: 1; to: 0; duration: 250 }
        }
    }

    Component {
        id: dashboardComp
        DashboardView {
            objectName: "dashboard"
            // VINCULAR MODELO GLOBAL
            externalModel: navRoot.projectsModel
            onOpenGallery: stack.push(galleryComp)
            onOpenProject: (path) => navRoot.openDrawing(path)
            onOpenSketchbook: (path, title) => navRoot.openSketchbook(path, title)
            onCreateNewProject: navRoot.createNewProject()
        }
    }
    
    Component {
        id: galleryComp
        GalleryView {
            objectName: "gallery"
            onBackRequested: if (stack.depth > 1) stack.pop()
            onOpenSketchbook: (path, title) => navRoot.openSketchbook(path, title)
            onOpenDrawing: (path) => navRoot.openDrawing(path)
            onCreateNewProject: navRoot.createNewProject()
            onCreateNewGroup: navRoot.createNewGroup()
        }
    }

    Component {
        id: groupComp
        ProjectGroupView {
            objectName: "groupContent"
            onBackRequested: stack.pop()
            onPageSelected: (path) => navRoot.openDrawing(path)
        }
    }

    function pushSketchbook(path, title) {
        stack.push(groupComp, { "currentSketchbookPath": path, "sketchbookTitle": title })
    }
}
