# 🎨 ArtFlow Studio

## Premium Illustration & Learning Platform for Artists

ArtFlow Studio is a professional-grade digital art application designed for illustrators, concept artists, and 2D animators. It combines powerful drawing tools with curated learning resources, brush libraries, and community features.

---

## 🌟 Key Features

### 🖌️ Drawing Engine (C++)
- High-performance canvas rendering with OpenGL
- Pressure-sensitive brush system
- Multi-layer support with blend modes
- Real-time brush preview
- ABR brush file import
- Unlimited undo/redo

### 📚 Learning Hub
- Curated YouTube playlists for:
  - Digital Illustration
  - Concept Art
  - 2D Animation
  - Character Design
- Progress tracking
- Bookmarking system

### 🎨 Brush Library
- Free & Premium brush packs
- ABR file support (Photoshop compatible)
- Brush preview and testing
- One-click download and install
- Custom brush creation

### 🔗 Resources Hub
- Curated useful websites for artists
- Artist of the Week spotlight
- Color palette collections
- Reference image library
- Storyboard templates

---

## 📁 Project Structure

```
ArtFlow-Studio/
├── src/
│   ├── core/                 # C++ Core Engine
│   │   ├── canvas/           # Canvas rendering
│   │   ├── brushes/          # Brush engine
│   │   ├── layers/           # Layer management
│   │   └── tools/            # Drawing tools
│   │
│   ├── ui/                   # Python UI Layer
│   │   ├── main_window.py    # Main application window
│   │   ├── panels/           # UI panels
│   │   ├── dialogs/          # Dialog windows
│   │   └── widgets/          # Custom widgets
│   │
│   ├── resources/            # Resource management
│   │   ├── brush_manager.py  # Brush pack handling
│   │   ├── video_manager.py  # YouTube integration
│   │   └── data_manager.py   # Data persistence
│   │
│   └── utils/                # Utilities
│       ├── config.py         # Configuration
│       └── constants.py      # App constants
│
├── assets/                   # Static assets
│   ├── icons/                # UI icons
│   ├── brushes/              # Default brushes
│   └── themes/               # UI themes
│
├── data/                     # App data
│   ├── playlists.json        # YouTube playlists
│   ├── brushes.json          # Brush catalog
│   └── resources.json        # Useful links
│
└── tests/                    # Unit tests
```

---

## 🛠️ Technology Stack

| Component | Technology |
|-----------|------------|
| Drawing Engine | C++ with OpenGL |
| UI Framework | Python + PyQt6 |
| Brush Rendering | C++ (via pybind11) |
| Data Storage | SQLite + JSON |
| Video Integration | YouTube Data API |
| Styling | QSS (Qt Style Sheets) |

---

## 🚀 Getting Started

### Prerequisites
- Python 3.10+
- C++ Compiler (MSVC/GCC)
- CMake 3.20+
- Qt6

### Installation

```bash
# Clone the repository
git clone https://github.com/yourname/artflow-studio.git
cd artflow-studio

# Install Python dependencies
pip install -r requirements.txt

# Build C++ core
mkdir build && cd build
cmake ..
cmake --build . --config Release

# Run the application
python src/main.py
```

---

## 📜 License

MIT License - See LICENSE file for details.

---

## 🤝 Contributing

Contributions are welcome! Please read our contributing guidelines before submitting PRs.

---

Made with ❤️ for artists everywhere
