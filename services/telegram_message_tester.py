"""
Módulo de pruebas de mensajes de Telegram.
Permite probar y modificar el formato de mensajes antes de aplicarlos globalmente.
"""
from datetime import datetime
from typing import Optional
from utils.logger import logger


class TelegramMessageTester:
    """Clase para probar formatos de mensajes de Telegram"""
    
    def __init__(self, telegram_service=None):
        self.telegram = telegram_service
        
        # Plantillas de mensajes para pruebas
        self.templates = {
            'signal_crypto': self._template_signal_crypto,
            'signal_traditional': self._template_signal_traditional,
            'market_summary': self._template_market_summary,
            'news': self._template_news,
            'pump_dump': self._template_pump_dump,
            'custom': self._template_custom,
        }
    
    def _template_signal_crypto(self) -> str:
        """Plantilla de señal de criptomoneda"""
        return """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🚀 SEÑAL DE TRADING CRYPTO
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 Par: BTC/USDT
📈 Tipo: LONG
⭐ Rating: ⭐⭐⭐ Premium

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💰 DETALLES DE LA OPERACIÓN
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎯 Entrada: $97,500.00
🎯 Take Profit: $102,375.00 (+5.0%)
🛑 Stop Loss: $94,575.00 (-3.0%)
📊 Ratio R:R: 1:1.67

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📉 INDICADORES TÉCNICOS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 RSI: 28.5 🟢 Sobreventa
📈 MACD: Cruce Alcista ✅
📉 BB: Precio en banda inferior
📊 EMA: 20 > 50 (Tendencia alcista)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💼 GESTIÓN DE CAPITAL
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💵 Capital sugerido: $20.00
⚠️ Riesgo máximo: 25% ($5.00)
📦 Tamaño posición: 0.0002 BTC
💰 Ganancia potencial: $8.33

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ DISCLAIMER
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• No es consejo financiero
• Usa stop loss SIEMPRE
• DYOR - Haz tu investigación
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔥 Confianza: 85%
⏰ {timestamp}
""".format(timestamp=datetime.now().strftime("%d/%m/%Y %H:%M"))

    def _template_signal_traditional(self) -> str:
        """Plantilla de señal de mercados tradicionales"""
        return """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📈 SEÑAL MERCADOS TRADICIONALES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 Instrumento: EUR/USD
💱 Mercado: FOREX
🔻 Tipo: SHORT
⭐ Rating: ⭐⭐ Estándar

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💰 DETALLES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎯 Entrada: $1.0850
🎯 Take Profit: $1.0750 (+0.92%)
🛑 Stop Loss: $1.0900 (-0.46%)
📊 Ratio R:R: 1:2.0

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📉 ANÁLISIS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 RSI: 72.3 🔴 Sobrecompra
📈 MACD: Cruce Bajista
📉 Tendencia: Corrección esperada

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ GESTIÓN DE RIESGO
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• Riesgo máximo: 25% ($5.00)
• Usa stop loss SIEMPRE
• DYOR - Haz tu investigación
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔥 Confianza: 60%
⏰ {timestamp}
""".format(timestamp=datetime.now().strftime("%d/%m/%Y %H:%M"))

    def _template_market_summary(self) -> str:
        """Plantilla de resumen de mercado"""
        return """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 RESUMEN DE MERCADO CRYPTO
⏰ {timestamp}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🌡️ SENTIMIENTO: Miedo Extremo 😱
📊 Fear & Greed Index: 14/100

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📈 TOP SUBIDAS 24H
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🟢 CREAM/USDT  +65.4%
🟢 PNT/USDT    +45.2%
🟢 ANIME/USDT  +32.1%

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📉 TOP BAJADAS 24H
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔴 BETA/USDT   -64.0%
🔴 VIB/USDT    -63.3%
🔴 HARD/USDT   -28.5%

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💡 ANÁLISIS IA
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

El mercado muestra señales de 
capitulación. Posible rebote en 
próximas 24-48h si BTC mantiene 
soporte en $95,000.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""".format(timestamp=datetime.now().strftime("%d/%m/%Y %H:%M"))

    def _template_news(self) -> str:
        """Plantilla de noticia"""
        return """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📰 NOTICIA IMPORTANTE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📌 Fed mantiene tasas sin cambios

📝 La Reserva Federal decidió 
mantener las tasas de interés 
sin cambios en su reunión de 
enero, señalando que vigilará 
la inflación de cerca.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 IMPACTO ESPERADO
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

• BTC: 📈 Positivo (Liquidez)
• ETH: 📈 Positivo
• Acciones: 📈 Positivo

🏷️ Categoría: Macro
📍 Fuente: Reuters
⏰ {timestamp}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""".format(timestamp=datetime.now().strftime("%d/%m/%Y %H:%M"))

    def _template_pump_dump(self) -> str:
        """Plantilla de alerta pump/dump"""
        return """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🚨 ALERTA DE MOVIMIENTO
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🚀 PUMP DETECTADO

📊 CREAM/USDT
💰 Precio: $0.0234
📈 Cambio: +45.6% (2h)
📊 Volumen: 5.2x promedio

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ PRECAUCIÓN
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

• Movimiento volátil detectado
• Alto riesgo de reversión
• NO es recomendación de compra

⏰ {timestamp}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""".format(timestamp=datetime.now().strftime("%d/%m/%Y %H:%M"))

    def _template_custom(self) -> str:
        """Plantilla personalizada para pruebas"""
        return """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🧪 MENSAJE DE PRUEBA
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Este es un mensaje de prueba
para verificar el formato en
Telegram.

📊 Sección 1
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• Elemento 1
• Elemento 2
• Elemento 3

📈 Sección 2
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🟢 Positivo: +25%
🔴 Negativo: -15%

⏰ {timestamp}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""".format(timestamp=datetime.now().strftime("%d/%m/%Y %H:%M"))

    def show_menu(self):
        """Muestra el menú de pruebas de mensajes"""
        while True:
            print("\n" + "=" * 60)
            print("🧪 PRUEBAS DE MENSAJES TELEGRAM")
            print("=" * 60)
            print("1. 🚀 Señal Crypto (LONG/SHORT)")
            print("2. 📈 Señal Mercados Tradicionales")
            print("3. 📊 Resumen de Mercado")
            print("4. 📰 Noticia")
            print("5. 🚨 Alerta Pump/Dump")
            print("6. 🧪 Mensaje Personalizado")
            print("7. ✏️  Editar mensaje antes de enviar")
            print("0. 🔙 Volver")
            print("=" * 60)
            
            choice = input("\nSelecciona una opción: ").strip()
            
            if choice == '0':
                break
            elif choice == '1':
                self._send_test_message('signal_crypto', "Señal Crypto")
            elif choice == '2':
                self._send_test_message('signal_traditional', "Señal Tradicional")
            elif choice == '3':
                self._send_test_message('market_summary', "Resumen de Mercado")
            elif choice == '4':
                self._send_test_message('news', "Noticia")
            elif choice == '5':
                self._send_test_message('pump_dump', "Alerta Pump/Dump")
            elif choice == '6':
                self._send_test_message('custom', "Mensaje Personalizado")
            elif choice == '7':
                self._edit_and_send()
            else:
                print("⚠️ Opción no válida")
    
    def _send_test_message(self, template_key: str, name: str):
        """Envía un mensaje de prueba"""
        if not self.telegram:
            print("❌ Servicio de Telegram no disponible")
            return
        
        template_func = self.templates.get(template_key)
        if not template_func:
            print(f"❌ Plantilla '{template_key}' no encontrada")
            return
        
        message = template_func()
        
        print(f"\n📝 Vista previa del mensaje ({name}):")
        print("-" * 50)
        print(message)
        print("-" * 50)
        
        confirm = input("\n¿Enviar este mensaje al canal de señales? (s/n): ").strip().lower()
        
        if confirm == 's':
            try:
                self.telegram.send_signal_message(message)
                print("✅ Mensaje enviado exitosamente")
                logger.info(f"✅ Mensaje de prueba '{name}' enviado a Telegram")
            except Exception as e:
                print(f"❌ Error enviando mensaje: {e}")
                logger.error(f"❌ Error enviando mensaje de prueba: {e}")
        else:
            print("❌ Envío cancelado")
    
    def _edit_and_send(self):
        """Permite editar un mensaje antes de enviarlo"""
        if not self.telegram:
            print("❌ Servicio de Telegram no disponible")
            return
        
        print("\n📝 Selecciona la plantilla base:")
        print("1. Señal Crypto")
        print("2. Señal Tradicional")
        print("3. Resumen de Mercado")
        print("4. Noticia")
        print("5. Alerta Pump/Dump")
        print("6. Vacío (escribir desde cero)")
        
        choice = input("\nOpción: ").strip()
        
        templates_map = {
            '1': 'signal_crypto',
            '2': 'signal_traditional',
            '3': 'market_summary',
            '4': 'news',
            '5': 'pump_dump',
        }
        
        if choice == '6':
            message = ""
        elif choice in templates_map:
            message = self.templates[templates_map[choice]]()
        else:
            print("❌ Opción no válida")
            return
        
        print("\n" + "=" * 60)
        print("✏️  EDITOR DE MENSAJE")
        print("=" * 60)
        print("Escribe tu mensaje (termina con una línea vacía + 'FIN'):")
        print("Para usar la plantilla base, escribe 'BASE'")
        print("-" * 60)
        
        if message:
            use_base = input("¿Usar plantilla como base? (s/n): ").strip().lower()
            if use_base == 's':
                print("\nPlantilla cargada. Puedes copiarla y modificarla.")
                print(message)
                print("-" * 60)
        
        print("\nEscribe tu mensaje (escribe 'ENVIAR' en una línea para terminar):")
        
        lines = []
        while True:
            line = input()
            if line.strip().upper() == 'ENVIAR':
                break
            if line.strip().upper() == 'BASE' and message:
                lines = message.split('\n')
                print("📋 Plantilla base cargada")
                continue
            lines.append(line)
        
        final_message = '\n'.join(lines)
        
        if not final_message.strip():
            print("❌ Mensaje vacío, cancelando")
            return
        
        print("\n📝 Vista previa:")
        print("-" * 50)
        print(final_message)
        print("-" * 50)
        
        confirm = input("\n¿Enviar este mensaje? (s/n): ").strip().lower()
        
        if confirm == 's':
            try:
                self.telegram.send_signal_message(final_message)
                print("✅ Mensaje enviado exitosamente")
                logger.info("✅ Mensaje personalizado enviado a Telegram")
            except Exception as e:
                print(f"❌ Error enviando mensaje: {e}")
        else:
            print("❌ Envío cancelado")
    
    def quick_test(self) -> bool:
        """Prueba rápida desde el modo espera inteligente"""
        print("\n🧪 PRUEBA RÁPIDA DE MENSAJE")
        print("1. Señal Crypto")
        print("2. Señal Tradicional")
        print("3. Resumen")
        print("0. Cancelar")
        
        choice = input("Opción: ").strip()
        
        if choice == '1':
            self._send_test_message('signal_crypto', "Señal Crypto")
            return True
        elif choice == '2':
            self._send_test_message('signal_traditional', "Señal Tradicional")
            return True
        elif choice == '3':
            self._send_test_message('market_summary', "Resumen")
            return True
        
        return False
