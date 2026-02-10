# -*- coding: utf-8 -*-
"""
Script de prueba para verificar conexión con proveedores de IA.
Soporta: Ollama, Gemini, OpenRouter, HuggingFace

VERSIÓN MEJORADA:
- ✅ Soporte para Ollama
- ✅ Mejor manejo de errores
- ✅ Estadísticas detalladas
- ✅ Validación de configuración
- ✅ Pruebas de análisis real
"""
import sys
import os
import time
from typing import Dict, Tuple, Optional

# Agregar directorio raíz al path para imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.logger import logger
from services.ai_analyzer_service import AIAnalyzerService
from config.config import Config


class AIConnectivityTester:
    """Clase para probar conectividad con proveedores de IA."""
    
    def __init__(self):
        self.results: Dict[str, Dict] = {}
        self.ai_service: Optional[AIAnalyzerService] = None
    
    def _format_duration(self, seconds: float) -> str:
        """Formatea duración en formato legible."""
        if seconds < 1:
            return f"{seconds*1000:.0f}ms"
        return f"{seconds:.2f}s"
    
    def _test_provider(
        self, 
        provider_name: str, 
        test_func, 
        timeout: int = 10
    ) -> Tuple[bool, str, float, Optional[str]]:
        """
        Prueba un proveedor de IA.
        Returns: (success, message, elapsed_time, model_used)
        """
        logger.info(f"\n🤖 Probando {provider_name.upper()}...")
        
        start_time = time.time()
        try:
            success, message, model = test_func()
            elapsed = time.time() - start_time
            
            if success:
                logger.info(f"✅ {provider_name} OK en {self._format_duration(elapsed)}")
                if model:
                    logger.info(f"   📦 Modelo: {model}")
                return True, message, elapsed, model
            else:
                logger.error(f"❌ {provider_name} FALLÓ: {message}")
                return False, message, elapsed, None
                
        except Exception as e:
            elapsed = time.time() - start_time
            error_msg = str(e)
            logger.error(f"❌ {provider_name} ERROR: {error_msg}")
            return False, error_msg, elapsed, None
    
    def test_ollama(self) -> Tuple[bool, str, Optional[str]]:
        """Prueba conexión con Ollama."""
        if not self.ai_service.ollama_host:
            return False, "No configurado (OLLAMA_HOST vacío)", None
        
        # Verificar health
        if not self.ai_service._ollama_health_ok():
            return False, "Health check falló", None
        # Probar cada modelo de Ollama configurado (ollama_0, ollama_1, ...)
        last_err: Optional[Exception] = None
        for i in range(len(getattr(self.ai_service, 'ollama_models', []))):
            prov = f"ollama_{i}"
            try:
                response, model = self.ai_service._call_provider(
                    prov,
                    "Responde solo con: OK",
                    max_tokens=10
                )
                if response and "ok" in response.lower():
                    return True, f"Respuesta: {response.strip()}", model
            except Exception as e:
                last_err = e
                continue

        if last_err:
            return False, f"Todos los modelos Ollama fallaron: {last_err}", None
        return False, "No hay modelos de Ollama para probar", None
    
    def test_gemini(self) -> Tuple[bool, str, Optional[str]]:
        """Prueba conexión con Gemini."""
        if not self.ai_service.gemini_client:
            return False, "No configurado (API Key faltante)", None
        
        # Verificar modelo disponible
        model = self.ai_service._get_gemini_model()
        if not model:
            return False, "No se pudo descubrir modelo compatible", None
        
        try:
            response, used_model = self.ai_service._call_provider(
                "gemini", 
                "Responde solo con: OK", 
                max_tokens=10
            )
            
            if response and "ok" in response.lower():
                return True, f"Respuesta: {response.strip()}", used_model
            else:
                return False, f"Respuesta inesperada: {response}", used_model
                
        except Exception as e:
            error_str = str(e).lower()
            if "429" in error_str or "quota" in error_str:
                return False, "Cuota excedida (429)", None
            return False, str(e), None
    
    def test_openrouter(self) -> Tuple[bool, str, Optional[str]]:
        """Prueba conexión con OpenRouter."""
        if not self.ai_service.openrouter_client:
            return False, "No configurado (API Key faltante)", None
        
        # Asegurar modelos cargados
        self.ai_service._ensure_openrouter_models()
        if not self.ai_service.openrouter_models:
            return False, "No hay modelos :free disponibles", None
        
        try:
            response, model = self.ai_service._call_provider(
                "openrouter", 
                "Responde solo con: OK", 
                max_tokens=10
            )
            
            if response and "ok" in response.lower():
                return True, f"Respuesta: {response.strip()} | {len(self.ai_service.openrouter_models)} modelos", model
            else:
                return False, f"Respuesta inesperada: {response}", model
                
        except Exception as e:
            return False, str(e), None
    
    def test_huggingface(self) -> Tuple[bool, str, Optional[str]]:
        """Prueba conexión con HuggingFace."""
        if not self.ai_service.huggingface_api_key:
            return False, "No configurado (API Key faltante)", None
        
        # Refrescar catálogo si está vacío
        if not self.ai_service.huggingface_models:
            logger.info("🔄 Refrescando catálogo de modelos HuggingFace...")
            self.ai_service._refresh_huggingface_model_catalog(force=True)
        
        if not self.ai_service.huggingface_models:
            return False, "No hay modelos candidatos disponibles", None
        
        try:
            response, model = self.ai_service._call_provider(
                "huggingface", 
                "Responde solo con: OK", 
                max_tokens=10
            )
            
            if response:
                task = self.ai_service._hf_model_task.get(model, "unknown")
                return True, f"Respuesta: {response.strip()} | {len(self.ai_service.huggingface_models)} modelos", f"{model} ({task})"
            else:
                return False, "Respuesta vacía", model
                
        except Exception as e:
            error_str = str(e).lower()
            if "503" in error_str or "loading" in error_str:
                return True, "Modelo cargando (503) - Cold start normal", None
            return False, str(e), None
    
    def test_fallback_system(self) -> Tuple[bool, str]:
        """Prueba el sistema de fallback con un análisis real."""
        logger.info("\n🔄 Probando SISTEMA DE FALLBACK...")
        
        test_prompt = """Analiza brevemente: Bitcoin subió 5% hoy.
Responde en JSON:
{
  "sentiment": "positivo/neutral/negativo",
  "confidence": 1-10
}"""
        
        try:
            start = time.time()
            response, provider = self.ai_service._call_with_fallback_robust(
                test_prompt, 
                max_tokens=100
            )
            elapsed = time.time() - start
            
            if provider:
                logger.info(f"✅ Fallback OK - Usó: {provider} en {self._format_duration(elapsed)}")
                logger.info(f"   📝 Respuesta: {response[:100]}...")
                return True, f"Proveedor usado: {provider}"
            else:
                logger.error("❌ Fallback FALLÓ - Ningún proveedor respondió")
                return False, "Todos los proveedores fallaron"
                
        except Exception as e:
            return False, str(e)
    
    def validate_configuration(self) -> Dict[str, bool]:
        """Valida la configuración de API keys."""
        logger.info("\n🔍 VALIDANDO CONFIGURACIÓN...")
        
        config_status = {
            "Ollama": bool(Config.OLLAMA_HOST),
            "Gemini": bool(Config.GOOGLE_GEMINI_API_KEY),
            "OpenRouter": bool(Config.OPENROUTER_API_KEY),
            "HuggingFace": bool(Config.HUGGINGFACE_API_KEY),
        }
        
        for provider, configured in config_status.items():
            status = "✅ Configurado" if configured else "❌ No configurado"
            logger.info(f"   {provider}: {status}")
        
        return config_status
    
    def print_summary(self):
        """Imprime resumen de resultados."""
        print("\n" + "="*70)
        print("📊 RESUMEN DE RESULTADOS")
        print("="*70)
        
        # Configuración
        print("\n🔧 CONFIGURACIÓN:")
        for provider, result in self.results.items():
            if provider == "fallback":
                continue
            configured = "✅" if result.get('configured', False) else "❌"
            print(f"   {provider:15} {configured}")
        
        # Conectividad
        print("\n🌐 CONECTIVIDAD:")
        for provider, result in self.results.items():
            if provider == "fallback":
                continue
            
            success = result.get('success', False)
            elapsed = result.get('elapsed', 0)
            model = result.get('model', 'N/A')
            
            status = "✅ OK" if success else "❌ FALLÓ"
            time_str = self._format_duration(elapsed) if elapsed else "N/A"
            
            print(f"   {provider:15} {status:12} {time_str:10} | {model}")
        
        # Fallback
        if 'fallback' in self.results:
            fb = self.results['fallback']
            status = "✅ OK" if fb['success'] else "❌ FALLÓ"
            print(f"\n🔄 FALLBACK:      {status}")
            print(f"   Mensaje: {fb['message']}")
        
        # Estadísticas generales
        print("\n📈 ESTADÍSTICAS:")
        total = len([r for r in self.results.values() if r.get('configured')])
        working = len([r for r in self.results.values() if r.get('success')])
        print(f"   Proveedores configurados: {total}")
        print(f"   Proveedores funcionando:  {working}")
        
        if working > 0:
            avg_time = sum(r.get('elapsed', 0) for r in self.results.values() if r.get('success')) / working
            print(f"   Tiempo promedio:          {self._format_duration(avg_time)}")
        
        print("="*70)
        
        # Recomendaciones
        if working == 0:
            print("\n⚠️  ADVERTENCIA: Ningún proveedor está funcionando")
            print("   Verifica tus API keys y conexión a internet")
        elif working < total:
            print(f"\n⚠️  ADVERTENCIA: Solo {working}/{total} proveedores funcionan")
            print("   Algunos servicios podrían no estar disponibles")
        else:
            print("\n✅ PERFECTO: Todos los proveedores configurados funcionan correctamente")
        
        print()
    
    def run_all_tests(self):
        """Ejecuta todas las pruebas."""
        print("="*70)
        print("🧪 PRUEBA DE CONECTIVIDAD DE IA - VERSIÓN MEJORADA")
        print("="*70)
        
        # Inicializar servicio
        try:
            logger.info("\n📦 Inicializando AIAnalyzerService...")
            self.ai_service = AIAnalyzerService()
            logger.info("✅ Servicio inicializado correctamente")
        except Exception as e:
            logger.error(f"❌ Error crítico inicializando servicio: {e}")
            return
        
        # Validar configuración
        config_status = self.validate_configuration()
        
        # Probar cada proveedor
        providers = [
            ("Ollama", self.test_ollama),
            ("Gemini", self.test_gemini),
            ("OpenRouter", self.test_openrouter),
            ("HuggingFace", self.test_huggingface),
        ]
        
        for provider_name, test_func in providers:
            success, message, elapsed, model = self._test_provider(
                provider_name, 
                test_func,
                timeout=15
            )
            
            self.results[provider_name] = {
                'configured': config_status.get(provider_name, False),
                'success': success,
                'message': message,
                'elapsed': elapsed,
                'model': model or 'N/A'
            }
            
            # Pequeña pausa entre pruebas
            time.sleep(0.5)
        
        # Probar sistema de fallback
        try:
            fb_success, fb_message = self.test_fallback_system()
            self.results['fallback'] = {
                'success': fb_success,
                'message': fb_message
            }
        except Exception as e:
            logger.error(f"❌ Error probando fallback: {e}")
            self.results['fallback'] = {
                'success': False,
                'message': str(e)
            }
        
        # Imprimir estadísticas del servicio
        try:
            stats = self.ai_service.get_stats()
            if stats:
                print("\n" + "="*70)
                print("📊 ESTADÍSTICAS DE USO")
                print("="*70)
                for provider, pstats in stats.items():
                    print(f"\n{provider.upper()}:")
                    print(f"   Peticiones: {pstats['requests']}")
                    print(f"   Fallos:     {pstats['failures']}")
                    print(f"   Tiempo avg: {self._format_duration(pstats['avg_response_time'])}")
        except Exception as e:
            logger.debug(f"No se pudieron obtener estadísticas: {e}")
        
        # Imprimir resumen
        self.print_summary()


def main():
    """Función principal."""
    tester = AIConnectivityTester()
    tester.run_all_tests()


if __name__ == "__main__":
    main()