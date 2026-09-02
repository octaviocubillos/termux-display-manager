import os
import shutil
import socket
import asyncio
import subprocess
from typing import Dict, Any, Optional
from pathlib import Path
from tdm.config import IS_TERMUX, PREFIX
from tdm.constants import PORT_PULSEAUDIO
from tdm.logger import log_event

class AudioManager:
    def __init__(self, port: int = PORT_PULSEAUDIO):
        self.port = port
        self.server_process: Optional[asyncio.subprocess.Process] = None

    def is_pulseaudio_installed(self) -> bool:
        """Verifica si pulseaudio o pactl estan instalados."""
        return bool(shutil.which("pulseaudio") or shutil.which("pactl"))

    def is_port_open(self) -> bool:
        """Comprueba si el puerto TCP de PulseAudio esta escuchando."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.3)
                return s.connect_ex(("127.0.0.1", self.port)) == 0
        except Exception:
            return False

    async def start_audio_server(self) -> bool:
        """Inicia el servidor de audio PulseAudio con modulo TCP y salida nativa."""
        pulse_bin = shutil.which("pulseaudio")
        if not pulse_bin:
            log_event("audio", "PulseAudio no esta instalado, omitiendo servidor de audio.")
            return False

        # Si ya esta escuchando en el puerto TCP correspondiente, no es necesario reiniciar
        if self.is_port_open():
            log_event("audio", f"Servidor PulseAudio ya activo y escuchando en 127.0.0.1:{self.port}")
            return True

        # Detener instancias previas colgadas sin soporte TCP
        await self.stop_audio_server()

        log_event("audio", f"Iniciando servidor de sonido PulseAudio en puerto TCP {self.port}...")
        
        args = [
            pulse_bin,
            "--start",
            f"--load=module-native-protocol-tcp auth-ip-acl=127.0.0.1 auth-anonymous=1 port={self.port}",
            "--exit-idle-time=-1"
        ]

        if IS_TERMUX:
            # En Android/Termux cargar salida OpenSL ES para altavoces del telefono
            args.insert(2, "--load=module-sles-sink")

        try:
            res = subprocess.run(args, capture_output=True, text=True, timeout=5)
            await asyncio.sleep(0.5)

            if self.is_port_open():
                log_event("audio", f"✅ PulseAudio activo en 127.0.0.1:{self.port} (Salida nativa conectada)")
                # Establecer volumen inicial del sink al 100% en software
                if shutil.which("pactl"):
                    subprocess.run(
                        ["pactl", "-s", f"127.0.0.1:{self.port}", "set-sink-volume", "@DEFAULT_SINK@", "100%"],
                        capture_output=True, timeout=1
                    )
                return True
            else:
                log_event("audio", f"Aviso: PulseAudio inicio pero puerto {self.port} no respondio: {res.stderr}", level="WARNING")
                return False
        except Exception as e:
            log_event("audio", f"Error iniciando PulseAudio: {e}", level="ERROR")
            return False

    async def stop_audio_server(self):
        """Detiene limpiamente el demonio de PulseAudio."""
        try:
            subprocess.run(["pulseaudio", "--kill"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=2)
        except Exception:
            pass
        try:
            subprocess.run(["pkill", "-9", "-x", "pulseaudio"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass

audio_manager = AudioManager()
