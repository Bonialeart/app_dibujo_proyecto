
import os
import shutil
import tempfile
import zipfile
import threading
from PyQt6.QtCore import QObject, pyqtSlot, pyqtSignal, QUrl
from PyQt6.QtGui import QImage
from PyQt6.QtQuick import QQuickImageProvider

class TimelapseController(QObject):
    previewReady = pyqtSignal(str) # Returns path to Animated Image
    previewError = pyqtSignal(str)
    videoExportFinished = pyqtSignal(bool, str) # Success, Message

    def __init__(self):
        super().__init__()
        self.current_temp_dir = None
        self.frames = []
        self._lock = threading.Lock()

    def _extract_frames_to_temp(self, project_path):
        """Helper to extract frames to a new temp dir. Returns (temp_dir, frame_paths_list)."""
        new_temp_dir = tempfile.mkdtemp(prefix="ArtFlow_TL_")
        extracted_frames = []
        
        # Handle file:/// conversion for path
        if project_path.startswith("file:///"):
            project_path = QUrl(project_path).toLocalFile()
        elif project_path.startswith("file:"):
             project_path = project_path[5:]
             
        if not os.path.exists(project_path):
            try: os.rmdir(new_temp_dir)
            except: pass
            raise FileNotFoundError(f"Project not found: {project_path}")

        # MODE A: ZIP (.aflow)
        if zipfile.is_zipfile(project_path):
            with zipfile.ZipFile(project_path, 'r') as zf:
                tl_files = [f for f in zf.namelist() if (f.startswith("timelapse/") or f.startswith("timelapse\\")) and f.lower().endswith(".jpg")]
                tl_files.sort()
                for member in tl_files:
                    zf.extract(member, new_temp_dir)
                    safe_name = member.replace("/", os.sep).replace("\\", os.sep)
                    extracted_frames.append(os.path.join(new_temp_dir, safe_name))

        # MODE B: FOLDER (Legacy)
        elif os.path.isdir(project_path):
            tl_dir = os.path.join(project_path, "timelapse")
            if os.path.exists(tl_dir) and os.path.isdir(tl_dir):
                files = sorted([f for f in os.listdir(tl_dir) if f.lower().endswith(".jpg")])
                for f in files:
                    src = os.path.join(tl_dir, f)
                    dst = os.path.join(new_temp_dir, f)
                    try:
                        shutil.copy2(src, dst)
                        extracted_frames.append(dst)
                    except: pass
        
        return new_temp_dir, extracted_frames

    @pyqtSlot(str)
    def startPreview(self, project_path):
        # Create thread
        thread = threading.Thread(target=self._preview_worker, args=(project_path,))
        thread.daemon = True
        thread.start()

    def _preview_worker(self, project_path):
        try:
            temp_dir, frames = self._extract_frames_to_temp(project_path)
            
            if not frames:
                print("[TLS] No frames found.")
                try: shutil.rmtree(temp_dir)
                except: pass
                self.previewReady.emit("")
                return

            self.frames = frames # Update internal list for ImageProvider if needed
            
            # Generate GIF using Pillow
            output_anim_path = os.path.join(temp_dir, "preview_anim.gif")
            try:
                from PIL import Image, ImageOps
                images = []
                
                # Determine target size from NEWEST (last) frame for best quality, or first?
                # Usually standardizing to a fixed preview size (e.g. 640px width) is safest for QuickLook.
                # Let's target 640w for the GIF preview.
                target_w = 640
                
                for fp in frames:
                    try:
                        im = Image.open(fp)
                        if im.mode != "RGB": im = im.convert("RGB")
                        
                        # Resize maintaining aspect ratio
                        ratio = target_w / float(im.width)
                        target_h = int(float(im.height) * ratio)
                        im = im.resize((target_w, target_h), Image.Resampling.LANCZOS)
                        
                        images.append(im)
                    except: pass
                
                if images:
                    images[0].save(
                        output_anim_path,
                        save_all=True,
                        append_images=images[1:],
                        duration=60, # ~16fps
                        loop=0,
                        optimize=False
                    )
                    
                    # Cleanup old
                    old_dir = self.current_temp_dir
                    with self._lock:
                        self.current_temp_dir = temp_dir
                    
                    if old_dir and old_dir != temp_dir and os.path.exists(old_dir):
                        try: shutil.rmtree(old_dir, ignore_errors=True)
                        except: pass
                        
                    self.previewReady.emit(QUrl.fromLocalFile(output_anim_path).toString())
                else:
                    self.previewReady.emit("")
            except ImportError:
                self.previewError.emit("Missing PIL Library")
            except Exception as e:
                self.previewError.emit(str(e))

        except Exception as e:
            print(f"[TLS] Preview Error: {e}")
            self.previewError.emit(str(e))

    @pyqtSlot(str, str, int, int, int)
    def exportVideo(self, project_path, output_path, duration_sec, aspect_mode, quality_mode):
        """Export project timelapse to MP4 with configuration."""
        output_url = QUrl(output_path).toLocalFile()
        if not output_url: output_url = output_path
        
        thread = threading.Thread(target=self._export_worker, args=(project_path, output_url, duration_sec, aspect_mode, quality_mode))
        thread.daemon = True
        thread.start()

    def _export_worker(self, project_path, output_path, duration_sec=0, aspect_mode=0, quality_mode=1):
        temp_dir = None
        try:
            print(f"[TLS] Exporting to {output_path} (Dur:{duration_sec}s, Aspect:{aspect_mode}, Quality:{quality_mode})...")
            temp_dir, frames = self._extract_frames_to_temp(project_path)
            
            if not frames:
                self.videoExportFinished.emit(False, "No frames found in project")
                return
                
            # Try using OpenCV
            try:
                import cv2
                import numpy as np
                
                # Determine dimensions from last frame
                last_frame = cv2.imread(frames[-1])
                orig_h, orig_w, _ = last_frame.shape
                
                # --- 1. ASPECT RATIO CALCULATIONS ---
                target_w, target_h = orig_w, orig_h
                crop_x, crop_y = 0, 0
                
                if aspect_mode == 1: # Square 1:1
                    s = min(orig_w, orig_h)
                    target_w, target_h = s, s
                    crop_x = (orig_w - s) // 2
                    crop_y = (orig_h - s) // 2
                elif aspect_mode == 2: # Portrait 9:16
                    target_ratio = 9 / 16
                    curr_ratio = orig_w / orig_h
                    if curr_ratio > target_ratio: # Too wide, crop width
                        new_w = int(orig_h * target_ratio)
                        target_w, target_h = new_w, orig_h
                        crop_x = (orig_w - new_w) // 2
                        crop_y = 0
                    else: # Too tall, crop height (unlikely for drawing canvas usually)
                        new_h = int(orig_w / target_ratio)
                        target_w, target_h = orig_w, new_h
                        crop_x = 0
                        crop_y = (orig_h - new_h) // 2
                
                # --- 2. QUALITY / RESOLUTION SCALING ---
                # Quality 0 = Web (Max 720p roughly)
                # Quality 1 = Studio (Original max up to 4k)
                if quality_mode == 0:
                     max_dim = 1080 # increased data from 720 to 1080 for web modern standards
                     if max(target_w, target_h) > max_dim:
                         scale = max_dim / max(target_w, target_h)
                         target_w = int(target_w * scale)
                         target_h = int(target_h * scale)

                # Ensure dimensions are even (codec requirement usually)
                if target_w % 2 != 0: target_w -= 1
                if target_h % 2 != 0: target_h -= 1
                
                # --- 3. FRAMERATE CALCULATION ---
                total_frames = len(frames)
                fps = 30
                step = 1.0
                
                if duration_sec > 0:
                    # Target specific duration
                    # Desired frame count = duration * 30fps (Standard)
                    # If we have too many frames, we skip. If too few, we lower FPS.
                    
                    target_fps = total_frames / duration_sec
                    
                    if target_fps <= 60:
                        fps = max(10, int(target_fps)) # Clamp min 10
                    else:
                        # Too many frames for 60fps. Needs skipping.
                        fps = 60
                        # total / step = duration * 60
                        # step = total / (duration * 60)
                        step = total_frames / (duration_sec * 60)
                else:
                    # Smart Auto Mode
                    if total_frames < 30: fps = 10
                    elif total_frames < 100: fps = 15
                    elif total_frames < 300: fps = 24
                
                print(f"[TLS] Config: {target_w}x{target_h} @ {fps}fps (Step: {step:.2f})")

                # Codec - H.264 is better (avc1) but mp4v is safer fallback
                fourcc = cv2.VideoWriter_fourcc(*'mp4v') 
                video = cv2.VideoWriter(output_path, fourcc, fps, (target_w, target_h))
                
                current_idx = 0.0
                frames_written = 0
                
                while current_idx < total_frames:
                    idx = int(current_idx)
                    f_path = frames[idx]
                    img = cv2.imread(f_path)
                    
                    if img is None: 
                        current_idx += step
                        continue

                    # Crop
                    if crop_x > 0 or crop_y > 0 or target_w != orig_w or target_h != orig_h:
                         # Crop logic depends on original image size matching calc
                         h, w, _ = img.shape
                         
                         # Center crop if sizes match expectation, else resize-crop logic complicated
                         # Simplification: Resize img to orig (unlikely to change mid-stream but safe)
                         # Then crop
                         roi = img[crop_y : crop_y+orig_h if aspect_mode!=0 else h, 
                                   crop_x : crop_x+orig_w if aspect_mode!=0 else w]
                         
                         # Resize to final target
                         img = cv2.resize(roi, (target_w, target_h), interpolation=cv2.INTER_AREA)
                    else:
                         img = cv2.resize(img, (target_w, target_h), interpolation=cv2.INTER_AREA) # Just resize if only quality changed

                    video.write(img)
                    frames_written += 1
                    current_idx += step
                    
                # HOLD LAST FRAME
                hold_frames = int(fps * 2) 
                
                # Re-process last frame correctly
                last_img = cv2.imread(frames[-1])
                # Crop/Resize last frame same way
                roi = last_img[crop_y : crop_y+orig_h if aspect_mode!=0 else last_img.shape[0], 
                               crop_x : crop_x+orig_w if aspect_mode!=0 else last_img.shape[1]]
                last_final = cv2.resize(roi, (target_w, target_h), interpolation=cv2.INTER_AREA)

                for _ in range(hold_frames):
                     video.write(last_final)
                
                cv2.destroyAllWindows()
                video.release()
                
                print(f"[TLS] Export Success: {frames_written} frames written.")
                self.videoExportFinished.emit(True, output_path)
                
            except ImportError:
                self.videoExportFinished.emit(False, "OpenCV (cv2) not installed")
            except Exception as ve:
                print(f"[TLS] CV2 Error: {ve}")
                self.videoExportFinished.emit(False, str(ve))
            
            # Cleanup
            try: shutil.rmtree(temp_dir)
            except: pass
            
        except Exception as e:
             print(f"[TLS] Export Error: {e}")
             self.videoExportFinished.emit(False, str(e))
             if temp_dir:
                 try: shutil.rmtree(temp_dir)
                 except: pass

class TimelapseProvider(QQuickImageProvider):
    def __init__(self, controller):
        super().__init__(QQuickImageProvider.ImageType.Image)
        self.controller = controller

    def requestImage(self, id, size, requestedSize):
        # id will be "frame_<index>?s=<session>"
        try:
            # Remove query params if any
            clean_id = id.split('?')[0]
            # Format: 'frame_123'
            idx = int(clean_id.split('_')[1])
            
            # Thread-safe access to list (atomic read in Python)
            frames = self.controller.frames 
            
            if 0 <= idx < len(frames):
                path = frames[idx]
                if os.path.exists(path):
                    img = QImage(path)
                    if not img.isNull():
                         return img, img.size()
        except Exception as e:
            # print(f"Image request failed: {id} - {e}")
            pass
            
        return QImage(), size
