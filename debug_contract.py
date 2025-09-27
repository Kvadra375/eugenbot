#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Отладка извлечения контракта
"""

import re

def debug_contract_extraction(message: str):
    """Отлаживает извлечение контракта"""
    print("🔍 Отладка извлечения контракта")
    print("=" * 50)
    print(f"Сообщение:\n{message}")
    print()
    
    # Ищем все возможные контракты
    print("1. Ищем CA: ...")
    ca_matches = re.findall(r'CA:\s*([a-fA-F0-9x]+)', message)
    print(f"   Найдено: {ca_matches}")
    
    print("2. Ищем в dexscreener ссылках...")
    dexscreener_matches = re.findall(r'dexscreener\.com/(\w+)/([a-fA-F0-9x]+)', message)
    print(f"   Найдено: {dexscreener_matches}")
    
    print("3. Ищем в gmgn ссылках...")
    gmgn_matches = re.findall(r'gmgn\.ai/(\w+)/token/([a-fA-F0-9x]+)', message)
    print(f"   Найдено: {gmgn_matches}")
    
    print("4. Ищем все hex адреса...")
    hex_matches = re.findall(r'0x[a-fA-F0-9]+', message)
    print(f"   Найдено: {hex_matches}")
    
    print("5. Ищем все адреса (включая Solana)...")
    all_addresses = re.findall(r'[a-fA-F0-9]{20,}', message)
    print(f"   Найдено: {all_addresses}")
    
    print("6. Ищем Chain: ...")
    chain_matches = re.findall(r'Chain:\s*(\w+)', message)
    print(f"   Найдено: {chain_matches}")

def test_different_messages():
    """Тестирует разные типы сообщений"""
    
    # Сообщение 1: с полным контрактом
    message1 = """RAIN | 8.05% | Short 

Price MEXC (https://futures.mexc.com/exchange/RAIN_USDT?inviteCode=1RTNH): 0.00369
Price Dexscreener (https://dexscreener.com/arbitrum/0x25118290e6A5f4139381D072181157035864099d): 0.003415

CA: 0x25118290e6A5f4139381D072181157035864099d
Chain: arbitrum"""
    
    print("📝 Тест 1: Сообщение с полным контрактом")
    debug_contract_extraction(message1)
    print("\n" + "="*80 + "\n")
    
    # Сообщение 2: с обрезанным контрактом
    message2 = """STREAMER | 8.05% | Short 

Price MEXC (https://futures.mexc.com/exchange/STREAMER_USDT?inviteCode=1RTNH): 0.00369
Price Dexscreener (https://dexscreener.com/solana/3a...): 0.003415

CA: 3a...
Chain: solana"""
    
    print("📝 Тест 2: Сообщение с обрезанным контрактом")
    debug_contract_extraction(message2)
    print("\n" + "="*80 + "\n")
    
    # Сообщение 3: с GMGN ссылкой
    message3 = """FTT +3.61% in 10 secs!
MEXC (https://futures.mexc.com/exchange/FTT_USDT) — GMGN (https://gmgn.ai/eth/token/0x50d1c9771902476076ecfc8b2a83ad6b9355a4c9) | Limit ~$95900"""
    
    print("📝 Тест 3: Сообщение с GMGN ссылкой")
    debug_contract_extraction(message3)

if __name__ == "__main__":
    test_different_messages()



