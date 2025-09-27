#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Автоматический мониторинг Telegram ботов
Получает сообщения в реальном времени и автоматически обрабатывает их
"""

import asyncio
import logging
import os
import sys
from datetime import datetime
from typing import Dict, List, Optional
import webbrowser
import pyperclip

try:
    from telethon import TelegramClient, events
    from telethon.tl.types import User
except ImportError:
    print("Ошибка: Необходимо установить telethon")
    print("Выполните: pip install telethon")
    sys.exit(1)

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot_monitor.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class BotMonitor:
    def __init__(self, api_id: str, api_hash: str, session_name: str = 'eugenbot_monitor'):
        """
        Инициализация монитора ботов
        
        Args:
            api_id: ID приложения Telegram
            api_hash: Hash приложения Telegram
            session_name: Имя сессии
        """
        self.client = TelegramClient(session_name, api_id, api_hash)
        
        # Список ботов для мониторинга
        self.monitored_bots = {
            'mexcTracker': {
                'username': 'mexcTracker',
                'pattern': r'(\w+)\s+\|\s+[\d.]+%\s+\|\s+(Long|Short)',
                'dex_pattern': r'dexscreener\.com/(\w+)/([a-fA-F0-9x]+)',
                'enabled': True
            },
            'kormushka_mexc': {
                'username': 'kormushka_mexc',
                'pattern': r'(\w+)\s+\+[\d.]+%\s+in\s+\d+\s+secs!',
                'dex_pattern': r'gmgn\.ai/(\w+)/token/([a-fA-F0-9x]+)',
                'enabled': True
            },
            'pumply_futures_dex': {
                'username': 'pumply_futures_dex',
                'pattern': r'🔻\s+(SHORT|LONG)\s+\$(\w+)\s+\+[\d.]+%\s+on\s+MEXC',
                'dex_pattern': r'dexscreener\.com/(\w+)/([a-fA-F0-9x]+)',
                'enabled': True
            }
        }
        
        # Статистика
        self.stats = {
            'messages_processed': 0,
            'tickers_found': 0,
            'errors': 0,
            'start_time': None
        }

    async def start(self):
        """Запуск клиента"""
        await self.client.start()
        logger.info("🚀 Telegram клиент запущен")
        self.stats['start_time'] = datetime.now()

    async def stop(self):
        """Остановка клиента"""
        await self.client.disconnect()
        logger.info("🛑 Telegram клиент остановлен")

    def extract_ticker(self, message: str, bot_name: str) -> Optional[Dict]:
        """Извлекает тикер из сообщения"""
        try:
            import re
            
            bot_config = self.monitored_bots[bot_name]
            pattern = bot_config['pattern']
            dex_pattern = bot_config['dex_pattern']
            
            # Ищем тикер
            ticker_match = re.search(pattern, message)
            if not ticker_match:
                return None
            
            ticker = None
            direction = None
            
            if bot_name == 'pumply_futures_dex':
                direction = ticker_match.group(1)
                ticker = ticker_match.group(2)
            elif bot_name == 'mexc_tracker':
                ticker = ticker_match.group(1)
                direction = ticker_match.group(2)
            else:  # kormushka_mexc
                ticker = ticker_match.group(1)
            
            # Ищем DEX информацию
            dex_match = re.search(dex_pattern, message)
            dex_info = None
            if dex_match:
                if 'gmgn' in dex_pattern:
                    chain = dex_match.group(1)
                    contract = dex_match.group(2)
                    dex_info = {
                        'type': 'gmgn',
                        'chain': chain,
                        'contract': contract,
                        'url': f"https://gmgn.ai/{chain}/token/{contract}"
                    }
                elif 'dexscreener' in dex_pattern:
                    chain = dex_match.group(1)
                    contract = dex_match.group(2)
                    dex_info = {
                        'type': 'dexscreener',
                        'chain': chain,
                        'contract': contract,
                        'url': f"https://gmgn.ai/{chain}/token/{contract}"  # Конвертируем в GMGN
                    }
            
            return {
                'ticker': ticker,
                'direction': direction,
                'dex_info': dex_info,
                'bot_name': bot_name
            }
            
        except Exception as e:
            logger.error(f"Ошибка извлечения тикера из {bot_name}: {e}")
            return None

    def convert_ticker_to_mexc(self, ticker: str) -> str:
        """Конвертирует тикер в формат MEXC"""
        return f"MEXC:{ticker}USDT.p"

    def copy_to_clipboard(self, text: str) -> bool:
        """Копирует текст в буфер обмена"""
        try:
            pyperclip.copy(text)
            return True
        except Exception as e:
            logger.error(f"Ошибка копирования в буфер обмена: {e}")
            return False

    def open_gmgn(self, dex_info: Dict) -> bool:
        """Открывает GMGN в браузере"""
        try:
            if not dex_info:
                return False
                
            url = dex_info['url']
            webbrowser.open(url)
            return True
        except Exception as e:
            logger.error(f"Ошибка открытия GMGN: {e}")
            return False

    async def process_message(self, message: str, bot_name: str, message_id: int):
        """Обрабатывает сообщение от бота"""
        try:
            self.stats['messages_processed'] += 1
            
            # Извлекаем тикер
            ticker_data = self.extract_ticker(message, bot_name)
            if not ticker_data:
                logger.debug(f"Тикер не найден в сообщении от {bot_name}")
                return
            
            self.stats['tickers_found'] += 1
            ticker = ticker_data['ticker']
            direction = ticker_data.get('direction', 'N/A')
            dex_info = ticker_data.get('dex_info')
            
            # Конвертируем тикер
            mexc_ticker = self.convert_ticker_to_mexc(ticker)
            
            # Копируем в буфер обмена
            if self.copy_to_clipboard(mexc_ticker):
                logger.info(f"📋 Скопировано: {mexc_ticker}")
            
            # Открываем GMGN
            if dex_info and self.open_gmgn(dex_info):
                logger.info(f"🌐 Открыто GMGN: {dex_info['url']}")
            
            # Логируем результат
            logger.info(f"✅ Обработано от @{bot_name}: {ticker} -> {mexc_ticker} ({direction})")
            
            # Выводим статистику каждые 10 сообщений
            if self.stats['messages_processed'] % 10 == 0:
                self.print_stats()
                
        except Exception as e:
            self.stats['errors'] += 1
            logger.error(f"Ошибка обработки сообщения от {bot_name}: {e}")

    def print_stats(self):
        """Выводит статистику"""
        uptime = datetime.now() - self.stats['start_time'] if self.stats['start_time'] else "N/A"
        logger.info(f"📊 Статистика: Обработано {self.stats['messages_processed']} сообщений, "
                   f"найдено {self.stats['tickers_found']} тикеров, "
                   f"ошибок {self.stats['errors']}, время работы: {uptime}")

    @events.register(events.NewMessage)
    async def handle_new_message(self, event):
        """Обработчик новых сообщений"""
        try:
            # Проверяем, что это сообщение от пользователя (бота)
            if not isinstance(event.sender, User):
                return
            
            sender_username = event.sender.username
            if not sender_username:
                return
            
            # Проверяем, что это один из мониторимых ботов
            bot_name = None
            for name, config in self.monitored_bots.items():
                if config['username'] == sender_username and config['enabled']:
                    bot_name = name
                    break
            
            if not bot_name:
                return
            
            message_text = event.message.message
            message_id = event.message.id
            
            logger.info(f"📨 Новое сообщение от @{sender_username}")
            
            # Обрабатываем сообщение
            await self.process_message(message_text, bot_name, message_id)
            
        except Exception as e:
            self.stats['errors'] += 1
            logger.error(f"Ошибка обработки события: {e}")

    async def run(self):
        """Основной цикл работы"""
        try:
            await self.start()
            
            # Регистрируем обработчик событий
            self.client.add_event_handler(self.handle_new_message)
            
            # Выводим информацию о мониторинге
            enabled_bots = [name for name, config in self.monitored_bots.items() if config['enabled']]
            logger.info(f"🔍 Мониторинг ботов: {', '.join(enabled_bots)}")
            logger.info("⏳ Ожидание сообщений... (Ctrl+C для остановки)")
            
            # Запускаем клиент
            await self.client.run_until_disconnected()
            
        except KeyboardInterrupt:
            logger.info("🛑 Получен сигнал остановки")
        except Exception as e:
            logger.error(f"❌ Критическая ошибка: {e}")
        finally:
            await self.stop()
            self.print_stats()

def main():
    """Основная функция"""
    # Получаем API ключи
    api_id = os.getenv('TELEGRAM_API_ID')
    api_hash = os.getenv('TELEGRAM_API_HASH')
    
    if not api_id or not api_hash:
        print("❌ Ошибка: Необходимо установить переменные окружения:")
        print("   TELEGRAM_API_ID - ID приложения Telegram")
        print("   TELEGRAM_API_HASH - Hash приложения Telegram")
        print("\n📋 Получить ключи можно на https://my.telegram.org/apps")
        print("\n🔧 Установка переменных (Windows):")
        print("   set TELEGRAM_API_ID=your_api_id")
        print("   set TELEGRAM_API_HASH=your_api_hash")
        return
    
    # Создаем и запускаем монитор
    monitor = BotMonitor(api_id, api_hash)
    
    try:
        asyncio.run(monitor.run())
    except Exception as e:
        logger.error(f"Ошибка запуска: {e}")

if __name__ == "__main__":
    main()

