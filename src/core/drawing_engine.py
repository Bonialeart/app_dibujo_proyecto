from PyQt6.QtGui import QImage, QPainter, QColor, QRadialGradient, QBrush
from PyQt6.QtCore import Qt, QRect, QRectF, QPointF, QPoint, pyqtSlot, QUrl
import numpy as np
import cv2
import time
import os
import base64
import colorsys

class DrawingEngineMixin:
    """
    Encapsulates all drawing logic:
    - Textured Line Drawing (Software & Native)
    - Brush Stamp Generation (Procedural & ABR)
    - Paper Texture Generation
    - Color Mixing (Kubelka-Munk, Fresco)
    - Native Sync
    """
    
    def _init_drawing_engine(self):
        # 1. Texture Generation
        print("DrawingEngine: generating paper...")
        self._paper_texture_size = 1024
        self._paper_texture = self._generate_seamless_paper(self._paper_texture_size)
    
        # Initialize internal caches
        self._brush_texture_cache = None
        self._brush_texture_params = None
        self._cached_stamp = None
        self._last_pstamp_key = None
        self._last_pstamp = None
        self._last_native_stamp_params = None
        
        # Spacing Logic
        self._spacing_residue = 0.0
        self._brush_stamp_mode = False
        
        # Drawing state variables
        self._brush_grain = 0.0
        self._brush_granulation = 0.0
        self._brush_diffusion = 0.5
        self._current_pressure = 1.0
        
        # --- OIL / REALISM STATE ---
        self._paint_load = 1.0 # 1.0 = Full, 0.0 = Dry
        self._brush_pickup_color = None # Color picked up from canvas (Dirty Brush)
        
        # --- PRO STRUCTURE: PERSISTENT MAPS ---
        # 1. WET MAP: Grayscale buffer (0=Dry, 1=Soaked)
        self._wet_map = np.zeros((getattr(self, '_canvas_height', 1080), getattr(self, '_canvas_width', 1920)), dtype=np.float32)
        
        # 2. PIGMENT MAP: High-precision color density (R, G, B, Density)
        self._pigment_map = np.zeros((getattr(self, '_canvas_height', 1080), getattr(self, '_canvas_width', 1920), 4), dtype=np.float32)
        
        # Drying Timer: Gradually dries the canvas
        from PyQt6.QtCore import QTimer
        self._dry_timer = QTimer(self)
        self._dry_timer.timeout.connect(self._evaporate_wet_map)
        self._dry_timer.start(3000)

        # Brush state
        self._custom_brushes = {}

    # --- NATIVE SYNC ---
    def _sync_active_layer_to_native(self):
        """Uploads the current layer's pixels to the GPU."""
        # Note: Needs HAS_NATIVE_RENDER and _native_initialized from host
        if not getattr(self, "HAS_NATIVE_RENDER", False) or not getattr(self, "_native_initialized", False): return
        active_layer = self.layers[self._active_layer_index]
        mirrored = active_layer.image.mirrored().convertToFormat(QImage.Format.Format_RGBA8888)
        ptr = mirrored.constBits()
        ptr.setsize(mirrored.sizeInBytes())
        self._native_renderer.setBufferData(bytes(ptr))

    def _sync_active_layer_from_native(self):
        """Downloads the current layer's pixels from the GPU."""
        if not getattr(self, "HAS_NATIVE_RENDER", False) or not getattr(self, "_native_initialized", False): return
        w, h = self._canvas_width, self._canvas_height
        ptr = self._native_renderer.getBufferData()
        if ptr:
             qimg = QImage(ptr, w, h, QImage.Format.Format_RGBA8888).mirrored().convertToFormat(QImage.Format.Format_ARGB32_Premultiplied)
             self.layers[self._active_layer_index].image = qimg.copy()

    # --- COLOR MIXING ---
    def _mix_kubelka_munk(self, canvas_patch_qimg, brush_patch_qimg, paper_patch, opacity, pressure):
        """VIBRANT RMS MIXING ENGINE."""
        w, h = canvas_patch_qimg.width(), canvas_patch_qimg.height()
        if w <= 0 or h <= 0: return canvas_patch_qimg, None
        
        c_ptr = canvas_patch_qimg.constBits()
        c_ptr.setsize(h * w * 4)
        bg_arr = np.frombuffer(c_ptr, dtype=np.uint8).reshape((h, w, 4)).astype(np.float32) / 255.0
        
        b_ptr = brush_patch_qimg.constBits()
        b_ptr.setsize(h * w * 4)
        fg_arr = np.frombuffer(b_ptr, dtype=np.uint8).reshape((h, w, 4)).astype(np.float32) / 255.0
        
        bg_rgb = bg_arr[:,:,:3]
        bg_a = bg_arr[:,:,3:4]
        fg_rgb = fg_arr[:,:,:3]
        fg_a = fg_arr[:,:,3:4] * opacity
        
        flow_mask = np.ones((h, w, 1), dtype=np.float32)
        if paper_patch is not None:
             if paper_patch.ndim == 2: paper_patch = paper_patch[:, :, np.newaxis]
             gran_intensity = getattr(self, '_brush_granulation', 0.0)
             if gran_intensity > 0.0:
                 texture_allowance = 1.0 - (paper_patch * gran_intensity * 0.8) 
                 noise = np.random.rand(h, w, 1).astype(np.float32)
                 texture_noise = 1.0 - (noise * gran_intensity * 0.4)
                 flow_mask = texture_allowance * texture_noise
        
        effective_brush_a = fg_a * flow_mask
        bg_rgb_effective = bg_rgb * bg_a + (1.0 - bg_a) * 1.0
        density = np.clip(effective_brush_a * pressure, 0.0, 1.0)
        
        bg_inv = 1.0 - bg_rgb_effective
        fg_inv = 1.0 - fg_rgb
        mixed_inv_sq = (bg_inv**2 * (1.0 - density)) + (fg_inv**2 * density)
        mix_rgb = 1.0 - np.sqrt(np.clip(mixed_inv_sq, 0.0, 1.0))

        diffusion = getattr(self, '_brush_diffusion', 0.0)
        if diffusion > 0.05:
              body_ratio = density * diffusion * 0.4
              mix_rgb = mix_rgb * (1.0 - body_ratio) + fg_rgb * body_ratio

        out_a = np.clip(bg_a + effective_brush_a, 0.0, 1.0)
        out_arr = (np.clip(np.dstack((mix_rgb, out_a)) * 255.0, 0, 255)).astype(np.uint8)
        return QImage(out_arr.data, w, h, w * 4, QImage.Format.Format_ARGB32).copy(), None

    def _mix_colors_fresco(self, brush_color, canvas_color, ratio):
        """Mezcla colores manteniendo la saturación."""
        if canvas_color.alpha() < 10: return brush_color
        r = brush_color.redF() * (1 - ratio) + canvas_color.redF() * ratio
        g = brush_color.greenF() * (1 - ratio) + canvas_color.greenF() * ratio
        b = brush_color.blueF() * (1 - ratio) + canvas_color.blueF() * ratio
        h, s, v = colorsys.rgb_to_hsv(r, g, b)
        s = min(1.0, s * 1.1)
        r, g, b = colorsys.hsv_to_rgb(h, s, v)
        return QColor.fromRgbF(min(1.0, r), min(1.0, g), min(1.0, b), brush_color.alphaF())

    # --- GENERATORS ---
    def _generate_seamless_paper(self, size):
        try:
            noise_small = np.random.randint(100, 200, (size//16, size//16), dtype=np.uint8)
            fiber_layer = cv2.resize(noise_small, (size, size), interpolation=cv2.INTER_CUBIC)
            fiber_layer = cv2.GaussianBlur(fiber_layer, (31, 31), 0)
            grit_layer = np.random.randint(0, 255, (size, size), dtype=np.uint8)
            grit_layer = cv2.GaussianBlur(grit_layer, (3, 3), 0)
            paper = (fiber_layer.astype(np.float32) * grit_layer.astype(np.float32)) / 255.0
            paper_f = np.clip((paper / 255.0 - 0.45) * 2.8, 0.0, 1.0)
            return cv2.GaussianBlur(paper_f, (3, 3), 0)
        except:
            return np.ones((size, size), dtype=np.float32)

    def _get_paper_patch(self, x, y, w, h):
        """Extracts a patch from the seamless paper texture with wrapping."""
        if not hasattr(self, "_paper_texture") or self._paper_texture is None:
             return np.ones((h, w), dtype=np.float32)
        ts = self._paper_texture_size
        tx, ty = int(x) % ts, int(y) % ts
        patch = np.zeros((h, w), dtype=np.float32)
        y_rem, y_c, s_y = h, 0, ty
        while y_rem > 0:
            copy_h = min(y_rem, ts - s_y)
            x_rem, x_c, s_x = w, 0, tx
            while x_rem > 0:
                copy_w = min(x_rem, ts - s_x)
                patch[y_c:y_c+copy_h, x_c:x_c+copy_w] = self._paper_texture[s_y:s_y+copy_h, s_x:s_x+copy_w]
                x_c += copy_w
                s_x = (s_x + copy_w) % ts
                x_rem -= copy_w
            y_c += copy_h
            s_y = (s_y + copy_h) % ts
            y_rem -= copy_h
        return patch

    def _generate_pencil_stamp(self, size, color):
        size = int(max(2, size))
        param_key = (size, color.rgba())
        if self._last_pstamp_key == param_key: return self._last_pstamp
        stamp = QImage(size, size, QImage.Format.Format_ARGB32_Premultiplied)
        stamp.fill(Qt.GlobalColor.transparent)
        painter = QPainter(stamp)
        grad = QRadialGradient(size/2, size/2, size/2)
        grad.setColorAt(0, QColor(color.red(), color.green(), color.blue(), 160)) 
        grad.setColorAt(0.4, QColor(color.red(), color.green(), color.blue(), 80))
        grad.setColorAt(1, QColor(color.red(), color.green(), color.blue(), 0))
        painter.setBrush(QBrush(grad)); painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(0, 0, size, size)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_DestinationIn)
        np.random.seed(size)
        noise = np.random.rand(size, size); lead_mask = (noise > 0.45).astype(np.uint8) * 255
        noise_img = QImage(lead_mask.data, size, size, size, QImage.Format.Format_Grayscale8)
        painter.drawImage(0, 0, noise_img); painter.end()
        np.random.seed(int(time.time() * 1000) % 2**32)
        self._last_pstamp_key = param_key; self._last_pstamp = stamp
        return stamp

    def _generate_pro_watercolor_stamp(self, size, color):
        size = int(max(4, size))
        if size % 2 == 1: size += 1
        noise_sz = max(4, size // 4)
        noise = np.random.rand(noise_sz, noise_sz).astype(np.float32)
        mask = cv2.resize(noise, (size, size), interpolation=cv2.INTER_CUBIC)
        y, x = np.ogrid[:size, :size]; center = size/2
        dist = np.sqrt((x-center)**2 + (y-center)**2) / center
        dist = np.clip(dist + (mask - 0.5) * 0.4, 0, 1)
        fringe = np.exp(-100 * (dist - 0.9)**2) * 0.5
        gran = (mask - 0.5) * 0.2
        alpha_map = np.clip((1.0 - dist**2) * 0.6 + fringe + gran, 0, 1) * (1.0 - np.power(dist, 8.0))
        c_r, c_g, c_b, c_a = color.red(), color.green(), color.blue(), color.alpha()
        alpha_ch = (alpha_map * c_a).astype(np.uint8)
        img = QImage(size, size, QImage.Format.Format_ARGB32_Premultiplied); img.fill(Qt.GlobalColor.transparent)
        ptr = img.bits(); ptr.setsize(size * size * 4); arr = np.frombuffer(ptr, np.uint8).reshape((size, size, 4))
        a_norm = alpha_ch.astype(np.float32)/255.0
        arr[..., 0] = (c_b * a_norm).astype(np.uint8); arr[..., 1] = (c_g * a_norm).astype(np.uint8)
        arr[..., 2] = (c_r * a_norm).astype(np.uint8); arr[..., 3] = alpha_ch
        return img

    def _generate_pro_oil_stamp(self, size, color):
        size = int(max(4, size))
        if size % 2 == 1: size += 1
        noise = np.random.normal(0.5, 0.15, (size, size)).astype(np.float32)
        k_sz = max(3, size // 3); kernel = np.zeros((k_sz, k_sz)); kernel[k_sz//2, :] = 1.0; kernel /= k_sz
        streaks = cv2.filter2D(noise, -1, kernel)
        y, x = np.ogrid[:size, :size]; center = size/2
        dist_sq = ((x-center)**2/(center**2)) + ((y-center)**2/(center*0.8)**2)
        body = np.where(dist_sq < 0.95, 1.0, 0.0).astype(np.float32)
        height = streaks * body
        h_pad = np.pad(height, 1, mode='edge')
        dx = h_pad[1:-1, 2:] - h_pad[1:-1, :-2]; dy = h_pad[2:, 1:-1] - h_pad[:-2, 1:-1]
        lighting = (-dx - dy) * 120.0
        c_r, c_g, c_b = color.red(), color.green(), color.blue()
        r_ch, g_ch, b_ch = [np.clip(c + lighting, 0, 255).astype(np.uint8) for c in (c_r, c_g, c_b)]
        alpha_ch = (body * 255).astype(np.uint8)
        img = QImage(size, size, QImage.Format.Format_ARGB32_Premultiplied); img.fill(Qt.GlobalColor.transparent)
        ptr = img.bits(); ptr.setsize(size * size * 4); arr = np.frombuffer(ptr, np.uint8).reshape((size, size, 4))
        a_norm = alpha_ch.astype(np.float32)/255.0
        arr[..., 0] = (b_ch * a_norm).astype(np.uint8); arr[..., 1] = (g_ch * a_norm).astype(np.uint8)
        arr[..., 2] = (r_ch * a_norm).astype(np.uint8); arr[..., 3] = alpha_ch
        return img

    def _generate_bristle_mask(self, size):
        size = int(max(1, size))
        if size % 2 == 1: size += 1 
        center = size / 2.0
        y, x = np.ogrid[:size, :size]
        dist_from_center = np.sqrt((x - center)**2 + ((y - center)/0.7)**2)
        circle_mask = np.power(1.0 - np.clip(dist_from_center / center, 0, 1), 0.5) 
        n_base = cv2.resize(np.random.rand(size//4, size//4).astype(np.float32), (size, size), interpolation=cv2.INTER_CUBIC)
        n_fine = np.random.rand(size, size).astype(np.float32)
        bristles = n_base * 0.7 + n_fine * 0.3
        k_sz = max(5, int(size * 0.3)); kernel = np.zeros((k_sz, k_sz)); kernel[int(k_sz/2), :] = 1.0; kernel /= k_sz 
        bristles = cv2.filter2D(bristles, -1, kernel)
        b_max = np.max(bristles)
        if b_max > 0: bristles /= b_max
        return (np.power(bristles, 2.0) * circle_mask).astype(np.float32)

    def _generate_fast_bristle_texture(self, size):
        small = max(4, size // 4)
        noise = np.random.randint(0, 255, (small, small), dtype=np.uint8)
        return QImage(noise.data, small, small, small, QImage.Format.Format_Grayscale8).scaled(size, size, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)

    def update_brush_cache(self):
        self._cached_stamp = self._get_brush_stamp(self._brush_size, self._brush_color)

    def _get_brush_stamp(self, size, color):
        size = int(max(1, size))
        if size > 1024: size = 1024
        brush_name = getattr(self, "activeBrushName", "Standard")
        hardness = getattr(self, "_brush_hardness", 0.1)
        grain = getattr(self, "_brush_grain", 0.0)
        roundness = getattr(self, "_brush_roundness", 1.0)
        param_key = (size, color.rgba(), hardness, grain, roundness, brush_name)
        if self._brush_texture_params == param_key and self._brush_texture_cache: return self._brush_texture_cache
            
        if brush_name in self._custom_brushes:
            brush_data = self._custom_brushes[brush_name]
            raw_img = brush_data.get("cached_stamp")
            if raw_img and not raw_img.isNull():
                stamp = raw_img.scaled(size, size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                final = QImage(size, size, QImage.Format.Format_ARGB32_Premultiplied); final.fill(Qt.GlobalColor.transparent)
                p = QPainter(final); dx, dy = (size-stamp.width())//2, (size-stamp.height())//2
                p.drawImage(dx, dy, stamp); p.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn); p.fillRect(final.rect(), color); p.end()
                self._brush_texture_cache = final; self._brush_texture_params = param_key; return final

        is_oil = "Oil" in brush_name or "Acrylic" in brush_name
        is_water = ("Water" in brush_name or "Wash" in brush_name) and "Blend" not in brush_name
        if is_oil: img = self._generate_pro_oil_stamp(size, color)
        elif is_water: img = self._generate_pro_watercolor_stamp(size, color)
        else:
            img = QImage(size, size, QImage.Format.Format_ARGB32_Premultiplied); img.fill(Qt.GlobalColor.transparent)
            p = QPainter(img); p.setRenderHint(QPainter.RenderHint.Antialiasing); p.setPen(Qt.PenStyle.NoPen)
            if any(k in brush_name for k in ["Pen", "Ink", "Maru", "G-Pen", "Pluma", "Marker"]):
                p.setBrush(QBrush(color)); p.drawEllipse(0, 0, size, size)
            else:
                seed = sum(ord(c) for c in brush_name) + size; np.random.seed(seed)
                for _ in range(12 + int(grain * 35)):
                    px, py = np.random.normal(size/2, size*0.19), np.random.normal(size/2, size*0.19)
                    ps = np.random.uniform(0.5, max(1.0, size * 0.35)); dist = ((px-size/2)**2 + (py-size/2)**2)**0.5
                    p_alpha = max(0, min(255, int(255 * (1.1 - (dist/(size/1.7))))))
                    c = QColor(color); c.setAlpha(p_alpha); p.setBrush(QBrush(c)); p.drawEllipse(QRectF(px-ps/2, py-ps/2, ps, ps))
                if grain > 0.1:
                    p.setCompositionMode(QPainter.CompositionMode.CompositionMode_DestinationIn)
                    noise = cv2.resize(np.random.randint(0, 255, (size//2+1, size//2+1), dtype=np.uint8), (size, size), interpolation=cv2.INTER_NEAREST)
                    noise = cv2.GaussianBlur(noise, (3, 3), 0); n_mask = np.where(noise > (255 - int(grain * 210)), 255, 110).astype(np.uint8)
                    p.drawImage(0, 0, QImage(n_mask.data, size, size, size, QImage.Format.Format_Grayscale8))
            p.end(); np.random.seed(int(time.time() * 1000) % (2**32))
        self._brush_texture_cache = img; self._brush_texture_params = param_key; return img

    # --- ENGINES ---
    def _draw_brush_dab(self, point, pressure):
        if self._active_layer_index < 0 or self._active_layer_index >= len(self.layers): return
        layer = self.layers[self._active_layer_index]
        if layer.locked: return
        canvas_point = (point - self._view_offset) / self._zoom_level
        rad = max(0.5, (self._brush_size * pressure) / 2.0)
        painter = QPainter(layer.image); painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        if self._current_tool == "eraser": painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_DestinationOut)
        elif layer.alpha_lock: painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceAtop)
        else: painter.setCompositionMode(self._brush_blend_mode)
        grad = QRadialGradient(canvas_point, rad); color = QColor(self._brush_color); color.setAlpha(int(self._brush_opacity * 255))
        h = max(0.05, min(0.95, getattr(self, "_brush_hardness", 0.5)))
        grad.setColorAt(0, color); grad.setColorAt(h, color); grad.setColorAt(1, QColor(0,0,0,0))
        painter.setBrush(QBrush(grad)); painter.setPen(Qt.PenStyle.NoPen); painter.drawEllipse(canvas_point, rad, rad); painter.end()

    def _draw_pencil_line_traditional(self, lp1, lp2, width, color, pressure):
        if not self.layers: return
        painter = QPainter(self.layers[self._active_layer_index].image)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing); painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Multiply)
        diff = lp2 - lp1; dist = (diff.x()**2 + diff.y()**2)**0.5
        step_dist = max(0.4, width * 0.05); steps = int(dist / step_dist) if dist > 0 else 1
        for i in range(steps + 1):
            t = i / steps; pt = lp1 + diff * t
            p_mod = 1.0
            if self._paper_texture is not None:
                try:
                    tx, ty = int(pt.x()) % self._paper_texture_size, int(pt.y()) % self._paper_texture_size
                    p_mod = np.clip((self._paper_texture[ty, tx] - (1.0 - pressure * 0.8)) * 5.0, 0.2, 1.0)
                except: pass
            jitter = (width * 0.02) * (1.1 - pressure); jx, jy = np.random.normal(0, jitter), np.random.normal(0, jitter)
            curr_sz = width * (0.6 + pressure * 0.4); op = (0.15 + pressure * 0.45) * p_mod
            painter.save(); painter.setOpacity(op); painter.translate(pt.x() + jx, pt.y() + jy); painter.rotate(np.random.randint(0, 360))
            painter.drawImage(QRectF(-curr_sz/2, -curr_sz/2, curr_sz, curr_sz), self._generate_pencil_stamp(curr_sz, color)); painter.restore()
        painter.end(); self.update()

    def _draw_inking_line_vector(self, lp1, lp2, width, color, pressure):
        if not self.layers: return
        active_name = self.activeBrushName; painter = QPainter(self.layers[self._active_layer_index].image)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing); painter.setCompositionMode(self._brush_blend_mode)
        painter.setOpacity(self._brush_opacity); painter.setBrush(QBrush(color)); painter.setPen(Qt.PenStyle.NoPen)
        diff = lp2 - lp1; dist = (diff.x()**2 + diff.y()**2)**0.5; steps = int(dist) if dist > 0 else 1
        for i in range(steps + 1):
            t = i / steps; pt = lp1 + diff * t
            curr_sz = width * (pressure**1.5) if "G-Pen" in active_name else (width*0.5)*(0.8+pressure*0.2) if "Maru" in active_name else width*(0.3+pressure*0.7) if pressure < 1.0 else width
            painter.drawEllipse(pt, max(0.5, curr_sz)/2, max(0.5, curr_sz)/2)
        painter.end(); self.update()

    def _draw_textured_line(self, p1, p2, width, color, segment_pressure=1.0):
        active_name = self.activeBrushName; lp1, lp2 = (p1 - self._view_offset) / self._zoom_level, (p2 - self._view_offset) / self._zoom_level
        is_pencil = any(k in active_name.lower() or k in self._current_tool.lower() for k in ["pencil", "lapiz", "charcoal", "hb", "6b", "graphite"])
        if is_pencil: self._draw_pencil_line_traditional(lp1, lp2, width, color, segment_pressure); return
        is_pen = any(k in active_name.lower() or k in self._current_tool.lower() for k in ["ink", "maru", "g-pen", "pluma", "marker", "entintado"]) or "pen" in active_name.lower() or "pen" in self._current_tool.lower()
        if is_pen: self._draw_inking_line_vector(lp1, lp2, width, color, segment_pressure); return
        
        # NATIVE PING-PONG ENGINE
        if getattr(self, "HAS_NATIVE_RENDER", False) and getattr(self, "_native_initialized", False):
            stamp = self._get_brush_stamp(int(self._brush_size), color)
            param_key = (self._brush_size, color.rgba(), self._brush_grain, self._brush_hardness, self._current_tool)
            if getattr(self, '_last_native_stamp_params', None) != param_key:
                 qimg = stamp.convertToFormat(QImage.Format.Format_RGBA8888); ptr = qimg.constBits(); ptr.setsize(qimg.sizeInBytes())
                 self._stroke_renderer.setBrushTip(bytes(ptr), qimg.width(), qimg.height()); self._last_native_stamp_params = param_key
            diff = lp2 - lp1; dist = (diff.x()**2 + diff.y()**2)**0.5
            is_wet = (self._brush_diffusion > 0.1) or ("Water" in active_name) or (self._current_tool == "water")
            is_oil = "Oil" in active_name or "Acrylic" in active_name
            s_dist = max(2.0, width * 0.08) if is_wet else max(1.0, width * 0.02) if is_oil else max(0.5, width * (0.1 if width >= 5 else 0.2))
            steps = int(dist / s_dist) if dist > 0 else 1
            self._native_renderer.beginFrame(); self._stroke_renderer.beginFrame(self._canvas_width, self._canvas_height)
            c_vec = [color.redF(), color.greenF(), color.blueF(), self._brush_opacity]
            for i in range(steps + 1):
                t = i / steps; pt = lp1 + diff * t; p = segment_pressure
                if steps > 5:
                    if i < 3: p *= (i / 3.0)
                    if (steps - i) < 3: p *= ((steps - i) / 3.0)
                self._native_renderer.swapBuffers()
                self._stroke_renderer.drawDabPingPong(pt.x(), pt.y(), width, self._current_cursor_rotation, c_vec, self._brush_hardness, p, 1, self._native_renderer.getSourceTexture(), 0)
            self._stroke_renderer.endFrame(); self._native_renderer.endFrame(); self._sync_active_layer_from_native(); self.update(); return

        # SOFTWARE FALLBACK
        active_layer = self.layers[self._active_layer_index]; painter = QPainter(active_layer.image)
        res = self._draw_textured_line_software_fallback(painter, lp1, lp2, width, color, segment_pressure); painter.end()

    def _draw_textured_line_software_fallback(self, painter, p1, p2, width, color, pressure=1.0):
        if not self.layers or self._active_layer_index >= len(self.layers): return
        diff = p2 - p1
        dist = (diff.x()**2 + diff.y()**2)**0.5
        
        # If distance is near zero (single tap), draw one dab and return
        if dist < 0.1:
            f_op = self._brush_opacity * pressure
            dab_size = int(max(1, width))
            painter.save()
            painter.translate(p1.x(), p1.y())
            painter.setOpacity(f_op)
            s_w, s_h = dab_size, int(dab_size * getattr(self, "_brush_roundness", 1.0))
            painter.drawImage(QRectF(-s_w/2, -s_h/2, s_w, s_h), self._get_brush_stamp(dab_size, color))
            painter.restore()
            return

        spacing = getattr(self, "_brush_spacing", 0.1); active_name = self.activeBrushName
        is_wet = (self._brush_diffusion > 0.1) or ("Water" in active_name) or (self._current_tool == "water")
        is_oil = "Oil" in active_name or "Acrylic" in active_name
        s_dist = max(2.0, width * (0.08 if width > 60 else 0.06)) if is_wet else max(1.0, width * (0.03 if width > 100 else 0.015)) if is_oil else 1.0 if any(k in active_name for k in ["Pen", "Ink", "Maru", "G-Pen", "Pluma", "Marker"]) else max(0.5, width * spacing)
        total_dist = self._spacing_residue + dist
        if total_dist < s_dist: self._spacing_residue = total_dist; return
        limit = 15 if width > 300 else 40 if width > 150 else 100 if width > 50 else 300
        steps = min(int(total_dist / s_dist), limit); self._spacing_residue = total_dist % s_dist; t_start = time.time(); dab_size = int(max(1, width))
        for i in range(steps):
            if time.time() - t_start > 0.1: break 
            t = np.clip(((i + 1) * s_dist - self._spacing_residue) / dist, 0.0, 1.0); pt = p1 + diff * t
            if is_wet:
                try:
                    dx, dy = int(pt.x() - dab_size/2), int(pt.y() - dab_size/2)
                    d_rect = QRect(dx, dy, dab_size, dab_size).intersected(QRect(0, 0, self._canvas_width, self._canvas_height))
                    if d_rect.width() < 2 or d_rect.height() < 2: continue
                    img_ref = self.layers[self._active_layer_index].image; canvas_patch = img_ref.copy(d_rect).convertToFormat(QImage.Format.Format_ARGB32_Premultiplied)
                    w, h = d_rect.width(), d_rect.height(); composite = QImage(w, h, QImage.Format.Format_ARGB32_Premultiplied); composite.fill(Qt.GlobalColor.transparent)
                    cp = QPainter(composite); p_bits = canvas_patch.bits(); p_bits.setsize(h * w * 4); arr = np.frombuffer(p_bits, np.uint8).reshape((h, w, 4))
                    if np.max(arr) > 0:
                         blur_k = max(3, int(width * 0.1) | 1)
                         if blur_k > 31: blur_k = 31 
                         blurred = QImage(cv2.GaussianBlur(arr, (blur_k, blur_k), 0).data, w, h, w * 4, QImage.Format.Format_ARGB32_Premultiplied).copy()
                         cp.drawImage(0, 0, blurred); cp.setCompositionMode(QPainter.CompositionMode.CompositionMode_DestinationIn)
                         cp.drawImage(0, 0, self._get_brush_stamp(w, QColor(255, 255, 255)))
                    if "Blend" not in active_name:
                         cp.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver); cp.setOpacity(0.35) 
                         cp.drawImage(0, 0, self._get_brush_stamp(w, self._brush_color))
                    cp.end(); painter.save(); painter.setOpacity(min(1.0, self._brush_opacity * pressure * 0.2)); painter.drawImage(d_rect.topLeft(), composite); painter.restore()
                    if self._current_tool == "water": continue
                except: pass
            elif is_oil:
                s_pt = QPoint(int(pt.x()), int(pt.y())); d_color = color; self._paint_load = max(0.1, self._paint_load - 0.001)
                if 0 <= s_pt.x() < self._canvas_width and 0 <= s_pt.y() < self._canvas_height:
                    cv = self.layers[self._active_layer_index].image.pixelColor(s_pt)
                    if cv.alpha() > 20: d_color = self._mix_colors_fresco(d_color, cv, 0.4 * (1.1 - self._paint_load))
                painter.save(); painter.translate(pt.x(), pt.y()); painter.setOpacity((self._brush_opacity * pressure) * (self._paint_load * 0.8 + 0.2))
                painter.rotate(math.degrees(math.atan2(diff.y(), diff.x())) + np.random.uniform(-5, 5)); painter.drawImage(QRectF(-dab_size/2, -dab_size/2, dab_size, dab_size), self._get_brush_stamp(dab_size, d_color)); painter.restore()
            else:
                f_op = self._brush_opacity * pressure; jx, jy = 0, 0
                if self._brush_grain > 0.1: j_amt = width * 0.05; jx, jy = np.random.uniform(-j_amt, j_amt), np.random.uniform(-j_amt, j_amt)
                painter.save(); painter.translate(pt.x() + jx, pt.y() + jy); painter.setOpacity(f_op); painter.setCompositionMode(self._brush_blend_mode)
                s_w, s_h = dab_size, int(dab_size * getattr(self, "_brush_roundness", 1.0))
                painter.drawImage(QRectF(-s_w/2, -s_h/2, s_w, s_h), self._get_brush_stamp(dab_size, color)); painter.restore()

    @pyqtSlot(str, result=int)
    def importABR(self, file_url):
        path = QUrl(file_url).toLocalFile() if "://" in file_url else file_url
        if not os.path.exists(path): return 0
        try:
            if not globals().get('HAS_PY_ABR', False): return 0
            parser = getattr(self, "PyABRParser", None)
            if not parser: return 0
            res = parser.parse(path)
            if not hasattr(res, 'brushes'): return 0
            extracted = 0
            for i, b in enumerate(res.brushes):
                name = str(b.name) if b.name else f"Brush {i+1}"
                fname = name
                cnt = 1
                while fname in self._custom_brushes:
                    fname = f"{name} ({cnt})"
                    cnt += 1
                tip = b.get_image()
                if tip:
                    from PIL import Image, ImageOps, ImageStat
                    if tip.mode == 'RGBA':
                        mask = tip.split()[-1]
                    else:
                        mask = tip.convert("L")
                        if ImageStat.Stat(mask).mean[0] > 128:
                            mask = ImageOps.invert(mask)
                    mask = ImageOps.autocontrast(mask, cutoff=1)
                    new = Image.new("RGBA", mask.size, (255, 255, 255, 0))
                    new.putalpha(mask)
                    qimg = QImage(new.tobytes("raw", "RGBA"), new.width, new.height, QImage.Format.Format_RGBA8888).copy()
                    sp = max(0.02, min(1.0, b.spacing/100.0 if b.spacing > 1.0 else b.spacing))
                    self._custom_brushes[fname] = {"is_custom": True, "category": os.path.basename(path).replace(".abr", ""), "size": getattr(b,'size',100), "opacity": 1.0, "hardness": 0.8, "spacing": sp, "cached_stamp": qimg}
                    extracted += 1
            if hasattr(self, "_update_available_brushes"): self._update_available_brushes()
            return extracted
        except Exception as e:
            print(f"ABR Import Error: {e}")
            return 0

    def loadBrushTip(self, name):
        if name in self._custom_brushes:
            b = self._custom_brushes[name]
            if "cached_stamp" in b:
                self._current_brush_name = name
                self.brushSize = b.get("size", 50)
                self.brushSpacing = b.get("spacing", 0.1)
                self.brushOpacity = b.get("opacity", 1.0)
                self.brushHardness = b.get("hardness", 0.5)
                self.brushColorChanged.emit(self._brush_color.name())

    def _evaporate_wet_map(self):
        """Simulates drying of the canvas over time."""
        if hasattr(self, '_wet_map'):
             # Reduce wetness by 5% every 3 seconds
             self._wet_map *= 0.95
             # Clamp small values to 0 to avoid denormal numbers
             self._wet_map[self._wet_map < 0.01] = 0.0

