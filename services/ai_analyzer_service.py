"""
Servicio de análisis con IA utilizando múltiples proveedores (Gemini, OpenRouter, Ollama, HuggingFace).
Analiza los datos del mercado y genera recomendaciones.

VERSIÓN CORREGIDA:
- ✅ Solucionados race conditions en cache
- ✅ Mejorado thread-safety
- ✅ Validaciones de entrada robustas
- ✅ Logging optimizado (DEBUG en lugar de INFO)
- ✅ Código duplicado refactorizado
- ✅ Manejo de errores mejorado
"""

import concurrent.futures
import hashlib
import json
import logging
import re
import threading
import time
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple

import google.genai as genai
import openai  # Solo para OpenRouter
import requests

# ✅ Importar logger PRIMERO
from config.config import Config
from utils.logger import logger

# ✅ Luego intentar import opcional
try:
    from huggingface_hub import InferenceClient
except ImportError:
    InferenceClient = None
    logger.warning("⚠️ 'huggingface_hub' no instalado. El proveedor Hugging Face estará deshabilitado. Ejecute: pip install huggingface_hub")


# ========== CONSTANTES ==========
VALID_CATEGORIES = frozenset(("crypto", "markets", "signals"))
GEMINI_MAX_RETRIES = 2
CACHE_VERSION = "v2"  # Incrementar cuando cambies lógica de análisis


@dataclass
class AIAnalyzerConfig:
    """Configuración del servicio de análisis con IA."""

    DEFAULT_TIMEOUT: int = 30
    CACHE_TTL: int = 300
    MAX_COINS_IN_PROMPT: int = 10
    GEMINI_TEMPERATURE: float = 0.7
    GEMINI_MODEL: Optional[str] = None

    OPENROUTER_MODEL_DISCOVERY_LIMIT: int = 30

    HF_MODEL_DISCOVERY_REFRESH_SECONDS: int = 6 * 60 * 60
    HF_MODEL_DISCOVERY_LIMIT: int = 50
    HF_MODEL_DISCOVERY_TIMEOUT_SECONDS: int = 10
    HF_MAX_BILLIONS: float = 34.0
    HF_VALIDATE_MAX_CANDIDATES: int = 25
    HF_VALIDATE_TARGET_MODELS: int = 12
    HF_VALIDATE_TIMEOUT_SECONDS: int = 12
    
    def __post_init__(self):
        pass


