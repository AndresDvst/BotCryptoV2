# -*- coding: utf-8 -*-
"""
Servicio para enviar mensajes a Telegram.
Envía reportes y análisis al bot de Telegram configurado.
"""
import requests
from typing import Dict
from config.config import Config
from utils.logger import logger

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
            if len(message) > 4096:
                logger.warning("⚠️ Mensaje muy largo, se truncará")
                message = message[:4093] + "..."
            
            url = f"{base_url}/sendMessage"
            payload = {
                'chat_id': self._resolve_chat_id(parse_mode),
                'text': message,
                'parse_mode': parse_mode,
                'disable_web_page_preview': False
            }
            
            response = requests.post(url, json=payload, timeout=10)
            
            if response.status_code == 200:
                return True
            else:
                logger.error(f"❌ Error Telegram ({response.status_code}): {response.text}")
                return False
        except Exception as e:
            logger.error(f"❌ Excepción Telegram: {e}")
            return False

    def _resolve_chat_id(self, parse_mode: str = "HTML", bot_type: str = 'crypto') -> str:
        """
        Resuelve el ID del chat destino.
        STRICT MODE: Solo devuelve grupos si están configurados.
        """
        if bot_type == 'markets':
            if self.group_markets:
                return self.group_markets
            logger.warning("⚠️ TELEGRAM_GROUP_MARKETS no configurado. Se omite envío para evitar chat privado.")
            return None
            
        if bot_type == 'signals':
            if self.group_signals:
                return self.group_signals
            logger.warning("⚠️ TELEGRAM_GROUP_SIGNALS no configurado. Se omite envío para evitar chat privado.")
            return None
            
        # Crypto (Default)
        if self.group_crypto:
            return self.group_crypto
        logger.warning("⚠️ TELEGRAM_GROUP_CRYPTO no configurado. Se omite envío para evitar chat privado.")
        return None

    def send_message(self, message: str, parse_mode: str = "HTML", bot_type: str = 'crypto', chat_id: str = None) -> bool:
        """
        Envía mensaje al bot especificado.
        bot_type: 'crypto', 'markets', 'signals'
        """
        target_url = self.url_crypto
        if bot_type == 'markets' and self.url_markets:
            target_url = self.url_markets
        elif bot_type == 'signals' and self.url_signals:
            target_url = self.url_signals
            
        # Resolver chat id por tipo (o usar el proporcionado)
        target_chat_id = chat_id or self._resolve_chat_id(parse_mode, bot_type)
        
        if not target_chat_id:
            logger.error(f"❌ No se pudo determinar un Target Group ID para {bot_type}. El envío ha sido bloqueado por seguridad (No Private Chat).")
            return False
        
        try:
            url = f"{target_url or self.url_crypto}/sendMessage"
            payload = {
                'chat_id': target_chat_id,
                'text': message[:4093] + "..." if len(message) > 4096 else message,
                'parse_mode': parse_mode,
                'disable_web_page_preview': False
            }
            response = requests.post(url, json=payload, timeout=10)
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

    def send_crypto_message(self, message: str) -> bool:
        """Envía mensaje al Bot de Crypto"""
        return self.send_message(message, bot_type='crypto')

    def send_market_message(self, message: str) -> bool:
        """Envía mensaje al Bot de Mercados"""
        return self.send_message(message, bot_type='markets')

    def send_signal_message(self, message: str) -> bool:
        """Envía mensaje al Bot de Señales"""
        return self.send_message(message, bot_type='signals')
    
    def send_report(self, analysis: Dict, market_sentiment: Dict, coins_only_binance: list, coins_both_enriched: list) -> bool:
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
            
            # Enviar el mensaje
            return self.send_message(message)
            
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
