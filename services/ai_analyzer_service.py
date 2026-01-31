"""
Servicio de análisis con IA utilizando múltiples proveedores (Gemini, OpenAI, OpenRouter).
Analiza los datos del mercado y genera recomendaciones.
"""

import concurrent.futures
import hashlib
import json
import re
import time
import warnings
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple

import google.generativeai as genai
import openai

from config.config import Config
from utils.logger import logger


warnings.filterwarnings("ignore", category=FutureWarning, module="google.generativeai")


@dataclass
class AIAnalyzerConfig:
    """Configuración del servicio de análisis con IA."""

    DEFAULT_TIMEOUT: int = 30
    CACHE_TTL: int = 300
    MAX_COINS_IN_PROMPT: int = 10
    GEMINI_TEMPERATURE: float = 0.7
    OPENAI_MODEL: str = "gpt-4o-mini"


class AIAnalyzerService:

    def __init__(self, config: Optional[AIAnalyzerConfig] = None) -> None:
        self.config = config or AIAnalyzerConfig()

        self.active_provider: Optional[str] = None
        self._cycle_provider_ok: bool = False
        self.gemini_model: Optional[Any] = None
        self.openai_client: Optional[Any] = None
        self.openrouter_client: Optional[Any] = None
        self.openrouter_model: str = "tngtech/deepseek-r1t2-chimera:free"

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

        try:
            api_key = getattr(Config, "GOOGLE_GEMINI_API_KEY", "") or ""
            if api_key.strip():
                genai.configure(api_key=api_key)
                generation_config = {
                    "temperature": self.config.GEMINI_TEMPERATURE,
                    "top_p": 0.95,
                    "top_k": 40,
                    "max_output_tokens": 2048,
                }
                safety_settings = [
                    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                    {
                        "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                        "threshold": "BLOCK_MEDIUM_AND_ABOVE",
                    },
                    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                ]
                self.gemini_model = genai.GenerativeModel(
                    model_name="gemini-2.5-flash",
                    generation_config=generation_config,
                    safety_settings=safety_settings,
                )
                self._providers["gemini"] = self.gemini_model
            else:
                logger.debug("Google Gemini API key no configurada")
        except Exception as e:
            logger.debug("Error al configurar Gemini")

        try:
            api_key = getattr(Config, "OPENAI_API_KEY", "") or ""
            if api_key.strip():
                self.openai_client = openai.OpenAI(api_key=api_key)
                self._providers["openai"] = self.openai_client
            else:
                logger.debug("OpenAI API key no configurada")
        except Exception as e:
            logger.debug("Error al configurar OpenAI")

        try:
            api_key = getattr(Config, "OPENROUTER_API_KEY", "") or ""
            if api_key.strip():
                self.openrouter_client = openai.OpenAI(
                    api_key=api_key,
                    base_url="https://openrouter.ai/api/v1",
                )
                self._providers["openrouter"] = self.openrouter_client
            else:
                logger.debug("OpenRouter API key no configurada")
        except Exception as e:
            logger.debug("Error al configurar OpenRouter")

        self.check_best_provider()

    def _run_with_timeout(self, fn: Callable[[], Any], timeout_seconds: int) -> Any:
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(fn)
                return future.result(timeout=timeout_seconds)
        except Exception as e:
            return e

    def _is_quota_error(self, e: Exception) -> bool:
        s = str(e).lower()
        return "429" in s or "rate limit" in s or "insufficient_quota" in s or "quota" in s

    def _get_provider_priority_list(self) -> List[str]:
        available: List[str] = []
        if self.gemini_model:
            available.append("gemini")
        if self.openai_client:
            available.append("openai")
        if self.openrouter_client:
            available.append("openrouter")

        if not available:
            return []

        providers: List[str] = []
        if self.active_provider in available:
            providers.append(self.active_provider)  # type: ignore[arg-type]
        providers.extend(p for p in available if p not in providers)
        return providers

    def _call_provider(self, provider: str, prompt: str, max_tokens: int = 2048) -> str:
        start = time.time()
        self._metrics["requests"][provider] += 1

        def _call() -> str:
            if provider == "gemini":
                if not self.gemini_model:
                    raise RuntimeError("Gemini no configurado")
                response = self.gemini_model.generate_content(prompt)
                text = getattr(response, "text", "") or ""
                if not text:
                    raise RuntimeError("Respuesta vacía de Gemini")
                return text

            if provider == "openai":
                if not self.openai_client:
                    raise RuntimeError("OpenAI no configurado")
                response = self.openai_client.chat.completions.create(
                    model=self.config.OPENAI_MODEL,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=max_tokens,
                    timeout=self._timeout,
                )
                if not response.choices:
                    raise RuntimeError("Respuesta vacía de OpenAI")
                return response.choices[0].message.content or ""

            if provider == "openrouter":
                if not self.openrouter_client:
                    raise RuntimeError("OpenRouter no configurado")
                response = self.openrouter_client.chat.completions.create(
                    model=self.openrouter_model,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=max_tokens,
                    timeout=self._timeout,
                )
                if not response.choices:
                    raise RuntimeError("Respuesta vacía de OpenRouter")
                return response.choices[0].message.content or ""

            raise RuntimeError("Proveedor inválido")

        result = self._run_with_timeout(_call, timeout_seconds=self._timeout)
        if isinstance(result, Exception):
            self._metrics["failures"][provider] += 1
            raise result

        elapsed = time.time() - start
        self._metrics["total_time"][provider] += elapsed
        return str(result)

    def _call_with_fallback(self, prompt: str, max_tokens: int = 2048) -> Tuple[str, Optional[str]]:
        providers = self._get_provider_priority_list()
        if not providers:
            return "", None

        last_error: Optional[Exception] = None
        for provider in providers:
            try:
                text = self._call_provider(provider, prompt, max_tokens=max_tokens)
                self._cycle_provider_ok = True
                return text, provider
            except Exception as e:
                last_error = e
                if not self._is_quota_error(e):
                    logger.debug("Fallo generando contenido")

        return "", None

    def reset_cycle_status(self) -> None:
        self._cycle_provider_ok = False

    def get_cycle_status(self) -> bool:
        return self._cycle_provider_ok

    def _test_gemini(self) -> Any:
        if not self.gemini_model:
            return RuntimeError("Gemini no configurado")
        response = self.gemini_model.generate_content("Hola")
        if not response or not response.text:
            return RuntimeError("Respuesta vacía de Gemini")
        return True

    def _test_openai(self) -> Any:
        if not self.openai_client:
            return RuntimeError("OpenAI no configurado")
        response = self.openai_client.chat.completions.create(
            model=self.config.OPENAI_MODEL,
            messages=[{"role": "user", "content": "Hola"}],
            max_tokens=5,
            timeout=self._timeout,
        )
        if not response.choices:
            return RuntimeError("Respuesta vacía de OpenAI")
        return True

    def _test_openrouter(self) -> Any:
        if not self.openrouter_client:
            return RuntimeError("OpenRouter no configurado")
        response = self.openrouter_client.chat.completions.create(
            model=self.openrouter_model,
            messages=[{"role": "user", "content": "Hola"}],
            max_tokens=5,
            timeout=self._timeout,
        )
        if not response.choices:
            return RuntimeError("Respuesta vacía de OpenRouter")
        return True

    def check_best_provider(self) -> None:
        """Verifica qué API responde y selecciona la activa para este ciclo."""
        # 1. Probar Gemini
        try:
            if self.gemini_model:
                result = self._run_with_timeout(self._test_gemini, timeout_seconds=6)
                if result is True:
                    self.active_provider = 'gemini'
                    return
                if isinstance(result, Exception):
                    raise result
        except Exception as e:
            if not self._is_quota_error(e):
                logger.debug("Gemini no disponible")

        # 2. Probar OpenAI (Fallback)
        try:
            if self.openai_client:
                result = self._run_with_timeout(self._test_openai, timeout_seconds=6)
                if result is True:
                    self.active_provider = 'openai'
                    return
                if isinstance(result, Exception):
                    raise result
        except Exception as e:
            if not self._is_quota_error(e):
                logger.debug("OpenAI no disponible")

        # 3. Probar OpenRouter (Fallback)
        try:
            if self.openrouter_client:
                result = self._run_with_timeout(self._test_openrouter, timeout_seconds=6)
                if result is True:
                    self.active_provider = 'openrouter'
                    return
                if isinstance(result, Exception):
                    raise result
        except Exception as e:
            if not self._is_quota_error(e):
                logger.debug("OpenRouter no disponible")
            
        self.active_provider = None

    def _generate_content(self, prompt: str, max_tokens: int = 2048) -> str:
        text, _ = self._call_with_fallback(prompt, max_tokens=max_tokens)
        return text

    def _simplify_coins(self, coins: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
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

    def _get_cache_key(self, *parts: str) -> str:
        raw = "||".join(parts)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def _is_cache_valid(self, key: str) -> bool:
        ts = self._cache_timestamps.get(key)
        if ts is None:
            return False
        return (time.time() - ts) < self._cache_ttl

    def _extract_json_safe(self, text: str, expect: str = "object") -> Any:
        if not text:
            return [] if expect == "list" else {}

        cleaned = text.strip().replace("\r", "")
        cleaned = cleaned.replace("```json", "```")

        if "```" in cleaned:
            parts = cleaned.split("```")
            if len(parts) >= 3:
                cleaned = parts[1]
            else:
                cleaned = cleaned.replace("```", "")

        obj_match = re.search(r"\{.*?\}", cleaned, re.DOTALL)
        list_match = re.search(r"\[.*?\]", cleaned, re.DOTALL)

        candidates: List[str] = []
        if expect == "list":
            if list_match:
                candidates.append(list_match.group(0))
        elif expect == "object":
            if obj_match:
                candidates.append(obj_match.group(0))
        else:
            if obj_match:
                candidates.append(obj_match.group(0))
            if list_match:
                candidates.append(list_match.group(0))

        for candidate in candidates:
            try:
                parsed = json.loads(candidate)
                if expect == "list" and isinstance(parsed, list):
                    return parsed
                if expect == "object" and isinstance(parsed, dict):
                    return parsed
                if expect == "any":
                    return parsed
            except Exception:
                continue

        return [] if expect == "list" else {}

    def _format_coins_for_tweet(self, coins: List[Dict[str, Any]], trend_emoji: str, change_key: str) -> List[str]:
        lines: List[str] = []
        for coin in coins:
            change = coin.get(change_key, 0)
            if not isinstance(change, (int, float)) or abs(change) <= 0.0:
                continue
            symbol = str(coin.get("symbol", "N/A")).replace("/USDT", "").replace("/usdt", "")
            lines.append(f"{symbol}{trend_emoji} {change:+.1f}%")
        return lines

    def generate_twitter_4_summaries(self, market_sentiment: Dict, coins_only_binance: list, coins_both_enriched: list, max_chars: int = 280) -> dict:
        """
        Genera 4 resúmenes para Twitter:
        1. Top subidas 24h (>10%)
        2. Top bajadas 24h (<-10%)
        3. Para las del top subidas 24h, su cambio 2h (si existe)
        4. Para las del top bajadas 24h, su cambio 2h (si existe)
        """
        sentiment = market_sentiment.get('overall_sentiment', 'Análisis')
        emoji = market_sentiment.get('sentiment_emoji', '📊')

        coins_up_24h = [coin for coin in coins_only_binance if coin.get('change_24h', 0) > 10 and abs(coin.get('change_24h', 0)) > 0.0]
        coins_up_sorted = sorted(coins_up_24h, key=lambda c: c.get('change_24h', 0), reverse=True)[:14]
        up_lines = self._format_coins_for_tweet(coins_up_sorted, '📈', 'change_24h')
        tweet_up_24h = f"{emoji} Top subidas de Cryptos últimas 24h (>10%):\n" + ("\n".join(up_lines) if up_lines else "Ninguna moneda subió más de 10%")
        tweet_up_24h = tweet_up_24h.strip()[:max_chars]

        coins_down_24h = [coin for coin in coins_only_binance if coin.get('change_24h', 0) < -10 and abs(coin.get('change_24h', 0)) > 0.0]
        coins_down_sorted = sorted(coins_down_24h, key=lambda c: c.get('change_24h', 0))[:14]
        down_lines = self._format_coins_for_tweet(coins_down_sorted, '📉', 'change_24h')
        tweet_down_24h = f"{emoji} Top bajadas de Cryptos últimas 24h (<-10%):\n" + ("\n".join(down_lines) if down_lines else "Ninguna moneda bajó más de 10%")
        tweet_down_24h = tweet_down_24h.strip()[:max_chars]


        coins_2h_lookup = {coin['symbol']: coin for coin in coins_both_enriched} if coins_both_enriched else {}
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
        tweet_up_2h = f"{emoji} Top subidas de Cryptos últimas 2h:\n" + ("\n".join(up_2h_lines) if up_2h_lines else "Ninguna moneda subió en 2h")
        tweet_up_2h = tweet_up_2h.strip()[:max_chars]

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
        tweet_down_2h = f"{emoji} Top bajadas de Cryptos últimas 2h:\n" + ("\n".join(down_2h_lines) if down_2h_lines else "Ninguna moneda bajó en 2h")
        tweet_down_2h = tweet_down_2h.strip()[:max_chars]

        return {
            "up_24h": tweet_up_24h,
            "down_24h": tweet_down_24h,
            "up_2h": tweet_up_2h,
            "down_2h": tweet_down_2h
        }

    def analyze_and_recommend(self, coins: List[Dict], market_sentiment: Dict) -> Dict:
        logger.debug("Analizando datos con IA")

        simplified_coins = self._simplify_coins(coins)
        cache_key = self._get_cache_key(
            "analyze_and_recommend",
            json.dumps(simplified_coins, ensure_ascii=False, sort_keys=True),
            json.dumps(market_sentiment, ensure_ascii=False, sort_keys=True),
        )

        if self._is_cache_valid(cache_key):
            logger.debug("Usando caché de análisis IA")
            return self._cache[cache_key]

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
            ai_analysis, _provider = self._call_with_fallback(prompt, max_tokens=2048)
            logger.debug("Análisis de IA completado")
            result: Dict[str, Any] = {
                "full_analysis": ai_analysis,
                "market_overview": self._extract_section(ai_analysis, 1),
                "top_coins_analysis": self._extract_section(ai_analysis, 2),
                "recommendation": self._extract_section(ai_analysis, 3),
                "confidence_level": self._extract_confidence(ai_analysis),
                "warnings": self._extract_section(ai_analysis, 5),
                "timestamp": market_sentiment.get("fear_greed_index", {}).get("timestamp", ""),
            }

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
                jr_text, _ = self._call_with_fallback(json_prompt, max_tokens=512)
                parsed = self._extract_json_safe(jr_text, expect="object")
                if isinstance(parsed, dict):
                    result["top_buys"] = parsed.get("top_buys", [])
                    result["top_sells"] = parsed.get("top_sells", [])
                    conf = parsed.get("confidence")
                    if isinstance(conf, int) and 1 <= conf <= 10:
                        result["confidence_level"] = conf
            except Exception:
                pass

            self._cache[cache_key] = result
            self._cache_timestamps[cache_key] = time.time()
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

    def generate_short_summaries(self, analysis: Dict, market_sentiment: Dict, coins_only_binance: list, max_chars: int = 280, coins_both_enriched: list = None) -> dict:
        try:
            sentiment = market_sentiment.get('overall_sentiment', 'Análisis')
            emoji = market_sentiment.get('sentiment_emoji', '📊')
            # Para buscar el cambio 2h si existe en coins_both_enriched
            coins_2h_lookup = {}
            if coins_both_enriched:
                coins_2h_lookup = {coin['symbol']: coin for coin in coins_both_enriched}
            def build_tweet(coins_list, trend_emoji):
                lines = []
                for coin in coins_list[:10]:
                    symbol = coin.get('symbol', 'N/A').replace('/USDT', '').replace('/usdt', '')
                    change_24h = coin.get('change_24h', 0)
                    # Buscar el cambio 2h en coins_both_enriched (aunque la moneda sea solo de Binance)
                    change_2h = None
                    if coins_both_enriched:
                        for coin_both in coins_both_enriched:
                            if coin_both.get('symbol') == coin.get('symbol') and coin_both.get('change_2h') is not None:
                                change_2h = coin_both.get('change_2h')
                                break
                    # Si no hay dato en coins_both_enriched, buscar en el propio coin (por si acaso)
                    if change_2h is None:
                        change_2h = coin.get('change_2h', None)
                    line = f"{symbol}{trend_emoji} {change_24h:+.1f}% 2h:"
                    if change_2h is not None:
                        line += f"{change_2h:+.1f}%"
                    else:
                        line += "N/A"
                    lines.append(line)
                return "\n".join(lines)
            # Subidas: Top 10 por 24h > 10% (solo Binance, igual que Telegram)
            coins_up_24h = [coin for coin in coins_only_binance if coin.get('change_24h', 0) > 10]
            coins_up_sorted = sorted(coins_up_24h, key=lambda c: c.get('change_24h', 0), reverse=True)
            up_lines = build_tweet(coins_up_sorted, '📈')
            tweet_up = f"{emoji} {sentiment}. Top:\n{up_lines}" if up_lines else f"{emoji} {sentiment}. Top:\nNinguna moneda subió más de 10%"
            tweet_up = tweet_up.strip()
            if len(tweet_up) > max_chars:
                tweet_up = tweet_up[:max_chars].rstrip(' .,;:\n')
            coins_down_24h = [coin for coin in coins_only_binance if coin.get('change_24h', 0) < -10]
            coins_down_sorted = sorted(coins_down_24h, key=lambda c: c.get('change_24h', 0))
            down_lines = build_tweet(coins_down_sorted, '📉')
            tweet_down = f"{emoji} {sentiment}. Top:\n{down_lines}" if down_lines else f"{emoji} {sentiment}. Top:\nNinguna moneda bajó más de 10% (debug: {len(coins_down_24h)} detectadas)"
            tweet_down = tweet_down.strip()
            if len(tweet_down) > max_chars:
                tweet_down = tweet_down[:max_chars].rstrip(' .,;:\n')
            return {"up": tweet_up, "down": tweet_down}
        except Exception as e:
            if not self._is_quota_error(e):
                logger.debug("Error al generar tweet")
            return {"up": "📊 Análisis de mercado cripto actualizado.", "down": "📊 Análisis de mercado cripto actualizado."}
    
    def analyze_news_batch(self, news_titles: List[str]) -> List[Dict]:
        """
        Analiza un lote de noticias y selecciona las más importantes.
        Soporta Gemini, OpenAI y OpenRouter.
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
            text, _ = self._call_with_fallback(prompt, max_tokens=1024)
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
        Usado para filtrar noticias.
        
        Args:
            text: Texto a analizar
            context: Contexto adicional (opcional)
            
        Returns:
            Dict con 'score' (0-10) y 'summary'
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

            result_text, _ = self._call_with_fallback(prompt, max_tokens=512)
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
        Usa título y resumen para mejorar la precisión.
        Returns:
            Dict con 'category' y 'confidence' (0-10)
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
            result_text, _ = self._call_with_fallback(prompt, max_tokens=512)
            if not result_text:
                return {"category": "crypto", "confidence": 5}

            parsed = self._extract_json_safe(result_text, expect="object")
            if not isinstance(parsed, dict):
                return {"category": "crypto", "confidence": 5}

            category_raw = str(parsed.get("category", "crypto")).lower()
            if category_raw not in ("crypto", "markets", "signals"):
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
        stats: Dict[str, Dict[str, Any]] = {}
        for provider in ("gemini", "openai", "openrouter"):
            if provider in self._providers:
                requests = self._metrics["requests"][provider]
                failures = self._metrics["failures"][provider]
                total_time = self._metrics["total_time"][provider]
                avg_time = total_time / requests if requests else 0.0
                stats[provider] = {
                    "requests": requests,
                    "failures": failures,
                    "avg_response_time": avg_time,
                }
        return stats
