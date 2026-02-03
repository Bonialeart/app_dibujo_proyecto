import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Dialog {
    id: root
    title: "Export Timelapse"
    modal: true
    width: 450
    height: 500
    x: (parent.width - width) / 2
    y: (parent.height - height) / 2
    
    // Properties to export
    property int durationMode: 0 // 0=Auto, 1=30s, 2=60s
    property int aspectMode: 0 // 0=Original, 1=1:1, 2=9:16
    property int qualityMode: 1 // 0=Standard, 1=Studio
    
    signal exportConfirmed(var settings)
    
    background: Rectangle { 
        color: "#1c1c1e"
        radius: 12
        border.color: "#333"
        border.width: 1
    }
    
    header: Item {
        height: 60
        width: parent.width
        Text { 
            text: "Timelapse Export"
            color: "white"
            font.pixelSize: 18
            font.weight: Font.Bold
            anchors.centerIn: parent 
        }
        Rectangle { height: 1; width: parent.width; color: "#333"; anchors.bottom: parent.bottom }
    }
    
    contentItem: ColumnLayout {
        spacing: 24
        
        // Duration
        ColumnLayout {
            Layout.fillWidth: true
            spacing: 12
            Text { text: "TARGET DURATION"; color: "#666"; font.pixelSize: 11; font.weight: Font.Bold }
            
            RadioButton { 
                checked: durationMode === 0
                onToggled: if(checked) durationMode = 0
                contentItem: Text { text: "Full Length (Variable Speed)"; color: "white"; leftPadding: 34; verticalAlignment: Text.AlignVCenter; font.pixelSize: 14 }
            }
            RadioButton { 
                checked: durationMode === 1
                onToggled: if(checked) durationMode = 1
                contentItem: Text { text: "30 Seconds"; color: "white"; leftPadding: 34; verticalAlignment: Text.AlignVCenter; font.pixelSize: 14 }
            }
            RadioButton { 
                checked: durationMode === 2
                onToggled: if(checked) durationMode = 2
                contentItem: Text { text: "60 Seconds"; color: "white"; leftPadding: 34; verticalAlignment: Text.AlignVCenter; font.pixelSize: 14 }
            }
        }
        
        Rectangle { height: 1; Layout.fillWidth: true; color: "#2c2c2e" }
        
        // Aspect Ratio
        ColumnLayout {
            Layout.fillWidth: true
            spacing: 12
            Text { text: "CROP & RATIO"; color: "#666"; font.pixelSize: 11; font.weight: Font.Bold }
            
            RowLayout {
                spacing: 20
                RadioButton { 
                    checked: aspectMode === 0
                    onToggled: if(checked) aspectMode = 0
                    contentItem: Text { text: "Original"; color: "white"; leftPadding: 34; verticalAlignment: Text.AlignVCenter; font.pixelSize: 14 }
                }
                RadioButton { 
                    checked: aspectMode === 1
                    onToggled: if(checked) aspectMode = 1
                    contentItem: Text { text: "Square (1:1)"; color: "white"; leftPadding: 34; verticalAlignment: Text.AlignVCenter; font.pixelSize: 14 }
                }
                RadioButton { 
                    checked: aspectMode === 2
                    onToggled: if(checked) aspectMode = 2
                    contentItem: Text { text: "9:16 (Shorts)"; color: "white"; leftPadding: 34; verticalAlignment: Text.AlignVCenter; font.pixelSize: 14 }
                }
            }
        }
        
        Rectangle { height: 1; Layout.fillWidth: true; color: "#2c2c2e" }
        
        // Quality
        ColumnLayout {
            Layout.fillWidth: true
            spacing: 12
            Text { text: "QUALITY MODE"; color: "#666"; font.pixelSize: 11; font.weight: Font.Bold }
            
            RowLayout {
                spacing: 20
                RadioButton { 
                    checked: qualityMode === 0
                    onToggled: if(checked) qualityMode = 0
                    contentItem: Text { text: "Web (1080p)"; color: "white"; leftPadding: 34; verticalAlignment: Text.AlignVCenter; font.pixelSize: 14 }
                }
                RadioButton { 
                    checked: qualityMode === 1
                    onToggled: if(checked) qualityMode = 1
                    contentItem: Text { text: "Studio (Source)"; color: "white"; leftPadding: 34; verticalAlignment: Text.AlignVCenter; font.pixelSize: 14 }
                }
            }
        }
    }
    
    footer: Item {
        height: 80
        width: parent.width
        
        RowLayout {
            anchors.centerIn: parent
            spacing: 16
            
            Button {
                text: "Cancel"
                implicitWidth: 100
                implicitHeight: 40
                background: Rectangle { color: "#2c2c2e"; radius: 8 }
                contentItem: Text { text: parent.text; color: "white"; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter; font.weight: Font.Medium }
                onClicked: root.close()
            }
            
            Button {
                text: "Continue to Save..."
                implicitWidth: 160
                implicitHeight: 40
                background: Rectangle { color: "#0a84ff"; radius: 8 }
                contentItem: Text { text: parent.text; color: "white"; font.weight: Font.Bold; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                onClicked: {
                    var s = {
                        durationSec: durationMode === 1 ? 30 : (durationMode === 2 ? 60 : 0),
                        aspectMode: aspectMode,
                        qualityMode: qualityMode
                    }
                    root.exportConfirmed(s)
                    root.close()
                }
            }
        }
    }
}