class AIAnalyzerService:

    def __init__(self, config: Optional[AIAnalyzerConfig] = None) -> None:
        self.config = config or AIAnalyzerConfig()

        self._state_lock = threading.RLock()
        self.active_provider: Optional[str] = None
        self._cycle_provider_ok: bool = False
        self.gemini_client: Optional[Any] = None
        self.openrouter_client: Optional[Any] = None
        self.openrouter_models: List[str] = []
        self.current_openrouter_model_index: int = 0
        self._openrouter_api_key: Optional[str] = None
        self._openrouter_last_model: Optional[str] = None
        
        self.huggingface_api_key: Optional[str] = None
        self.huggingface_models: List[str] = []
        self._hf_model_task: Dict[str, str] = {}
        self._hf_models_last_refresh_ts: float = 0.0
        self._hf_client: Optional[Any] = None

        self._providers: Dict[str, Any] = {}

        self._metrics: Dict[str, Dict[str, Any]] = {
            "requests": defaultdict(int),
            "failures": defaultdict(int),
            "total_time": defaultdict(float),
        }

        self._cache: Dict[str, Any] = {}
        self._cache_timestamps: Dict[str, float] = {}

        self._timeout: int = self.config.DEFAULT_TIMEOUT
        self._cache_ttl: int = self.config.CACHE_TTL
        self._http_timeout = (min(3, self._timeout), self._timeout)
        self._last_success_provider: Optional[str] = None
        self._last_success_model: Optional[str] = None
        self._gemini_model_cache: Optional[str] = None
        
        # Configurar Ollama
        _raw_ollama_host = getattr(Config, "OLLAMA_HOST", "") or ""
        _prefer_local = bool(getattr(Config, "OLLAMA_PREFER_LOCAL_ON_LINUX", True))
        if bool(getattr(Config, "IS_LINUX", False)) and _prefer_local:
            self.ollama_host = "http://localhost:11434"
        else:
            self.ollama_host = _raw_ollama_host
        self.ollama_host = self._format_ollama_host(self.ollama_host)
        self.ollama_model: str = getattr(Config, "OLLAMA_MODEL", "qwen2.5:7b") or "qwen2.5:7b"
        self._ollama_health_cache_seconds: int = int(getattr(Config, "OLLAMA_HEALTH_CACHE_SECONDS", 60) or 60)
        self._ollama_health_last_ts: float = 0.0
        self._ollama_health_last_ok: bool = False
        if self.ollama_host:
            self._providers["ollama"] = "ollama"

        # Configurar Gemini
        try:
            api_key = getattr(Config, "GOOGLE_GEMINI_API_KEY", "") or ""
            if api_key.strip():
                self.gemini_client = genai.Client(api_key=api_key)
                self._providers["gemini"] = self.gemini_client
                if self.config.GEMINI_MODEL:
                    logger.debug(f"✅ Gemini configurado (modelo fijo={self.config.GEMINI_MODEL})")
                else:
                    logger.debug("✅ Gemini configurado (modelo dinámico)")
            else:
                logger.debug("Google Gemini API key no configurada")
        except Exception as e:
            logger.debug(f"Error al configurar Gemini: {e}")

        # Configurar OpenRouter
        try:
            api_key = getattr(Config, "OPENROUTER_API_KEY", "") or ""
            if api_key.strip():
                self._openrouter_api_key = api_key
                self.openrouter_client = openai.OpenAI(
                    api_key=api_key,
                    base_url="https://openrouter.ai/api/v1",
                )
                self._providers["openrouter"] = self.openrouter_client
                logger.debug("✅ OpenRouter configurado (modelos dinámicos)")
            else:
                logger.debug("OpenRouter API key no configurada")
        except Exception as e:
            logger.debug(f"Error al configurar OpenRouter: {e}")

        # Configurar Hugging Face
        try:
            api_key = getattr(Config, "HUGGINGFACE_API_KEY", "") or ""
            if api_key.strip():
                self.huggingface_api_key = api_key
                self._providers["huggingface"] = "inference_client"
                if InferenceClient is not None:
                    with self._state_lock:
                        self._hf_client = InferenceClient(
                            api_key=self.huggingface_api_key, 
                            provider="hf-inference", 
                            timeout=self._timeout
                        )
                logger.debug("✅ Hugging Face configurado (modelos dinámicos)")
            else:
                logger.debug("Hugging Face API key no configurada")
        except Exception as e:
            logger.debug(f"Error al configurar Hugging Face: {e}")

        self.check_best_provider()

    def _discover_gemini_model(self) -> Optional[str]:
        """Descubre el mejor modelo de Gemini disponible."""
        if not self.gemini_client:
            return None
        preferred = [
            "gemini-2.0-flash",
            "gemini-2.0-flash-lite",
            "gemini-1.5-flash",
            "gemini-1.5-flash-8b",
            "gemini-1.5-pro",
            "gemini-2.5-flash",
        ]
        try:
            models = self.gemini_client.models.list()
            model_names: List[str] = []
            for m in models:
                name = getattr(m, "name", None)
                if isinstance(name, str) and name:
                    model_names.append(name)
            for p in preferred:
                for n in model_names:
                    if n.endswith(p) or n == p or n.split("/")[-1] == p:
                        return n.split("/")[-1]
            if model_names:
                return model_names[0].split("/")[-1]
            return None
        except Exception as e:
            logger.debug(f"Gemini: no se pudo listar modelos: {e}")
            return None

    def _get_gemini_model(self) -> Optional[str]:
        """Obtiene el modelo de Gemini a usar (fijo o dinámico)."""
        if self.config.GEMINI_MODEL:
            return self.config.GEMINI_MODEL
        with self._state_lock:
            if self._gemini_model_cache:
                return self._gemini_model_cache
        model = self._discover_gemini_model()
        if model:
            with self._state_lock:
                self._gemini_model_cache = model
        return model

    def _discover_openrouter_free_models(self, api_key: str) -> List[str]:
        """Descubre modelos gratuitos de OpenRouter."""
        try:
            resp = requests.get(
                "https://openrouter.ai/api/v1/models",
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=10,
            )
            if resp.status_code != 200:
                logger.warning(f"⚠️ OpenRouter: no se pudo listar modelos (HTTP {resp.status_code})")
                return []
            payload = resp.json() or {}
            items = payload.get("data") or []
            if not isinstance(items, list):
                return []
            free_ids: List[str] = []
            for it in items:
                if not isinstance(it, dict):
                    continue
                mid = it.get("id")
                if isinstance(mid, str) and mid.endswith(":free"):
                    free_ids.append(mid)
            free_ids = list(dict.fromkeys(free_ids))
            return free_ids[: self.config.OPENROUTER_MODEL_DISCOVERY_LIMIT]
        except Exception as e:
            logger.debug(f"OpenRouter: no se pudo descubrir modelos gratuitos: {e}")
            return []

    def _refresh_huggingface_model_catalog(self, force: bool = False) -> None:
        """Refresca el catálogo de modelos de HuggingFace."""
        if not self.huggingface_api_key:
            return
        now = time.time()
        if (not force) and (now - self._hf_models_last_refresh_ts) < self.config.HF_MODEL_DISCOVERY_REFRESH_SECONDS:
            return
        models, task_map = self._discover_huggingface_public_free_candidates()
        if not models:
            return
        verified_models, verified_task_map = self._validate_huggingface_candidates(models, task_map)
        if verified_models:
            with self._state_lock:
                self.huggingface_models = verified_models
                self._hf_model_task = verified_task_map
                self._hf_models_last_refresh_ts = now

    def _discover_huggingface_public_free_candidates(self) -> Tuple[List[str], Dict[str, str]]:
        """Descubre candidatos de modelos públicos de HuggingFace."""
        if InferenceClient is None:
            return [], {}

        def parse_billion_hint(model_id: str) -> Optional[float]:
            s = model_id.lower()
            m = re.search(r"(\d+(?:\.\d+)?)\s*b\b", s)
            if not m:
                m = re.search(r"[-_/](\d+(?:\.\d+)?)b[-_/]", s)
            if not m:
                return None
            try:
                return float(m.group(1))
            except Exception:
                return None

        def is_preferred_name(model_id: str) -> bool:
            s = model_id.lower()
            if any(k in s for k in ["instruct", "instruction", "chat", "-it", "_it", "assistant"]):
                return True
            return False

        def fetch(tag: str, search: str) -> List[Dict[str, Any]]:
            try:
                resp = requests.get(
                    "https://huggingface.co/api/models",
                    params={
                        "pipeline_tag": tag,
                        "search": search,
                        "sort": "downloads",
                        "direction": -1,
                        "limit": self.config.HF_MODEL_DISCOVERY_LIMIT,
                    },
                    timeout=self.config.HF_MODEL_DISCOVERY_TIMEOUT_SECONDS,
                )
                if resp.status_code != 200:
                    logger.warning(f"⚠️ HuggingFace: listado modelos falló (HTTP {resp.status_code}) tag={tag} search={search}")
                    return []
                data = resp.json()
                if isinstance(data, list):
                    return data
                return []
            except Exception as e:
                logger.debug(f"HuggingFace: error consultando api/models: {e}")
                return []

        raw: List[Dict[str, Any]] = []
        for tag in ["conversational", "text-generation"]:
            for search in ["instruct", "chat"]:
                raw.extend(fetch(tag, search))

        seen: set = set()
        candidates: List[Tuple[str, str, int, int, Optional[float]]] = []
        for it in raw:
            if not isinstance(it, dict):
                continue
            model_id = it.get("modelId") or it.get("id")
            if not isinstance(model_id, str) or not model_id:
                continue
            if model_id in seen:
                continue
            seen.add(model_id)
            if it.get("private") is True:
                continue
            if it.get("gated") is True:
                continue
            pipeline_tag = it.get("pipeline_tag")
            if pipeline_tag not in ("conversational", "text-generation"):
                continue
            if not is_preferred_name(model_id):
                continue
            size_hint = parse_billion_hint(model_id)
            if size_hint is not None and size_hint > float(self.config.HF_MAX_BILLIONS):
                continue
            downloads = it.get("downloads") or 0
            likes = it.get("likes") or 0
            try:
                downloads_i = int(downloads)
            except Exception:
                downloads_i = 0
            try:
                likes_i = int(likes)
            except Exception:
                likes_i = 0
            candidates.append((model_id, pipeline_tag, downloads_i, likes_i, size_hint))

        candidates.sort(key=lambda x: (x[4] is None, x[4] or 0.0, -x[2], -x[3], x[0]))
        selected: List[str] = []
        task_map: Dict[str, str] = {}
        for model_id, pipeline_tag, _, __, ___ in candidates[: self.config.HF_MODEL_DISCOVERY_LIMIT]:
            selected.append(model_id)
            task_map[model_id] = pipeline_tag
        return selected, task_map

    def _validate_huggingface_candidates(self, model_ids: List[str], task_map: Dict[str, str]) -> Tuple[List[str], Dict[str, str]]:
        """Valida candidatos de HuggingFace con pruebas rápidas."""
        if not self.huggingface_api_key or InferenceClient is None:
            return [], {}

        client = InferenceClient(
            api_key=self.huggingface_api_key,
            provider="hf-inference",
            timeout=self.config.HF_VALIDATE_TIMEOUT_SECONDS,
        )

        verified: List[str] = []
        verified_task: Dict[str, str] = {}

        def quick_probe(mid: str, preferred_task: str) -> Optional[str]:
            prompt = "Responde solo con: OK"
            try:
                text = self._call_huggingface_model(client, mid, preferred_task, prompt, max_tokens=8).strip()
                if text:
                    return preferred_task
            except Exception as e:
                s = str(e).lower()
                if "not supported for task" in s and "supported task" in s:
                    alt = "conversational" if preferred_task == "text-generation" else "text-generation"
                    try:
                        text = self._call_huggingface_model(client, mid, alt, prompt, max_tokens=8).strip()
                        if text:
                            return alt
                    except Exception:
                        return None
                if any(kw in s for kw in ["402", "payment", "billing", "401", "unauthorized", "403", "forbidden", "gated", "404", "not found"]):
                    return None
                if "429" in s or "rate limit" in s:
                    time.sleep(1)
                    return None
                if "503" in s or "loading" in s:
                    return None
                return None
            return None

        limit = min(len(model_ids), self.config.HF_VALIDATE_MAX_CANDIDATES)
        for mid in model_ids[:limit]:
            preferred_task = task_map.get(mid, "text-generation")
            selected_task = self._run_with_timeout(
                lambda: quick_probe(mid, preferred_task), 
                timeout_seconds=self.config.HF_VALIDATE_TIMEOUT_SECONDS
            )
            if isinstance(selected_task, Exception):
                continue
            if isinstance(selected_task, str) and selected_task:
                verified.append(mid)
                verified_task[mid] = selected_task
                if len(verified) >= self.config.HF_VALIDATE_TARGET_MODELS:
                    break

        if verified:
            logger.debug(
                f"🤗 HuggingFace: verificados {len(verified)}/{limit} modelos (target={self.config.HF_VALIDATE_TARGET_MODELS})"
            )
        return verified, verified_task

    def _run_with_timeout(self, fn: Callable[[], Any], timeout_seconds: int) -> Any:
        """Ejecuta función con timeout, devuelve resultado o excepción."""
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(fn)
                return future.result(timeout=timeout_seconds)
        except Exception as e:
            return e

    def _is_quota_error(self, e: Exception) -> bool:
        """Detecta si el error es por cuota/límite de API."""
        s = str(e).lower()
        return "429" in s or "rate limit" in s or "insufficient_quota" in s or "quota" in s

    def _format_ollama_host(self, host: str) -> str:
        """Formatea y normaliza URL de Ollama."""
        h = (host or "").strip()
        if not h:
            return ""
        # Eliminar duplicaciones de protocolo
        while any(h.startswith(dup) for dup in ["http://http://", "https://https://", "http://https://", "https://http://"]):
            for dup in ["http://http://", "https://https://", "http://https://", "https://http://"]:
                if h.startswith(dup):
                    h = h.replace(dup, "http://" if dup.startswith("http://http://") else "https://", 1)
                    break
        if not (h.startswith("http://") or h.startswith("https://")):
            h = f"http://{h}"
        return h.rstrip("/")

    def _call_ollama(self, prompt: str, max_tokens: int, allow_short: bool = False) -> str:
        """Llama a Ollama para generar texto."""
        host = self._format_ollama_host(self.ollama_host)
        if not host:
            raise RuntimeError("Ollama no configurado")
        payload: Dict[str, Any] = {
            "model": self.ollama_model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "options": {"num_predict": max(1, int(max_tokens))},
        }
        resp = requests.post(f"{host}/api/chat", json=payload, timeout=self._http_timeout)
        if resp.status_code != 200:
            raise RuntimeError(f"Ollama falló (HTTP {resp.status_code})")
        data = resp.json() or {}
        text = ""
        msg = data.get("message")
        if isinstance(msg, dict):
            text = msg.get("content") or ""
        if not text and isinstance(data.get("response"), str):
            text = data.get("response") or ""
        if not text and not allow_short:
            raise RuntimeError("Respuesta vacía de Ollama")
        return text

    def _ollama_health_ok(self) -> bool:
        """Verifica si Ollama está disponible (con cache)."""
        host = self._format_ollama_host(self.ollama_host)
        if not host:
            return False
        now = time.time()
        with self._state_lock:
            if self._ollama_health_cache_seconds > 0 and (now - self._ollama_health_last_ts) < self._ollama_health_cache_seconds:
                return self._ollama_health_last_ok
        ok = False
        result = self._run_with_timeout(
            lambda: self._call_ollama("OK", max_tokens=6, allow_short=True), 
            timeout_seconds=min(4, self._timeout)
        )
        if isinstance(result, str) and result.strip():
            ok = True
        with self._state_lock:
            self._ollama_health_last_ts = now
            self._ollama_health_last_ok = ok
        return ok

    def _get_provider_priority_list(self) -> List[str]:
        """Obtiene lista priorizada de proveedores disponibles."""
        available: List[str] = []
        if self._ollama_health_ok():
            available.append("ollama")
        if self.gemini_client:
            available.append("gemini")
        if self.openrouter_client:
            available.append("openrouter")
        if self.huggingface_api_key:
            available.append("huggingface")

        if not available:
            return []

        providers: List[str] = []
        # Priorizar último exitoso
        with self._state_lock:
            last_success = self._last_success_provider
            active = self.active_provider
        
        if last_success in available:
            providers.append(last_success)
        elif active in available:
            providers.append(active)
        
        # Luego orden por defecto
        default_order = ["ollama", "gemini", "openrouter", "huggingface"]
        providers.extend(p for p in default_order if p in available and p not in providers)
        providers.extend(p for p in available if p not in providers)
        return providers

    def _record_success(self, provider: str, model: str) -> None:
        """Registra éxito de un proveedor."""
        with self._state_lock:
            self._last_success_provider = provider
            self._last_success_model = model
            self.active_provider = provider

    def _call_provider(self, provider: str, prompt: str, max_tokens: int = 2048) -> Tuple[str, str]:
        """
        Llama a un proveedor específico de IA.
        Returns: (texto_generado, modelo_usado)
        """
        start = time.time()
        with self._state_lock:
            self._metrics["requests"][provider] += 1

        def _call() -> Tuple[str, str]:
            if provider == "gemini":
                if not self.gemini_client:
                    raise RuntimeError("Gemini no configurado")
                model = self._get_gemini_model()
                if not model:
                    raise RuntimeError("Gemini sin modelo compatible (no se pudo descubrir)")
                last_err: Optional[Exception] = None
                for attempt in range(GEMINI_MAX_RETRIES):
                    try:
                        response = self.gemini_client.models.generate_content(
                            model=model,
                            contents=prompt,
                            config={
                                "temperature": self.config.GEMINI_TEMPERATURE,
                                "top_p": 0.95,
                                "top_k": 40,
                                "max_output_tokens": max_tokens,
                            },
                        )
                        text = getattr(response, "text", "") or ""
                        if not text:
                            raise RuntimeError("Respuesta vacía de Gemini")
                        return text, model
                    except Exception as e:
                        last_err = e
                        err_str = str(e).lower()
                        if attempt == 0 and (self._is_quota_error(e) or "timeout" in err_str or "temporar" in err_str):
                            time.sleep(1)
                            continue
                        raise
                # Si salimos del loop
                if last_err:
                    raise last_err
                raise RuntimeError("Gemini falló sin excepción específica")

            if provider == "openrouter":
                if not self.openrouter_client:
                    raise RuntimeError("OpenRouter no configurado")
                self._ensure_openrouter_models()
                if not self.openrouter_models:
                    raise RuntimeError("OpenRouter: no hay modelos gratuitos disponibles")
                
                with self._state_lock:
                    models = list(self.openrouter_models)
                    last_model = self._openrouter_last_model
                    # ✅ FIX: Validar índice antes de usar
                    indexed_model = None
                    if 0 <= self.current_openrouter_model_index < len(models):
                        indexed_model = models[self.current_openrouter_model_index]
                
                # Construir lista de candidatos
                candidates: List[str] = []
                if last_model and last_model in models:
                    candidates.append(last_model)
                if indexed_model and indexed_model not in candidates:
                    candidates.append(indexed_model)
                for model in models:
                    if model not in candidates:
                        candidates.append(model)
                    if len(candidates) >= min(len(models), 3):
                        break
                
                # ✅ FIX: Validar que hay candidatos
                if not candidates:
                    raise RuntimeError("OpenRouter: no hay modelos candidatos para probar")
                
                last_error: Optional[Exception] = None
                for model in candidates:
                    try:
                        if logger.isEnabledFor(logging.DEBUG):
                            logger.debug(f"🤖 OpenRouter probando modelo: {model}")
                        
                        response = self.openrouter_client.chat.completions.create(
                            model=model,
                            messages=[{"role": "user", "content": prompt}],
                            max_tokens=max_tokens,
                            timeout=self._timeout,
                        )
                        if not response.choices:
                            raise RuntimeError(f"Respuesta vacía de OpenRouter ({model})")
                        
                        result_text = response.choices[0].message.content or ""
                        
                        if logger.isEnabledFor(logging.DEBUG):
                            logger.debug(f"✅ Éxito con OpenRouter modelo: {model}")
                        
                        with self._state_lock:
                            self._openrouter_last_model = model
                            if model in models:
                                self.current_openrouter_model_index = models.index(model)
                        return result_text, model
                        
                    except Exception as model_err:
                        last_error = model_err
                        err_str = str(model_err).lower()
                        if "429" in err_str or "rate limit" in err_str:
                            logger.warning(f"⏳ OpenRouter rate limit con {model}, probando siguiente")
                            time.sleep(1)
                        elif "timeout" in err_str or "timed out" in err_str:
                            logger.warning(f"⏳ OpenRouter timeout con {model}, probando siguiente")
                        else:
                            logger.warning(f"⚠️ OpenRouter modelo {model} falló: {err_str[:140]}")
                        continue
                
                # ✅ FIX: Validar last_error antes de usar
                if last_error:
                    raise RuntimeError(f"Todos los modelos de OpenRouter fallaron. Último error: {last_error}")
                else:
                    raise RuntimeError("OpenRouter: todos los modelos candidatos fallaron sin error específico")

            if provider == "ollama":
                text = self._call_ollama(prompt, max_tokens=max_tokens, allow_short=False)
                return text, self.ollama_model

            if provider == "huggingface":
                if not self.huggingface_api_key:
                    raise RuntimeError("Hugging Face no configurado")
                
                if InferenceClient is None:
                    raise RuntimeError("Librería 'huggingface_hub' no instalada")
                
                # Refrescar catálogo si es necesario
                self._refresh_huggingface_model_catalog(force=False)
                if not self.huggingface_models:
                    self._refresh_huggingface_model_catalog(force=True)
                if not self.huggingface_models:
                    raise RuntimeError("HuggingFace: no hay modelos candidatos disponibles")

                # ✅ FIX: Thread-safe client creation
                with self._state_lock:
                    client = self._hf_client
                    if client is None:
                        client = InferenceClient(
                            api_key=self.huggingface_api_key, 
                            provider="hf-inference", 
                            timeout=self._timeout
                        )
                        self._hf_client = client

                last_error: Optional[Exception] = None
                for model in self.huggingface_models:
                    try:
                        task = self._hf_model_task.get(model, "text-generation")
                        
                        if logger.isEnabledFor(logging.DEBUG):
                            logger.debug(f"🤗 HuggingFace probando modelo: {model} (task={task})")
                        
                        text = self._call_huggingface_model(client, model, task, prompt, max_tokens=max_tokens)
                        if not text:
                            raise RuntimeError("Respuesta vacía")

                        if logger.isEnabledFor(logging.DEBUG):
                            logger.debug(f"✅ Éxito con HuggingFace modelo: {model} (task={task})")
                        
                        return text, model
                            
                    except Exception as model_err:
                        err_str = str(model_err).lower()
                        if "503" in err_str or "loading" in err_str:
                            logger.warning(f"⏳ HuggingFace modelo {model} cargando (503). Probando siguiente")
                        elif "429" in err_str or "rate limit" in err_str:
                            logger.warning(f"⏳ HuggingFace rate limit con {model}. Probando siguiente")
                            time.sleep(1)
                        elif "not found" in err_str or "404" in err_str:
                            logger.warning(f"🧹 HuggingFace modelo inexistente/no accesible: {model}")
                        elif "not supported for task" in err_str and "supported task" in err_str:
                            logger.warning(f"🔁 HuggingFace task no compatible con {model}: {str(model_err)[:140]}")
                        else:
                            logger.warning(f"⚠️ Error HuggingFace {model}: {err_str[:140]}")
                        last_error = model_err
                        continue
                
                # ✅ FIX: Validar last_error
                if last_error:
                    raise RuntimeError(f"Todos los modelos de HuggingFace fallaron. Último error: {last_error}")
                else:
                    raise RuntimeError("HuggingFace: no se pudo probar ningún modelo")

            raise RuntimeError(f"Proveedor inválido: {provider}")

        # Ejecutar con timeout
        result = self._run_with_timeout(_call, timeout_seconds=self._timeout)
        
        # ✅ FIX: Manejo mejorado de excepciones
        if isinstance(result, Exception):
            with self._state_lock:
                self._metrics["failures"][provider] += 1
            # Re-lanzar la excepción original
            raise result

        elapsed = time.time() - start
        with self._state_lock:
            self._metrics["total_time"][provider] += elapsed
        
        text, model = result
        return str(text), model

    def _ensure_openrouter_models(self) -> None:
        """Asegura que la lista de modelos de OpenRouter esté cargada."""
        with self._state_lock:
            if self.openrouter_models:
                return
        if not self._openrouter_api_key:
            return
        models = self._discover_openrouter_free_models(api_key=self._openrouter_api_key)
        if models:
            with self._state_lock:
                self.openrouter_models = models
            logger.debug(f"🔎 OpenRouter: detectados {len(self.openrouter_models)} modelos :free")

    def _call_with_fallback_robust(self, prompt: str, max_tokens: int = 2048, min_chars: int = 5) -> Tuple[str, Optional[str]]:
        """
        Intenta obtener respuesta de múltiples proveedores con fallback robusto.
        Returns: (texto, proveedor_usado)
        """
        providers = self._get_provider_priority_list()
        if not providers:
            logger.error("❌ No hay proveedores de IA configurados/disponibles")
            return "Error: Sin proveedores de IA", None

        last_error: Optional[Exception] = None
        
        for provider in providers:
            try:
                logger.info(f"🤖 Intentando con {provider}...")
                text, model = self._call_provider(provider, prompt, max_tokens=max_tokens)
                
                if not text or len(text.strip()) < min_chars:
                    raise RuntimeError("Respuesta vacía o muy corta")
                    
                self._record_success(provider, model)
                with self._state_lock:
                    self._cycle_provider_ok = True
                logger.info(f"✅ Éxito con {provider}")
                return text, provider
                
            except Exception as e:
                last_error = e
                logger.warning(f"⚠️ Falló {provider}: {str(e)}")
                logger.info("🔁 Activando fallback al siguiente proveedor...")
                if self._is_quota_error(e):
                    logger.warning(f"⏳ Quota excedida en {provider}")

        logger.error("❌ Todos los proveedores de IA fallaron")
        return "Error: Todos los proveedores fallaron. Revise logs.", None

    def reset_cycle_status(self) -> None:
        """Resetea el estado del ciclo."""
        with self._state_lock:
            self._cycle_provider_ok = False

    def get_cycle_status(self) -> bool:
        """Obtiene el estado del ciclo."""
        with self._state_lock:
            return self._cycle_provider_ok

    def _test_gemini(self) -> Any:
        """Prueba conexión con Gemini."""
        if not self.gemini_client:
            return RuntimeError("Gemini no configurado")
        model = self._get_gemini_model()
        if not model:
            return RuntimeError("Gemini sin modelo compatible (no se pudo descubrir)")
        response = self.gemini_client.models.generate_content(
            model=model,
            contents="Hola",
            config={
                "temperature": self.config.GEMINI_TEMPERATURE,
                "top_p": 0.95,
                "top_k": 40,
                "max_output_tokens": 32,
            },
        )
        if not response or not response.text:
            return RuntimeError("Respuesta vacía de Gemini")
        return True

    def _test_ollama(self) -> Any:
        """Prueba conexión con Ollama."""
        if not self.ollama_host:
            return RuntimeError("Ollama no configurado")
        try:
            _ = self._call_ollama("Hola", max_tokens=8, allow_short=True)
            return True
        except Exception as e:
            return e

    def _test_openrouter(self) -> Any:
        """Prueba conexión con OpenRouter."""
        if not self.openrouter_client:
            return RuntimeError("OpenRouter no configurado")
        try:
            _text, _model = self._call_provider("openrouter", "Hola", max_tokens=6)
            return True
        except Exception as e:
            return e

    def _test_huggingface(self) -> Any:
        """Prueba conexión con HuggingFace."""
        if not self.huggingface_api_key:
            return RuntimeError("Hugging Face no configurado")
            
        if InferenceClient is None:
            return RuntimeError("Librería 'huggingface_hub' no instalada")
        
        try:
            _text, _model = self._call_provider("huggingface", "Hola, responde solo con OK", max_tokens=5)
            return True
        except Exception as e:
            err_str = str(e).lower()
            if "503" in err_str:
                logger.debug("⚠️ Modelo HuggingFace cargando (503), conexión OK")
                return True
            return e

    def check_best_provider(self) -> None:
        """Verifica qué API responde y selecciona la activa para este ciclo."""
        # Probar Ollama
        try:
            if self._ollama_health_ok():
                result = self._run_with_timeout(self._test_ollama, timeout_seconds=6)
                if result is True:
                    self._record_success("ollama", self.ollama_model)
                    logger.info(f"✅ Proveedor activo: Ollama (modelo={self.ollama_model})")
                    return
                if isinstance(result, Exception):
                    raise result
        except Exception as e:
            logger.debug(f"Ollama no disponible: {e}")

        # Probar Gemini
        try:
            if self.gemini_client:
                result = self._run_with_timeout(self._test_gemini, timeout_seconds=6)
                if result is True:
                    model = self._get_gemini_model() or "gemini"
                    self._record_success("gemini", model)
                    logger.info(f"✅ Proveedor activo: Gemini (modelo={model})")
                    return
                if isinstance(result, Exception):
                    raise result
        except Exception as e:
            if not self._is_quota_error(e):
                logger.debug("Gemini no disponible")

        # Probar OpenRouter
        try:
            if self.openrouter_client:
                result = self._run_with_timeout(self._test_openrouter, timeout_seconds=6)
                if result is True:
                    model = self._openrouter_last_model or (self.openrouter_models[0] if self.openrouter_models else "openrouter")
                    self._record_success("openrouter", model)
                    logger.info(f"✅ Proveedor activo: OpenRouter ({len(self.openrouter_models)} modelos disponibles)")
                    return
                if isinstance(result, Exception):
                    raise result
        except Exception as e:
            if not self._is_quota_error(e):
                logger.debug("OpenRouter no disponible")

        # Probar Hugging Face
        try:
            if self.huggingface_api_key:
                result = self._run_with_timeout(self._test_huggingface, timeout_seconds=8)
                if result is True:
                    model = self.huggingface_models[0] if self.huggingface_models else "huggingface"
                    self._record_success("huggingface", model)
                    logger.info(f"✅ Proveedor activo: Hugging Face ({len(self.huggingface_models)} modelos)")
                    return
                if isinstance(result, Exception):
                    raise result
        except Exception as e:
            logger.debug(f"Hugging Face no disponible: {e}")
            
        with self._state_lock:
            self.active_provider = None
        logger.warning("⚠️ Ningún proveedor de IA disponible")

    def _call_huggingface_model(self, client: Any, model: str, task: str, prompt: str, max_tokens: int) -> str:
        """Llama a un modelo específico de HuggingFace."""
        messages = [{"role": "user", "content": prompt}]
        if task == "conversational":
            try:
                resp = client.chat_completion(
                    model=model,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=0.7,
                    top_p=0.95,
                )
                text = resp.choices[0].message.content
                return text or ""
            except Exception as e:
                err = str(e).lower()
                if "not supported for task" in err and "supported task" in err:
                    return self._call_huggingface_model(client, model, task="text-generation", prompt=prompt, max_tokens=max_tokens)
                raise

        if task == "text-generation":
            try:
                resp = client.text_generation(
                    prompt=prompt,
                    model=model,
                    max_new_tokens=max_tokens,
                    temperature=0.7,
                    return_full_text=False,
                )
                return str(resp or "")
            except Exception as e:
                err = str(e).lower()
                if "not supported for task" in err and "supported task" in err:
                    return self._call_huggingface_model(client, model, task="conversational", prompt=prompt, max_tokens=max_tokens)
                raise

        raise RuntimeError(f"HuggingFace: task inválida ({task})")

    def _generate_content(self, prompt: str, max_tokens: int = 2048) -> str:
        """Genera contenido usando el mejor proveedor disponible."""
        text, _ = self._call_with_fallback_robust(prompt, max_tokens=max_tokens)
        return text

    def _simplify_coins(self, coins: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Simplifica lista de monedas para reducir tamaño de prompt."""
        simplified: List[Dict[str, Any]] = []
        for coin in coins[: self.config.MAX_COINS_IN_PROMPT]:
            symbol = str(coin.get("symbol", ""))
            price = coin.get("price")
            change_24h = coin.get("change_24h")
            volume = coin.get("volume_24h") or coin.get("quoteVolume") or coin.get("volume")

            clean: Dict[str, Any] = {"symbol": symbol}

            if isinstance(price, (int, float)):
                clean["price"] = round(float(price), 6)
            if isinstance(change_24h, (int, float)):
                clean["change_24h"] = round(float(change_24h), 3)
            if isinstance(volume, (int, float)):
                clean["volume"] = float(volume)

            simplified.append(clean)

        return simplified

    def _get_cache_key(self, payload: Dict[str, Any]) -> str:
        """Genera clave de cache a partir de payload."""
        # ✅ Agregar versión al cache
        payload_with_version = {**payload, "cache_version": CACHE_VERSION}
        raw = json.dumps(payload_with_version, ensure_ascii=False, sort_keys=True)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def _is_cache_valid(self, key: str) -> bool:
        """Verifica si entrada de cache es válida (thread-safe)."""
        # ✅ FIX: Agregar lock para thread-safety
        with self._state_lock:
            ts = self._cache_timestamps.get(key)
            if ts is None:
                return False
            return (time.time() - ts) < self._cache_ttl

    def _get_cache_value(self, key: str) -> Optional[Any]:
        """Obtiene valor del cache si es válido."""
        with self._state_lock:
            if not self._is_cache_valid(key):
                return None
            return self._cache.get(key)

    def _set_cache_value(self, key: str, value: Any) -> None:
        """Guarda valor en cache."""
        with self._state_lock:
            self._cache[key] = value
            self._cache_timestamps[key] = time.time()

    def _extract_json_safe(self, text: str, expect: str = "object") -> Any:
        """
        Extrae JSON de texto de forma segura, manejando markdown y texto extra.
        ✅ MEJORADO: Valida estructura después de parsear
        """
        if not text:
            return [] if expect == "list" else {}
        
        s = text.strip()
        s = s.replace("\r", "")
        s = s.replace("```json", "```")
        
        # Eliminar bloques de código markdown
        if "```" in s:
            parts = s.split("```")
            if len(parts) >= 3 and parts[1].strip():
                s = parts[1].strip()
            else:
                s = s.replace("```", "")
        
        decoder = json.JSONDecoder()
        
        def try_decode(fragment: str) -> Optional[Any]:
            try:
                obj, _ = decoder.raw_decode(fragment)
                return obj
            except Exception:
                return None
        
        # Intentar parsear directamente
        parsed = try_decode(s)
        if parsed is not None:
            # ✅ Validar tipo esperado
            if expect == "list" and isinstance(parsed, list):
                return parsed
            if expect == "object" and isinstance(parsed, dict):
                return parsed
            if expect == "any":
                return parsed
        
        # Buscar JSON en el texto
        first_brace = s.find("{")
        first_bracket = s.find("[")
        idxs: List[int] = []
        if first_brace != -1:
            idxs.append(first_brace)
        if first_bracket != -1:
            idxs.append(first_bracket)
        
        for idx in sorted(idxs):
            candidate = s[idx:]
            parsed = try_decode(candidate)
            if parsed is None:
                continue
            # ✅ Validar tipo esperado
            if expect == "list" and isinstance(parsed, list):
                return parsed
            if expect == "object" and isinstance(parsed, dict):
                return parsed
            if expect == "any":
                return parsed
        
        # Fallback
        return [] if expect == "list" else {}

    def _format_coins_for_tweet(self, coins: List[Dict[str, Any]], trend_emoji: str, change_key: str) -> List[str]:
        """Formatea lista de monedas para tweet."""
        lines: List[str] = []
        for coin in coins:
            change = coin.get(change_key, 0)
            if not isinstance(change, (int, float)) or abs(change) <= 0.0:
                continue
            symbol = str(coin.get("symbol", "N/A")).replace("/USDT", "").replace("/usdt", "")
            lines.append(f"{symbol}{trend_emoji} {change:+.1f}%")
        return lines

    def _filter_and_format_coins(
        self, 
        coins: List[Dict[str, Any]], 
        threshold: float, 
        trend_emoji: str, 
        change_key: str,
        reverse_sort: bool = True
    ) -> Tuple[List[Dict[str, Any]], List[str]]:
        """
        ✅ REFACTORIZADO: Método unificado para filtrar y formatear monedas.
        Reduce duplicación de código.
        """
        # Filtrar por umbral
        if threshold > 0:
            filtered = [coin for coin in coins if coin.get(change_key, 0) > threshold]
        else:
            filtered = [coin for coin in coins if coin.get(change_key, 0) < threshold]
        
        # Ordenar
        sorted_coins = sorted(filtered, key=lambda c: c.get(change_key, 0), reverse=reverse_sort)
        
        # Formatear
        lines = self._format_coins_for_tweet(sorted_coins[:14], trend_emoji, change_key)
        
        return sorted_coins, lines

    def generate_twitter_4_summaries(
        self, 
        market_sentiment: Dict, 
        coins_only_binance: list, 
        coins_both_enriched: list, 
        max_chars: int = 280
    ) -> dict:
        """
        Genera 4 resúmenes para Twitter:
        1. Top subidas 24h (>10%)
        2. Top bajadas 24h (<-10%)
        3. Para las del top subidas 24h, su cambio 2h (si existe)
        4. Para las del top bajadas 24h, su cambio 2h (si existe)
        
        ✅ MEJORADO: Validación de entrada
        """
        # ✅ FIX: Validar market_sentiment
        if not market_sentiment or not isinstance(market_sentiment, dict):
            market_sentiment = {
                'overall_sentiment': 'Análisis',
                'sentiment_emoji': '📊'
            }
        
        sentiment = market_sentiment.get('overall_sentiment', 'Análisis')
        emoji = market_sentiment.get('sentiment_emoji', '📊')

        # ✅ REFACTORIZADO: Usar método unificado
        coins_up_sorted, up_lines = self._filter_and_format_coins(
            coins_only_binance, 10, '📈', 'change_24h', reverse_sort=True
        )
        
        tweet_up_24h = f"{emoji} Top subidas de Cryptos últimas 24h (>10%):\n" + (
            "\n".join(up_lines) if up_lines else "Ninguna moneda subió más de 10%"
        )
        tweet_up_24h = tweet_up_24h.strip()[:max_chars]

        coins_down_sorted, down_lines = self._filter_and_format_coins(
            coins_only_binance, -10, '📉', 'change_24h', reverse_sort=False
        )
        
        tweet_down_24h = f"{emoji} Top bajadas de Cryptos últimas 24h (<-10%):\n" + (
            "\n".join(down_lines) if down_lines else "Ninguna moneda bajó más de 10%"
        )
        tweet_down_24h = tweet_down_24h.strip()[:max_chars]

        # Lookup para cambio 2h
        coins_2h_lookup = {coin['symbol']: coin for coin in coins_both_enriched} if coins_both_enriched else {}
        
        # Top subidas con cambio 2h
        up_2h_lines = []
        for coin in coins_up_sorted[:14]:
            symbol = coin.get('symbol', 'N/A')
            coin_2h = coins_2h_lookup.get(symbol)
            if coin_2h and coin_2h.get('change_2h') is not None and abs(coin_2h.get('change_2h')) > 0.0:
                change_2h = coin_2h.get('change_2h')
                up_2h_lines.append(f"{symbol.replace('/USDT','').replace('/usdt','')}📈 2h:{change_2h:+.1f}%")
        
        if not up_2h_lines and coins_both_enriched:
            coins_up_2h = [coin for coin in coins_both_enriched if coin.get('change_2h', 0) > 0 and abs(coin.get('change_2h', 0)) > 0.0]
            coins_up_2h_sorted = sorted(coins_up_2h, key=lambda c: c.get('change_2h', 0), reverse=True)
            for coin in coins_up_2h_sorted[:14]:
                change_2h = coin.get('change_2h', 0)
                if abs(change_2h) > 0.0:
                    symbol = coin.get('symbol', 'N/A').replace('/USDT','').replace('/usdt','')
                    up_2h_lines.append(f"{symbol}📈 2h:{change_2h:+.1f}%")
        
        tweet_up_2h = f"{emoji} Top subidas de Cryptos últimas 2h:\n" + (
            "\n".join(up_2h_lines) if up_2h_lines else "Ninguna moneda subió en 2h"
        )
        tweet_up_2h = tweet_up_2h.strip()[:max_chars]

        # Top bajadas con cambio 2h
        down_2h_lines = []
        for coin in coins_down_sorted[:14]:
            symbol = coin.get('symbol', 'N/A')
            coin_2h = coins_2h_lookup.get(symbol)
            if coin_2h and coin_2h.get('change_2h') is not None and abs(coin_2h.get('change_2h')) > 0.0:
                change_2h = coin_2h.get('change_2h')
                down_2h_lines.append(f"{symbol.replace('/USDT','').replace('/usdt','')}📉 2h:{change_2h:+.1f}%")
        
        if not down_2h_lines and coins_both_enriched:
            coins_down_2h = [coin for coin in coins_both_enriched if coin.get('change_2h', 0) < 0 and abs(coin.get('change_2h', 0)) > 0.0]
            coins_down_2h_sorted = sorted(coins_down_2h, key=lambda c: c.get('change_2h', 0))
            for coin in coins_down_2h_sorted[:14]:
                change_2h = coin.get('change_2h', 0)
                if abs(change_2h) > 0.0:
                    symbol = coin.get('symbol', 'N/A').replace('/USDT','').replace('/usdt','')
                    down_2h_lines.append(f"{symbol}📉 2h:{change_2h:+.1f}%")
        
        tweet_down_2h = f"{emoji} Top bajadas de Cryptos últimas 2h:\n" + (
            "\n".join(down_2h_lines) if down_2h_lines else "Ninguna moneda bajó en 2h"
        )
        tweet_down_2h = tweet_down_2h.strip()[:max_chars]

        return {
            "up_24h": tweet_up_24h,
            "down_24h": tweet_down_24h,
            "up_2h": tweet_up_2h,
            "down_2h": tweet_down_2h
        }

    def analyze_and_recommend(self, coins: List[Dict], market_sentiment: Dict) -> Dict:
        """
        Analiza mercado y genera recomendaciones usando IA.
        ✅ MEJORADO: Cache con versión
        """
        logger.debug("Analizando datos con IA")

        simplified_coins = self._simplify_coins(coins)
        
        # ✅ Cache con versión
        with self._state_lock:
            last_provider = self._last_success_provider
            last_model = self._last_success_model
        
        cache_key = None
        if last_provider and last_model:
            cache_payload = {
                "task": "analyze_and_recommend",
                "inputs": {
                    "coins": simplified_coins,
                    "market_sentiment": market_sentiment,
                },
                "provider": last_provider,
                "model": last_model,
                "timeout": self._timeout,
            }
            cache_key = self._get_cache_key(cache_payload)
            cached = self._get_cache_value(cache_key)
            if cached is not None:
                logger.debug("Usando caché de análisis IA")
                return cached

        prompt = f"""Eres un analista experto de criptomonedas. Analiza los siguientes datos y genera un reporte conciso:

DATOS DEL MERCADO:
{json.dumps(market_sentiment, ensure_ascii=False)}

CRIPTOMONEDAS CON CAMBIOS SIGNIFICATIVOS:
{json.dumps(simplified_coins, ensure_ascii=False)}

Por favor, proporciona:
1. Un análisis del sentimiento general del mercado (2-3 líneas)
2. Análisis de las top 3 criptomonedas con mayor potencial
3. Tu recomendación principal: ¿Cuál moneda tiene mejor oportunidad de inversión y por qué? (máximo 4 líneas)
4. Un nivel de confianza de tu recomendación (1-10)
5. Advertencias o riesgos principales a considerar

Sé conciso, directo y profesional. Usa emojis relevantes para hacer el texto más amigable."""
        
        try:
            ai_analysis, provider = self._call_with_fallback_robust(prompt, max_tokens=2048)
            
            if not provider:
                logger.error("❌ Fallo en análisis IA - ningún proveedor respondió")
                return {
                    "full_analysis": "⚠️ **ERROR DE IA**\n\nNo se pudo conectar con ningún proveedor de inteligencia artificial. Por favor intente más tarde.",
                    "recommendation": "Sin recomendación (Fallo de IA)",
                    "confidence_level": 0,
                    "ai_status": "FAILED"
                }

            logger.info(f"✅ Análisis de IA completado con {provider}")
            
            result: Dict[str, Any] = {
                "full_analysis": ai_analysis,
                "dataset_provider": provider,
                "ai_status": "ONLINE",
                "market_overview": self._extract_section(ai_analysis, 1),
                "top_coins_analysis": self._extract_section(ai_analysis, 2),
                "recommendation": self._extract_section(ai_analysis, 3),
                "confidence_level": self._extract_confidence(ai_analysis),
                "warnings": self._extract_section(ai_analysis, 5),
                "timestamp": market_sentiment.get("fear_greed_index", {}).get("timestamp", ""),
            }

            # Análisis JSON adicional
            json_prompt = f"""Devuelve en JSON válido las mejores oportunidades:
{{
  "top_buys": [
    {{"symbol": "SYM1", "reason": "breve razón"}},
    {{"symbol": "SYM2", "reason": "breve razón"}},
    {{"symbol": "SYM3", "reason": "breve razón"}}
  ],
  "top_sells": [
    {{"symbol": "SYM1", "reason": "breve razón"}},
    {{"symbol": "SYM2", "reason": "breve razón"}},
    {{"symbol": "SYM3", "reason": "breve razón"}}
  ],
  "confidence": 1-10
}}
Basado en estas monedas y datos:
Monedas: {json.dumps(simplified_coins, ensure_ascii=False)}
Sentimiento: {json.dumps(market_sentiment, ensure_ascii=False)}
Responde SOLO el JSON."""
            
            try:
                jr_text, _ = self._call_with_fallback_robust(json_prompt, max_tokens=512, min_chars=1)
                parsed = self._extract_json_safe(jr_text, expect="object")
                if isinstance(parsed, dict):
                    result["top_buys"] = parsed.get("top_buys", [])
                    result["top_sells"] = parsed.get("top_sells", [])
                    conf = parsed.get("confidence")
                    if isinstance(conf, int) and 1 <= conf <= 10:
                        result["confidence_level"] = conf
            except Exception:
                pass

            # Guardar en cache
            if cache_key:
                self._set_cache_value(cache_key, result)
            
            return result
            
        except Exception as e:
            if not self._is_quota_error(e):
                logger.debug("Error al analizar con IA")
            return {
                "full_analysis": "Error al generar análisis",
                "recommendation": "No se pudo generar recomendación",
                "confidence_level": 0,
            }

    def _extract_section(self, text: str, section_number: int) -> str:
        """Extrae una sección numerada del texto."""
        try:
            lines = text.split('\n')
            section_lines = []
            capture = False
            for line in lines:
                if line.strip().startswith(f"{section_number}.") or line.strip().startswith(f"**{section_number}."):
                    capture = True
                    section_lines.append(line.split('.', 1)[1].strip() if '.' in line else line)
                    continue
                elif capture and any(line.strip().startswith(f"{i}.") or line.strip().startswith(f"**{i}.") for i in range(1, 10)):
                    break
                elif capture and line.strip():
                    section_lines.append(line)
            return '\n'.join(section_lines).strip()
        except:
            return "N/A"

    def _extract_confidence(self, text: str) -> int:
        """Extrae nivel de confianza del texto."""
        try:
            patterns = [
                r'(\d+)/10',
                r'(\d+)\s*de\s*10',
                r'nivel\s*(\d+)',
                r'confianza.*?(\d+)',
            ]
            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    confidence = int(match.group(1))
                    return min(confidence, 10)
            return 0
        except:
            return 0

    def generate_short_summaries(
        self, 
        analysis: Dict, 
        market_sentiment: Dict, 
        coins_only_binance: list, 
        max_chars: int = 280, 
        coins_both_enriched: list = None
    ) -> dict:
        """
        Genera resúmenes cortos para Twitter.
        ✅ MEJORADO: Validación de entrada
        """
        try:
            # ✅ FIX: Validar market_sentiment
            if not market_sentiment or not isinstance(market_sentiment, dict):
                market_sentiment = {
                    'overall_sentiment': 'Análisis',
                    'sentiment_emoji': '📊'
                }
            
            sentiment = market_sentiment.get('overall_sentiment', 'Análisis')
            emoji = market_sentiment.get('sentiment_emoji', '📊')
            
            # Lookup para cambio 2h
            coins_2h_lookup = {}
            if coins_both_enriched:
                coins_2h_lookup = {coin['symbol']: coin for coin in coins_both_enriched}
            
            def build_tweet(coins_list, trend_emoji):
                lines = []
                for coin in coins_list[:10]:
                    symbol = coin.get('symbol', 'N/A').replace('/USDT', '').replace('/usdt', '')
                    change_24h = coin.get('change_24h', 0)
                    # Buscar cambio 2h
                    change_2h = None
                    if coins_both_enriched:
                        for coin_both in coins_both_enriched:
                            if coin_both.get('symbol') == coin.get('symbol') and coin_both.get('change_2h') is not None:
                                change_2h = coin_both.get('change_2h')
                                break
                    if change_2h is None:
                        change_2h = coin.get('change_2h', None)
                    
                    line = f"{symbol}{trend_emoji} {change_24h:+.1f}% 2h:"
                    if change_2h is not None:
                        line += f"{change_2h:+.1f}%"
                    else:
                        line += "N/A"
                    lines.append(line)
                return "\n".join(lines)
            
            # Subidas: Top 10 por 24h > 10%
            coins_up_24h = [coin for coin in coins_only_binance if coin.get('change_24h', 0) > 10]
            coins_up_sorted = sorted(coins_up_24h, key=lambda c: c.get('change_24h', 0), reverse=True)
            up_lines = build_tweet(coins_up_sorted, '📈')
            tweet_up = f"{emoji} {sentiment}. Top:\n{up_lines}" if up_lines else f"{emoji} {sentiment}. Top:\nNinguna moneda subió más de 10%"
            tweet_up = tweet_up.strip()
            if len(tweet_up) > max_chars:
                tweet_up = tweet_up[:max_chars].rstrip(' .,;:\n')
            
            # Bajadas: Top 10 por 24h < -10%
            coins_down_24h = [coin for coin in coins_only_binance if coin.get('change_24h', 0) < -10]
            coins_down_sorted = sorted(coins_down_24h, key=lambda c: c.get('change_24h', 0))
            down_lines = build_tweet(coins_down_sorted, '📉')
            tweet_down = f"{emoji} {sentiment}. Top:\n{down_lines}" if down_lines else f"{emoji} {sentiment}. Top:\nNinguna moneda bajó más de 10%"
            tweet_down = tweet_down.strip()
            if len(tweet_down) > max_chars:
                tweet_down = tweet_down[:max_chars].rstrip(' .,;:\n')
            
            return {"up": tweet_up, "down": tweet_down}
            
        except Exception as e:
            if not self._is_quota_error(e):
                logger.debug("Error al generar tweet")
            return {
                "up": "📊 Análisis de mercado cripto actualizado.", 
                "down": "📊 Análisis de mercado cripto actualizado."
            }
    
    def analyze_complete_market_batch(
        self, 
        coins: list, 
        market_sentiment: dict, 
        news_titles: list = None
    ) -> dict:
        """
        Analiza TODO en un solo lote para minimizar llamadas a IA.
        ✅ MEJORADO: Validación de entrada
        """
        logger.info("🤖 Ejecutando análisis BATCH completo con IA")
        logger.info(f"   📊 {len(coins)} monedas, {len(news_titles or [])} noticias")
        
        # ✅ FIX: Validar entradas
        if not coins:
            coins = []
        if not market_sentiment or not isinstance(market_sentiment, dict):
            market_sentiment = {
                'fear_greed_index': {'value': 50},
                'overall_sentiment': 'Neutral',
                'market_trend': 'Lateral'
            }
        
        # Simplificar datos para reducir tokens
        simplified_coins = self._simplify_coins(coins)
        simplified_sentiment = {
            'fear_greed': market_sentiment.get('fear_greed_index', {}).get('value', 50),
            'sentiment': market_sentiment.get('overall_sentiment', 'Neutral'),
            'trend': market_sentiment.get('market_trend', 'Lateral')
        }
        
        # Construir mega-prompt con TODO
        mega_prompt = f"""Eres un analista experto de mercados financieros y criptomonedas.

Analiza TODOS los siguientes datos en un solo análisis y devuelve un JSON estructurado con TODO.

═══════════════════════════════════════════════════════
📊 DATOS DEL MERCADO:
{json.dumps(simplified_sentiment, ensure_ascii=False)}

🪙 CRIPTOMONEDAS (Top cambios 24h):
{json.dumps(simplified_coins[:20], ensure_ascii=False)}

📰 NOTICIAS RECIENTES:
{json.dumps(news_titles[:30] if news_titles else [], ensure_ascii=False)}
═══════════════════════════════════════════════════════

RESPONDE EN UN SOLO JSON CON ESTA ESTRUCTURA EXACTA:

{{
  "market_analysis": {{
    "overview": "<2-3 líneas sobre estado general del mercado>",
    "sentiment_interpretation": "<qué significa el Fear & Greed actual>",
    "key_trends": ["<tendencia 1>", "<tendencia 2>", "<tendencia 3>"]
  }},
  
  "crypto_recommendations": {{
    "top_buys": [
      {{"symbol": "BTC", "reason": "<razón breve>", "confidence": 1-10}},
      {{"symbol": "ETH", "reason": "<razón breve>", "confidence": 1-10}},
      {{"symbol": "...", "reason": "<razón breve>", "confidence": 1-10}}
    ],
    "top_sells": [
      {{"symbol": "...", "reason": "<razón breve>", "confidence": 1-10}},
      {{"symbol": "...", "reason": "<razón breve>", "confidence": 1-10}}
    ],
    "overall_confidence": 1-10
  }},
  
  "news_analysis": [
    {{
      "index": <índice original en lista>,
      "score": 6-10,
      "summary": "<resumen 1 línea>",
      "category": "crypto|markets|signals"
    }},
    ...
  ],
  
  "trading_summary": {{
    "main_recommendation": "<recomendación principal en 3-4 líneas>",
    "risk_level": "bajo|medio|alto",
    "confidence": 1-10,
    "warnings": ["<advertencia 1>", "<advertencia 2>"]
  }}
}}

IMPORTANTE:
- Responde SOLO el JSON, sin texto adicional
- Usa análisis objetivo basado en datos
- Sé conciso pero preciso
- Incluye TODOS los análisis en esta única respuesta
"""
        
        try:
            # UNA SOLA LLAMADA a IA
            response_text, provider_used = self._call_with_fallback_robust(
                mega_prompt, 
                max_tokens=4096
            )
            
            logger.info(f"✅ Análisis batch completado usando: {provider_used}")
            logger.info(f"   📏 Respuesta: {len(response_text)} caracteres")
            
            # Parsear JSON
            parsed = self._extract_json_safe(response_text, expect="object")
            
            if not isinstance(parsed, dict):
                logger.error("❌ IA no retornó JSON válido")
                return self._generate_fallback_analysis()
            
            # Desglosar en estructura legible
            result = {
                'market_analysis': parsed.get('market_analysis', {}),
                'crypto_recommendations': parsed.get('crypto_recommendations', {}),
                'news_analysis': parsed.get('news_analysis', []),
                'trading_summary': parsed.get('trading_summary', {}),
                'raw_response': response_text,
                'provider_used': provider_used
            }
            
            logger.info("✅ Análisis batch desglosado correctamente")
            logger.info(f"   📰 {len(result['news_analysis'])} noticias analizadas")
            logger.info(f"   🎯 Confianza general: {result['trading_summary'].get('confidence', 0)}/10")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Error en análisis batch: {e}")
            return self._generate_fallback_analysis()

    def _generate_fallback_analysis(self) -> dict:
        """Genera análisis fallback cuando IA falla."""
        return {
            'market_analysis': {
                'overview': 'Análisis no disponible temporalmente',
                'sentiment_interpretation': 'Servicio de IA en mantenimiento',
                'key_trends': []
            },
            'crypto_recommendations': {
                'top_buys': [],
                'top_sells': [],
                'overall_confidence': 0
            },
            'news_analysis': [],
            'trading_summary': {
                'main_recommendation': 'No se pudo generar recomendación automática. Revisa datos manualmente.',
                'risk_level': 'alto',
                'confidence': 0,
                'warnings': ['Servicio de IA temporalmente no disponible']
            }
        }
    
    def analyze_news_batch(self, news_titles: List[str]) -> List[Dict]:
        """
        Analiza un lote de noticias y selecciona las más importantes.
        """
        if not news_titles:
            return []
            
        # Preparar el prompt
        titles_formatted = "\n".join([f"{i}. {title}" for i, title in enumerate(news_titles)])
        
        prompt = f"""Eres un experto analista de noticias financieras y criptomonedas.
Analiza la siguiente lista de titulares de noticias y selecciona ÚNICAMENTE las más importantes y relevantes (impacto medio/alto en el mercado).

LISTA DE NOTICIAS:
{titles_formatted}

INSTRUCCIONES:
1. Ignora noticias irrelevantes, spam, o de bajo impacto.
2. Selecciona las noticias con score de relevancia >= 7 sobre 10.
3. Clasifica cada noticia en: 'crypto' (general), 'markets' (bolsa/forex/macro), 'signals' (señales de trading específicas).
4. Devuelve el resultado en formato JSON puro (sin markdown).

FORMATO DE RESPUESTA JSON (Lista de objetos):
[
  {{
    "original_index": <número del índice original en la lista>,
    "score": <número 7-10>,
    "summary": "<Resumen de 1 linea en español>",
    "category": "<crypto|markets|signals>"
  }},
  ...
]
"""
        try:
            text, _ = self._call_with_fallback_robust(prompt, max_tokens=1024)
            if not text:
                return []

            results = self._extract_json_safe(text, expect="list")
            valid_results: List[Dict[str, Any]] = []
            if isinstance(results, list):
                for item in results:
                    if isinstance(item, dict) and 'original_index' in item and 'score' in item:
                        valid_results.append(item)

            logger.debug(f"Análisis por lote completado. Seleccionadas {len(valid_results)} noticias relevantes.")
            return valid_results
        except Exception as e:
            if not self._is_quota_error(e):
                logger.debug("Error en análisis por lote de noticias")
            return []

    def analyze_text(self, text: str, context: str = "") -> Dict:
        """
        Analiza un texto genérico y devuelve un score de relevancia.
        """
        try:
            prompt = f"""Analiza la siguiente noticia y asigna un score de relevancia del 0 al 10.
            
Noticia: {text}
            
Responde SOLO con un JSON en este formato:
{{
    "score": <número del 0 al 10>,
    "summary": "<resumen breve en 1 línea>"
}}
            
Criterios:
- 10: Noticia extremadamente importante (crash, regulación mayor, hack grande)
- 7-9: Noticia muy relevante (movimientos significativos, anuncios importantes)
- 4-6: Noticia moderadamente interesante
- 1-3: Noticia poco relevante
- 0: Spam o irrelevante"""

            result_text, _ = self._call_with_fallback_robust(prompt, max_tokens=512)
            if not result_text:
                return {"score": 5, "summary": text[:100]}

            parsed = self._extract_json_safe(result_text, expect="object")
            if not isinstance(parsed, dict):
                return {"score": 5, "summary": text[:100]}

            score_raw = parsed.get("score", 5)
            summary_raw = parsed.get("summary", text[:100])

            try:
                score = int(score_raw)
            except Exception:
                score = 5

            score = max(0, min(score, 10))
            summary = str(summary_raw) if summary_raw is not None else text[:100]

            return {"score": score, "summary": summary}

        except Exception as e:
            if not self._is_quota_error(e):
                logger.debug("Error en analyze_text")
            return {"score": 5, "summary": text[:100]}

    def classify_news_category(self, title: str, summary: str = "") -> Dict:
        """
        Clasifica una noticia en 'crypto', 'markets' o 'signals'.
        ✅ MEJORADO: Usa constante VALID_CATEGORIES
        """
        try:
            prompt = f"""Clasifica la noticia en UNA sola categoría: crypto, markets o signals.
Titulo: {title}
Resumen: {summary}

Reglas:
- crypto: todo lo relacionado con criptomonedas, exchanges, tokens, DeFi, blockchain.
- markets: acciones, índices bursátiles, forex, commodities, macroeconomía tradicional.
- signals: alertas de trading, oportunidades LONG/SHORT, setups técnicos, pumps/dumps.

Responde SOLO con JSON:
{{
  "category": "<crypto|markets|signals>",
  "confidence": <entero 0-10>
}}"""
            result_text, _ = self._call_with_fallback_robust(prompt, max_tokens=512)
            if not result_text:
                return {"category": "crypto", "confidence": 5}

            parsed = self._extract_json_safe(result_text, expect="object")
            if not isinstance(parsed, dict):
                return {"category": "crypto", "confidence": 5}

            category_raw = str(parsed.get("category", "crypto")).lower()
            # ✅ Usar constante
            if category_raw not in VALID_CATEGORIES:
                category_raw = "crypto"

            confidence_raw = parsed.get("confidence", 7)
            try:
                confidence = int(confidence_raw)
            except Exception:
                confidence = 7
            confidence = min(max(confidence, 0), 10)

            return {"category": category_raw, "confidence": confidence}
        except Exception as e:
            if not self._is_quota_error(e):
                logger.debug("Error en classify_news_category")
            return {"category": "crypto", "confidence": 5}

    def get_stats(self) -> Dict[str, Dict[str, Any]]:
        """Obtiene estadísticas de uso de proveedores."""
        stats: Dict[str, Dict[str, Any]] = {}
        for provider in ("ollama", "gemini", "openrouter", "huggingface"):
            if provider in self._providers:
                with self._state_lock:
                    requests = self._metrics["requests"][provider]
                    failures = self._metrics["failures"][provider]
                    total_time = self._metrics["total_time"][provider]
                avg_time = total_time / requests if requests else 0.0
                stats[provider] = {
                    "requests": requests, 
                    "failures": failures, 
                    "avg_response_time": avg_time
                }
        return stats
