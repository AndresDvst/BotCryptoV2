# -*- coding: utf-8 -*-
"""
Servicio para enviar mensajes a Telegram.
Envía reportes y análisis al bot de Telegram configurado.
"""
import os
import time
from typing import Any, Dict, List, Optional, Tuple

import requests
from config.config import Config
from utils.logger import logger
from .telegram_templates import TelegramMessageTemplates

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
                    logger.error(f"❌ Error Telegram ({response.status_code}): {response.text}")
                    return False
            return True
        except Exception as e:
            logger.error(f"❌ Excepción Telegram: {e}")
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
        lines = text.splitlines(keepends=True)
        chunks: List[str] = []
        current = ""
        for line in lines:
            if len(current) + len(line) <= limit:
                current += line
            else:
                if current:
                    chunks.append(current)
                current = line
        if current:
            chunks.append(current)
        return chunks

    def _split_text_two_parts(self, text: str, first_limit: int, second_limit: int) -> Tuple[str, str]:
        if len(text) <= first_limit:
            return text, ""
        prefix1 = "1/2 "
        prefix2 = "2/2 "
        first_chunks = self._split_text_by_lines(text, first_limit - len(prefix1))
        part1 = (prefix1 + first_chunks[0].rstrip()) if first_chunks else prefix1
        remaining_text = "".join(first_chunks[1:]).lstrip("\n") if first_chunks else text
        remaining_chunks = self._split_text_by_lines(remaining_text, second_limit - len(prefix2))
        part2_base = remaining_chunks[0].rstrip() if remaining_chunks else remaining_text[: max(0, second_limit - len(prefix2))]
        part2 = prefix2 + part2_base if part2_base else ""
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
                    'parse_mode': parse_mode,
                    'disable_web_page_preview': False
                }
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
            data = {
                'chat_id': target_chat_id,
                'parse_mode': parse_mode
            }
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
        """Envía mensaje al Bot de Crypto"""
        if image_path:
            part1, part2 = self._split_text_two_parts(message, self._caption_limit, self._text_limit)
            if part2:
                sent = self.send_photo(image_path, caption=part1, bot_type='crypto')
                if not sent:
                    return False
                return self.send_message(part2, bot_type='crypto')
            return self.send_photo(image_path, caption=message, bot_type='crypto')
        part1, part2 = self._split_text_two_parts(message, self._text_limit, self._text_limit)
        if part2:
            return self.send_message(part1, bot_type='crypto') and self.send_message(part2, bot_type='crypto')
        return self.send_message(message, bot_type='crypto')

    def send_market_message(self, message: str, image_path: Optional[str] = None) -> bool:
        """Envía mensaje al Bot de Mercados"""
        if image_path:
            return self.send_photo(image_path, caption=message, bot_type='markets')
        return self.send_message(message, bot_type='markets')

    def send_news_message(self, news: dict, image_path: Optional[str] = None) -> bool:
        """Envía noticia usando plantilla profesional"""
        try:
            message = TelegramMessageTemplates.format_news(news)
            
            # Determinar grupo según categoría
            category = news.get('category', 'crypto').lower()
            if category == 'markets':
                group = self.group_markets or Config.TELEGRAM_GROUP_MARKETS
            elif category == 'signals':
                group = self.group_signals or Config.TELEGRAM_GROUP_SIGNALS
            else:
                group = self.group_crypto or Config.TELEGRAM_GROUP_CRYPTO

            message = message.replace("**", "*") # Fix markdown

            return self.send_to_specific_group(message, group, image_path=image_path, parse_mode='Markdown')
        except Exception as e:
            logger.error(f"❌ Error enviando noticia: {e}")
            return False

    def send_market_analysis(self, analysis: dict, sentiment: dict, image_path: Optional[str] = None) -> bool:
        """Envía análisis usando plantilla profesional"""
        try:
            message = TelegramMessageTemplates.format_market_analysis(analysis, sentiment)
            # Fix bold
            message = message.replace("**", "*")
            
            return self.send_to_specific_group(message, self.group_crypto, image_path=image_path, parse_mode='Markdown')
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
            longs = signals_data.get('top_longs', [])
            shorts = signals_data.get('top_shorts', [])
            
            # Usar plantilla profesional
            message = TelegramMessageTemplates.format_signals_batch(longs, shorts)
            message = message.replace("**", "*") # Fix markdown
            
            return self.send_to_specific_group(
                message, 
                Config.TELEGRAM_GROUP_SIGNALS or self.group_signals,
                image_path=image_path,
                parse_mode='Markdown'
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
        Envía un reporte completo formateado a Telegram.
        
        Args:
            analysis: Análisis generado por la IA
            market_sentiment: Datos del sentimiento del mercado
            coins: Lista de criptomonedas analizadas
            
        Returns:
            True si se envió correctamente
        """
        try:
            # Crear el mensaje formateado
            message = self._format_report(analysis, market_sentiment, coins_only_binance, coins_both_enriched)
            
            image_path = Config.REPORT_24H_IMAGE_PATH or Config.REPORT_2H_IMAGE_PATH
            if image_path:
                part1, part2 = self._split_text_two_parts(message, self._caption_limit, self._text_limit)
                if part2:
                    sent = self.send_photo(image_path, caption=part1, bot_type='crypto')
                    if not sent:
                        return False
                    return self.send_message(part2, bot_type='crypto')
                return self.send_photo(image_path, caption=message, bot_type='crypto')
            part1, part2 = self._split_text_two_parts(message, self._text_limit, self._text_limit)
            if part2:
                return self.send_message(part1, bot_type='crypto') and self.send_message(part2, bot_type='crypto')
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
            message += f"\n<b>🤖 Recomendación de IA:</b>\n"
            recommendation = analysis.get('recommendation', '')
            recommendation = recommendation.replace('**', '').replace('*', '').strip()
            if recommendation and recommendation.lower() != 'n/a':
                first_line = recommendation.split('\n')[0].strip()
                message += f"{first_line}\n"
            else:
                message += "Análisis completado. Revisar oportunidades en el mercado.\n"
        
        # Nivel de confianza
        confidence = analysis.get('confidence_level', 0)
        confidence_bar = "🟢" * confidence + "⚪" * (10 - confidence)
        message += f"\n<b>📊 Confianza:</b> {confidence_bar} ({confidence}/10)\n"
        
        # Footer
        message += "\n<i>⚠️ Disclaimer: Este análisis es automatizado y no constituye asesoría financiera. Investiga antes de invertir.</i>"
        
        return message
