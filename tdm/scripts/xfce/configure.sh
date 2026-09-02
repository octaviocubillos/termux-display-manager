#!/usr/bin/env bash
# ==============================================================================
# 🐭 [TDM] Configuración nativa para XFCE4 (con Batería y Audio PulseAudio)
# ==============================================================================
PREFIX_PATH="${PREFIX:-/data/data/com.termux/files/usr}"
HOME_DIR="${HOME:-/data/data/com.termux/files/home}"
CONFIG_DIR="$HOME_DIR/.config/xfce4/xfconf/xfce-perchannel-xml"
PANEL_XML="$CONFIG_DIR/xfce4-panel.xml"

# 1. Crear configuración de panel con plugin de batería y pulseaudio si no existe
mkdir -p "$CONFIG_DIR"
if [ ! -f "$PANEL_XML" ]; then
    cat << 'XML_EOF' > "$PANEL_XML"
<?xml version="1.0" encoding="UTF-8"?>
<channel name="xfce4-panel" version="1.0">
  <property name="configver" type="int" value="2"/>
  <property name="panels" type="array">
    <value type="int" value="1"/>
    <property name="dark-mode" type="bool" value="true"/>
    <property name="panel-1" type="empty">
      <property name="position" type="string" value="p=6;x=0;y=0"/>
      <property name="length" type="uint" value="100"/>
      <property name="position-locked" type="bool" value="true"/>
      <property name="icon-size" type="uint" value="16"/>
      <property name="size" type="uint" value="26"/>
      <property name="plugin-ids" type="array">
        <value type="int" value="1"/>
        <value type="int" value="2"/>
        <value type="int" value="3"/>
        <value type="int" value="4"/>
        <value type="int" value="5"/>
        <value type="int" value="6"/>
        <value type="int" value="19"/>
        <value type="int" value="20"/>
        <value type="int" value="7"/>
        <value type="int" value="8"/>
        <value type="int" value="9"/>
        <value type="int" value="10"/>
      </property>
    </property>
  </property>
  <property name="plugins" type="empty">
    <property name="plugin-1" type="string" value="applicationsmenu"/>
    <property name="plugin-2" type="string" value="tasklist">
      <property name="grouping" type="uint" value="1"/>
    </property>
    <property name="plugin-3" type="string" value="separator">
      <property name="expand" type="bool" value="true"/>
      <property name="style" type="uint" value="0"/>
    </property>
    <property name="plugin-4" type="string" value="pager"/>
    <property name="plugin-5" type="string" value="separator">
        <property name="style" type="uint" value="0"/>
    </property>
    <property name="plugin-6" type="string" value="systray">
        <property name="square-icons" type="bool" value="true"/>
    </property>
    <property name="plugin-19" type="string" value="pulseaudio">
      <property name="enable-keyboard-shortcuts" type="bool" value="true"/>
      <property name="show-notifications" type="bool" value="true"/>
    </property>
    <property name="plugin-20" type="string" value="battery">
      <property name="display-percentage" type="bool" value="true"/>
      <property name="display-time" type="bool" value="false"/>
    </property>
    <property name="plugin-7" type="string" value="separator">
      <property name="style" type="uint" value="0"/>
    </property>
    <property name="plugin-8" type="string" value="clock"/>
    <property name="plugin-9" type="string" value="separator">
      <property name="style" type="uint" value="0"/>
    </property>
    <property name="plugin-10" type="string" value="actions"/>
  </property>
</channel>
XML_EOF
fi

# 2. Configurar Logo de TDM en menú de aplicaciones
LOGO_PATH="$PREFIX_PATH/opt/termux-display-manager/tdm/web/assets/logos/xfce.svg"
if [ ! -f "$LOGO_PATH" ]; then LOGO_PATH="$HOME_DIR/.tdm/assets/xfce.svg"; fi

if command -v xfconf-query >/dev/null 2>&1; then
    (sleep 1 && \
     if [ -f "$LOGO_PATH" ]; then xfconf-query -c xfce4-panel -p /plugins/plugin-1/button-icon -s "$LOGO_PATH" --create -t string >/dev/null 2>&1 || true; fi) &
fi
