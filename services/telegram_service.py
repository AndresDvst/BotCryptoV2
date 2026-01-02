# -*- coding: utf-8 -*-
"""
Servicio para enviar mensajes a Telegram.
Envía reportes y análisis al bot de Telegram configurado.
"""
# -*- coding: utf-8 -*-
import requests
from typing import Dict
from config.config import Config
from utils.logger import logger

class TelegramService:
    """Servicio para enviar mensajes a Telegram"""
    
    def __init__(self):
        """Inicializa el servicio de Telegram"""
        self.bot_token = Config.TELEGRAM_BOT_TOKEN
        self.chat_id = Config.TELEGRAM_CHAT_ID
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"
        logger.info("✅ Servicio de Telegram inicializado")
    
    def send_message(self, message: str, parse_mode: str = "HTML") -> bool:
        """
        Envía un mensaje al chat de Telegram.
        
        Args:
            message: Mensaje a enviar (máximo 4096 caracteres)
            parse_mode: Modo de parseo (HTML o Markdown)
            
        Returns:
            True si se envió correctamente, False en caso contrario
        """
        try:
            # Telegram tiene límite de 4096 caracteres
            if len(message) > 4096:
                logger.warning("⚠️ Mensaje muy largo, se truncará")
                message = message[:4093] + "..."
            
            url = f"{self.base_url}/sendMessage"
            payload = {
                'chat_id': self.chat_id,
                'text': message,
                'parse_mode': parse_mode,
                'disable_web_page_preview': False
            }
            
            response = requests.post(url, json=payload, timeout=10)
            
            if response.status_code == 200:
                logger.info("✅ Mensaje enviado a Telegram")
                return True
            else:
                logger.error(f"❌ Error al enviar mensaje: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error al enviar mensaje a Telegram: {e}")
            return False
    
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
        sentiment = market_sentiment.get('sentiment', 'N/A')
        
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
        message += "\n<b>⏱ Top 10 Criptomonedas que SUBIERON en 2h (Binance + Bybit):</b>\n"
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

        message += "\n<b>⏱ Top 10 Criptomonedas que BAJARON en 2h (Binance + Bybit):</b>\n"
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
        
        # Recomendación de la IA
        message += f"\n<b>🤖 Recomendación de IA:</b>\n"
        recommendation = analysis.get('recommendation', '')
        # Limpiar el texto de la recomendación
        recommendation = recommendation.replace('**', '').replace('*', '').strip()
        if recommendation and recommendation.lower() != 'n/a':
            # Tomar solo la primera línea si hay múltiples líneas
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