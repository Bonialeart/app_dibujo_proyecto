"""
ArtFlow Studio - Resources Panel
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QGridLayout, QTabWidget
)
from PyQt6.QtCore import Qt, pyqtSignal, QUrl
from PyQt6.QtGui import QDesktopServices, QFont


class ResourceCard(QFrame):
    """Resource/website card widget."""
    
    def __init__(self, resource_data: dict, parent=None):
        super().__init__(parent)
        self.resource_data = resource_data
        self.setFixedHeight(140)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)
        
        # Icon/preview
        icon_label = QLabel(self.resource_data.get("icon", "🔗"))
        icon_label.setFixedSize(80, 80)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setStyleSheet("""
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                stop:0 #7c3aed, stop:1 #00d4aa);
            border-radius: 12px;
            font-size: 32px;
        """)
        layout.addWidget(icon_label)
        
        # Info
        info_layout = QVBoxLayout()
        info_layout.setSpacing(4)
        
        title = QLabel(self.resource_data.get("title", "Resource"))
        title.setStyleSheet("color: #ffffff; font-weight: bold; font-size: 16px;")
        info_layout.addWidget(title)
        
        desc = QLabel(self.resource_data.get("description", ""))
        desc.setStyleSheet("color: #a0a0b0; font-size: 13px;")
        desc.setWordWrap(True)
        info_layout.addWidget(desc)
        
        category = QLabel(self.resource_data.get("category", "General"))
        category.setStyleSheet("""
            color: #00d4aa;
            background: rgba(0, 212, 170, 0.1);
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 11px;
        """)
        category.setFixedWidth(category.sizeHint().width() + 16)
        info_layout.addWidget(category)
        
        layout.addLayout(info_layout, 1)
        
        # Open button
        open_btn = QPushButton("Abrir →")
        open_btn.setStyleSheet("""
            QPushButton {
                background: #252540;
                color: #ffffff;
                border: none;
                border-radius: 8px;
                padding: 12px 24px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #00d4aa;
                color: #0f0f1a;
            }
        """)
        open_btn.clicked.connect(self._open_link)
        layout.addWidget(open_btn)
        
        self.setStyleSheet("""
            QFrame {
                background: #1a1a2e;
                border-radius: 12px;
                border: 1px solid #252540;
            }
            QFrame:hover {
                border-color: #3a3a5a;
            }
        """)
    
    def _open_link(self):
        url = self.resource_data.get("url", "")
        if url:
            QDesktopServices.openUrl(QUrl(url))


class ArtistCard(QFrame):
    """Artist of the week card."""
    
    def __init__(self, artist_data: dict, parent=None):
        super().__init__(parent)
        self.artist_data = artist_data
        self.setFixedSize(300, 380)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Featured image
        image_frame = QFrame()
        image_frame.setFixedHeight(200)
        image_frame.setStyleSheet("""
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                stop:0 #ff6b6b, stop:0.5 #7c3aed, stop:1 #00d4aa);
            border-radius: 16px 16px 0 0;
        """)
        
        # Badge
        badge = QLabel("⭐ Artista de la Semana")
        badge.setStyleSheet("""
            background: rgba(251, 191, 36, 0.9);
            color: #0f0f1a;
            padding: 6px 12px;
            border-radius: 4px;
            font-weight: bold;
            font-size: 11px;
        """)
        badge.setParent(image_frame)
        badge.move(12, 12)
        
        layout.addWidget(image_frame)
        
        # Info section
        info_frame = QFrame()
        info_frame.setStyleSheet("background: #252540; border-radius: 0 0 16px 16px;")
        
        info_layout = QVBoxLayout(info_frame)
        info_layout.setContentsMargins(16, 16, 16, 16)
        info_layout.setSpacing(8)
        
        # Avatar and name row
        header = QHBoxLayout()
        
        avatar = QLabel("👤")
        avatar.setFixedSize(48, 48)
        avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        avatar.setStyleSheet("background: #1a1a2e; border-radius: 24px; font-size: 24px;")
        header.addWidget(avatar)
        
        name_layout = QVBoxLayout()
        name = QLabel(self.artist_data.get("name", "Artist Name"))
        name.setStyleSheet("color: #ffffff; font-weight: bold; font-size: 16px;")
        name_layout.addWidget(name)
        
        handle = QLabel(self.artist_data.get("handle", "@artist"))
        handle.setStyleSheet("color: #a0a0b0; font-size: 12px;")
        name_layout.addWidget(handle)
        
        header.addLayout(name_layout, 1)
        info_layout.addLayout(header)
        
        # Style tags
        style = QLabel(self.artist_data.get("style", "Digital Art · Character Design"))
        style.setStyleSheet("color: #00d4aa; font-size: 12px;")
        info_layout.addWidget(style)
        
        # Description
        desc = QLabel(self.artist_data.get("bio", "Artista destacado por su estilo único."))
        desc.setStyleSheet("color: #a0a0b0; font-size: 12px;")
        desc.setWordWrap(True)
        info_layout.addWidget(desc)
        
        # Social links
        social_layout = QHBoxLayout()
        
        for platform, icon in [("twitter", "🐦"), ("instagram", "📷"), ("artstation", "🎨")]:
            btn = QPushButton(icon)
            btn.setFixedSize(36, 36)
            btn.setStyleSheet("""
                QPushButton {
                    background: #1a1a2e;
                    border: none;
                    border-radius: 8px;
                    font-size: 16px;
                }
                QPushButton:hover {
                    background: #3a3a5a;
                }
            """)
            social_layout.addWidget(btn)
        
        social_layout.addStretch()
        info_layout.addLayout(social_layout)
        
        layout.addWidget(info_frame)
        
        self.setStyleSheet("border-radius: 16px;")


class ResourcesPanel(QWidget):
    """Panel for useful resources and artist spotlight."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(24)
        
        # Header
        header = QHBoxLayout()
        
        title = QLabel("Recursos para Artistas")
        title.setStyleSheet("color: #ffffff; font-size: 28px; font-weight: bold;")
        header.addWidget(title)
        
        header.addStretch()
        layout.addLayout(header)
        
        # Main content scroll
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none; background: transparent;")
        
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setSpacing(32)
        
        # Artist of the week section
        artist_section = QVBoxLayout()
        
        artist_header = QHBoxLayout()
        artist_title = QLabel("⭐ Artista de la Semana")
        artist_title.setStyleSheet("color: #fbbf24; font-size: 20px; font-weight: bold;")
        artist_header.addWidget(artist_title)
        artist_header.addStretch()
        artist_section.addLayout(artist_header)
        
        artist_row = QHBoxLayout()
        
        featured_artist = ArtistCard({
            "name": "Sakimichan",
            "handle": "@sakimichan",
            "style": "Digital Painting · Fantasy · Characters",
            "bio": "Artista digital conocida por sus retratos estilizados y técnicas de iluminación cinematográfica."
        })
        artist_row.addWidget(featured_artist)
        
        # More artists
        more_artists = QVBoxLayout()
        more_artists.setSpacing(12)
        
        other_artists = [
            {"name": "Ross Tran", "handle": "@rossdraws", "style": "Illustration"},
            {"name": "Loish", "handle": "@loikitten", "style": "Character Design"},
            {"name": "WLOP", "handle": "@wlopwangling", "style": "Fantasy Art"},
        ]
        
        for artist in other_artists:
            mini_card = QFrame()
            mini_card.setFixedHeight(70)
            mini_card.setStyleSheet("background: #252540; border-radius: 8px;")
            
            mini_layout = QHBoxLayout(mini_card)
            mini_layout.setContentsMargins(12, 8, 12, 8)
            
            avatar = QLabel("👤")
            avatar.setFixedSize(40, 40)
            avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
            avatar.setStyleSheet("background: #1a1a2e; border-radius: 20px;")
            mini_layout.addWidget(avatar)
            
            info = QVBoxLayout()
            name = QLabel(artist["name"])
            name.setStyleSheet("color: #ffffff; font-weight: bold;")
            info.addWidget(name)
            style = QLabel(artist["style"])
            style.setStyleSheet("color: #a0a0b0; font-size: 11px;")
            info.addWidget(style)
            mini_layout.addLayout(info, 1)
            
            more_artists.addWidget(mini_card)
        
        artist_row.addLayout(more_artists, 1)
        artist_section.addLayout(artist_row)
        
        content_layout.addLayout(artist_section)
        
        # Useful links section
        links_section = QVBoxLayout()
        
        links_title = QLabel("🔗 Páginas Útiles")
        links_title.setStyleSheet("color: #ffffff; font-size: 20px; font-weight: bold;")
        links_section.addWidget(links_title)
        
        resources = [
            {
                "title": "Quickposes",
                "description": "Generador de poses para práctica de dibujo con temporizador.",
                "icon": "🏃",
                "category": "Práctica",
                "url": "https://quickposes.com"
            },
            {
                "title": "PureRef",
                "description": "Aplicación para organizar referencias visuales mientras dibujas.",
                "icon": "🖼",
                "category": "Herramientas",
                "url": "https://pureref.com"
            },
            {
                "title": "Color Hunt",
                "description": "Paletas de colores curadas para diseño e ilustración.",
                "icon": "🎨",
                "category": "Colores",
                "url": "https://colorhunt.co"
            },
            {
                "title": "Sketchfab",
                "description": "Modelos 3D para usar como referencia de ángulos y poses.",
                "icon": "🎭",
                "category": "Referencia 3D",
                "url": "https://sketchfab.com"
            },
            {
                "title": "Pinterest",
                "description": "Tableros de inspiración y referencias visuales.",
                "icon": "📌",
                "category": "Inspiración",
                "url": "https://pinterest.com"
            },
            {
                "title": "ArtStation",
                "description": "Portafolio profesional y showcase de artistas.",
                "icon": "💼",
                "category": "Portfolio",
                "url": "https://artstation.com"
            },
        ]
        
        resources_grid = QGridLayout()
        resources_grid.setSpacing(12)
        
        for i, res in enumerate(resources):
            card = ResourceCard(res)
            resources_grid.addWidget(card, i // 2, i % 2)
        
        links_section.addLayout(resources_grid)
        content_layout.addLayout(links_section)
        
        content_layout.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll, 1)
        
        self.setStyleSheet("background: #0f0f1a;")
