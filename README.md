# HematologIA

Aplicación de escritorio para la identificación automatizada de células sanguíneas (leucocitos maduros e inmaduros) en imágenes de frotis sanguíneo capturadas con un microscopio Swift Cam SCA-EA05. Pensada para uso en laboratorios de hematología clínica.

> **Estado:** Fase 1 — Interfaz funcional sin IA. La integración del modelo (YOLOv6 / EfficientNet-B3) se hará en Fase 2.

## Stack

- **Python 3.10**
- **PySide6** (Qt para UI)
- **SQLite 3** (base de datos local)
- **bcrypt** (hashing de passwords)
- **Sistema operativo objetivo:** Windows

## Roles

- **Jefe de Laboratorio** — gestión completa (operarios, todos los estudios, configuración).
- **Personal** — operativo (creación de estudios, captura de imágenes, generación de reportes).

## Setup

```bash
# Crear y activar entorno virtual con conda
conda create -n hematologia python=3.10 -y
conda activate hematologia

# Instalar dependencias
pip install -r requirements.txt

# Inicializar la base de datos (solo la primera vez o para resetear)
python scripts/init_db.py

# Para regenerar la DB desde cero borrando la existente
python scripts/init_db.py --reset

# Correr la aplicación
python main.py
```

## Usuarios de prueba

Después de correr `init_db.py`, podés iniciar sesión con:

| Usuario     | Password       | Rol      |
|-------------|----------------|----------|
| `jefe`      | `jefe123`      | jefe     |
| `personal`  | `personal123`  | personal |

> Estos usuarios son solo para desarrollo. Los hashes se generan en runtime; no se commitean al repo.

## Estructura

Ver `CLAUDE.md` (sección 4) para la estructura completa de directorios y la guía de convenciones.

## Logs

Los logs se escriben en `logs/hematologia.log` con rotación (máx. 5 MB por archivo, 3 archivos de backup). No se versiona.
