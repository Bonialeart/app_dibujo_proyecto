"""
ArtFlow Studio - Brush Manager
Handles brush packs, ABR files, and brush library
"""

import os
import json
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass
import struct


@dataclass
class BrushInfo:
    """Information about a brush."""
    id: str
    name: str
    category: str
    diameter: int = 100
    spacing: float = 0.25
    hardness: float = 0.8
    opacity: float = 1.0
    is_custom: bool = False


@dataclass
class BrushPack:
    """Information about a brush pack."""
    id: str
    name: str
    author: str
    category: str
    description: str
    brush_count: int
    file_size: str
    downloads: int
    rating: float
    price: float
    preview_image: str
    download_url: str
    is_installed: bool = False


class BrushManager:
    """Manages brush library and brush packs."""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        self._brushes: Dict[str, BrushInfo] = {}
        self._brush_packs: Dict[str, BrushPack] = {}
        self._installed_packs: List[str] = []
        
        self._load_default_brushes()
        self._load_brush_catalog()
    
    def _load_default_brushes(self):
        """Load built-in default brushes."""
        defaults = [
            BrushInfo("round_soft", "Redondo Suave", "paint", 100, 0.1, 0.3),
            BrushInfo("round_hard", "Redondo Duro", "paint", 100, 0.1, 0.9),
            BrushInfo("pencil", "Lápiz", "sketch", 20, 0.05, 0.95),
            BrushInfo("airbrush", "Aerógrafo", "paint", 150, 0.1, 0.1),
            BrushInfo("charcoal", "Carboncillo", "charcoal", 80, 0.15, 0.6),
            BrushInfo("ink", "Tinta", "ink", 30, 0.05, 1.0),
            BrushInfo("watercolor", "Acuarela", "watercolor", 120, 0.2, 0.4),
        ]
        
        for brush in defaults:
            self._brushes[brush.id] = brush
    
    def _load_brush_catalog(self):
        """Load brush catalog from JSON."""
        # Adjust path to match project structure
        catalog_path = Path(__file__).parent.parent.parent / "data" / "brushes.json"
        
        if catalog_path.exists():
            try:
                with open(catalog_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                for pack_data in data.get("brush_packs", []):
                    pack = BrushPack(
                        id=pack_data["id"],
                        name=pack_data["name"],
                        author=pack_data.get("author", "Unknown"),
                        category=pack_data.get("category", "general"),
                        description=pack_data.get("description", ""),
                        brush_count=pack_data.get("brush_count", 0),
                        file_size=pack_data.get("file_size", "0MB"),
                        downloads=pack_data.get("downloads", 0),
                        rating=pack_data.get("rating", 0.0),
                        price=pack_data.get("price", 0.0),
                        preview_image=pack_data.get("preview_image", ""),
                        download_url=pack_data.get("download_url", "")
                    )
                    self._brush_packs[pack.id] = pack
            except Exception as e:
                print(f"Error loading brush catalog: {e}")
    
    def get_brush(self, brush_id: str) -> Optional[BrushInfo]:
        return self._brushes.get(brush_id)
    
    def get_all_brushes(self) -> List[BrushInfo]:
        return list(self._brushes.values())
    
    def get_brushes_by_category(self, category: str) -> List[BrushInfo]:
        return [b for b in self._brushes.values() if b.category == category]
    
    def get_all_packs(self) -> List[BrushPack]:
        return list(self._brush_packs.values())
    
    def import_abr(self, file_path: str) -> List[BrushInfo]:
        """Import brushes from ABR file."""
        brushes = []
        try:
            with open(file_path, 'rb') as f:
                data = f.read()
            
            # Simplified parsing logic
            if len(data) >= 2:
                version = struct.unpack('>H', data[0:2])[0]
                
                # Mock import for now as full ABR parsing in Python without C++ binding is complex
                # In a real scenario, we'd use the C++ engine or a library
                brush = BrushInfo(
                    f"imported_{len(self._brushes)}",
                    Path(file_path).stem,
                    "imported",
                    is_custom=True
                )
                brushes.append(brush)
                self._brushes[brush.id] = brush
        except Exception as e:
            print(f"Error importing ABR: {e}")
        
        return brushes


brush_manager = BrushManager()
