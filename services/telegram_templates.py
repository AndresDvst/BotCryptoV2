"""
Plantillas de mensajes profesionales para Telegram.
Usa caracteres Unicode y emojis para crear diseños atractivos.
"""

class TelegramMessageTemplates:
    """Plantillas profesionales para diferentes tipos de mensajes"""
    
    # Emojis animados (Telegram los renderiza animados automáticamente)
    EMOJI_FIRE = "🔥"
    EMOJI_ROCKET = "🚀"
    EMOJI_CHART_UP = "📈"
    EMOJI_CHART_DOWN = "📉"
    EMOJI_MONEY = "💰"
    EMOJI_ALERT = "⚠️"
    EMOJI_CHECK = "✅"
    EMOJI_CROSS = "❌"
    EMOJI_STAR = "⭐"
    EMOJI_DIAMOND = "💎"
    EMOJI_BRAIN = "🧠"
    EMOJI_EYES = "👀"
    EMOJI_LIGHTNING = "⚡"
    
    # Caracteres Unicode para diseño
    BOX_TOP_LEFT = "╔"
    BOX_TOP_RIGHT = "╗"
    BOX_BOTTOM_LEFT = "╚"
    BOX_BOTTOM_RIGHT = "╝"
    BOX_HORIZONTAL = "═"
    BOX_VERTICAL = "║"
    LINE_HEAVY = "━"
    LINE_LIGHT = "─"
    BULLET = "•"
    ARROW_RIGHT = "→"
    ARROW_UP = "↑"
    ARROW_DOWN = "↓"
    
    @staticmethod
    def create_header(title: str, emoji: str = "🎯") -> str:
        """Crea header profesional con caja"""
        box_width = len(title) + 4
        # Asegurar que no sea demasiado ancho para móviles
        if box_width > 30:
            box_width = 30
            title = title[:24] + "..."
            
        top_line = f"{TelegramMessageTemplates.BOX_TOP_LEFT}{TelegramMessageTemplates.BOX_HORIZONTAL * box_width}{TelegramMessageTemplates.BOX_TOP_RIGHT}"
        middle_line = f"{TelegramMessageTemplates.BOX_VERTICAL} {emoji} {title} {TelegramMessageTemplates.BOX_VERTICAL}"
        bottom_line = f"{TelegramMessageTemplates.BOX_BOTTOM_LEFT}{TelegramMessageTemplates.BOX_HORIZONTAL * box_width}{TelegramMessageTemplates.BOX_BOTTOM_RIGHT}"
        
        return f"{top_line}\n{middle_line}\n{bottom_line}"
    
    @staticmethod
    def format_trading_signal(signal: dict, index: int) -> str:
        """
        Formatea una señal de trading de forma ultra-profesional.
        """
        symbol = signal.get('symbol', 'N/A').replace('/USDT', '')
        signal_type = signal.get('signal_type', 'NEUTRAL')
        confidence = signal.get('confidence', 0)
        entry = signal.get('entry_price', 0)
        sl = signal.get('stop_loss', 0)
        tp = signal.get('take_profit', 0)
        reasons = signal.get('reasons', [])
        
        # Emoji según tipo
        type_emoji = "🚀" if signal_type == "LONG" else "🔻" if signal_type == "SHORT" else "⚪"
        
        # Barra de confianza visual
        bars_filled = int(confidence / 10)
        bars_empty = 10 - bars_filled
        confidence_bar = "█" * bars_filled + "░" * bars_empty
        
        # Calcular risk/reward
        if signal_type == "LONG":
            risk = abs(entry - sl)
            reward = abs(tp - entry)
        else:
            risk = abs(sl - entry)
            reward = abs(entry - tp)
        
        rr_ratio = reward / risk if risk > 0 else 0
        
        # Calcular porcentajes SL/TP
        sl_percent = ((sl - entry) / entry * 100) if entry > 0 else 0
        tp_percent = ((tp - entry) / entry * 100) if entry > 0 else 0
        
        message = f"""
{TelegramMessageTemplates.LINE_HEAVY * 30}
{type_emoji} **#{index} {symbol} {signal_type}**
{TelegramMessageTemplates.LINE_HEAVY * 30}

📊 **Confianza:** {confidence_bar} **{confidence:.0f}%**
💰 **Entrada:**   `${entry:,.8f}`
🛑 **Stop Loss:** `${sl:,.8f}` *({sl_percent:+.1f}%)*
🎯 **Target:**    `${tp:,.8f}` *({tp_percent:+.1f}%)*

📈 **Señales activas:**"""
        
        # Añadir razones con checkmarks
        for reason in reasons[:5]:  # Max 5 razones
            message += f"\n  ✓ {reason}"
        
        # Risk/Reward
        message += f"\n\n⚡ **Risk/Reward:** 1:{rr_ratio:.2f}"
        
        # Advertencia si confianza baja
        if confidence < 50:
            message += f"\n\n{TelegramMessageTemplates.EMOJI_ALERT} **ADVERTENCIA:** Baja confianza - Alto riesgo"
        
        return message
    
    @staticmethod
    def format_signals_batch(longs: list, shorts: list) -> str:
        """
        Formatea lote completo de señales de forma profesional.
        """
        header = TelegramMessageTemplates.create_header("SEÑALES DE TRADING", "🎯")
        
        message_parts = [header, ""]
        
        # Timestamp
        from datetime import datetime
        timestamp = datetime.now().strftime("%d/%m/%Y %H:%M")
        message_parts.append(f"🕐 **Actualizado:** {timestamp}\n")
        
        # Señales LONG
        if longs:
            message_parts.append(f"{'🟢' * 3} **POSICIONES LONG** {'🟢' * 3}\n")
            for i, signal in enumerate(longs, 1):
                message_parts.append(TelegramMessageTemplates.format_trading_signal(signal, i))
                message_parts.append("")  # Espacio
        
        # Señales SHORT
        if shorts:
            message_parts.append(f"{'🔴' * 3} **POSICIONES SHORT** {'🔴' * 3}\n")
            for i, signal in enumerate(shorts, 1):
                message_parts.append(TelegramMessageTemplates.format_trading_signal(signal, i))
                message_parts.append("")  # Espacio
        
        # Footer con disclaimer
        footer = f"""
{TelegramMessageTemplates.LINE_LIGHT * 40}
⚠️ **DISCLAIMER**
Este análisis es automatizado. No constituye asesoría financiera.
Investiga antes de invertir. Usa gestión de riesgo apropiada.
{TelegramMessageTemplates.LINE_LIGHT * 40}
"""
        message_parts.append(footer)
        
        return "\n".join(message_parts)
    
    @staticmethod
    def format_news(news: dict) -> str:
        """
        Formatea noticia de forma ultra-atractiva.
        """
        category = news.get('category', 'crypto').upper()
        title = news.get('title', '')
        summary = news.get('summary', '')
        score = news.get('score', 0)
        
        # Emoji según categoría
        cat_emoji = "🪙" if category == 'CRYPTO' else "📈" if category == 'MARKETS' else "🎯"
        
        # Header
        header = TelegramMessageTemplates.create_header(f"{cat_emoji} NOTICIA {category}", cat_emoji)
        
        # Relevancia visual
        stars = "⭐" * min(score, 10)
        
        # Emoji para título según relevancia
        title_emoji = "🔥" if score >= 8 else "💎" if score >= 6 else "📌"
        
        message = f"""{header}

{title_emoji} **{title}**

{summary}

{TelegramMessageTemplates.LINE_LIGHT * 30}
📊 **Relevancia:** {stars} *({score}/10)*

🔗 **Fuente:** TradingView
"""
        return message
    
    @staticmethod
    def format_market_analysis(analysis: dict, sentiment: dict) -> str:
        """
        Formatea análisis de mercado tipo dashboard.
        """
        sentiment_value = sentiment.get('fear_greed_index', {}).get('value', 50)
        sentiment_text = sentiment.get('overall_sentiment', 'Neutral')
        recommendation = analysis.get('recommendation', 'N/A')
        confidence = analysis.get('confidence_level', 0)
        
        # Emoji según sentimiento
        if sentiment_value >= 75:
            sentiment_emoji = "🤑"  # Greed
        elif sentiment_value >= 50:
            sentiment_emoji = "😊"  # Neutral-Positive
        elif sentiment_value >= 25:
            sentiment_emoji = "😨"  # Fear
        else:
            sentiment_emoji = "😱"  # Extreme Fear
        
        # Barra de confianza
        bars_filled = int(confidence / 10)
        bars_empty = 10 - bars_filled
        confidence_bar = "█" * bars_filled + "░" * bars_empty
        
        header = TelegramMessageTemplates.create_header("ANÁLISIS DE MERCADO", "🧠")
        
        message = f"""{header}

📊 **SENTIMIENTO GENERAL**
{TelegramMessageTemplates.LINE_HEAVY * 25}
{sentiment_emoji} **Fear & Greed:** {sentiment_value} *({sentiment_text})*
📈 **Tendencia:** Alcista
📉 **Volatilidad:** Media

🎯 **RECOMENDACIÓN IA**
{TelegramMessageTemplates.LINE_HEAVY * 25}
{recommendation[:300]}...

🧠 **Confianza:** {confidence_bar} **{confidence}/10**
"""
        return message
