#!/bin/bash
# Script para subir wetrack-mcp-server a GitHub

REPO_NAME="wetrack-mcp-server"
GITHUB_USER="${GITHUB_USER:-TU_USUARIO}"  # Cambia esto por tu usuario de GitHub

echo "🚀 Subiendo $REPO_NAME a GitHub..."
echo ""

# Renombrar branch a main si es necesario
git branch -M main

# Verificar si ya existe el remote
if git remote get-url origin > /dev/null 2>&1; then
    echo "✅ Remote 'origin' ya existe"
    git remote set-url origin "https://github.com/$GITHUB_USER/$REPO_NAME.git"
else
    echo "➕ Agregando remote 'origin'..."
    git remote add origin "https://github.com/$GITHUB_USER/$REPO_NAME.git"
fi

echo ""
echo "📤 Subiendo código a GitHub..."
echo "   Repositorio: https://github.com/$GITHUB_USER/$REPO_NAME"
echo ""

# Intentar push
if git push -u origin main; then
    echo ""
    echo "✅ ¡Código subido exitosamente!"
    echo "   Ver en: https://github.com/$GITHUB_USER/$REPO_NAME"
else
    echo ""
    echo "❌ Error al subir. Asegúrate de:"
    echo "   1. Haber creado el repositorio en GitHub"
    echo "   2. Tener permisos de escritura"
    echo "   3. Haber configurado GITHUB_USER en el script o como variable de entorno"
    echo ""
    echo "   Para crear el repositorio, ve a: https://github.com/new"
    echo "   Nombre del repositorio: $REPO_NAME"
fi

