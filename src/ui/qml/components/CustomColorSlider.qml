import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

Item {
    id: root
    
    // Mode: "H" (0-360), "C" (0-100), "L" (0-100)
    // or "R","G","B" (0-255) if extended later
    // Mode: "H"(360), "S"(100), "B"(100), "R"(255), "G"(255), "B_Blue"(255), "C"(100), "L"(100)
    property string mode: "H"
    
    // We will use "mode" for logic, and an alias or explicit label for display
    property string labelText: mode
    
    property real value: 0
    property real max: (mode === "H" ? 360 : (mode === "R" || mode === "G" || mode === "B_Blue") ? 255 : 100)
    // We need "current" values of the other components to show a meaningful gradient.
    // e.g. if adjusting H, we need fixed C and L.
    property var otherComponents: [0, 0] // [c, l] or [h, l] etc.
    
    signal moved(real value)
    
    implicitHeight: 32
    implicitWidth: 200
    
    RowLayout {
        anchors.fill: parent
        spacing: 12
        
        // Label
        Text {
            text: root.labelText
            color: "#888"
            font.bold: true
            font.pixelSize: 12
            Layout.preferredWidth: 16
        }
        
        // Slider Area
        Item {
            Layout.fillWidth: true
            Layout.preferredHeight: 18
            
            // Track (Gradient)
            Rectangle {
                anchors.fill: parent
                radius: 9
                border.width: 1
                border.color: "#333"
                clip: true
                
                // Dynamic Gradient
                // Since QML Gradient is static definition mostly, we can use a ShaderEffect or a row of Rectangles for complex HCL.
                // But for standard H/S/L, we can approximate.
                // For HCL Hue: Rainbow spectrum (roughly)
                // For Chroma: Grayscale to Color
                // For Luma: Black to Color to White basically
                // We will use a simple approximation for "Premium Visuals"
                
                // Dynamic Gradient (Horizontal)
                Rectangle {
                    anchors.fill: parent
                    gradient: Gradient {
                        orientation: Gradient.Horizontal
                        GradientStop { position: 0.0; color: getStartColor() }
                        GradientStop { position: 0.5; color: getMidColor() }
                        GradientStop { position: 1.0; color: getEndColor() }
                    }
                    visible: root.mode !== "H"
                }
                
                // Fallback for HUE (Rainbow)
                visible: root.mode !== "H"
            }
            
            // Hue Rainbow (Static Image or Shader is better, but here multiple stops)
            Rectangle {
                anchors.fill: parent; radius: 9; visible: root.mode === "H"
                gradient: Gradient {
                    orientation: Gradient.Horizontal
                    GradientStop { position: 0.0; color: "#ff0000" }
                    GradientStop { position: 0.17; color: "#ffff00" }
                    GradientStop { position: 0.33; color: "#00ff00" }
                    GradientStop { position: 0.5; color: "#00ffff" }
                    GradientStop { position: 0.67; color: "#0000ff" }
                    GradientStop { position: 0.83; color: "#ff00ff" }
                    GradientStop { position: 1.0; color: "#ff0000" }
                }
            }


            // Handle
            Rectangle {
                x: (root.value / root.max) * (parent.width - width)
                y: -4
                width: 26; height: 26; radius: 13
                color: "#ffffff"
                border.color: "#000"
                border.width: 1 // High contrast ring
                
                // Inner color preview
                Rectangle {
                     anchors.centerIn: parent
                     width: 18; height: 18; radius: 9
                     color: getCurrentPreviewColor() 
                     border.color: Qt.rgba(0,0,0,0.1)
                     border.width: 1
                }
                
                // Shadow simulation handled manually or via layer effects elsewhere
                // shadow: true
            }
            
            MouseArea {
                anchors.fill: parent
                // Extend hit area
                anchors.margins: -10 
                
                onPositionChanged: {
                    if (pressed) {
                        var normalized = (mouseX - 10) / (parent.width) // adjust for margin? No, parent is Item
                        // Actually mouseX is relative to this area (which includes margins if accurate?)
                        // Let's use simple logic
                        var pp = mouseX 
                        if (pp < 0) pp = 0
                        if (pp > width) pp = width
                        
                        var val = (pp / width) * root.max
                        root.moved(val)
                    }
                }
                onPressed: positionChanged(mouse)
            }
        }
        
        // Value Text
        Text {
            text: Math.round(root.value)
            color: "#ccc"
            font.pixelSize: 11
            font.family: "Monospace"
            Layout.preferredWidth: 24
            horizontalAlignment: Text.AlignRight
        }
    }

    // Helper functions for gradient preview
    // Note: These assume 'mainCanvas' or global context availability for hclToHex, or we pass a converter.
    // For standalone component, better to emit request or use internal logic.
    // But since HCL logic is Python-side, we can't easily generate gradient stops.
    // Compromise: Use simple CSS color logic for C/L gradients (gray-to-color, black-to-white)
    
    function getStartColor() {
        if (mode === "C" || mode === "S") return "white" // Low Saturation/Chroma often implies white/gray (context dep)
        if (mode === "L" || mode === "B" || mode === "V") return "black" 
        
        // RGB
        if (mode === "R") return "black"
        if (mode === "G") return "black"
        if (mode === "B_Blue") return "black"
        
        return "black"
    }
    
    function getEndColor() {
        if (mode === "C" || mode === "S") return "red" 
        if (mode === "L" || mode === "B" || mode === "V") return "white"
        
        if (mode === "R") return "red"
        if (mode === "G") return "green"
        if (mode === "B_Blue") return "blue"
        
        return "white"
    }
    
    function getMidColor() {
         // rough approx
         if (mode === "C" || mode === "S") return "#884444" 
         if (mode === "L" || mode === "B" || mode === "V") return "gray"
         
         if (mode === "R") return "#800000"
         if (mode === "G") return "#008000"
         if (mode === "B_Blue") return "#000080"
         
         return "gray"
    }
    
    function getCurrentPreviewColor() {
        // Here we ideally want the TRUE combined color.
        // We can bind this to the parent's current color reference if available.
        return "transparent" 
    }
}
