"""
Servicio de análisis con IA utilizando Google Gemini.
Analiza los datos del mercado y genera recomendaciones.
"""
import google.generativeai as genai
from typing import Dict, List
from config.config import Config
from utils.logger import logger
import json

class AIAnalyzerService:

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
    def __init__(self):
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
            self.model = genai.GenerativeModel(
                model_name="gemini-2.5-flash",
                generation_config=self.generation_config,
                safety_settings=self.safety_settings
            )
            logger.info("✅ Cliente de IA (Gemini) inicializado")
        except Exception as e:
            logger.error(f"❌ Error al inicializar Gemini: {e}")
            raise

    def analyze_and_recommend(self, coins: List[Dict], market_sentiment: Dict) -> Dict:
        logger.info("🤖 Analizando datos con IA (Gemini)...")
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
            response = self.model.generate_content(prompt)
            ai_analysis = response.text
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
            import re
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