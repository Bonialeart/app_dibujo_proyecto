from PyQt6.QtGui import QPainter

class BrushPresets:
    """Central repository for Brush Presets and Blend Modes."""
    
    BLEND_MODES = {
        "Normal": QPainter.CompositionMode.CompositionMode_SourceOver,
        "Multiply": QPainter.CompositionMode.CompositionMode_Multiply,
        "Screen": QPainter.CompositionMode.CompositionMode_Screen,
        "Overlay": QPainter.CompositionMode.CompositionMode_Overlay,
        "Darken": QPainter.CompositionMode.CompositionMode_Darken,
        "Lighten": QPainter.CompositionMode.CompositionMode_Lighten,
        "Color Dodge": QPainter.CompositionMode.CompositionMode_ColorDodge,
        "Color Burn": QPainter.CompositionMode.CompositionMode_ColorBurn,
        "Add": QPainter.CompositionMode.CompositionMode_Plus,
        "Soft Light": QPainter.CompositionMode.CompositionMode_SoftLight,
        "Hard Light": QPainter.CompositionMode.CompositionMode_HardLight,
        "Difference": QPainter.CompositionMode.CompositionMode_Difference,
        "Exclusion": QPainter.CompositionMode.CompositionMode_Exclusion
    }
    
    BLEND_MODES_INV = {v: k for k, v in BLEND_MODES.items()}

    PRESETS = {
        "Pencil HB": {"size": 4, "opacity": 0.5, "hardness": 0.1, "smoothing": 0.2, "blend": "Multiply", "grain": 0.6, "granulation": 0.0, "diffusion": 0.0, "spacing": 0.05},
        "Pencil 6B": {"size": 15, "opacity": 0.85, "hardness": 0.4, "smoothing": 0.1, "blend": "Multiply", "grain": 0.9, "granulation": 0.0, "diffusion": 0.0, "spacing": 0.05},
        "Ink Pen": {"size": 12, "opacity": 1.0, "hardness": 1.0, "smoothing": 0.7, "blend": "Normal", "grain": 0.0, "granulation": 0.0, "diffusion": 0.0},
        "Marker": {"size": 25, "opacity": 0.4, "hardness": 0.9, "smoothing": 0.1, "blend": "Multiply", "grain": 0.0, "granulation": 0.0, "diffusion": 0.0},
        
        # --- PRO INKING PRESETS ---
        "G-Pen": {"size": 15, "opacity": 1.0, "hardness": 0.98, "smoothing": 0.7, "blend": "Normal", "grain": 0.0, "granulation": 0.0, "diffusion": 0.0},
        "Maru Pen": {"size": 8, "opacity": 1.0, "hardness": 1.0, "smoothing": 0.5, "blend": "Normal", "grain": 0.0, "granulation": 0.0, "diffusion": 0.0},
        
        # --- WATERCOLOR PRESETS ---
        "Watercolor":      {"size": 45, "opacity": 0.35, "hardness": 0.25, "smoothing": 0.4, "blend": "Multiply", "grain": 0.05, "granulation": 0.1, "diffusion": 0.4},
        "Watercolor Wet":  {"size": 55, "opacity": 0.3, "hardness": 0.1, "smoothing": 0.5, "blend": "Multiply", "grain": 0.0, "granulation": 0.0, "diffusion": 0.9},
        "Mineral Wash":    {"size": 40, "opacity": 0.4, "hardness": 0.3, "smoothing": 0.4, "blend": "Multiply", "grain": 0.15, "granulation": 0.8, "diffusion": 0.2}, 
        "Water Blend":     {"size": 60, "opacity": 1.0, "hardness": 0.1, "smoothing": 0.4, "blend": "Normal", "grain": 0.0, "granulation": 0.0, "diffusion": 0.8},

        # --- PAINTING PRESETS (Updated for Realism) ---
        "Oil Paint":       {"size": 35, "opacity": 1.0, "hardness": 0.8, "smoothing": 0.3, "blend": "Normal", "grain": 0.5, "granulation": 0.0, "diffusion": 0.0, "spacing": 0.02, "impasto": 0.8},
        "Acrylic":         {"size": 35, "opacity": 0.95, "hardness": 0.9, "smoothing": 0.2, "blend": "Normal", "grain": 0.5, "granulation": 0.0, "diffusion": 0.0, "spacing": 0.02, "impasto": 0.6},
        
        # --- AIRBRUSH PRESETS ---
        "Soft":            {"size": 60, "opacity": 0.15, "hardness": 0.0, "smoothing": 0.1, "blend": "Normal", "grain": 0.0, "granulation": 0.0, "diffusion": 0.0},
        "Hard":            {"size": 40, "opacity": 0.2, "hardness": 0.85, "smoothing": 0.1, "blend": "Normal", "grain": 0.0, "granulation": 0.0, "diffusion": 0.0},

        # --- PENCIL PRESETS ---
        "Mechanical":      {"size": 2, "opacity": 0.8, "hardness": 0.8, "smoothing": 0.4, "blend": "Multiply", "grain": 0.2, "granulation": 0.0, "diffusion": 0.0},

        "Eraser Soft": {"size": 40, "opacity": 1.0, "hardness": 0.2, "smoothing": 0.1, "blend": "Normal", "grain": 0.0, "granulation": 0.0, "diffusion": 0.0},
        "Eraser Hard": {"size": 20, "opacity": 1.0, "hardness": 0.95, "smoothing": 0.1, "blend": "Normal", "grain": 0.0, "granulation": 0.0, "diffusion": 0.0}
    }
