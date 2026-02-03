#version 330 core
// brush.frag - High Fidelity Watercolor Physics Shader
// Implements Coffee Ring, Granulation, Turbulence, and Kubelka-Munk Mixing

in vec2 vUV;
in vec2 vCanvasCoords; 

uniform sampler2D uBrushTip;   
uniform sampler2D uPaperTex;   
uniform sampler2D uCanvasTex;  // FBO Source (Previous Canvas state)
uniform sampler2D uWetMap;     

uniform vec4 uColor;          
uniform float uPressure;      
uniform float uHardness;
uniform int uMode;             

out vec4 fragColor;

// --- NOISE UTILS ---
float hash(vec2 p) {
    p = fract(p * vec2(123.34, 456.21));
    p += dot(p, p + 45.32);
    return fract(p.x * p.y);
}

float noise(vec2 p) {
    vec2 i = floor(p);
    vec2 f = fract(p);
    float a = hash(i);
    float b = hash(i + vec2(1.0, 0.0));
    float c = hash(i + vec2(0.0, 1.0));
    float d = hash(i + vec2(1.0, 1.0));
    vec2 u = f * f * (3.0 - 2.0 * f);
    return mix(a, b, u.x) + (c - a) * u.y * (1.0 - u.x) + (d - b) * u.x * u.y;
}

// --- KUBELKA-MUNK UTILS ---
vec3 rgbToK(vec3 rgb) {
    return (vec3(1.0) - rgb) * (vec3(1.0) - rgb) / (2.0 * rgb + 0.001);
}

vec3 kToRGB(vec3 k) {
    return vec3(1.0) + k - sqrt(max(k * k + 2.0 * k, 0.0));
}

void main() {
    // 0. COORDINATE DISTORTION (Turbulence)
    // Romper la forma perfecta del pincel digital
    float turb = noise(vCanvasCoords * 100.0 + uPressure * 0.5);
    vec2 distortedUV = vUV + (turb - 0.5) * 0.04 * (1.1 - uPressure);
    
    // 1. SAMPLES
    vec4 canvasState = texture(uCanvasTex, vCanvasCoords);
    float brushValue = texture(uBrushTip, distortedUV).a;
    float paperHeight = texture(uPaperTex, vCanvasCoords * 2.0).r; // Escalar grano
    
    // 2. FLOW DYNAMICS (Low Frequency Noise)
    // Simula la carga desigual de agua/pigmento en las cerdas
    float flowNoise = noise(vCanvasCoords * 8.0 + uPressure * 0.2);
    float flow = 0.5 + 0.5 * flowNoise;
    
    // 3. COFFEE RING EFFECT (Edge Darkening)
    // El pigmento se acumula en las orillas de la mancha
    float edge = 1.0 - brushValue;
    float edgeFactor = pow(edge, 5.0) * uHardness * 2.5; 
    float organicIntensity = mix(brushValue, brushValue * (1.0 + edgeFactor), 0.8);

    // 4. PAPER GRANULATION
    // El pigmento solo llena los valles si hay presión
    float threshold = 1.0 - uPressure;
    float granulation = smoothstep(threshold - 0.3, threshold + 0.3, paperHeight);
    
    // Combined Concentration
    float concentration = organicIntensity * uColor.a * uPressure * flow * granulation;
    concentration = clamp(concentration, 0.0, 1.0);

    // 5. KUBELKA-MUNK SUSTRACTIVE MIXING
    // No usamos mezcla alpha normal (suma), usamos mezcla sustractiva (multiplicación de absorción)
    vec3 K_canvas = rgbToK(canvasState.rgb);
    vec3 K_pigment = rgbToK(uColor.rgb);
    
    // La mezcla física: el lienzo absorbe la luz y el nuevo pigmento agrega su absorción
    vec3 K_final = mix(K_canvas, K_canvas + K_pigment, concentration);
    
    // Volvover a espacio RGB
    vec3 finalRGB = kToRGB(K_final);
    
    // 6. PREMIUM DITHERING
    // Elimina el banding en degradados suaves
    float dither = (hash(gl_FragCoord.xy) - 0.5) / 255.0;
    finalRGB += dither;

    fragColor = vec4(clamp(finalRGB, 0.0, 1.0), 1.0);
}
