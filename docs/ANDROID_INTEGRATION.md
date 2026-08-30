# 📱 Integración con Android & Asistente Post-Instalación (Setup Wizard)

Cuando el usuario descarga e instala el **APK de TDM** en su teléfono o tablet, la aplicación incluye un **Asistente de Primera Configuración (Onboarding / Setup Wizard)** para dejar todo listo en menos de 1 minuto sin requerir conocimientos técnicos avanzados.

---

## 🧙‍♂️ Flujo del Asistente Post-Instalación del APK (Setup Wizard)

```
 ┌──────────────────────┐     ┌──────────────────────┐     ┌──────────────────────┐     ┌──────────────────────┐
 │ 1. Detección Termux  │ ──► │ 2. Permiso Comandos  │ ──► │ 3. App Termux:X11    │ ──► │ 4. ¡Listo para Usar! │
 │    (Verificar app)   │     │    (RUN_COMMAND)     │     │    (Instalar visor)  │     │    (Ir al Panel)     │
 └──────────────────────┘     └──────────────────────┘     └──────────────────────┘     └──────────────────────┘
```

---

### Paso 1: Verificación de Termux
* **¿Qué hace la App?**
  Comprueba si el paquete `com.termux` está instalado en Android.
* **Si no está instalado:** Muestra un botón directo para descargar la versión oficial de Termux (F-Droid / GitHub).
* **Si está instalado:** Muestra un check verde `✓ Termux detectado correctamente`.

---

### Paso 2: Permiso de Ejecución (`com.termux.permission.RUN_COMMAND`)
* **¿Qué hace la App?**
  Solicita al sistema Android el permiso para que TDM pueda encender y apagar servicios en segundo plano dentro de Termux.
* **Configuración automática:**
  Genera la línea `allow-external-apps = true` en `~/.termux/termux.properties` para permitir la comunicación fluida.

---

### Paso 3: Instalación de la App de Pantalla (Termux:X11)
* **¿Qué hace la App?**
  Comprueba si la app complementaria `com.termux.x11` está instalada en el dispositivo.
* **Si no está:** Ofrece un botón de descarga rápida del APK oficial de Termux:X11.
* **Opciones alternativas:** Si el usuario no desea instalar Termux:X11, puede marcar *"Usar noVNC Web integrado"* y no necesita instalar ninguna app extra.

---

### Paso 4: Inicialización y Prueba de Conexión
* La app envía una orden de prueba a Termux para iniciar el servicio en `http://127.0.0.1:9050`.
* Una vez recibido el `HTTP 200 OK`, el asistente se cierra automáticamente y da paso al **Panel Principal de Pantallas**.
