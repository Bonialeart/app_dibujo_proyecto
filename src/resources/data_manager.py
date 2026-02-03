"""
ArtFlow Studio - Data Manager
Handles application data persistence and resource links
"""

import json
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass


@dataclass
class ResourceInfo:
    """Information about an external resource."""
    id: str
    title: str
    description: str
    url: str
    category: str
    icon: str
    featured: bool = False


@dataclass
class ArtistInfo:
    """Information about a featured artist."""
    id: str
    name: str
    handle: str
    bio: str
    style: List[str]
    social: Dict[str, str]


class DataManager:
    """Manages application data and resources."""
    
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
        self._resources: List[ResourceInfo] = []
        self._artists: List[ArtistInfo] = []
        self._current_artist_id: str = ""
        
        self._load_data()
    
    def _load_data(self):
        """Load resources data from JSON."""
        data_path = Path(__file__).parent.parent.parent / "data" / "resources.json"
        
        if data_path.exists():
            try:
                with open(data_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Load resources
                for r in data.get("resources", []):
                    self._resources.append(ResourceInfo(
                        id=r["id"],
                        title=r["title"],
                        description=r["description"],
                        url=r["url"],
                        category=r["category"],
                        icon=r.get("icon", "🔗"),
                        featured=r.get("featured", False)
                    ))
                
                # Load artists
                for a in data.get("artists_of_the_week", []):
                    self._artists.append(ArtistInfo(
                        id=a["id"],
                        name=a["name"],
                        handle=a["handle"],
                        bio=a.get("bio", ""),
                        style=a.get("style", []),
                        social=a.get("social", {})
                    ))
                
                self._current_artist_id = data.get("current_artist_of_week", "")
            except Exception as e:
                print(f"Error loading resources data: {e}")
    
    def get_resources(self, category: str = None) -> List[ResourceInfo]:
        if category:
            return [r for r in self._resources if r.category == category]
        return self._resources
    
    def get_featured_resources(self) -> List[ResourceInfo]:
        return [r for r in self._resources if r.featured]
    
    def get_artist_of_week(self) -> Optional[ArtistInfo]:
        if not self._current_artist_id:
            return self._artists[0] if self._artists else None
            
        for artist in self._artists:
            if artist.id == self._current_artist_id:
                return artist
        return None
    
    def get_all_artists(self) -> List[ArtistInfo]:
        return self._artists


data_manager = DataManager()
