import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Effects
import "../Translations.js" as Trans

Item {
    id: dashboardRoot
    anchors.fill: parent

    // RECARGAR DATOS
    onVisibleChanged: if (visible) refresh()

    property var externalModel: null
    signal openGallery()
    signal openProject(string path)
    signal openSketchbook(string path, string title)
    signal createNewProject()

    readonly property string lang: (typeof preferencesManager !== "undefined") ? preferencesManager.language : "en"
    function qs(key) { return Trans.get(key, lang); }

    readonly property color colorAccent: "#3c82f6"
    readonly property color colorSurface: "#1a1a1c"
    readonly property color colorBorder: "#2c2c2e"

    // 1. FONDO DEEP SPACE (Premium Gradient)
    Rectangle {
        anchors.fill: parent
        z: -2
        gradient: Gradient {
            GradientStop { position: 0.0; color: "#060608" }
            GradientStop { position: 0.5; color: "#0a0a0d" }
            GradientStop { position: 1.0; color: "#0d0d10" }
        }
    }

    // Reflejo de luz superior izquierdo para dar volumen
    Rectangle {
        width: parent.width * 0.6; height: width; radius: width/2
        x: -width/3; y: -height/3
        color: colorAccent; opacity: 0.03
        z: -1
        layer.enabled: true
        layer.effect: MultiEffect { blurEnabled: true; blur: 1.0 }
    }

    // 2. CONTENIDO SCROLLABLE
    Flickable {
        id: flick
        anchors.fill: parent
        contentHeight: mainCol.height + 150
        topMargin: 0; bottomMargin: 50
        clip: true
        boundsBehavior: Flickable.StopAtBounds

        Column {
            id: mainCol
            width: Math.min(parent.width - 100, 1400)
            anchors.horizontalCenter: parent.horizontalCenter
            topPadding: 80; spacing: 60

            // --- SECCIÓN 1: BIENVENIDA Y ACCIÓN RÁPIDA ---
            RowLayout {
                width: parent.width
                spacing: 40
                Column {
                    Layout.fillWidth: true; spacing: 8
                    Text { 
                        text: dashboardRoot.qs("welcome"); color: "white"
                        font.pixelSize: 52; font.weight: Font.Black; font.letterSpacing: -2.0
                    }
                    Text { 
                        text: dashboardRoot.qs("welcome_desc"); color: "#8e8e93"
                        font.pixelSize: 18; font.weight: Font.Light
                    }
                }
                
                // Botón "Nuevo Proyecto" con efecto Glow
                Rectangle {
                    id: btnNew
                    width: 240; height: 64
                    Layout.preferredWidth: 240; Layout.preferredHeight: 64; radius: 32
                    
                    gradient: Gradient {
                        orientation: Gradient.Horizontal
                        GradientStop { position: 0.0; color: "#3c82f6" }
                        GradientStop { position: 1.0; color: "#2563eb" }
                    }
                    
                    // Subtle inner highlight
                    Rectangle {
                        anchors.fill: parent; anchors.margins: 1; radius: 32; color: "transparent"
                        border.color: "white"; border.width: 1; opacity: 0.15
                    }

                    Row {
                        anchors.centerIn: parent; spacing: 14
                        // Animated Icon
                        Item {
                            width: 24; height: 24
                            Rectangle { width: 14; height: 2; color: "white"; anchors.centerIn: parent; radius: 1 }
                            Rectangle { width: 2; height: 14; color: "white"; anchors.centerIn: parent; radius: 1 }
                            rotation: maNew.containsMouse ? 90 : 0
                            Behavior on rotation { NumberAnimation { duration: 400; easing.type: Easing.OutBack } }
                        }
                        Text { 
                            text: dashboardRoot.qs("new_drawing")
                            color: "white"; font.bold: true; font.pixelSize: 18; font.letterSpacing: -0.2
                        }
                    }

                    // Efecto de brillo al pasar el mouse (Sin MultiEffect para evitar que desaparezca)
                    Rectangle {
                        anchors.fill: parent; radius: 32
                        color: "white"; opacity: maNew.containsMouse ? 0.15 : 0.0
                        Behavior on opacity { NumberAnimation { duration: 150 } }
                    }

                    scale: maNew.pressed ? 0.95 : (maNew.containsMouse ? 1.04 : 1.0)
                    Behavior on scale { NumberAnimation { duration: 250; easing.type: Easing.OutBack } }
                    
                    MouseArea {
                        id: maNew; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor
                        onClicked: dashboardRoot.createNewProject()
                    }
                }
            }

            // --- SECCIÓN 2: PROYECTOS RECIENTES ---
            Column {
                width: parent.width; spacing: 25
                RowLayout {
                    width: parent.width
                    Text { text: dashboardRoot.qs("recent_creations"); color: "white"; font.pixelSize: 26; font.weight: Font.Bold; font.letterSpacing: -0.5 }
                    Item { Layout.fillWidth: true }
                    Text { 
                        text: dashboardRoot.qs("go_gallery"); color: colorAccent; font.bold: true; font.pixelSize: 15
                        opacity: maGal.containsMouse ? 1.0 : 0.7
                        Behavior on opacity { NumberAnimation { duration: 200 } }
                        MouseArea { id: maGal; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: dashboardRoot.openGallery() }
                    }
                }

                Flow {
                    width: parent.width; spacing: 25
                    Repeater {
                        model: dashboardRoot.externalModel || recentModel
                        delegate: Item {
                            id: projItem; width: 220; height: 280
                            
                            // Micro-interacción: Escala al pasar el ratón
                            scale: maProj.containsMouse ? 1.05 : 1.0
                            Behavior on scale { NumberAnimation { duration: 300; easing.type: Easing.OutBack } }
                            
                            Rectangle {
                                anchors.fill: parent; radius: 20; color: colorSurface; border.color: maProj.containsMouse ? "#555" : colorBorder
                                clip: true
                                
                                Loader {
                                    id: cellLoader
                                    anchors.fill: parent
                                    property var thumbnails: model.thumbnails || []
                                    property string title: model.name || ""
                                    property string preview: model.preview || ""
                                    sourceComponent: (model.type === "folder" || model.type === "sketchbook") ? stackComp : drawingComp
                                }
                                
                                // Borde de cristal al pasar el mouse
                                Rectangle {
                                    anchors.fill: parent; radius: 20; color: "transparent"
                                    border.color: colorAccent; border.width: 2; opacity: maProj.containsMouse ? 0.6 : 0.0
                                    Behavior on opacity { NumberAnimation { duration: 200 } }
                                }
                            }

                            MouseArea {
                                id: maProj; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor
                                onClicked: {
                                    if (model.type === "folder" || model.type === "sketchbook") dashboardRoot.openSketchbook(model.path, model.name)
                                    else dashboardRoot.openProject(model.path)
                                }
                            }
                        }
                    }
                }
            }

            // --- SECCIÓN 3: EXPLORAR ASSETS (NUEVO) ---
            Column {
                width: parent.width; spacing: 25
                Text { text: dashboardRoot.qs("resources_assets"); color: "white"; font.pixelSize: 26; font.weight: Font.Bold; font.letterSpacing: -0.5 }
                RowLayout {
                    width: parent.width; spacing: 25
                    // Card 1: Pinceles
                    AssetCard { 
                        title: dashboardRoot.qs("new_brushes"); 
                        desc: dashboardRoot.qs("watercolor_pack"); 
                        accentColor: "#ff4757"; icon: "brush.svg" 
                    }
                    // Card 2: Texturas
                    AssetCard { 
                        title: dashboardRoot.qs("paper_textures"); 
                        desc: dashboardRoot.qs("fine_grain"); 
                        accentColor: "#2ed573"; icon: "image.svg" 
                    }
                    // Card 3: Paletas
                    AssetCard { 
                        title: dashboardRoot.qs("color_palettes"); 
                        desc: dashboardRoot.qs("sunset_insp"); 
                        accentColor: "#ffa502"; icon: "palette.svg" 
                    }
                }
            }

            // --- SECCIÓN 4: CENTRO DE APRENDIZAJE (NUEVO) ---
            Column {
                width: parent.width; spacing: 25
                Text { text: dashboardRoot.qs("improve_technique"); color: "white"; font.pixelSize: 26; font.weight: Font.Bold; font.letterSpacing: -0.5 }
                Flow {
                    width: parent.width; spacing: 25
                        VideoCard { title: dashboardRoot.qs("mastering_layers"); duration: "05:20"; thumbColor: "#2c3e50" }
                        VideoCard { title: dashboardRoot.qs("pro_workflow"); duration: "12:45"; thumbColor: "#4b6584" }
                        VideoCard { title: dashboardRoot.qs("advanced_shading"); duration: "08:15"; thumbColor: "#1e272e" }
                }
            }
        }
    }

    // --- COMPONENTES INTERNOS PARA EL DISEÑO ---
    
    // Tarjeta de Proyecto Simple
    Component {
        id: drawingComp
        Item {
            anchors.fill: parent
            Rectangle {
                anchors.fill: parent; anchors.bottomMargin: 60; color: "#000"; clip: true; radius: 18
                Image { 
                    id: imgPreview
                    anchors.fill: parent
                    source: model.preview || ""
                    fillMode: Image.PreserveAspectCrop; mipmap: true 
                    asynchronous: true
                }
                // Placeholder: Solo visible si no hay imagen o está cargando
                Rectangle {
                    anchors.fill: parent; color: "#252529"
                    visible: imgPreview.status !== Image.Ready
                    Text { anchors.centerIn: parent; text: "✎"; color: "#444"; font.pixelSize: 40 }
                }
            }
            Text { 
                anchors.bottom: parent.bottom; anchors.bottomMargin: 20; anchors.horizontalCenter: parent.horizontalCenter
                text: model.name || dashboardRoot.qs("untitled")
                color: "white"; font.bold: true; font.pixelSize: 15; width: parent.width - 20; elide: Text.ElideRight; horizontalAlignment: Text.AlignHCenter 
            }
        }
    }

    // Componente para Assets
    component AssetCard : Rectangle {
        id: assetRoot
        property string title: ""; property string desc: ""; property string icon: ""; property color accentColor: "white"
        Layout.fillWidth: true; height: 120; radius: 20; color: colorSurface; border.color: colorBorder
        clip: true
        RowLayout {
            anchors.fill: parent; anchors.margins: 20; spacing: 20
            Rectangle { width: 60; height: 60; radius: 15; color: assetRoot.accentColor; opacity: 0.15 
                Text { anchors.centerIn: parent; text: "★"; color: assetRoot.accentColor; font.pixelSize: 24 }
            }
            Column {
                Layout.fillWidth: true
                Text { text: assetRoot.title; color: "white"; font.bold: true; font.pixelSize: 16 }
                Text { text: assetRoot.desc; color: "#8e8e93"; font.pixelSize: 14 }
            }
        }
        MouseArea { anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onPressed: parent.scale = 0.98; onReleased: parent.scale = 1.0 }
        Behavior on scale { NumberAnimation { duration: 100 } }
    }

    // Componente para Vídeos
    component VideoCard : Rectangle {
        property string title: ""; property string duration: ""; property color thumbColor: "grey"
        width: 320; height: 180; radius: 20; color: colorSurface; border.color: colorBorder; clip: true
        Rectangle {
            anchors.fill: parent; anchors.bottomMargin: 50; color: parent.thumbColor; radius: 18
            Rectangle { width: 50; height: 50; radius: 25; color: "#aa000000"; anchors.centerIn: parent
                Text { text: "▶"; color: "white"; anchors.centerIn: parent; anchors.leftMargin: 3 }
            }
            Text { text: parent.parent.duration; color: "white"; anchors.bottom: parent.bottom; anchors.right: parent.right; anchors.margins: 10; font.pixelSize: 12; font.bold: true }
        }
        Text { anchors.bottom: parent.bottom; anchors.bottomMargin: 15; anchors.left: parent.left; anchors.leftMargin: 15; text: parent.title; color: "white"; font.bold: true }
        MouseArea { anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onPressed: parent.opacity = 0.8; onReleased: parent.opacity = 1.0 }
    }

    // MODELO DE RESPALDO
    ListModel { id: recentModel }
    function refresh() {
        recentModel.clear()
        if (typeof mainCanvas !== "undefined") {
            var items = mainCanvas.getRecentProjects()
            for(var i=0; i<items.length; i++) {
                var it = items[i]
                if (it.thumbnails) {
                    var th = []
                    for(var j=0; j<it.thumbnails.length; j++) th.push({ "modelData": it.thumbnails[j] })
                    it.thumbnails = th
                }
                recentModel.append(it)
            }
        }
    }
    Component.onCompleted: refresh()

    Component { 
        id: stackComp
        StackFolder {
            thumbnails: parent.thumbnails
            title: parent.title
        }
    }
}
