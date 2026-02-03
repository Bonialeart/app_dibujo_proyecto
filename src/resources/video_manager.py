"""
ArtFlow Studio - Video Manager
Handles YouTube playlists and video resources
"""

import json
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass


@dataclass
class VideoInfo:
    """Information about a video."""
    id: str
    title: str
    duration: str
    youtube_id: str


@dataclass
class PlaylistInfo:
    """Information about a playlist."""
    id: str
    title: str
    category: str
    thumbnail: str
    video_count: int
    difficulty: str
    videos: List[VideoInfo]


class VideoManager:
    """Manages video learning content."""
    
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
        self._playlists: Dict[str, PlaylistInfo] = {}
        self._categories: Dict[str, dict] = {}
        
        self._load_content()
    
    def _load_content(self):
        """Load video content from JSON."""
        content_path = Path(__file__).parent.parent.parent / "data" / "playlists.json"
        
        if content_path.exists():
            try:
                with open(content_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                self._categories = data.get("categories", {})
                
                for pl_data in data.get("playlists", []):
                    videos = []
                    for v in pl_data.get("videos", []):
                        videos.append(VideoInfo(
                            id=v["id"],
                            title=v["title"],
                            duration=v["duration"],
                            youtube_id=v["youtube_id"]
                        ))
                    
                    playlist = PlaylistInfo(
                        id=pl_data["id"],
                        title=pl_data["title"],
                        category=pl_data["category"],
                        thumbnail=pl_data.get("thumbnail", ""),
                        video_count=pl_data.get("video_count", 0),
                        difficulty=pl_data.get("difficulty", "intermediate"),
                        videos=videos
                    )
                    self._playlists[playlist.id] = playlist
            except Exception as e:
                print(f"Error loading video content: {e}")
    
    def get_playlist(self, playlist_id: str) -> Optional[PlaylistInfo]:
        return self._playlists.get(playlist_id)
    
    def get_all_playlists(self) -> List[PlaylistInfo]:
        return list(self._playlists.values())
    
    def get_playlists_by_category(self, category: str) -> List[PlaylistInfo]:
        return [p for p in self._playlists.values() if p.category == category]
    
    def get_categories(self) -> Dict[str, dict]:
        return self._categories


video_manager = VideoManager()
