# Recomendaciones de Funcionalidades para ArtFlow Studio Pro

Basado en el análisis del código actual, aquí tienes una lista completa de características que elevarían tu aplicación al nivel de estándares profesionales como Clip Studio Paint o Procreate.

## 1. Herramientas Esenciales (Alta Prioridad)
Actualmente tienes Pincel, Borrador y Mano. Faltan las herramientas de manipulación básicas:

- [ ] **Herramientas de Selección**: 
  - *Lazo (Alzada)*, *Rectángulo* y *Varita Mágica*.
  - Permitir mover/copiar lo seleccionado.
- [ ] **Herramienta de Transformación**:
  - Escalar, Rotar y Distorsionar capas o selecciones.
- [ ] **Cubo de Pintura (Fill)**:
  - Relleno solido con tolerancia (ya tienes lógica en `fill_tool.py`, falta UI robusta).
  - Relleno de degradado (Lineal/Radial).
- [ ] **Formas Geométricas**:
  - Línea recta, Rectángulo, Elipse.

## 2. Gestión Avanzada de Capas
El sistema de capas actual es funcional pero básico.

- [ ] **Modos de Fusión (Blending Modes)**:
  - UI para cambiar modo de capa (Multiplicar, Pantalla, Superponer, etc.).
- [ ] **Bloqueo Alfa (Alpha Lock)**:
  - Un botón en la capa para "Bloquear transparencia" (solo pintar donde ya hay píxeles).
- [ ] **Máscaras de Capa**:
  - Pintar con blanco/negro para ocultar partes sin borrar.
- [ ] **Grupos de Capas**:
  - Carpetas para organizar capas.
- [ ] **Máscaras de Recorte (Clipping Masks)**:
  - Que una capa se recorte a la forma de la de abajo.

## 3. Ajustes y Filtros (Edición de Imagen)
Para que no solo sea dibujo, sino edición.

- [ ] **Ajustes de Color**:
  - Tono/Saturación/Luminosidad (HSV).
  - Brillo y Contraste.
  - Curvas o Niveles.
- [ ] **Filtros**:
  - Desenfoque Gaussiano (Gaussian Blur).
  - Ruido (Noise) para texturas.

## 4. Ayudas de Dibujo (Canvas Aids)
Funciones que ayudan al artista a dibujar mejor.

- [ ] **Voltear Lienzo (Flip Canvas)**:
  - Horizontalmente (Espejo) para ver errores de proporción. Atajo rápido (ej. tecla 'M').
- [ ] **Simetría**:
  - Ejes Y/X o Radial (Mandala). Todo lo que dibujas se repite.
- [ ] **Estabilizador Avanzado**:
  - UI para ajustar el "Streamline" (suavizado de trazo) en tiempo real en la barra superior.

## 5. Flujo de Trabajo y Sistema
- [ ] **Ventana de Referencia**:
  - Un panel flotante pequeño donde cargar una imagen de referencia.
- [ ] **Diálogo de Exportación**:
  - Opciones para PNG, JPG, PSD.
  - Redimensionar al exportar.
- [ ] **Recuperación Automática**:
  - Sistema de Auto-Guardado robusto en caso de cierre inesperado.

## Resumen de Prioridades Sugeridas
1.  **Herramientas de Selección y Transformación** (Vital para corregir dibujos).
2.  **Modos de Fusión y Bloqueo Alfa** (Vital para sombreado/iluminación).
3.  **Voltear Lienzo y Estabilizador** (Mejoran la experiencia de dibujo inmediata).
