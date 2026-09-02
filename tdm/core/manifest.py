import sqlite3
import time
import subprocess
import shutil
from contextlib import contextmanager
from pathlib import Path
from typing import List, Dict, Any, Optional
from tdm.config import TDM_DIR
from tdm.version import __version__, MANIFEST_SCHEMA_VERSION

MANIFEST_DB_PATH = TDM_DIR / "manifest.sqlite3"

class ManifestLedger:
    """Registro SQLite de auditoría de paquetes y archivos instalados exclusivamente por TDM."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or MANIFEST_DB_PATH
        self._init_db()

    @contextmanager
    def _get_connection(self):
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init_db(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS manifest_meta (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tdm_installed_packages (
                    package_name TEXT PRIMARY KEY,
                    component TEXT,
                    installed_at REAL,
                    tdm_version TEXT
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tdm_installed_files (
                    file_path TEXT PRIMARY KEY,
                    component TEXT,
                    created_at REAL
                )
            """)
            cursor.execute(
                "INSERT OR REPLACE INTO manifest_meta (key, value) VALUES (?, ?)",
                ("schema_version", str(MANIFEST_SCHEMA_VERSION))
            )
            cursor.execute(
                "INSERT OR REPLACE INTO manifest_meta (key, value) VALUES (?, ?)",
                ("tdm_version", __version__)
            )
            conn.commit()

    @staticmethod
    def is_package_installed_in_system(package_name: str) -> bool:
        """Comprueba si un paquete ya está instalado en el sistema antes de que TDM lo instale."""
        try:
            res = subprocess.run(
                ["dpkg-query", "-W", "-f=${Status}", package_name],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            return "install ok installed" in res.stdout
        except Exception:
            return False

    def record_package_if_new(self, package_name: str, component: str = "general") -> bool:
        """Registra un paquete como instalado por TDM sólo si NO existía previamente en el sistema."""
        already_present = self.is_package_installed_in_system(package_name)
        if not already_present:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT OR IGNORE INTO tdm_installed_packages (package_name, component, installed_at, tdm_version) VALUES (?, ?, ?, ?)",
                    (package_name, component, time.time(), __version__)
                )
                conn.commit()
            return True
        return False

    def record_packages_if_new(self, packages: List[str], component: str = "general"):
        for pkg in packages:
            self.record_package_if_new(pkg.strip(), component)

    def get_tdm_installed_packages(self) -> List[Dict[str, Any]]:
        """Devuelve únicamente los paquetes que fueron instalados mediante TDM."""
        if not self.db_path.exists():
            return []
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM tdm_installed_packages ORDER BY installed_at ASC")
            return [dict(row) for row in cursor.fetchall()]

    def record_file(self, file_path: str, component: str = "general"):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR REPLACE INTO tdm_installed_files (file_path, component, created_at) VALUES (?, ?, ?)",
                (str(file_path), component, time.time())
            )
            conn.commit()

    def get_tdm_installed_files(self) -> List[str]:
        if not self.db_path.exists():
            return []
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT file_path FROM tdm_installed_files")
            return [row["file_path"] for row in cursor.fetchall()]

    def clear(self):
        if self.db_path.exists():
            try:
                self.db_path.unlink()
            except Exception:
                pass

manifest_ledger = ManifestLedger()
