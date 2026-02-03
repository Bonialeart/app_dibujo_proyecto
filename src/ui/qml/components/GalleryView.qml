import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Effects
import "../Translations.js" as Trans

Item {
    id: galleryRoot
    anchors.fill: parent

    // RECARGAR AL VOLVER A SER VISIBLE
    onVisibleChanged: if (visible) refreshGallery()

    // SEÑALES
    signal openSketchbook(string path, string title)
    signal openDrawing(string path)
    signal createNewProject()
    signal createNewGroup()
    signal backRequested()

    property int draggedIndex: -1
    property int targetIndex: -1
    property point grabOffset: "0,0"
    readonly property color colorAccent: "#3c82f6"

    readonly property string lang: (typeof preferencesManager !== "undefined") ? preferencesManager.language : "en"
    function qs(key) { return Trans.get(key, lang); }

    // 1. FONDO PREMIUM RESTAURADO
    Rectangle {
        anchors.fill: parent
        gradient: Gradient {
            GradientStop { position: 0.0; color: "#08080a" }
            GradientStop { position: 1.0; color: "#0f0f12" }
        }
    }

    // 2. EL FANTASMA (Levitación Pro)
    Item {
        id: ghost
        width: 170; height: 230
        z: 99999
        visible: galleryRoot.draggedIndex !== -1
        property var ghostData: null

        scale: visible ? 1.18 : 0.5
        rotation: visible ? 4 : 0
        Behavior on scale { NumberAnimation { duration: 250; easing.type: Easing.OutBack } }
        Behavior on rotation { NumberAnimation { duration: 250 } }
        Behavior on x { NumberAnimation { duration: dragController.pressed ? 45 : 0 } }
        Behavior on y { NumberAnimation { duration: dragController.pressed ? 45 : 0 } }

        layer.enabled: true
        layer.effect: MultiEffect {
            shadowEnabled: true; shadowBlur: 1.0; shadowVerticalOffset: 25; shadowOpacity: 0.6
        }

        Rectangle {
            anchors.fill: parent; radius: 20; color: "#1c1c1e"; border.color: "#333"
            Loader {
                anchors.fill: parent; anchors.margins: 4
                sourceComponent: (ghost.ghostData && (ghost.ghostData.type === "folder" || ghost.ghostData.type === "sketchbook")) ? ghostStackComp : ghostImgComp
            }
        }
    }

    // 3. CONTENIDO (ColumnLayout para estructura limpia)
    ColumnLayout {
        anchors.fill: parent; anchors.margins: 40; spacing: 40

        // HEADER PREMIUM
        RowLayout {
            Layout.fillWidth: true; spacing: 25
            Rectangle {
                width: 52; height: 52; radius: 16; color: "#161618"; border.color: "#333"
                Text { text: "←"; color: "white"; font.pixelSize: 24; anchors.centerIn: parent }
                MouseArea { 
                    anchors.fill: parent; cursorShape: Qt.PointingHandCursor
                    onClicked: galleryRoot.backRequested()
                    onPressed: parent.scale = 0.9; onReleased: parent.scale = 1.0
                }
                Behavior on scale { NumberAnimation { duration: 100 } }
            }
            Column {
                Text { text: galleryRoot.qs("gallery_title"); color: "white"; font.pixelSize: 34; font.bold: true; font.letterSpacing: -0.5 }
                Text { text: galleryRoot.qs("gallery_desc"); color: "#666"; font.pixelSize: 15 }
            }
            Item { Layout.fillWidth: true }
            Row {
                spacing: 15
                // Botón Nuevo Grupo
                Rectangle {
                    width: 160; height: 52; radius: 26; color: "#161618"; border.color: "#333"
                    Text { text: galleryRoot.qs("new_group"); color: "white"; font.bold: true; anchors.centerIn: parent }
                    MouseArea { 
                        anchors.fill: parent; cursorShape: Qt.PointingHandCursor
                        onClicked: galleryRoot.createNewGroup()
                        onPressed: parent.scale = 0.95; onReleased: parent.scale = 1.0
                    }
                    Behavior on scale { NumberAnimation { duration: 150; easing.type: Easing.OutBack } }
                }
                // Botón Nuevo Dibujo (Premium Style)
                Rectangle {
                    id: btnNewGal
                    width: 180; height: 52; radius: 26
                    gradient: Gradient {
                        orientation: Gradient.Horizontal
                        GradientStop { position: 0.0; color: "#3c82f6" }
                        GradientStop { position: 1.0; color: "#2563eb" }
                    }
                    Text { text: "+ " + galleryRoot.qs("new_drawing"); color: "white"; font.bold: true; anchors.centerIn: parent; anchors.horizontalCenterOffset: 12 }
                    
                    scale: maNewGal.pressed ? 0.95 : (maNewGal.containsMouse ? 1.05 : 1.0)
                    Behavior on scale { NumberAnimation { duration: 150; easing.type: Easing.OutBack } }
                    
                    // Efecto de brillo (Sin MultiEffect para asegurar visibilidad)
                    Rectangle {
                        anchors.fill: parent; radius: 26
                        color: "white"; opacity: maNewGal.containsMouse ? 0.15 : 0.0
                        Behavior on opacity { NumberAnimation { duration: 150 } }
                    }

                    MouseArea { 
                        id: maNewGal; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor
                        onClicked: galleryRoot.createNewProject() 
                    }
                }
            }
        }

        // GRID DE PROYECTOS
        GridView {
            id: grid
            Layout.fillWidth: true; Layout.fillHeight: true
            cellWidth: 220; cellHeight: 300
            model: projectModel; clip: true; interactive: galleryRoot.draggedIndex === -1

            delegate: Item {
                id: delegateRoot; width: grid.cellWidth; height: grid.cellHeight
                opacity: galleryRoot.draggedIndex === index ? 0.0 : 1.0
                scale: (galleryRoot.targetIndex === index && galleryRoot.draggedIndex !== index) ? 1.1 : 1.0
                Behavior on scale { NumberAnimation { duration: 250; easing.type: Easing.OutBack } }

                Loader {
                    id: cellLoaderGal
                    anchors.centerIn: parent
                    property var thumbnails: model.thumbnails || []
                    property string title: model.name || ""
                    property bool isExpanded: (galleryRoot.targetIndex === index)
                    property string preview: model.preview || ""
                    sourceComponent: (model.type === "folder" || model.type === "sketchbook") ? stackComp : drawingComp
                }

                MouseArea {
                    anchors.fill: parent; cursorShape: Qt.PointingHandCursor; pressAndHoldInterval: 250
                    onClicked: {
                        if (model.type === "folder" || model.type === "sketchbook") galleryRoot.openSketchbook(model.path, model.name)
                        else galleryRoot.openDrawing(model.path)
                    }
                    onPressAndHold: (mouse) => {
                        galleryRoot.draggedIndex = index
                        ghost.ghostData = projectModel.get(index)
                        var pos = delegateRoot.mapToItem(galleryRoot, 0, 0)
                        ghost.x = pos.x + (delegateRoot.width - ghost.width)/2
                        ghost.y = pos.y + (delegateRoot.height - ghost.height)/2
                        var m = mapToItem(galleryRoot, mouse.x, mouse.y)
                        galleryRoot.grabOffset = Qt.point(m.x - ghost.x, m.y - ghost.y)
                    }
                }
            }
        }
    }

    // 4. CONTROLADOR DE ARRASTRE GLOBAL
    MouseArea {
        id: dragController; anchors.fill: parent; enabled: galleryRoot.draggedIndex !== -1
        onPositionChanged: (mouse) => {
            ghost.x = mouse.x - galleryRoot.grabOffset.x
            ghost.y = mouse.y - galleryRoot.grabOffset.y
            var p = mapToItem(grid, mouse.x, mouse.y)
            var idx = grid.indexAt(p.x, p.y + grid.contentY)
            galleryRoot.targetIndex = (idx !== -1 && idx !== galleryRoot.draggedIndex) ? idx : -1
        }
        onReleased: {
            if (galleryRoot.targetIndex !== -1) {
                var a = projectModel.get(galleryRoot.draggedIndex)
                var b = projectModel.get(galleryRoot.targetIndex)
                if (mainCanvas.create_folder_from_merge(a.path, b.path)) refreshGallery()
            }
            galleryRoot.draggedIndex = -1; galleryRoot.targetIndex = -1
        }
    }

    // MODELO Y RECARGA
    ListModel { id: projectModel }
    function refreshGallery() {
        projectModel.clear()
        if (typeof mainCanvas !== "undefined") {
            var list = mainCanvas.get_project_list()
            for(var i=0; i<list.length; i++) {
                var it = list[i]
                if (it.thumbnails) {
                    var th = []
                    for(var j=0; j<it.thumbnails.length; j++) th.push({ "modelData": it.thumbnails[j] })
                    it.thumbnails = th
                }
                projectModel.append(it)
            }
        }
    }
    Component.onCompleted: refreshGallery()

    // COMPONENTES DELEGADOS
    Component { 
        id: stackComp
        StackFolder {
            thumbnails: parent.thumbnails
            title: parent.title
            isExpanded: parent.isExpanded
        }
    }
    Component { 
        id: drawingComp
        Item { 
            width: 175; height: 235
            Rectangle { 
                anchors.fill: parent; anchors.bottomMargin: 40; radius: 18; color: "#161618"; 
                border.color: (galleryRoot.targetIndex === index) ? colorAccent : "#333"; 
                border.width: (galleryRoot.targetIndex === index) ? 2 : 1; clip: true
                
                Image { 
                    id: imgPreviewGal
                    anchors.fill: parent; source: model.preview || ""; fillMode: Image.PreserveAspectCrop; mipmap: true 
                    asynchronous: true
                }
                // Placeholder
                Rectangle {
                    anchors.fill: parent; color: "#252529"
                    visible: imgPreviewGal.status !== Image.Ready
                    Text { anchors.centerIn: parent; text: "✎"; color: "#444"; font.pixelSize: 40 }
                }
                Rectangle { 
                    anchors.fill: parent
                    gradient: Gradient { 
                        GradientStop { position: 0; color: "#10ffffff" }
                        GradientStop { position: 1; color: "transparent" } 
                    }
                    opacity: 0.1 
                }
            }
            Text { 
                anchors.bottom: parent.bottom; anchors.horizontalCenter: parent.horizontalCenter; 
                text: model.name || "Sin título"; color: "white"; font.bold: true; font.pixelSize: 15; 
                width: parent.width; elide: Text.ElideRight; horizontalAlignment: Text.AlignHCenter 
            }
        } 
    }
    Component { id: ghostStackComp; StackFolder { thumbnails: ghost.ghostData ? ghost.ghostData.thumbnails : []; title: ghost.ghostData ? (ghost.ghostData.title || ghost.ghostData.name) : "" } }
    Component { 
        id: ghostImgComp
        Item { 
            width: 170; height: 230
            Rectangle { 
                anchors.fill: parent; radius: 18; color: "#1c1c1e"; border.color: "#444"; clip: true
                Image { anchors.fill: parent; source: ghost.ghostData ? ghost.ghostData.preview : ""; fillMode: Image.PreserveAspectCrop; mipmap: true } 
            } 
        } 
    }
}
