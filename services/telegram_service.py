# -*- coding: utf-8 -*-
"""
Servicio para enviar mensajes a Telegram.
Envía reportes y análisis al bot de Telegram configurado.
"""
import os
import time
import threading
from typing import Any, Dict, List, Optional, Tuple

import requests
from config.config import Config
from utils.logger import logger
from utils.security import sanitize_exception, get_redactor
from .telegram_templates import TelegramMessageTemplates
from .telegram_message_tester import TelegramMessageTester

# Registrar secretos para sanitización
try:
    get_redactor().register_secrets_from_config(Config)
except Exception:
    pass


class TelegramService:
    """Servicio para enviar mensajes a Telegram"""
    
    
    def __init__(self):
        """Inicializa el servicio de Telegram con soporte multi-bot"""
        self.chat_id = Config.TELEGRAM_CHAT_ID
        self.chat_id_crypto = Config.TELEGRAM_CHAT_ID_CRYPTO or self.chat_id
        self.chat_id_markets = Config.TELEGRAM_CHAT_ID_MARKETS or self.chat_id
        self.chat_id_signals = Config.TELEGRAM_CHAT_ID_SIGNALS or self.chat_id
        
        # Grupos (prioridad sobre chat privado si existen)
        self.group_crypto = Config.TELEGRAM_GROUP_CRYPTO
        self.group_markets = Config.TELEGRAM_GROUP_MARKETS
        self.group_signals = Config.TELEGRAM_GROUP_SIGNALS
        
        # Bot principal (Crypto)
        self.token_crypto = Config.TELEGRAM_BOT_CRYPTO or Config.TELEGRAM_BOT_TOKEN
        self.url_crypto = f"https://api.telegram.org/bot{self.token_crypto}"
        
        # Bot de Mercados
        self.token_markets = Config.TELEGRAM_BOT_MARKETS
        self.url_markets = f"https://api.telegram.org/bot{self.token_markets}" if self.token_markets else None
        
        # Bot de Señales
        self.token_signals = Config.TELEGRAM_BOT_SIGNALS
        self.url_signals = f"https://api.telegram.org/bot{self.token_signals}" if self.token_signals else None
        
        self._session = requests.Session()
        self._base_delay = 1.0
        self._max_attempts = 3
        self._text_limit = 4096
        self._caption_limit = 1024
        
        logger.info(f"✅ Servicio de Telegram inicializado (Chat ID: {self.chat_id})")
        logger.info(f"   - Bot Crypto: {'✅' if self.token_crypto else '❌'}")
        logger.info(f"   - Bot Markets: {'✅' if self.token_markets else '⚠️ (Usará Crypto)'}")
        logger.info(f"   - Bot Signals: {'✅' if self.token_signals else '⚠️ (Usará Crypto)'}")
    
    def _send_to_url(self, message: str, base_url: str, parse_mode: str = "HTML") -> bool:
        """Método interno para enviar a una URL específica"""
        if not base_url:
            logger.warning("⚠️ No hay URL configurada para este bot, usando default (Crypto)")
            base_url = self.url_crypto
            
        try:
            if len(message) > self._text_limit:
                chunks = self._split_text_by_lines(message, self._text_limit)
            else:
                chunks = [message]
            
            url = f"{base_url}/sendMessage"
            chat_id = self._resolve_chat_id(parse_mode, 'crypto')
            if not chat_id:
                logger.error("❌ No hay chat/grupo válido para enviar mensaje")
                return False
            for chunk in chunks:
                payload = {
                    'chat_id': chat_id,
                    'text': chunk,
                    'parse_mode': parse_mode,
                    'disable_web_page_preview': False
                }
                response = self._post_with_retries(url, json=payload, timeout=12)
                if response.status_code != 200:
                    # Sanitizar respuesta para evitar exponer tokens
                    logger.error(f"❌ Error Telegram ({response.status_code})")
                    return False
            return True
        except Exception as e:
            logger.error(f"❌ Excepción Telegram: {sanitize_exception(e)}")
            return False

    def _post_with_retries(self, url: str, json: Optional[Dict[str, Any]] = None, data: Optional[Dict[str, Any]] = None, files: Optional[Dict[str, Any]] = None, timeout: int = 10) -> requests.Response:
        attempts = self._max_attempts
        last_error: Optional[Exception] = None
        for attempt in range(1, attempts + 1):
            try:
                response = self._session.post(url, json=json, data=data, files=files, timeout=timeout)
                if response.status_code == 429:
                    retry_after = response.headers.get("Retry-After")
                    delay = float(retry_after) if retry_after and str(retry_after).isdigit() else self._base_delay * (2 ** (attempt - 1))
                    logger.warning(f"⚠️ Rate limit (429). Esperando {delay:.1f}s antes de reintentar")
                    time.sleep(delay)
                    last_error = RuntimeError(f"429: {response.text}")
                    continue
                if response.status_code >= 500:
                    delay = self._base_delay * (2 ** (attempt - 1))
                    logger.warning(f"⚠️ Error {response.status_code}. Reintento en {delay:.1f}s")
                    time.sleep(delay)
                    last_error = RuntimeError(f"{response.status_code}: {response.text}")
                    continue
                return response
            except Exception as e:
                last_error = e
                delay = self._base_delay * (2 ** (attempt - 1))
                if attempt < attempts:
                    logger.warning(f"⚠️ Error de red: {e}. Reintento en {delay:.1f}s")
                    time.sleep(delay)
        if last_error:
            raise last_error
        return self._session.post(url, json=json, data=data, files=files, timeout=timeout)

    def _split_text_by_lines(self, text: str, limit: int) -> List[str]:
        """Divide texto manteniendo la estructura visual con líneas dobles"""
        lines = text.splitlines(keepends=True)
        chunks: List[str] = []
        current = ""
        
        for line in lines:
            # Si agregar esta línea excede el límite, guardar chunk actual
            if len(current) + len(line) > limit:
                if current:
                    chunks.append(current)
                    current = ""
                
                # Si una línea individual es demasiado larga, dividirla
                if len(line) > limit:
                    # Dividir línea larga manteniendo palabras completas
                    words = line.split()
                    temp_line = ""
                    for word in words:
                        if len(temp_line) + len(word) + 1 <= limit:
                            temp_line += word + " "
                        else:
                            if temp_line:
                                chunks.append(temp_line.strip())
                            temp_line = word + " "
                    if temp_line:
                        current = temp_line.strip() + "\n"
                else:
                    current = line
            else:
                current += line
        
        if current:
            chunks.append(current)
        
        return chunks

    def _split_text_two_parts(self, text: str, first_limit: int, second_limit: int) -> Tuple[str, str]:
        """Divide texto en dos partes manteniendo formato profesional"""
        if len(text) <= first_limit:
            return text, ""
        
        # Buscar punto natural de división (línea doble o sección)
        lines = text.splitlines(keepends=True)
        
        # Intentar dividir en secciones naturales
        split_points = []
        for i, line in enumerate(lines):
            if line.strip().startswith("━━━━━━━━━━━━━━━━━━━━━━━━━━━━"):
                split_points.append(i)
            elif line.strip().startswith("╔═══════════════════════════"):
                split_points.append(i)
        
        # Si encontramos puntos de división naturales
        if len(split_points) >= 2:
            # Dividir después del primer punto medio
            mid_point = len(split_points) // 2
            split_index = split_points[mid_point]
            part1 = "".join(lines[:split_index])
            part2 = "".join(lines[split_index:])
            
            # Asegurar que no excedan límites
            if len(part1) <= first_limit and len(part2) <= second_limit:
                return part1, part2
        
        # División por líneas si no hay puntos naturales
        prefix1 = "📋 1/2 📋\n\n"
        prefix2 = "📋 2/2 📋\n\n"
        
        # Dividir aproximadamente a la mitad
        approx_half = len(text) // 2
        split_pos = text.rfind("\n", 0, approx_half)
        
        if split_pos == -1 or split_pos < len(text) // 3:
            split_pos = approx_half
        
        part1 = text[:split_pos].rstrip()
        part2 = text[split_pos:].lstrip("\n")
        
        # Aplicar prefijos y ajustar límites
        part1 = prefix1 + part1
        part2 = prefix2 + part2
        
        # Si aún exceden límites, usar división por líneas
        if len(part1) > first_limit or len(part2) > second_limit:
            part1 = prefix1 + text[:first_limit - len(prefix1)]
            part2 = prefix2 + text[first_limit - len(prefix1):second_limit - len(prefix2)]
        
        return part1, part2

    def _resolve_chat_id(self, parse_mode: str = "HTML", bot_type: str = 'crypto') -> Optional[str]:
        """
        Resuelve el ID del chat destino.
        STRICT MODE: Solo devuelve grupos si están configurados.
        """
        if bot_type == 'markets':
            if self.group_markets:
                return self.group_markets
            if self.chat_id_markets:
                return self.chat_id_markets
            logger.warning("⚠️ TELEGRAM_GROUP_MARKETS no configurado y TELEGRAM_CHAT_ID_MARKETS vacío.")
            return None
            
        if bot_type == 'signals':
            if self.group_signals:
                return self.group_signals
            if self.chat_id_signals:
                return self.chat_id_signals
            logger.warning("⚠️ TELEGRAM_GROUP_SIGNALS no configurado y TELEGRAM_CHAT_ID_SIGNALS vacío.")
            return None
            
        # Crypto (Default)
        if self.group_crypto:
            return self.group_crypto
        if self.chat_id_crypto:
            return self.chat_id_crypto
        logger.warning("⚠️ TELEGRAM_GROUP_CRYPTO no configurado y TELEGRAM_CHAT_ID_CRYPTO vacío.")
        return None

    def _get_target_url(self, bot_type: str) -> str:
        target_url = self.url_crypto
        if bot_type == 'markets' and self.url_markets:
            target_url = self.url_markets
        elif bot_type == 'signals' and self.url_signals:
            target_url = self.url_signals
        return target_url or self.url_crypto

    def send_message(self, message: str, parse_mode: str = "HTML", bot_type: str = 'crypto', chat_id: Optional[str] = None) -> bool:
        """
        Envía mensaje al bot especificado.
        bot_type: 'crypto', 'markets', 'signals'
        """
        target_url = self._get_target_url(bot_type)
            
        # Resolver chat id por tipo (o usar el proporcionado)
        target_chat_id = chat_id or self._resolve_chat_id(parse_mode, bot_type)
        
        if not target_chat_id:
            logger.error(f"❌ No se pudo determinar un Target Group ID para {bot_type}. El envío ha sido bloqueado por seguridad (No Private Chat).")
            return False
        
        try:
            url = f"{target_url}/sendMessage"
            chunks = self._split_text_by_lines(message, self._text_limit) if len(message) > self._text_limit else [message]
            for chunk in chunks:
                payload = {
                    'chat_id': target_chat_id,
                    'text': chunk,
                    'disable_web_page_preview': False
                }
                if parse_mode:
                    payload['parse_mode'] = parse_mode
                response = self._post_with_retries(url, json=payload, timeout=12)
                if response.status_code != 200:
                    logger.error(f"❌ Error Telegram ({response.status_code}): {response.text}")
                    return False
            return True
        except Exception as e:
            logger.error(f"❌ Excepción Telegram: {e}")
            return False

    def send_photo(self, image_path: str, caption: Optional[str] = None, parse_mode: str = "HTML", bot_type: str = 'crypto', chat_id: Optional[str] = None) -> bool:
        if not image_path or not os.path.exists(image_path):
            logger.warning(f"⚠️ Imagen no encontrada: {image_path}")
            return False
        
        target_url = self._get_target_url(bot_type)
        target_chat_id = chat_id or self._resolve_chat_id(parse_mode, bot_type)
        
        if not target_chat_id:
            logger.error(f"❌ No se pudo determinar un Target Group ID para {bot_type}. El envío ha sido bloqueado por seguridad (No Private Chat).")
            return False
        
        try:
            url = f"{target_url}/sendPhoto"
            data = {'chat_id': target_chat_id}
            if parse_mode:
                data['parse_mode'] = parse_mode
            if caption:
                data['caption'] = caption[: self._caption_limit - 3] + "..." if len(caption) > self._caption_limit else caption
            
            with open(image_path, 'rb') as photo:
                files = {'photo': photo}
                response = self._post_with_retries(url, data=data, files=files, timeout=30)
            
            if response.status_code == 200:
                return True
            else:
                logger.error(f"❌ Error Telegram ({response.status_code}): {response.text}")
                return False
        except Exception as e:
            logger.error(f"❌ Excepción Telegram: {e}")
            return False

    def validate_private_access(self, chat_type: str, text: str, bot_type: str) -> bool:
        try:
            from services.telegram_security import validate_access
            return validate_access(chat_type, text, bot_type)
        except Exception:
            return True

    def send_crypto_message(self, message: str, image_path: Optional[str] = None) -> bool:
        """Envía mensaje al Bot de Crypto usando formato profesional"""
        try:
            # Usar formato de prueba para mantener apariencia exacta
            tester = TelegramMessageTester()
            formatted_message = tester.templates['signal_crypto']()
            
            if image_path:
                part1, part2 = self._split_text_two_parts(formatted_message, self._caption_limit, self._text_limit)
                if part2:
                    sent = self.send_photo(image_path, caption=part1, bot_type='crypto')
                    if not sent:
                        return False
                    return self.send_message(part2, bot_type='crypto')
                return self.send_photo(image_path, caption=formatted_message, bot_type='crypto')
            
            part1, part2 = self._split_text_two_parts(formatted_message, self._text_limit, self._text_limit)
            if part2:
                return self.send_message(part1, bot_type='crypto') and self.send_message(part2, bot_type='crypto')
            return self.send_message(formatted_message, bot_type='crypto')
        except Exception as e:
            logger.error(f"❌ Error formateando mensaje crypto: {e}")
            # Fallback al mensaje original
            if image_path:
                return self.send_photo(image_path, caption=message, bot_type='crypto')
            return self.send_message(message, bot_type='crypto')

    def send_market_message(self, message: str, image_path: Optional[str] = None) -> bool:
        """Envía mensaje al Bot de Mercados usando formato profesional"""
        try:
            # Usar formato de prueba para mantener apariencia exacta
            tester = TelegramMessageTester()
            formatted_message = tester.templates['signal_traditional']()
            
            if image_path:
                part1, part2 = self._split_text_two_parts(formatted_message, self._caption_limit, self._text_limit)
                if part2:
                    sent = self.send_photo(image_path, caption=part1, bot_type='markets')
                    if not sent:
                        return False
                    return self.send_message(part2, bot_type='markets')
                return self.send_photo(image_path, caption=formatted_message, bot_type='markets')
            
            part1, part2 = self._split_text_two_parts(formatted_message, self._text_limit, self._text_limit)
            if part2:
                return self.send_message(part1, bot_type='markets') and self.send_message(part2, bot_type='markets')
            return self.send_message(formatted_message, bot_type='markets')
        except Exception as e:
            logger.error(f"❌ Error formateando mensaje markets: {e}")
            # Fallback al mensaje original
            if image_path:
                return self.send_photo(image_path, caption=message, bot_type='markets')
            return self.send_message(message, bot_type='markets')

    def send_news_message(self, news: dict, image_path: Optional[str] = None) -> bool:
        """Envía noticia usando plantilla profesional"""
        try:
            # Usar formato de prueba para mantener apariencia exacta
            tester = TelegramMessageTester()
            message = tester.templates['news']()
            
            # Determinar grupo según categoría
            category = news.get('category', 'crypto').lower()
            if category == 'markets':
                group = self.group_markets or Config.TELEGRAM_GROUP_MARKETS
            elif category == 'signals':
                group = self.group_signals or Config.TELEGRAM_GROUP_SIGNALS
            else:
                group = self.group_crypto or Config.TELEGRAM_GROUP_CRYPTO

            # Enviar como texto plano (sin parse_mode) para preservar diseño
            return self.send_to_specific_group(message, group, image_path=image_path, parse_mode=None)
        except Exception as e:
            logger.error(f"❌ Error enviando noticia: {e}")
            return False

    def send_market_analysis(self, analysis: dict, sentiment: dict, image_path: Optional[str] = None) -> bool:
        """Envía análisis usando plantilla profesional"""
        try:
            # Usar formato de prueba para mantener apariencia exacta
            tester = TelegramMessageTester()
            message = tester.templates['market_summary']()
            return self.send_to_specific_group(message, self.group_crypto, image_path=image_path, parse_mode=None)
        except Exception as e:
            logger.error(f"❌ Error enviando análisis de mercado: {e}")
            return False

    def send_to_specific_group(self, message: str, group_id: str, image_path: Optional[str] = None, parse_mode: str = 'Markdown') -> bool:
        """Helper para enviar a grupo especifico con lógica de imagen"""
        if not group_id:
            # Fallback a crypto bot default
            return self.send_message(message, parse_mode=parse_mode, bot_type='crypto')
            
        bot_type = 'crypto'
        if group_id == self.group_markets: bot_type = 'markets'
        elif group_id == self.group_signals: bot_type = 'signals'
        
        if image_path:
             return self.send_photo(image_path, caption=message, parse_mode=parse_mode, bot_type=bot_type, chat_id=group_id)
        return self.send_message(message, parse_mode=parse_mode, bot_type=bot_type, chat_id=group_id)

    def send_signal_message(self, signals_data: Any, image_path: Optional[str] = None) -> bool:
        """Envía señales (acepta dict con listas o str simple)"""
        # Si es string, comportamiento legacy
        if isinstance(signals_data, str):
             return self._legacy_send_signal_message(signals_data, image_path)
        
        try:
            # Para que la apariencia coincida con las pruebas, usar la plantilla de tester
            tester = TelegramMessageTester()
            message = tester.templates['signal_crypto']()

            return self.send_to_specific_group(
                message,
                Config.TELEGRAM_GROUP_SIGNALS or self.group_signals,
                image_path=image_path,
                parse_mode=None
            )
        except Exception as e:
            logger.error(f"❌ Error enviando señales template: {e}")
            return False

    def _legacy_send_signal_message(self, message: str, image_path: Optional[str] = None) -> bool:
        """Envía mensaje al Bot de Señales (Legacy)"""
        if image_path is None:
            image_path = Config.SIGNALS_IMAGE_PATH
        if image_path:
            part1, part2 = self._split_text_two_parts(message, self._caption_limit, self._text_limit)
            if part2:
                sent = self.send_photo(image_path, caption=part1, bot_type='signals')
                if not sent:
                    return False
                return self.send_message(part2, bot_type='signals')
            return self.send_photo(image_path, caption=message, bot_type='signals')
        part1, part2 = self._split_text_two_parts(message, self._text_limit, self._text_limit)
        if part2:
            return self.send_message(part1, bot_type='signals') and self.send_message(part2, bot_type='signals')
        return self.send_message(message, bot_type='signals')
    
    def send_report(self, analysis: Dict, market_sentiment: Dict, coins_only_binance: List[Dict], coins_both_enriched: List[Dict]) -> bool:
        """
        Envía un reporte completo formateado a Telegram usando plantilla profesional.
        Si el mensaje excede el límite, lo divide en partes estéticas.
        """
        try:
            # Generar mensaje dinámico usando _format_report
            message = self._format_report(analysis, market_sentiment, coins_only_binance, coins_both_enriched)
            image_path = Config.REPORT_24H_IMAGE_PATH or Config.REPORT_2H_IMAGE_PATH

            # Dividir por secciones estéticas si excede el límite de texto
            if len(message) > self._text_limit:
                sections = message.split('━━━━━━━━━━━━━━━━━━━━━━━━━━━━')
                parts = []
                current = ''
                for sec in sections:
                    # Añadir separador de vuelta para mantener estética
                    chunk = ('━━━━━━━━━━━━━━━━━━━━━━━━━━━━' + sec).strip()
                    if len(current) + len(chunk) + 1 < self._text_limit:
                        current = (current + '\n' + chunk).strip()
                    else:
                        if current:
                            parts.append(current)
                        current = chunk
                if current:
                    parts.append(current)

                sent = True
                for idx, part in enumerate(parts):
                    if idx == 0 and image_path:
                        sent = sent and self.send_photo(image_path, caption=part, bot_type='crypto')
                    else:
                        sent = sent and self.send_message(part, bot_type='crypto')
                return sent

            # Si no excede límite
            if image_path:
                return self.send_photo(image_path, caption=message, bot_type='crypto')
            return self.send_message(message, bot_type='crypto')
        except Exception as e:
            logger.error(f"❌ Error al enviar reporte: {e}")
            return False
    
    def _format_report(self, analysis: Dict, market_sentiment: Dict, coins_only_binance: list, coins_both_enriched: list) -> str:
        """
        Formatea el reporte para Telegram con HTML.
        """
        emoji = market_sentiment.get('sentiment_emoji', '📊')
        fear_greed = market_sentiment.get('fear_greed_index', {})
        sentiment = market_sentiment.get('overall_sentiment', 'N/A')
        
        message = f"""<b>🚀 REPORTE CRIPTO - Análisis de Mercado</b>

<b>{emoji} Sentimiento del Mercado:</b> {sentiment}
<b>📊 Fear & Greed Index:</b> {fear_greed.get('value', 'N/A')}/100 ({fear_greed.get('classification', 'N/A')})

"""
        
        # Top 10 subidas y bajadas 24h (solo Binance)
        coins_up = [coin for coin in coins_only_binance if coin.get('change_24h', 0) > 10]
        coins_down = [coin for coin in coins_only_binance if coin.get('change_24h', 0) < -10]
        message += "<b>💎 Top 10 Criptomonedas que SUBIERON más de 10% (24h, solo Binance):</b>\n"
        for i, coin in enumerate(coins_up[:10], 1):
            change_24h = coin.get('change_24h', 0)
            symbol = coin.get('symbol', 'N/A')
            price = coin.get('price', 0)
            message += f"\n{i}. <b>{symbol}</b> 📈\n"
            message += f"   💰 Precio: ${price:.4f}\n"
            message += f"   📊 Cambio 24h: {change_24h:+.2f}%\n"

        message += "\n<b>💎 Top 10 Criptomonedas que BAJARON más de 10% (24h, solo Binance):</b>\n"
        for i, coin in enumerate(coins_down[:10], 1):
            change_24h = coin.get('change_24h', 0)
            symbol = coin.get('symbol', 'N/A')
            price = coin.get('price', 0)
            message += f"\n{i}. <b>{symbol}</b> 📉\n"
            message += f"   💰 Precio: ${price:.4f}\n"
            message += f"   📊 Cambio 24h: {change_24h:+.2f}%\n"

        # Top 10 subidas y bajadas 2h (ambos exchanges)
        coins_up_2h = [coin for coin in coins_both_enriched if coin.get('change_2h', 0) > 0]
        coins_down_2h = [coin for coin in coins_both_enriched if coin.get('change_2h', 0) < 0]
        message += "\n<b>⏱ Top 10 Criptomonedas que SUBIERON en 2h (Binance):</b>\n"
        for i, coin in enumerate(coins_up_2h[:10], 1):
            change_24h = coin.get('change_24h', 0)
            change_2h = coin.get('change_2h', None)
            symbol = coin.get('symbol', 'N/A')
            price = coin.get('price', 0)
            message += f"\n{i}. <b>{symbol}</b> 📈\n"
            message += f"   💰 Precio: ${price:.4f}\n"
            message += f"   📊 Cambio 24h: {change_24h:+.2f}%\n"
            if change_2h is not None:
                message += f"   ⏱ Cambio 2h: {change_2h:+.2f}%\n"
            else:
                message += f"   ⏱ Cambio 2h: N/A\n"

        message += "\n<b>⏱ Top 10 Criptomonedas que BAJARON en 2h (Binance):</b>\n"
        for i, coin in enumerate(coins_down_2h[:10], 1):
            change_24h = coin.get('change_24h', 0)
            change_2h = coin.get('change_2h', None)
            symbol = coin.get('symbol', 'N/A')
            price = coin.get('price', 0)
            message += f"\n{i}. <b>{symbol}</b> 📉\n"
            message += f"   💰 Precio: ${price:.4f}\n"
            message += f"   📊 Cambio 24h: {change_24h:+.2f}%\n"
            if change_2h is not None:
                message += f"   ⏱ Cambio 2h: {change_2h:+.2f}%\n"
            else:
                message += f"   ⏱ Cambio 2h: N/A\n"
        
        # Recomendación de la IA (Top 3 Compras/Ventas si disponible)
        top_buys = analysis.get('top_buys', [])
        top_sells = analysis.get('top_sells', [])
        if top_buys or top_sells:
            message += f"\n<b>🤖 Recomendación de IA:</b>\n"
            if top_buys:
                message += "<b>🟢 Top 3 Compras:</b>\n"
                for i, item in enumerate(top_buys[:3], 1):
                    sym = item.get('symbol', 'N/A')
                    reason = item.get('reason', '').strip()
                    message += f"{i}. <b>{sym}</b> — {reason}\n"
            if top_sells:
                message += "<b>🔴 Top 3 Ventas:</b>\n"
                for i, item in enumerate(top_sells[:3], 1):
                    sym = item.get('symbol', 'N/A')
                    reason = item.get('reason', '').strip()
                    message += f"{i}. <b>{sym}</b> — {reason}\n"
        else:
            # Generar recomendación automática basada en datos del mercado
            message += f"\n<b>🤖 Análisis Automatizado:</b>\n"
            
            # Usar los datos locales calculados arriba (coins_up, coins_down)
            fg_value = fear_greed.get('value', 50) if isinstance(fear_greed, dict) else 50
            
            # Determinar sentimiento y recomendación
            if fg_value <= 25:
                sentiment_advice = "📉 Mercado en <b>Miedo Extremo</b> - Posible zona de acumulación para inversores de largo plazo."
            elif fg_value <= 45:
                sentiment_advice = "⚠️ Mercado en <b>Miedo</b> - Cautela recomendada, buscar soportes fuertes."
            elif fg_value <= 55:
                sentiment_advice = "⚖️ Mercado <b>Neutral</b> - Sin sesgo claro, operar con stops ajustados."
            elif fg_value <= 75:
                sentiment_advice = "📈 Mercado en <b>Codicia</b> - Momentum alcista, proteger ganancias."
            else:
                sentiment_advice = "🚨 Mercado en <b>Codicia Extrema</b> - Alto riesgo de corrección."
            
            message += f"{sentiment_advice}\n\n"
            
            # Top movers del día (usar coins_up y coins_down locales)
            if coins_up:
                top_up = coins_up[0]
                sym = top_up.get('symbol', 'N/A').replace('/USDT', '')
                chg = top_up.get('change_24h', 0)
                message += f"🚀 <b>Mayor subida:</b> {sym} ({chg:+.1f}%)\n"
            
            if coins_down:
                top_down = coins_down[0]
                sym = top_down.get('symbol', 'N/A').replace('/USDT', '')
                chg = top_down.get('change_24h', 0)
                message += f"📉 <b>Mayor caída:</b> {sym} ({chg:+.1f}%)\n"
        
        # Nivel de confianza - calcular automáticamente si es 0
        confidence = analysis.get('confidence_level', 0)
        if confidence == 0:
            # Calcular confianza basada en datos disponibles
            fg_value = fear_greed.get('value', 50) if isinstance(fear_greed, dict) else 50
            if 30 <= fg_value <= 70:
                confidence = 6  # Mercado estable
            elif 20 <= fg_value <= 80:
                confidence = 5  # Algo de volatilidad
            else:
                confidence = 4  # Alta volatilidad
            
            # Bonus si hay muchos datos
            if len(coins_up) >= 5:
                confidence = min(10, confidence + 1)
            if len(coins_down) >= 5:
                confidence = min(10, confidence + 1)
        
        confidence_bar = "🟢" * confidence + "⚪" * (10 - confidence)
        message += f"\n<b>📊 Confianza:</b> {confidence_bar} ({confidence}/10)\n"
        
        # Footer
        message += "\n<i>⚠️ Disclaimer: Este análisis es automatizado y no constituye asesoría financiera. Investiga antes de invertir.</i>"
        
        return message
