#!/usr/bin/env python3
# Script: envía un mensaje de prueba a cada grupo (crypto, markets, signals)
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.config import Config
from services.telegram_service import TelegramService
from services.telegram_message_tester import TelegramMessageTester


def main():
    tg = TelegramService()
    tester = TelegramMessageTester(telegram_service=tg)

    # Mapear grupos a plantillas de prueba
    mapping = [
        ('crypto', Config.TELEGRAM_GROUP_CRYPTO or Config.TELEGRAM_CHAT_ID_CRYPTO, 'signal_crypto'),
        ('markets', Config.TELEGRAM_GROUP_MARKETS or Config.TELEGRAM_CHAT_ID_MARKETS, 'signal_traditional'),
        ('signals', Config.TELEGRAM_GROUP_SIGNALS or Config.TELEGRAM_CHAT_ID_SIGNALS, 'signal_crypto'),
    ]

    results = {}
    for name, group_id, template_key in mapping:
        if not group_id:
            print(f"[SKIP] Grupo {name} no configurado (group_id vacío)")
            results[name] = False
            continue
        msg = tester.templates.get(template_key)()
        print(f"[SEND] {name} -> group {group_id} using template {template_key}")
        try:
            ok = tg.send_to_specific_group(msg, group_id, image_path=None, parse_mode=None)
            results[name] = ok
            print(f"   -> Sent: {ok}")
        except Exception as e:
            print(f"   -> Error: {e}")
            results[name] = False

    print('\nSummary:')
    for k, v in results.items():
        print(f" - {k}: {'OK' if v else 'FAILED'}")

if __name__ == '__main__':
    main()
