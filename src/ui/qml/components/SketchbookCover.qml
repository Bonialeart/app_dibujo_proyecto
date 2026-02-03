import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Effects

Item {
    id: root
    width: 250; height: 290
    
    // Propiedades que se pasarán desde el modelo
    property string title: "Sin Título"
    property color bookColor: "#e74c3c"
    property bool isFolder: false // Si es true, parece una carpeta, si no, un libro
    property string coverImage: ""
    
    signal openRequested()

    Rectangle {
        id: shadow
        anchors.fill: cover
        anchors.topMargin: 10
        anchors.leftMargin: 10
        color: "black"; radius: root.isFolder ? 8 : 4; opacity: 0.2
    }

    // EL BLOQUE DE HOJAS (Solo visible si es Sketchbook)
    Rectangle {
        visible: !root.isFolder
        width: cover.width - 12
        height: cover.height - 8
        anchors.centerIn: cover
        anchors.horizontalCenterOffset: 4
        color: "#fff"
        radius: 3
        
        // Efecto de páginas (rayas laterales)
        Column {
            anchors.right: parent.right; anchors.rightMargin: 2
            anchors.top: parent.top; anchors.bottom: parent.bottom
            anchors.topMargin: 5; anchors.bottomMargin: 5
            width: 8
            spacing: 2
            Repeater {
                model: 20
                Rectangle { width: parent.width; height: 1; color: "#e0e0e0" }
            }
        }
    }

    // LA TAPA (COVER)
    Rectangle {
        id: cover
        anchors.fill: parent
        anchors.bottomMargin: 40 // Leave space for label below in gallery if needed, but here it's full size
        color: root.bookColor
        radius: root.isFolder ? 8 : 4 // Carpeta más redonda, Libro más recto
        
        border.color: Qt.rgba(1,1,1,0.1)
        border.width: 1

        // Cover Image (optional background)
        Image {
            anchors.fill: parent
            anchors.margins: root.isFolder ? 2 : 1
            visible: root.coverImage !== ""
            source: root.coverImage
            fillMode: Image.PreserveAspectCrop
            opacity: 0.3
        }

        // Lomo del libro (Izquierda)
        Rectangle {
            visible: !root.isFolder
            width: 20; height: parent.height
            color: Qt.darker(root.bookColor, 1.2)
            anchors.left: parent.left
            
            // Texture for spine
            Rectangle {
                anchors.right: parent.right; width: 1; height: parent.height
                color: Qt.rgba(0,0,0,0.2)
            }
        }

        // Título del Proyecto
        Column {
            anchors.centerIn: parent
            anchors.horizontalCenterOffset: root.isFolder ? 0 : 10
            width: parent.width - 60
            spacing: 12

            Text {
                width: parent.width
                text: root.title
                color: "white"
                font.bold: true
                font.pixelSize: 18
                wrapMode: Text.Wrap
                horizontalAlignment: Text.AlignHCenter
                font.family: "Outfit"
            }
            
            Rectangle {
                width: 40; height: 2; color: "white"; opacity: 0.3; anchors.horizontalCenter: parent
            }
        }
        
        // Banda elástica (Detalle Premium)
        Rectangle {
            visible: !root.isFolder
            width: 10; height: parent.height
            anchors.right: parent.right
            anchors.rightMargin: 30
            color: "#1a1a1a"; opacity: 0.5
        }
        
        // Folder Tab
        Rectangle {
            visible: root.isFolder
            width: 80; height: 20; radius: 4
            color: root.bookColor
            anchors.bottom: parent.top
            anchors.left: parent.left
            anchors.bottomMargin: -5
        }

        // Icono de carpeta (Si es carpeta)
        Text {
            visible: root.isFolder
            text: "📂"
            font.pixelSize: 32
            anchors.bottom: parent.bottom; anchors.right: parent.right
            anchors.margins: 15
            opacity: 0.5
        }
    }

    // Label below
    Text {
        anchors.top: cover.bottom
        anchors.topMargin: 12
        anchors.horizontalCenter: parent.horizontalCenter
        text: root.isFolder ? "Folder" : "Sketchbook"
        color: "#666"
        font.pixelSize: 12
        font.weight: Font.Medium
        font.letterSpacing: 1
    }
}
