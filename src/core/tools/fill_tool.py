from PyQt6.QtCore import pyqtSlot, pyqtProperty, pyqtSignal
from PyQt6.QtGui import QImage, QColor
import cv2
import numpy as np

class FillToolMixin:
    """
    Mixin for QCanvasItem to handle Fill Tool logic (Bucket Fill, Lasso Fill).
    Expects 'self' to be QCanvasItem.
    """
    
    def _init_fill_tool(self):
        # Fill Tool State
        self._fill_tolerance = 30
        self._fill_expand = 0 
        self._fill_mode = "bucket" 
        self._fill_sample_all = False
        self._lasso_points = []
    
    # --- DATA ACCESSORS (To be used by QCanvasItem properties) ---
    def get_fill_tolerance(self): return self._fill_tolerance
    def set_fill_tolerance(self, val):
        if self._fill_tolerance != val:
            self._fill_tolerance = val
            self.fillToleranceChanged.emit(val)

    def get_fill_expand(self): return self._fill_expand
    def set_fill_expand(self, val):
        if self._fill_expand != val:
            self._fill_expand = val
            self.fillExpandChanged.emit(val)

    def get_fill_mode(self): return self._fill_mode
    def set_fill_mode(self, val):
        if self._fill_mode != val:
            self._fill_mode = val
            self.fillModeChanged.emit(val)

    def get_fill_sample_all(self): return self._fill_sample_all
    def set_fill_sample_all(self, val):
        if self._fill_sample_all != val:
            self._fill_sample_all = val
            self.fillSampleAllChanged.emit(val)

    # --- ACTION METHODS ---

    @pyqtSlot(float, float, QColor)
    def apply_color_drop(self, x, y, new_color):
        if not self.layers or self._active_layer_index < 0:
            return

        layer = self.layers[self._active_layer_index]
        if layer.locked or not layer.visible: return
        
        # GUARDAR ESTADO PARA DESHACER (CRUCIAL)
        self.save_undo_state()
        
        # 1. TRADUCCIÓN DE COORDENADAS
        if self._zoom_level == 0: self._zoom_level = 1.0
        ix = int((x - self._view_offset.x()) / self._zoom_level)
        iy = int((y - self._view_offset.y()) / self._zoom_level)

        if not (0 <= ix < layer.image.width() and 0 <= iy < layer.image.height()):
            return

        # 2. PREPARACIÓN DE BUFFER
        if layer.image.format() != QImage.Format.Format_ARGB32:
            layer.image = layer.image.convertToFormat(QImage.Format.Format_ARGB32)

        w, h = layer.image.width(), layer.image.height()
        bpl = layer.image.bytesPerLine()
        ptr = layer.image.bits()
        ptr.setsize(layer.image.sizeInBytes())
        
        try:
            # Vista strided segura
            arr_view = np.ndarray(shape=(h, w, 4), dtype=np.uint8, buffer=ptr, strides=(bpl, 4, 1))
            
            # --- LÓGICA ROBUSTA (SIMPLIFICADA) ---
            # Volvemos a lo que funcionaba: Relleno de 3 canales sin máscaras complejas
            
            # 1. Copia de trabajo
            work_img = arr_view.copy()

            # 2. PREPARAR CANALES (Split & Merge)
            b, g, r, a = cv2.split(work_img)
            bgr = cv2.merge([b, g, r])
            
            # 3. MÁSCARA LIMPIA (H+2, W+2)
            mask = np.zeros((h + 2, w + 2), np.uint8)

            # --- SELECTION MASK INTEGRATION (PREMIUM) ---
            # If a selection exists, we block everything OUTSIDE the selection.
            # OpenCV floodFill Mask: 0 = Valid, Non-Zero = Blocked.
            if hasattr(self, "_selection_active") and self._selection_active and hasattr(self, "_selection_mask") and self._selection_mask:
                # 1. Convert QImage Mask to Numpy
                # Mask in QImage: 0=Unselected, 255=Selected
                # We want: 0=Selected (Valid to Fill), 255=Unselected (Blocked)
                
                sel_ptr = self._selection_mask.bits()
                sel_ptr.setsize(self._selection_mask.sizeInBytes())
                
                # Careful with Stride/Format. Mask is Grayscale8 (1 channel)
                # But it might be 32bit aligned. QImage.bytesPerLine() is the truth.
                sel_bpl = self._selection_mask.bytesPerLine()
                
                try:
                    # Raw view of Selection Mask
                    sel_raw = np.ndarray(shape=(h, w), dtype=np.uint8, buffer=sel_ptr, strides=(sel_bpl, 1))
                    
                    # 2. Invert logic for floodFill mask
                    # FloodFill needs: 0 to paint, >0 to block.
                    # Our Mask: 255 is selection (open), 0 is protected.
                    # So we need to invert: 255->0, 0->255.
                    # Using bitwise_not or just 255 - mask.
                    inverted_sel = cv2.bitwise_not(sel_raw) # Now 255=Blocked, 0=Open
                    
                    # 3. Insert into the Center of the padded mask (1:-1, 1:-1)
                    mask[1:-1, 1:-1] = inverted_sel
                    
                except Exception as me:
                    print(f"Mask integration error: {me}")
                    # Fallback to no mask if error
            
            # 4. EJECUTAR FLOODFILL
            target_bgr = (new_color.blue(), new_color.green(), new_color.red())
            
            # Use Dynamic Tolerance from Settings
            t = self._fill_tolerance
            tolerance = (t, t, t)
            
            # Flags: Connectivity 4 | FIXED_RANGE
            num_filled, _, mask, _ = cv2.floodFill(
                bgr, mask, (ix, iy), target_bgr,
                loDiff=tolerance, upDiff=tolerance,
                flags=4 | cv2.FLOODFILL_FIXED_RANGE
            )

            print(f"Relleno Básico: {num_filled} px")
            
            # 6. ACTUALIZAR ALPHA
            # Recortamos la máscara resultante para ver dónde pintó
            # Nota: dilated_edges (255) ya estaba en la máscara. floodFill pone 1s en lo nuevo.
            fill_mask = mask[1:-1, 1:-1]
            
            # Detectar dónde pintó floodFill (valor 1)
            # Ojo: Si la máscara original tenía 255, floodFill evita esas zonas.
            newly_filled = (fill_mask == 1)
            
            # Hacer opaco lo recién pintado
            a[newly_filled] = 255
            
            # 7. RECONSTRUIR
            final_bgra = cv2.merge([bgr[:,:,0], bgr[:,:,1], bgr[:,:,2], a])
            arr_view[:] = final_bgra
            
            self.update()
            self.layersChanged.emit(self.getLayersList())
            print(f"Relleno inteligente (Gap Closing) en ({ix},{iy})")
            
        except Exception as e:
            print(f"CRITICAL ERROR en ColorDrop: {e}")
            import traceback
            traceback.print_exc()

    def apply_lasso_fill(self):
        """Fills the polygon defined by self._lasso_points."""
        if not self.layers or self._active_layer_index < 0: return
        if not self._lasso_points or len(self._lasso_points) < 3: return
        
        layer = self.layers[self._active_layer_index]
        if layer.locked or not layer.visible: return
        self.save_undo_state()

        # 1. Convert Screen Points -> Canvas Pixels
        # Logic: P_img = (P_screen - Offset) / Zoom
        poly_pts = []
        xo = self._view_offset.x()
        yo = self._view_offset.y()
        z = self._zoom_level if self._zoom_level > 0 else 1.0

        for p in self._lasso_points:
             ix = int((p.x() - xo) / z)
             iy = int((p.y() - yo) / z)
             poly_pts.append([ix, iy])

        # Convert to numpy format for fillPoly (shape: (1, N, 2) or (N, 2)?)
        # cv2.fillPoly expects list of arrays. Each array is point set.
        pts = np.array(poly_pts, np.int32)
        pts = pts.reshape((-1, 1, 2))

        # 2. Prepare Image
        if layer.image.format() != QImage.Format.Format_ARGB32:
             layer.image = layer.image.convertToFormat(QImage.Format.Format_ARGB32)
        
        w, h = layer.image.width(), layer.image.height()
        bpl = layer.image.bytesPerLine()
        ptr = layer.image.bits()
        ptr.setsize(layer.image.sizeInBytes())

        try:
             # 3. Secure Memory Access
             arr_view = np.ndarray(shape=(h, w, 4), dtype=np.uint8, buffer=ptr, strides=(bpl, 4, 1))
             work_img = arr_view.copy()

             # 4. Split Channels
             b, g, r, a = cv2.split(work_img)
             bgr = cv2.merge([b, g, r])

             # 5. Fill Poly
             # Color
             c = self._brush_color # Use primary color
             target_bgr = (c.blue(), c.green(), c.red())
             
             # Fill color channel
             cv2.fillPoly(bgr, [pts], target_bgr)
             
             # Fill Alpha channel (Make Opaque)
             cv2.fillPoly(a, [pts], 255)

             # 6. Reconstruct
             final_bgra = cv2.merge([bgr[:,:,0], bgr[:,:,1], bgr[:,:,2], a])
             arr_view[:] = final_bgra
             
             self.update()
             # We should emit layersChanged but let's avoid it for perf unless needed for thumbnails
             # self.layersChanged.emit(self.getLayersList()) 
             print(f"Lasso Fill Applied ({len(poly_pts)} pts)")

        except Exception as e:
             print(f"Lasso Fill Error: {e}")
