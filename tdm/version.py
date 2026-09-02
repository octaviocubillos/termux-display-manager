"""
Termux Display Manager (TDM) - Información de Versionado
"""

__version__ = "0.0.68"
__version_code__ = 68
MANIFEST_SCHEMA_VERSION = 1

def get_version_info() -> dict:
    return {
        "version": __version__,
        "version_code": __version_code__,
        "manifest_schema": MANIFEST_SCHEMA_VERSION,
        "name": "Termux Display Manager",
        "description": "Display & Server Manager para Android y Termux"
    }
