#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Telegram Bot Parser для автоматизации работы с криптовалютными ботами
Парсит сообщения от ботов и конвертирует тикеры в формат MEXC
"""

import re
import webbrowser
import pyperclip
import time
from typing import Optional, Dict, List, Tuple
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TelegramBotParser:
    def __init__(self):
        self.ticker_patterns = {
            'mexc_tracker': r'(\w+)\s+\|\s+[\d.]+%\s+\|\s+(Long|Short)',
            'kormushka': r'(\w+)\s+\+[\d.]+%\s+in\s+\d+\s+secs!',
            'pumply': r'🔻\s+(SHORT|LONG)\s+\$(\w+)\s+\+[\d.]+%\s+on\s+MEXC'
        }
        
        self.dex_patterns = {
            'dexscreener': r'dexscreener\.com/(\w+)/([a-fA-F0-9x]+)',
            'gmgn': r'gmgn\.ai/(\w+)/token/([a-fA-F0-9x]+)'
        }

    def parse_mexc_tracker_message(self, message: str) -> Optional[Dict]:
        """Парсит сообщения от @mexcTracker"""
        try:
            # Ищем тикер в формате "DEXE | 8.17% | Long"
            ticker_match = re.search(self.ticker_patterns['mexc_tracker'], message)
            if not ticker_match:
                return None
                
            ticker = ticker_match.group(1)
            direction = ticker_match.group(2)
            
            # Ищем ссылку на dexscreener
            dexscreener_match = re.search(self.dex_patterns['dexscreener'], message)
            dex_info = None
            if dexscreener_match:
                chain = dexscreener_match.group(1)
                contract = dexscreener_match.group(2)
                dex_info = {
                    'type': 'dexscreener',
                    'chain': chain,
                    'contract': contract,
                    'url': f"https://dexscreener.com/{chain}/{contract}"
                }
            
            return {
                'ticker': ticker,
                'direction': direction,
                'dex_info': dex_info,
                'source': 'mexc_tracker'
            }
        except Exception as e:
            logger.error(f"Ошибка парсинга mexc_tracker: {e}")
            return None

    def parse_kormushka_message(self, message: str) -> Optional[Dict]:
        """Парсит сообщения от @kormushka_mexc"""
        try:
            # Ищем тикер в формате "FTT +3.61% in 10 secs!"
            ticker_match = re.search(self.ticker_patterns['kormushka'], message)
            if not ticker_match:
                return None
                
            ticker = ticker_match.group(1)
            
            # Ищем ссылку на gmgn
            gmgn_match = re.search(self.dex_patterns['gmgn'], message)
            dex_info = None
            if gmgn_match:
                chain = gmgn_match.group(1)
                contract = gmgn_match.group(2)
                dex_info = {
                    'type': 'gmgn',
                    'chain': chain,
                    'contract': contract,
                    'url': f"https://gmgn.ai/{chain}/token/{contract}"
                }
            
            return {
                'ticker': ticker,
                'direction': None,  # В этом боте нет направления
                'dex_info': dex_info,
                'source': 'kormushka'
            }
        except Exception as e:
            logger.error(f"Ошибка парсинга kormushka: {e}")
            return None

    def parse_pumply_message(self, message: str) -> Optional[Dict]:
        """Парсит сообщения от @pumply_futures_dex"""
        try:
            # Ищем тикер в формате "🔻 SHORT $RICE +6.32% on MEXC"
            ticker_match = re.search(self.ticker_patterns['pumply'], message)
            if not ticker_match:
                return None
                
            direction = ticker_match.group(1)
            ticker = ticker_match.group(2)
            
            # Ищем ссылку на dexscreener в network
            dexscreener_match = re.search(self.dex_patterns['dexscreener'], message)
            dex_info = None
            if dexscreener_match:
                chain = dexscreener_match.group(1)
                contract = dexscreener_match.group(2)
                dex_info = {
                    'type': 'dexscreener',
                    'chain': chain,
                    'contract': contract,
                    'url': f"https://dexscreener.com/{chain}/{contract}"
                }
            
            return {
                'ticker': ticker,
                'direction': direction,
                'dex_info': dex_info,
                'source': 'pumply'
            }
        except Exception as e:
            logger.error(f"Ошибка парсинга pumply: {e}")
            return None

    def convert_ticker_to_mexc_format(self, ticker: str) -> str:
        """Конвертирует тикер в формат MEXC"""
        return f"MEXC:{ticker}USDT.p"

    def copy_to_clipboard(self, text: str) -> bool:
        """Копирует текст в буфер обмена"""
        try:
            pyperclip.copy(text)
            logger.info(f"Скопировано в буфер обмена: {text}")
            return True
        except Exception as e:
            logger.error(f"Ошибка копирования в буфер обмена: {e}")
            return False

    def open_gmgn_in_browser(self, dex_info: Dict) -> bool:
        """Открывает DEX ссылку в браузере, конвертируя dexscreener в gmgn"""
        try:
            if not dex_info:
                logger.warning("Нет информации о DEX для открытия")
                return False
                
            if dex_info['type'] == 'gmgn':
                # Уже GMGN ссылка
                url = dex_info['url']
            elif dex_info['type'] == 'dexscreener':
                # Конвертируем dexscreener в gmgn
                chain = dex_info['chain']
                contract = dex_info['contract']
                url = f"https://gmgn.ai/{chain}/token/{contract}"
            else:
                logger.warning(f"Неизвестный тип DEX: {dex_info['type']}")
                return False
                
            webbrowser.open(url)
            logger.info(f"Открыто в браузере: {url}")
            return True
        except Exception as e:
            logger.error(f"Ошибка открытия в браузере: {e}")
            return False

    def process_message(self, message: str) -> Optional[Dict]:
        """Обрабатывает сообщение от любого из ботов"""
        # Пробуем парсить каждым парсером
        parsers = [
            self.parse_mexc_tracker_message,
            self.parse_kormushka_message,
            self.parse_pumply_message
        ]
        
        for parser in parsers:
            result = parser(message)
            if result:
                return result
                
        return None

    def handle_message(self, message: str) -> bool:
        """Основная функция обработки сообщения"""
        try:
            # Парсим сообщение
            parsed_data = self.process_message(message)
            if not parsed_data:
                logger.warning("Не удалось распарсить сообщение")
                return False
            
            # Конвертируем тикер
            mexc_ticker = self.convert_ticker_to_mexc_format(parsed_data['ticker'])
            
            # Копируем в буфер обмена
            if not self.copy_to_clipboard(mexc_ticker):
                return False
            
            # Открываем DEX в браузере
            if parsed_data['dex_info']:
                self.open_gmgn_in_browser(parsed_data['dex_info'])
            
            logger.info(f"Обработано сообщение от {parsed_data['source']}: {mexc_ticker}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка обработки сообщения: {e}")
            return False

def main():
    """Основная функция для тестирования"""
    parser = TelegramBotParser()
    
    # Тестовые сообщения
    test_messages = [
        # mexc_tracker
        """Arbitrage (https://t.me/c/2447107119/77592) with DEXE ended 1m, 5s

DEXE | 8.17% | Long 

Price Gate (https://www.gate.io/futures/USDT/DEXE_USDT?ref=VLMQUL9YCA): 8.944
Price Dexscreener (https://dexscreener.com/ethereum/0xde4EE8057785A7e8e800Db58F9784845A5C2Cbd6): 9.74

CA: 0xde4EE8057785A7e8e800Db58F9784845A5C2Cbd6
Chain: ethereum""",
        
        # kormushka
        """FTT +3.61% in 10 secs!
MEXC (https://futures.mexc.com/exchange/FTT_USDT) — GMGN (https://gmgn.ai/eth/token/0x50d1c9771902476076ecfc8b2a83ad6b9355a4c9) | Limit ~$95900""",
        
        # pumply
        """🔻 SHORT $RICE +6.32% on MEXC

mexc: $0.098
dex: $0.09292916686752106
size: $104 (+$7)

deposit: ✅  withdraw: ✅

⏱️ 00:07

liquidity: $1.4M
volume 24h: $6.4M
network: BEP20 (https://dexscreener.com/bsc/0x2afdf2cd0384a3b5d7836b70c8da5e73841ba826)
contract: 0xb5761f36FdFE2892f1b54Bc8EE8baBb2a1b698D3"""
    ]
    
    print("Тестирование парсера Telegram ботов...")
    print("=" * 50)
    
    for i, message in enumerate(test_messages, 1):
        print(f"\nТест {i}:")
        print("-" * 30)
        success = parser.handle_message(message)
        print(f"Результат: {'Успешно' if success else 'Ошибка'}")
        time.sleep(1)  # Пауза между тестами

if __name__ == "__main__":
    main()

