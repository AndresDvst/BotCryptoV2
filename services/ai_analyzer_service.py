"""
Servicio de análisis con IA utilizando Google Gemini.
Analiza los datos del mercado y genera recomendaciones.
"""
import warnings
warnings.filterwarnings("ignore", category=FutureWarning, module="google.generativeai")
import google.generativeai as genai
import openai
from typing import Dict, List, Optional
import concurrent.futures
from config.config import Config
from utils.logger import logger
import json
import re

class AIAnalyzerService:

    def __init__(self):
        self.active_provider = None # 'gemini' o 'openai'
        self.gemini_model = None
        self.openai_client = None
        
        # Configurar Gemini
        try:
            genai.configure(api_key=Config.GOOGLE_GEMINI_API_KEY)
            self.generation_config = {
                "temperature": 0.7,
                "top_p": 0.95,
                "top_k": 40,
                "max_output_tokens": 2048,
            }
            self.safety_settings = [
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
            ]
            self.gemini_model = genai.GenerativeModel(
                model_name="gemini-2.5-flash",
                generation_config=self.generation_config,
                safety_settings=self.safety_settings
            )
        except Exception as e:
            logger.warning(f"⚠️ Error al configurar Gemini: {e}")

        # Configurar OpenAI
        try:
            if Config.OPENAI_API_KEY:
                self.openai_client = openai.OpenAI(api_key=Config.OPENAI_API_KEY)
        except Exception as e:
            logger.warning(f"⚠️ Error al configurar OpenAI: {e}")

        # Probar y seleccionar el mejor proveedor
        self.check_best_provider()

    def _run_with_timeout(self, fn, timeout_seconds: int):
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(fn)
                return future.result(timeout=timeout_seconds)
        except Exception as e:
            return e

    def _test_gemini(self):
        if not self.gemini_model:
            return RuntimeError("Gemini no configurado")
        response = self.gemini_model.generate_content("Hola")
        if not response or not response.text:
            return RuntimeError("Respuesta vacía de Gemini")
        return True

    def _test_openai(self):
        if not self.openai_client:
            return RuntimeError("OpenAI no configurado")
        response = self.openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "Hola"}],
            max_tokens=5
        )
        if not response.choices:
            return RuntimeError("Respuesta vacía de OpenAI")
        return True

    def check_best_provider(self):
        """Verifica qué API responde y selecciona la activa para este ciclo"""
        logger.info("🔄 Verificando disponibilidad de IAs...")
        
        # 1. Probar Gemini
        try:
            if self.gemini_model:
                logger.info("🧪 Probando Gemini...")
                result = self._run_with_timeout(self._test_gemini, timeout_seconds=6)
                if result is True:
                    self.active_provider = 'gemini'
                    logger.info("✅ Gemini ACTIVO y seleccionado.")
                    return
                if isinstance(result, Exception):
                    raise result
        except Exception as e:
            logger.warning(f"⚠️ Gemini falló la prueba: {e}")

        # 2. Probar OpenAI (Fallback)
        try:
            if self.openai_client:
                logger.info("🧪 Probando OpenAI...")
                result = self._run_with_timeout(self._test_openai, timeout_seconds=6)
                if result is True:
                    self.active_provider = 'openai'
                    logger.info("✅ OpenAI ACTIVO y seleccionado.")
                    return
                if isinstance(result, Exception):
                    raise result
        except Exception as e:
            logger.warning(f"⚠️ OpenAI falló la prueba: {e}")
            
        logger.error("❌ NINGUNA IA DISPONIBLE. El bot funcionará sin análisis inteligente.")
        self.active_provider = None

    def _generate_content(self, prompt: str) -> str:
        """Genera contenido usando el proveedor activo"""
        if self.active_provider == 'gemini':
            try:
                response = self.gemini_model.generate_content(prompt)
                return response.text
            except Exception as e:
                logger.error(f"❌ Error generando con Gemini: {e}")
                # Intentar switch a OpenAI si falla en runtime
                if self.openai_client:
                    self.active_provider = 'openai'
                    return self._generate_content(prompt)
                return ""
                
        elif self.active_provider == 'openai':
            try:
                response = self.openai_client.chat.completions.create(
                    model="gpt-4o-mini", # Usamos gpt-4o-mini por ser rápido y eficiente (text-embedding no genera texto)
                    messages=[{"role": "user", "content": prompt}]
                )
                return response.choices[0].message.content
            except Exception as e:
                logger.error(f"❌ Error generando con OpenAI: {e}")
                return ""
        
        return ""

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
        # 1. Top subidas 24h (sin cambio 2h, hasta 15 criptos)
        coins_up_24h = [coin for coin in coins_only_binance if coin.get('change_24h', 0) > 10 and abs(coin.get('change_24h', 0)) > 0.0]
        coins_up_sorted = sorted(coins_up_24h, key=lambda c: c.get('change_24h', 0), reverse=True)
        up_lines = []
        for coin in coins_up_sorted[:15]:
            change_24h = coin.get('change_24h', 0)
            if abs(change_24h) > 0.0:
                symbol = coin.get('symbol', 'N/A').replace('/USDT', '').replace('/usdt', '')
                up_lines.append(f"{symbol}📈 {change_24h:+.1f}%")
        tweet_up_24h = f"{emoji} Top subidas últimas 24h (>10%):\n" + ("\n".join(up_lines) if up_lines else "Ninguna moneda subió más de 10%")
        tweet_up_24h = tweet_up_24h.strip()[:max_chars]

        # 2. Top bajadas 24h (sin cambio 2h, hasta 15 criptos)
        coins_down_24h = [coin for coin in coins_only_binance if coin.get('change_24h', 0) < -10 and abs(coin.get('change_24h', 0)) > 0.0]
        coins_down_sorted = sorted(coins_down_24h, key=lambda c: c.get('change_24h', 0))
        down_lines = []
        for coin in coins_down_sorted[:15]:
            change_24h = coin.get('change_24h', 0)
            if abs(change_24h) > 0.0:
                symbol = coin.get('symbol', 'N/A').replace('/USDT', '').replace('/usdt', '')
                down_lines.append(f"{symbol}📉 {change_24h:+.1f}%")
        tweet_down_24h = f"{emoji} Top bajadas últimas 24h (<-10%):\n" + ("\n".join(down_lines) if down_lines else "Ninguna moneda bajó más de 10%")
        tweet_down_24h = tweet_down_24h.strip()[:max_chars]


        # 3. Subidas 2h para las del top subidas 24h (si hay dato 2h, si no, top 2h general)
        coins_2h_lookup = {coin['symbol']: coin for coin in coins_both_enriched} if coins_both_enriched else {}
        up_2h_lines = []
        for coin in coins_up_sorted[:10]:
            symbol = coin.get('symbol', 'N/A')
            coin_2h = coins_2h_lookup.get(symbol)
            if coin_2h and coin_2h.get('change_2h') is not None and abs(coin_2h.get('change_2h')) > 0.0:
                change_2h = coin_2h.get('change_2h')
                up_2h_lines.append(f"{symbol.replace('/USDT','').replace('/usdt','')}📈 2h:{change_2h:+.1f}%")
        # Si no hay ninguna, mostrar top 10 subidas 2h de coins_both_enriched
        if not up_2h_lines and coins_both_enriched:
            coins_up_2h = [coin for coin in coins_both_enriched if coin.get('change_2h', 0) > 0 and abs(coin.get('change_2h', 0)) > 0.0]
            coins_up_2h_sorted = sorted(coins_up_2h, key=lambda c: c.get('change_2h', 0), reverse=True)
            for coin in coins_up_2h_sorted[:10]:
                change_2h = coin.get('change_2h', 0)
                if abs(change_2h) > 0.0:
                    symbol = coin.get('symbol', 'N/A').replace('/USDT','').replace('/usdt','')
                    up_2h_lines.append(f"{symbol}📈 2h:{change_2h:+.1f}%")
        tweet_up_2h = f"{emoji} Top subidas últimas 2h:\n" + ("\n".join(up_2h_lines) if up_2h_lines else "Ninguna moneda subió en 2h")
        tweet_up_2h = tweet_up_2h.strip()[:max_chars]

        # 4. Bajadas 2h para las del top bajadas 24h (si hay dato 2h, si no, top 2h general)
        down_2h_lines = []
        for coin in coins_down_sorted[:15]:
            symbol = coin.get('symbol', 'N/A')
            coin_2h = coins_2h_lookup.get(symbol)
            if coin_2h and coin_2h.get('change_2h') is not None and abs(coin_2h.get('change_2h')) > 0.0:
                change_2h = coin_2h.get('change_2h')
                down_2h_lines.append(f"{symbol.replace('/USDT','').replace('/usdt','')}📉 2h:{change_2h:+.1f}%")
        # Si no hay ninguna, mostrar top 15 bajadas 2h de coins_both_enriched
        if not down_2h_lines and coins_both_enriched:
            coins_down_2h = [coin for coin in coins_both_enriched if coin.get('change_2h', 0) < 0 and abs(coin.get('change_2h', 0)) > 0.0]
            coins_down_2h_sorted = sorted(coins_down_2h, key=lambda c: c.get('change_2h', 0))
            for coin in coins_down_2h_sorted[:15]:
                change_2h = coin.get('change_2h', 0)
                if abs(change_2h) > 0.0:
                    symbol = coin.get('symbol', 'N/A').replace('/USDT','').replace('/usdt','')
                    down_2h_lines.append(f"{symbol}📉 2h:{change_2h:+.1f}%")
        tweet_down_2h = f"{emoji} Top bajadas últimas 2h:\n" + ("\n".join(down_2h_lines) if down_2h_lines else "Ninguna moneda bajó en 2h")
        tweet_down_2h = tweet_down_2h.strip()[:max_chars]

        return {
            "up_24h": tweet_up_24h,
            "down_24h": tweet_down_24h,
            "up_2h": tweet_up_2h,
            "down_2h": tweet_down_2h
        }

    def analyze_and_recommend(self, coins: List[Dict], market_sentiment: Dict) -> Dict:
        logger.info(f"🤖 Analizando datos con IA ({self.active_provider})...")
        prompt = f"""Eres un analista experto de criptomonedas. Analiza los siguientes datos y genera un reporte conciso:


DATOS DEL MERCADO:
{json.dumps(market_sentiment, indent=2, ensure_ascii=False)}

CRIPTOMONEDAS CON CAMBIOS SIGNIFICATIVOS (Top 10):
{json.dumps(coins[:10], indent=2, ensure_ascii=False)}

Por favor, proporciona:
1. Un análisis del sentimiento general del mercado (2-3 líneas)
2. Análisis de las top 3 criptomonedas con mayor potencial
3. Tu recomendación principal: ¿Cuál moneda tiene mejor oportunidad de inversión y por qué? (máximo 4 líneas)
4. Un nivel de confianza de tu recomendación (1-10)
5. Advertencias o riesgos principales a considerar

Sé conciso, directo y profesional. Usa emojis relevantes para hacer el texto más amigable."""
        try:
            ai_analysis = self._generate_content(prompt)
            logger.info("✅ Análisis de IA completado")
            result = {
                'full_analysis': ai_analysis,

                'market_overview': self._extract_section(ai_analysis, 1),
                'top_coins_analysis': self._extract_section(ai_analysis, 2),
                'recommendation': self._extract_section(ai_analysis, 3),
                'confidence_level': self._extract_confidence(ai_analysis),
                'warnings': self._extract_section(ai_analysis, 5),
                'timestamp': market_sentiment.get('fear_greed_index', {}).get('timestamp', ''),
            }
            # Segunda pasada: obtener Top 3 Compras/Ventas en JSON estructurado
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
            Monedas: {json.dumps(coins[:10], ensure_ascii=False)}
            Sentimiento: {json.dumps(market_sentiment, ensure_ascii=False)}
            Responde SOLO el JSON."""
            try:
                jr_text = self._generate_content(json_prompt)
                txt = jr_text.strip()
                # Limpieza extra para OpenAI que a veces incluye markdown
                if txt.startswith("```"):
                    txt = txt.replace("```json", "").replace("```", "")
                parsed = json.loads(txt)
                if isinstance(parsed, dict):
                    result['top_buys'] = parsed.get('top_buys', [])
                    result['top_sells'] = parsed.get('top_sells', [])
                    conf = parsed.get('confidence', None)
                    if isinstance(conf, int) and 1 <= conf <= 10:
                        result['confidence_level'] = conf
            except Exception:
                pass
            return result
        except Exception as e:
            logger.error(f"❌ Error al analizar con IA: {e}")
            return {
                'full_analysis': 'Error al generar análisis',
                'recommendation': 'No se pudo generar recomendación',
                'confidence_level': 0,
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
            # Bajadas: Top 10 por 24h < -10% (solo Binance, igual que Telegram)
            coins_down_24h = [coin for coin in coins_only_binance if coin.get('change_24h', 0) < -10]
            logger.debug("[Twitter] Todas las monedas (Binance): %s", ", ".join([f"{coin.get('symbol')} {coin.get('change_24h')}" for coin in coins_only_binance]))
            logger.debug("[Twitter] Monedas bajaron >10%% (24h, Binance): %s", ", ".join([f"{coin.get('symbol')} {coin.get('change_24h')}" for coin in coins_down_24h]))
            coins_down_sorted = sorted(coins_down_24h, key=lambda c: c.get('change_24h', 0))
            down_lines = build_tweet(coins_down_sorted, '📉')
            tweet_down = f"{emoji} {sentiment}. Top:\n{down_lines}" if down_lines else f"{emoji} {sentiment}. Top:\nNinguna moneda bajó más de 10% (debug: {len(coins_down_24h)} detectadas)"
            tweet_down = tweet_down.strip()
            if len(tweet_down) > max_chars:
                tweet_down = tweet_down[:max_chars].rstrip(' .,;:\n')
            return {"up": tweet_up, "down": tweet_down}
        except Exception as e:
            logger.error(f"❌ Error al generar tweet: {e}")
            return {"up": "📊 Análisis de mercado cripto actualizado.", "down": "📊 Análisis de mercado cripto actualizado."}
    
    def analyze_news_batch(self, news_titles: List[str]) -> List[Dict]:
        """
        Analiza un lote de noticias y selecciona las más importantes.
        Soporta Gemini y OpenAI.
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
            def run_provider(provider: str) -> str:
                if provider == 'gemini':
                    response = self.gemini_model.generate_content(prompt)
                    return response.text
                if provider == 'openai':
                    response = self.openai_client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[{"role": "user", "content": prompt}]
                    )
                    return response.choices[0].message.content
                raise RuntimeError("Proveedor inválido")

            if self.active_provider not in ("gemini", "openai"):
                logger.error("❌ Ningún proveedor de IA activo para analizar noticias.")
                return []

            try:
                text = run_provider(self.active_provider)
            except Exception as e:
                logger.warning(f"⚠️ Falló {self.active_provider} en noticias: {e}")
                fallback = 'openai' if self.active_provider == 'gemini' else 'gemini'
                if fallback == 'openai' and not self.openai_client:
                    raise e
                if fallback == 'gemini' and not self.gemini_model:
                    raise e
                self.active_provider = fallback
                text = run_provider(self.active_provider)

            text = text.strip()
            if text.startswith("```"):
                lines = text.split("\n")
                if len(lines) > 2:
                    if "json" in lines[0]:
                        text = "\n".join(lines[1:-1])
                    else:
                        text = text.replace("```json", "").replace("```", "")
                else:
                    text = text.replace("```json", "").replace("```", "")

            text = text.replace("```json", "").replace("```", "").strip()
            results = json.loads(text)
            valid_results = []
            if isinstance(results, list):
                for item in results:
                    if isinstance(item, dict) and 'original_index' in item and 'score' in item:
                        valid_results.append(item)

            logger.info(f"✅ Análisis por lote completado ({self.active_provider}). Seleccionadas {len(valid_results)} noticias relevantes.")
            return valid_results
        except Exception as e:
            logger.error(f"❌ Error en análisis por lote de noticias ({self.active_provider}): {e}")
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

            result_text = ""
            if self.active_provider == 'gemini':
                response = self.gemini_model.generate_content(prompt)
                result_text = response.text
            elif self.active_provider == 'openai':
                response = self.openai_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": prompt}]
                )
                result_text = response.choices[0].message.content
            else:
                return {'score': 5, 'summary': text[:100]}

            result_text = result_text.strip()
            
            # Extraer JSON
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0].strip()
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0].strip()
            
            result = json.loads(result_text)
            return {
                'score': int(result.get('score', 5)),
                'summary': result.get('summary', text[:100])
            }
            
        except Exception as e:
            logger.warning(f"⚠️ Error en analyze_text ({self.active_provider}): {e}")
            return {'score': 5, 'summary': text[:100]}

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
            result_text = ""
            if self.active_provider == 'gemini':
                response = self.gemini_model.generate_content(prompt)
                result_text = response.text
            elif self.active_provider == 'openai':
                response = self.openai_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": prompt}]
                )
                result_text = response.choices[0].message.content
            else:
                 return {"category": "crypto", "confidence": 5}

            result_text = result_text.strip()
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0].strip()
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0].strip()
            result = json.loads(result_text)
            category = result.get("category", "crypto").lower()
            if category not in ("crypto", "markets", "signals"):
                category = "crypto"
            confidence = int(result.get("confidence", 7))
            return {"category": category, "confidence": min(max(confidence, 0), 10)}
        except Exception as e:
            logger.warning(f"⚠️ Error en classify_news_category ({self.active_provider}): {e}")
            return {"category": "crypto", "confidence": 5}
