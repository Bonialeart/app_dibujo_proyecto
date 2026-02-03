"""
ArtFlow Studio - Learn Panel (YouTube Integration)
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QGridLayout, QLineEdit, QTabWidget,
    QStackedWidget, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal, QUrl, QSize
from PyQt6.QtGui import QPixmap, QFont, QDesktopServices


class VideoCard(QFrame):
    """Video thumbnail card widget."""
    
    clicked = pyqtSignal(dict)
    
    def __init__(self, video_data: dict, parent=None):
        super().__init__(parent)
        self.video_data = video_data
        self.setFixedSize(320, 220)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        # Thumbnail container
        thumb_container = QFrame()
        thumb_container.setFixedHeight(160)
        thumb_container.setStyleSheet("background: #252540; border-radius: 12px 12px 0 0;")
        
        thumb_layout = QVBoxLayout(thumb_container)
        thumb_layout.setContentsMargins(0, 0, 0, 0)
        
        # Play button overlay
        play_overlay = QLabel("▶")
        play_overlay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        play_overlay.setStyleSheet("""
            font-size: 48px;
            color: rgba(255, 255, 255, 0.8);
            background: rgba(0, 0, 0, 0.3);
            border-radius: 12px 12px 0 0;
        """)
        thumb_layout.addWidget(play_overlay)
        
        # Duration badge
        duration = QLabel(self.video_data.get("duration", "10:30"))
        duration.setStyleSheet("""
            background: rgba(0, 0, 0, 0.8);
            color: white;
            padding: 2px 6px;
            border-radius: 4px;
            font-size: 11px;
        """)
        duration.setParent(thumb_container)
        duration.move(280, 130)
        
        layout.addWidget(thumb_container)
        
        # Info section
        info = QVBoxLayout()
        info.setContentsMargins(12, 0, 12, 8)
        info.setSpacing(4)
        
        # Title
        title = QLabel(self.video_data.get("title", "Video Title"))
        title.setStyleSheet("color: #ffffff; font-weight: bold; font-size: 13px;")
        title.setWordWrap(True)
        title.setMaximumHeight(40)
        info.addWidget(title)
        
        # Channel & views
        meta = QLabel(f"{self.video_data.get('channel', 'Channel')} · {self.video_data.get('views', '10K')} vistas")
        meta.setStyleSheet("color: #a0a0b0; font-size: 11px;")
        info.addWidget(meta)
        
        layout.addLayout(info)
        
        self.setStyleSheet("""
            QFrame {
                background: #1a1a2e;
                border-radius: 12px;
                border: 1px solid #252540;
            }
            QFrame:hover {
                border-color: #00d4aa;
            }
        """)
    
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.video_data)


class PlaylistCard(QFrame):
    """Playlist card with video count."""
    
    clicked = pyqtSignal(dict)
    
    def __init__(self, playlist_data: dict, parent=None):
        super().__init__(parent)
        self.playlist_data = playlist_data
        self.setFixedSize(280, 180)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Thumbnail stack effect
        thumb_container = QFrame()
        thumb_container.setFixedHeight(120)
        thumb_container.setStyleSheet("""
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                stop:0 #7c3aed, stop:1 #00d4aa);
            border-radius: 12px 12px 0 0;
        """)
        
        # Video count badge
        count_layout = QVBoxLayout(thumb_container)
        count_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        count_label = QLabel(f"📺 {self.playlist_data.get('count', 12)} videos")
        count_label.setStyleSheet("""
            background: rgba(0, 0, 0, 0.6);
            color: white;
            padding: 8px 16px;
            border-radius: 8px;
            font-weight: bold;
        """)
        count_layout.addWidget(count_label, alignment=Qt.AlignmentFlag.AlignCenter)
        
        layout.addWidget(thumb_container)
        
        # Info
        info = QVBoxLayout()
        info.setContentsMargins(12, 8, 12, 12)
        
        title = QLabel(self.playlist_data.get("title", "Playlist"))
        title.setStyleSheet("color: #ffffff; font-weight: bold;")
        title.setWordWrap(True)
        info.addWidget(title)
        
        layout.addLayout(info)
        
        self.setStyleSheet("""
            QFrame {
                background: #252540;
                border-radius: 12px;
            }
            QFrame:hover {
                background: #2a2a55;
            }
        """)
    
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.playlist_data)


class LearnPanel(QWidget):
    """Learning hub with curated YouTube content."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(24)
        
        # Header
        header = QHBoxLayout()
        
        title = QLabel("Aprende a Dibujar")
        title.setStyleSheet("color: #ffffff; font-size: 28px; font-weight: bold;")
        header.addWidget(title)
        
        header.addStretch()
        
        # Search
        search = QLineEdit()
        search.setPlaceholderText("🔍 Buscar tutoriales...")
        search.setFixedWidth(300)
        search.setStyleSheet("""
            QLineEdit {
                background: #252540;
                color: #ffffff;
                border: 1px solid #3a3a5a;
                border-radius: 8px;
                padding: 10px 16px;
            }
        """)
        header.addWidget(search)
        
        layout.addLayout(header)
        
        # Category tabs
        tabs = QTabWidget()
        tabs.setStyleSheet("""
            QTabWidget::pane { border: none; background: transparent; }
            QTabBar::tab {
                background: transparent;
                color: #a0a0b0;
                padding: 12px 24px;
                border-bottom: 2px solid transparent;
                font-weight: 500;
            }
            QTabBar::tab:selected { color: #00d4aa; border-bottom-color: #00d4aa; }
            QTabBar::tab:hover { color: #ffffff; }
        """)
        
        # Tab contents
        tabs.addTab(self._create_overview_tab(), "📚 Todo")
        tabs.addTab(self._create_category_tab("illustration"), "🎨 Ilustración")
        tabs.addTab(self._create_category_tab("concept_art"), "🏛 Arte Conceptual")
        tabs.addTab(self._create_category_tab("animation"), "🎬 Animación 2D")
        tabs.addTab(self._create_category_tab("character"), "👤 Diseño de Personajes")
        tabs.addTab(self._create_category_tab("fundamentals"), "📐 Fundamentos")
        
        layout.addWidget(tabs, 1)
        
        self.setStyleSheet("background: #0f0f1a;")
    
    def _create_overview_tab(self) -> QWidget:
        """Create overview tab with playlists and featured videos."""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none; background: transparent;")
        
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setSpacing(32)
        
        # Featured playlists section
        playlist_section = QVBoxLayout()
        
        section_header = QLabel("📺 Playlists Curadas")
        section_header.setStyleSheet("color: #ffffff; font-size: 20px; font-weight: bold;")
        playlist_section.addWidget(section_header)
        
        playlist_grid = QHBoxLayout()
        playlist_grid.setSpacing(16)
        
        playlists = [
            {"title": "Fundamentos del Dibujo", "count": 25, "category": "fundamentals"},
            {"title": "Pintura Digital Avanzada", "count": 18, "category": "illustration"},
            {"title": "Arte Conceptual para Videojuegos", "count": 32, "category": "concept_art"},
            {"title": "Animación 2D desde Cero", "count": 40, "category": "animation"},
        ]
        
        for pl in playlists:
            card = PlaylistCard(pl)
            card.clicked.connect(self._on_playlist_clicked)
            playlist_grid.addWidget(card)
        
        playlist_grid.addStretch()
        playlist_section.addLayout(playlist_grid)
        layout.addLayout(playlist_section)
        
        # Recent videos section
        videos_section = QVBoxLayout()
        
        videos_header = QLabel("🔥 Videos Populares")
        videos_header.setStyleSheet("color: #ffffff; font-size: 20px; font-weight: bold;")
        videos_section.addWidget(videos_header)
        
        videos_grid = QGridLayout()
        videos_grid.setSpacing(16)
        
        videos = [
            {"title": "Cómo dibujar rostros - Guía completa", "channel": "Proko", "views": "2.1M", "duration": "45:30"},
            {"title": "Color y luz para ilustradores", "channel": "Marco Bucci", "views": "890K", "duration": "28:15"},
            {"title": "Diseño de personajes profesional", "channel": "Sinix Design", "views": "1.2M", "duration": "35:20"},
            {"title": "Perspectiva fácil para principiantes", "channel": "Draw with Jazza", "views": "1.5M", "duration": "22:10"},
            {"title": "Anatomía humana simplificada", "channel": "Proko", "views": "3.2M", "duration": "52:00"},
            {"title": "Técnicas de sombreado", "channel": "Art of Wei", "views": "670K", "duration": "18:45"},
        ]
        
        for i, video in enumerate(videos):
            card = VideoCard(video)
            card.clicked.connect(self._on_video_clicked)
            videos_grid.addWidget(card, i // 3, i % 3)
        
        videos_section.addLayout(videos_grid)
        layout.addLayout(videos_section)
        
        layout.addStretch()
        scroll.setWidget(content)
        return scroll
    
    def _create_category_tab(self, category: str) -> QWidget:
        """Create a category-specific tab."""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none; background: transparent;")
        
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setSpacing(16)
        
        # Category-specific videos
        videos_grid = QGridLayout()
        videos_grid.setSpacing(16)
        
        # Placeholder videos for each category
        category_videos = {
            "illustration": [
                {"title": "Técnicas de ilustración digital", "channel": "Loish", "views": "500K", "duration": "32:00"},
                {"title": "Workflow de ilustración profesional", "channel": "Ross Draws", "views": "800K", "duration": "28:00"},
            ],
            "concept_art": [
                {"title": "Diseño de ambientes", "channel": "FZD School", "views": "1.1M", "duration": "45:00"},
                {"title": "Thumbnailing rápido", "channel": "Tyler Edlin", "views": "400K", "duration": "20:00"},
            ],
            "animation": [
                {"title": "12 principios de animación", "channel": "Animator Island", "views": "2M", "duration": "55:00"},
                {"title": "Walk cycle tutorial", "channel": "Howard Wimshurst", "views": "600K", "duration": "25:00"},
            ],
            "character": [
                {"title": "Diseño de siluetas", "channel": "Ahmed Aldoori", "views": "700K", "duration": "30:00"},
                {"title": "Expresiones faciales", "channel": "Ethan Becker", "views": "900K", "duration": "22:00"},
            ],
            "fundamentals": [
                {"title": "Las 5 formas básicas", "channel": "Proko", "views": "1.5M", "duration": "15:00"},
                {"title": "Composición para artistas", "channel": "Sycra", "views": "400K", "duration": "35:00"},
            ],
        }
        
        videos = category_videos.get(category, [])
        for i, video in enumerate(videos):
            card = VideoCard(video)
            card.clicked.connect(self._on_video_clicked)
            videos_grid.addWidget(card, i // 3, i % 3)
        
        layout.addLayout(videos_grid)
        layout.addStretch()
        
        scroll.setWidget(content)
        return scroll
    
    def _on_video_clicked(self, video_data: dict):
        """Handle video card click."""
        # In a real implementation, this would open an embedded player
        # For now, we'll show a placeholder message
        print(f"Playing video: {video_data.get('title')}")
    
    def _on_playlist_clicked(self, playlist_data: dict):
        """Handle playlist card click."""
        print(f"Opening playlist: {playlist_data.get('title')}")
