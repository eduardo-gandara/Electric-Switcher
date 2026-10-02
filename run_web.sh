#!/bin/bash
# Script para ejecutar Electric Switcher en modo web

cd /home/gandara/Projects/Electric-Switcher

# Activar entorno virtual
source venv/bin/activate

# Crear directorio uploads si no existe
mkdir -p uploads

# Ejecutar servidor Flask
echo "🚀 Iniciando Electric Switcher en modo web..."
echo "📱 Abre tu navegador en: http://localhost:5000"
echo "⏹️  Presiona Ctrl+C para detener el servidor"
echo ""

python3 app.py
