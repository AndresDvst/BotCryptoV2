"""
Script para limpiar archivos innecesarios del repositorio.
Ejecutar ANTES de hacer commit para mantener el repo limpio.
"""
import os
import shutil
from pathlib import Path

def cleanup_repository():
    """Limpia archivos y directorios innecesarios"""
    
    print("🧹 Iniciando limpieza del repositorio...")
    print("=" * 60)
    
    # Directorios a eliminar
    directories_to_remove = [
        '__pycache__',
        'utils/__pycache__',
        'config/__pycache__',
        'services/__pycache__',
        'database/__pycache__',  # Agregado database
        'tests/__pycache__',     # Agregado tests
        '.pytest_cache',
        '.mypy_cache',
        'build',
        'dist',
        '*.egg-info'
    ]
    
    # Directorios Opcionales (comentados por seguridad en modo runtime)
    # 'venv',
    # 'logs',
    # 'utils/chrome-win64',
    
    # Archivos a eliminar
    files_to_remove = [
        'tweet_log.json',
        'utils/twitter_login_error_*.html',
        'utils/twitter_login_error_*.png',
        '*.pyc',
        '*.pyo',
        '*.log',
        '*.tmp',
        '*.temp'
    ]
    
    removed_count = 0
    
    # Eliminar directorios
    for dir_pattern in directories_to_remove:
        for dir_path in Path('.').glob(dir_pattern):
            if dir_path.exists() and dir_path.is_dir():
                try:
                    shutil.rmtree(dir_path)
                    print(f"✅ Eliminado directorio: {dir_path}")
                    removed_count += 1
                except Exception as e:
                    print(f"❌ Error eliminando {dir_path}: {e}")
    
    # Eliminar archivos
    for file_pattern in files_to_remove:
        for file_path in Path('.').rglob(file_pattern):
            if file_path.exists() and file_path.is_file():
                try:
                    file_path.unlink()
                    print(f"✅ Eliminado archivo: {file_path}")
                    removed_count += 1
                except Exception as e:
                    print(f"❌ Error eliminando {file_path}: {e}")
    
    print("=" * 60)
    print(f"🎉 Limpieza completada: {removed_count} elementos eliminados")
    print("\n⚠️  IMPORTANTE:")
    print("   - Verifica que .env NO esté en el repositorio")
    print("   - Asegúrate de tener .gitignore configurado")
    print("   - Revisa 'git status' antes de hacer commit")

if __name__ == "__main__":
    cleanup_repository()
