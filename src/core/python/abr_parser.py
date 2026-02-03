import io
import struct
import re
import sys
from PIL import Image

class ABRParser:
    """
    UNIVERSAL ABR PARSER (V4 - OMNIVORE)
    Soporta:
    1. Modernos (V6+): Minería de PNG.
    2. Intermedios (V2): Minería de Patrones RLE/Raw (32-bit coords).
    3. Ancestrales (V1): Parseo Estructurado (16-bit coords).
    """

    class BrushTip:
        def __init__(self, name, pil_image, spacing=0.1):
            self.name = name
            self.pil_image = pil_image
            self.spacing = spacing
            self.width = pil_image.width
            self.height = pil_image.height
            self.size = max(self.width, self.height)
            
        def get_image(self):
            return self.pil_image

    @staticmethod
    def parse(filepath):
        print(f"\n[ABR_OMNIVORE] Analizando: {filepath}")
        results = ParserResult()
        
        with open(filepath, 'rb') as f:
            data = f.read()

        # ESTRATEGIA 1: MINERÍA DE PNG (La más fiable para pinceles HD)
        if b'\x89PNG' in data:
            print("[ABR] Detectada firma PNG. Ejecutando Modo Moderno...")
            results = ABRParser._parse_modern_png(data)
        
        # ESTRATEGIA 2: BINARIO LEGACY (V1/V2)
        if not results.brushes:
            print("[ABR] No hay PNGs. Analizando estructura binaria...")
            try:
                results = ABRParser._parse_legacy_binary(data)
            except Exception as e:
                print(f"[ABR] Fallo en modo Legacy: {e}")

        # ESTRATEGIA 3: FUERZA BRUTA (Si todo falla, busca cualquier mapa de bits)
        if not results.brushes:
            print("[ABR] Intentando escaneo de fuerza bruta profundo...")
            try:
                # Buscamos cabeceras de profundidad 8 sin importar versión
                results = ABRParser._parse_deep_scan(data)
            except Exception as e:
                print(f"[ABR] Fallo en fuerza bruta: {e}")

        # FALLBACK FINAL (Para que la UI no explote)
        if not results.brushes:
            print("[ABR] (!) Archivo ilegible.")
            # Crear pincel de error
            diag_img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
            from PIL import ImageDraw
            draw = ImageDraw.Draw(diag_img)
            draw.text((10, 25), "?", fill=(255,0,0,255))
            results.brushes.append(ABRParser.BrushTip("Error", diag_img))

        print(f"[ABR] Total cargado: {len(results.brushes)}")
        return results

    # =========================================================================
    #  MODO 1: MODERNO (PNG)
    # =========================================================================
    @staticmethod
    def _parse_modern_png(data):
        res = ParserResult()
        png_sig = b'\x89PNG\r\n\x1a\n'
        offset = 0
        count = 0
        while True:
            start = data.find(png_sig, offset)
            if start == -1: break
            iend = data.find(b'IEND', start)
            if iend == -1: break
            end = iend + 8 
            try:
                pil_img = Image.open(io.BytesIO(data[start:end]))
                pil_img.load()
                name = ABRParser._extract_name_near(data, start)
                if not name: name = f"Brush {count+1}"
                res.brushes.append(ABRParser.BrushTip(name, pil_img))
                count += 1
            except: pass
            offset = end
        return res

    @staticmethod
    def _extract_name_near(data, png_start):
        try:
            chunk = data[max(0, png_start-300):png_start]
            text = chunk.decode('utf-16-be', errors='ignore')
            clean = "".join([c for c in text if c.isprintable() and c.isalnum() or c in ' -_()'])
            matches = re.findall(r'[a-zA-Z0-9\s\-\_\(\)]{3,}', clean)
            if matches: return matches[-1].strip()
        except: pass
        return None

    # =========================================================================
    #  MODO 2: LEGACY ESTRUCTURADO (V1 y V2)
    # =========================================================================
    @staticmethod
    def _parse_legacy_binary(data):
        res = ParserResult()
        stream = io.BytesIO(data)
        
        def read_short(): return struct.unpack('>h', stream.read(2))[0]
        def read_long(): return struct.unpack('>l', stream.read(4))[0]
        
        version = read_short()
        print(f"[ABR] Versión detectada: {version}")
        
        if version == 1:
            # --- PARSEO ABR VERSIÓN 1 (Ancestral) ---
            count = read_short()
            print(f"[ABR] Pinceles V1 declarados: {count}")
            
            for i in range(count):
                try:
                    # Estructura V1: Type(2), Size(4)
                    brush_type = read_short()
                    block_size = read_long()
                    
                    if brush_type == 1: # Computed brush (saltar)
                        stream.seek(block_size, 1)
                    elif brush_type == 2: # Sampled brush
                        # Leer estructura interna
                        start_pos = stream.tell()
                        read_long() # Misc
                        spacing = read_short()
                        
                        # Nombre Pascal String (Length byte + string)
                        name_raw = stream.read(1)
                        if not name_raw: break
                        name_len = ord(name_raw)
                        name = stream.read(name_len).decode('latin-1', errors='ignore')
                        if (name_len + 1) % 2 != 0: stream.read(1) # Padding
                        
                        read_short() # Antialias + misc
                        
                        # COORDENADAS V1 SON SHORTS (2 bytes), NO LONGS
                        top, left, bottom, right = read_short(), read_short(), read_short(), read_short()
                        width = right - left
                        height = bottom - top
                        
                        read_short() # Depth
                        compression_raw = stream.read(1)
                        if not compression_raw: break
                        compression = compression_raw[0] # 0=Raw, 1=RLE
                        
                        # Leer imagen
                        if 0 < width < 4000 and 0 < height < 4000:
                            img_data = ABRParser._read_bitmap(stream, width, height, compression)
                            if img_data:
                                img = Image.frombytes('L', (width, height), bytes(img_data))
                                # Convertir a RGBA
                                bg = Image.new("RGB", (width, height), (255, 255, 255))
                                final = Image.merge("RGBA", (*bg.split(), img))
                                res.brushes.append(ABRParser.BrushTip(name, final, spacing/100.0))
                        
                        # Asegurar que avanzamos al siguiente bloque correctamente
                        end_pos = stream.tell()
                        remaining = (start_pos + block_size) - end_pos
                        if remaining > 0: stream.seek(remaining, 1)
                        
                except Exception as e:
                    print(f"[ABR] Error en bloque V1 {i}: {e}")
                    break

        elif version == 2 or version == 6:
            # Reusamos el deep scan para V2 porque la estructura es demasiado compleja
            # para parsearla secuencialmente sin documentación oficial.
            res = ABRParser._parse_deep_scan(data)
            
        return res

    # =========================================================================
    #  MODO 3: FUERZA BRUTA (DEEP SCAN)
    # =========================================================================
    @staticmethod
    def _parse_deep_scan(data):
        res = ParserResult()
        
        # Buscar firmas de encabezado de imagen:
        # \x00\x08 (Profundidad 8) + \x00 (Raw) O \x01 (RLE)
        # Esto ocurre tanto en V1 como V2
        patterns = [b'\x00\x08\x01', b'\x00\x08\x00']
        
        stream = io.BytesIO(data)
        
        for pattern in patterns:
            offset = 0
            while True:
                loc = data.find(pattern, offset)
                if loc == -1: break
                
                try:
                    # Verificar coordenadas. En V2 son Longs (4 bytes), en V1 son Shorts (2 bytes)
                    # Probamos hipótesis V2 (más común en deep scan)
                    # Bounds están 16 bytes antes: T(4) L(4) B(4) R(4)
                    header_start = loc - 16
                    if header_start >= 0:
                        stream.seek(header_start)
                        t, l, b, r = struct.unpack('>llll', stream.read(16))
                        w, h = r - l, b - t
                        
                        if 0 < w < 2500 and 0 < h < 2500:
                            stream.seek(loc + 3) # Saltar firma
                            compression = pattern[2]
                            img_data = ABRParser._read_bitmap(stream, w, h, compression)
                            
                            if img_data:
                                img = Image.frombytes('L', (w, h), bytes(img_data))
                                bg = Image.new("RGB", (w, h), (255, 255, 255))
                                final = Image.merge("RGBA", (*bg.split(), img))
                                res.brushes.append(ABRParser.BrushTip(f"Scanned Brush {len(res.brushes)+1}", final))
                                offset = loc + len(img_data) # Saltar datos leídos
                                continue
                except: pass
                
                offset = loc + 3
        return res

    @staticmethod
    def _read_bitmap(stream, width, height, compression):
        expected = width * height
        if compression == 0: # Raw
            return stream.read(expected)
        elif compression == 1: # RLE (PackBits)
            rle_data = bytearray()
            # Leemos por filas
            for r in range(height):
                # En ABR V1/V2 suele ser PackBits continuo sin conteo de fila.
                # Intentamos decodificar continuo hasta llenar width.
                row_data = bytearray()
                while len(row_data) < width:
                    try:
                        header_raw = stream.read(1)
                        if not header_raw: break
                        header = ord(header_raw)
                        if header > 127: header -= 256
                        
                        if 0 <= header <= 127:
                            cnt = header + 1
                            row_data.extend(stream.read(cnt))
                        elif -127 <= header <= -1:
                            cnt = -header + 1
                            val = stream.read(1)
                            row_data.extend(val * cnt)
                        # -128 es noop
                    except: break
                rle_data.extend(row_data[:width])
            return rle_data
        return None

class ParserResult:
    def __init__(self):
        self.brushes = []
