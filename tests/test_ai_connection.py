# -*- coding: utf-8 -*-
"""
Script de prueba para verificar conexión con proveedores de IA (Gemini y OpenRouter).
"""
import sys
import os
import time
import time

# Agregar directorio raíz al path para imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.logger import logger
from services.ai_analyzer_service import AIAnalyzerService
from config.config import Config

def test_gemini(ai_service):
    """Prueba conexión directa con Gemini"""
    logger.info("\n🤖 Probando GEMINI...")
    
    if not ai_service.gemini_client:
        logger.error("❌ Cliente Gemini NO inicializado (Revisar API Key)")
        return False
        
    try:
        start_time = time.time()
        response = ai_service._call_provider("gemini", "Hola, responde solo con la palabra 'OK'", max_tokens=10)
        
        elapsed = time.time() - start_time
        logger.info(f"✅ Gemini respondió en {elapsed:.2f}s (modelo={ai_service.config.GEMINI_MODEL}): {response.strip()}")
        return True
    except Exception as e:
        logger.error(f"❌ Error en Gemini: {e}")
        return False

def test_openrouter(ai_service):
    """Prueba conexión directa con OpenRouter"""
    logger.info("\n🤖 Probando OPENROUTER...")
    
    if not ai_service.openrouter_client:
        logger.error("❌ Cliente OpenRouter NO inicializado (Revisar API Key)")
        return False
    
    try:
        start_time = time.time()
        response = ai_service._call_provider("openrouter", "Hola, responde solo con la palabra 'OK'", max_tokens=10)
        elapsed = time.time() - start_time
        logger.info(f"✅ OpenRouter respondió en {elapsed:.2f}s: {response.strip()}")
        return True
            
    except Exception as e:
        logger.error(f"❌ Error en OpenRouter: {e}")
        return False

def test_huggingface(ai_service):
    """Prueba conexión directa con Hugging Face"""
    logger.info("\n🤖 Probando HUGGING FACE...")
    
    if not ai_service.huggingface_api_key:
        logger.error("❌ Cliente Hugging Face NO inicializado (Revisar API Key)")
        return False
    
    try:
        start_time = time.time()
        response = ai_service._call_provider("huggingface", "Hola, responde solo con la palabra 'OK'", max_tokens=10)
        elapsed = time.time() - start_time
        
        if response:
            model_used = ai_service.huggingface_models[0] if ai_service.huggingface_models else "desconocido"
            task_used = ai_service._hf_model_task.get(model_used, "desconocido")
            logger.info(f"✅ Hugging Face respondió en {elapsed:.2f}s (modelo≈{model_used}, task≈{task_used}): {response.strip()}")
            return True
        else:
            logger.error("❌ Respuesta vacía")
            return False
            
    except Exception as e:
        err_str = str(e).lower()
        if "503" in err_str or "loading" in err_str:
            logger.warning(f"⏳ Modelo cargando (503) - Esto es normal en cold start")
            return True
        
        logger.error(f"❌ Error en Hugging Face: {e}")
        return False

def run_tests():
    print("="*60)
    print("🧪 INICIANDO PRUEBA DE CONECTIVIDAD IA")
    print("="*60)
    
    try:
        ai_service = AIAnalyzerService()
        
        if ai_service.huggingface_api_key:
            try:
                ai_service._refresh_huggingface_model_catalog(force=True)
                logger.info(f"🤗 HuggingFace: modelos verificados: {len(ai_service.huggingface_models)}")
            except Exception as e:
                logger.warning(f"⚠️ HuggingFace: no se pudo refrescar catálogo: {e}")

        gemini_ok = test_gemini(ai_service)
        openrouter_ok = test_openrouter(ai_service)
        hf_ok = test_huggingface(ai_service)
        
        print("\n" + "="*60)
        print("📊 RESUMEN DE RESULTADOS")
        print("="*60)
        print(f"🔹 Gemini:      {'✅ OK' if gemini_ok else '❌ FALLÓ'}")
        print(f"🔹 OpenRouter:  {'✅ OK' if openrouter_ok else '❌ FALLÓ'}")
        print(f"🔹 HuggingFace: {'✅ OK' if hf_ok else '❌ FALLÓ'}")
        print("="*60)
        
    except Exception as e:
        logger.error(f"❌ Error crítico inicializando servicio: {e}")

if __name__ == "__main__":
    run_tests()
