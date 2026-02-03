import QtQuick
import QtQuick.Effects

Item {
    id: root
    implicitWidth: 160; implicitHeight: 220
    
    property var thumbnails: [] 
    property string title: "Grupo"
    property bool isExpanded: false 

    readonly property var _thumbList: {
        if (!thumbnails) return []
        var arr = []
        var c = 0
        try {
            c = (thumbnails.count !== undefined) ? thumbnails.count : thumbnails.length
        } catch(e) { }
        
        if (!c || c <= 0) return []
        
        for (var i = 0; i < Math.min(c, 3); i++) {
            var item = null
            try {
                item = (thumbnails.get) ? thumbnails.get(i) : thumbnails[i]
            } catch(e) { }
            
            if (item === undefined || item === null) continue
            
            if (typeof item === "string") {
                if (item) arr.push(item)
            } else if (typeof item === "object") {
                // If it's a ListModel item wrapping a string from Python
                var path = item.modelData || item.display || item.value || ""
                if (!path && item.toString) {
                    var s = item.toString()
                    if (s.indexOf("file://") !== -1) path = s
                }
                if (path) arr.push(path)
            }
        }
        return arr
    }

    // FONDO DE SEGURIDAD (Si está vacío)
    Rectangle {
        visible: root._thumbList.length === 0
        anchors.centerIn: parent
        width: 140; height: 180; radius: 14
        color: "#1c1c1e"; border.color: "#333"
        Text { 
            anchors.centerIn: parent; 
            text: (typeof dashboardRoot !== "undefined" && dashboardRoot.qs) ? dashboardRoot.qs("empty") : 
                  ((typeof galleryRoot !== "undefined" && galleryRoot.qs) ? galleryRoot.qs("empty") : "Vacío"); 
            color: "#444"; font.bold: true 
        }
    }

    // LA PILA (STAK)
    Repeater {
        model: Math.min(3, root._thumbList.length)
        
        delegate: Item {
            id: cardWrapper
            width: 140; height: 180
            anchors.centerIn: parent
            z: 100 - index 

            // EFECTO DE PILA VISIBLE
            rotation: {
                if (index === 0) return 3 // Ligera inclinación al frente
                var rot = (index === 1) ? -6 : 8
                return root.isExpanded ? rot * 3 : rot
            }
            
            x: root.isExpanded ? (index === 1 ? -40 : 40) : (index === 0 ? 0 : (index === 1 ? -5 : 5))
            y: root.isExpanded ? (index * 20) : (index * -4) // Las de atrás suben un poco

            Behavior on rotation { NumberAnimation { duration: 350; easing.type: Easing.OutBack } }
            Behavior on x { NumberAnimation { duration: 350; easing.type: Easing.OutBack } }
            Behavior on y { NumberAnimation { duration: 350; easing.type: Easing.OutBack } }

            Rectangle {
                anchors.fill: parent
                radius: 12; color: "#161618"; border.color: "#333"; clip: true
                
                Image {
                    anchors.fill: parent
                    source: root._thumbList[index] || ""
                    fillMode: Image.PreserveAspectCrop
                    mipmap: true
                }

                // Sombra interna para separar cartas
                Rectangle {
                    anchors.fill: parent; color: "black"; radius: 12
                    opacity: index === 0 ? 0.0 : 0.2 * index
                }
            }

            layer.enabled: true
            layer.effect: MultiEffect {
                shadowEnabled: true; shadowBlur: 0.8
                shadowColor: "black"; shadowOpacity: 0.5
                shadowVerticalOffset: 3 + (index * 2)
            }
        }
    }

    Text {
        anchors.top: parent.bottom; anchors.topMargin: 5
        width: parent.width; horizontalAlignment: Text.AlignHCenter
        text: root.title; color: "white"; font.bold: true; font.pixelSize: 14; elide: Text.ElideRight
    }
}
