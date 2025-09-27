#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Отладочный монитор для проверки работы с каналами
Показывает все входящие сообщения для диагностики
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from typing import Dict, List, Optional
import webbrowser
import pyperclip
import re

try:
    from telethon import TelegramClient, events
    from telethon.tl.types import User, Channel, Chat
except ImportError:
    print("❌ Ошибка: Необходимо установить telethon")
    print("Выполните: pip install telethon")
    sys.exit(1)

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('debug_monitor.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class DebugMonitor:
    def __init__(self, config_file: str = 'config.json'):
        """Инициализация отладочного монитора"""
        self.config = self.load_config(config_file)
        
        # Инициализация клиента
        api_id = self.config['telegram']['api_id'] or os.getenv('TELEGRAM_API_ID')
        api_hash = self.config['telegram']['api_hash'] or os.getenv('TELEGRAM_API_HASH')
        session_name = self.config['telegram']['session_name']
        
        if not api_id or not api_hash:
            raise ValueError("Необходимо указать API ключи в config.json или переменных окружения")
        
        self.client = TelegramClient(session_name, api_id, api_hash)
        
        # Статистика
        self.stats = {
            'messages_processed': 0,
            'tickers_found': 0,
            'errors': 0,
            'start_time': None,
            'last_activity': None
        }

    def load_config(self, config_file: str) -> Dict:
        """Загружает конфигурацию из файла"""
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.error(f"Файл конфигурации {config_file} не найден")
            sys.exit(1)
        except json.JSONDecodeError as e:
            logger.error(f"Ошибка парсинга конфигурации: {e}")
            sys.exit(1)

    async def start(self):
        """Запуск клиента"""
        await self.client.start()
        logger.info("🚀 Отладочный монитор запущен")
        self.stats['start_time'] = datetime.now()

    async def stop(self):
        """Остановка клиента"""
        await self.client.disconnect()
        logger.info("🛑 Монитор остановлен")

    def extract_ticker_data(self, message: str, source_name: str) -> Optional[Dict]:
        """Извлекает данные тикера из сообщения"""
        try:
            # Проверяем все паттерны ботов
            for bot_name, bot_config in self.config['monitored_bots'].items():
                if not bot_config['enabled']:
                    continue
                    
                pattern = bot_config['pattern']
                
                # Ищем тикер
                ticker_match = re.search(pattern, message)
                if not ticker_match:
                    continue
                
                ticker = None
                direction = None
                
                if bot_name == 'pumply_futures_dex':
                    direction = ticker_match.group(1)
                    ticker = ticker_match.group(2)
                elif bot_name == 'mexcTracker':
                    ticker = ticker_match.group(1)
                    direction = ticker_match.group(2)
                else:  # kormushka_mexc
                    ticker = ticker_match.group(1)
                
                # Ищем контракт и сеть в сообщении
                dex_info = self.extract_contract_info(message)
                
                return {
                    'ticker': ticker,
                    'direction': direction,
                    'dex_info': dex_info,
                    'bot_name': bot_name,
                    'timestamp': datetime.now()
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Ошибка извлечения данных: {e}")
            return None

    def extract_contract_info(self, message: str) -> Optional[Dict]:
        """Извлекает информацию о контракте и сети из сообщения"""
        try:
            # Сначала ищем прямую ссылку на GMGN в сообщении
            gmgn_match = re.search(r'gmgn\.ai/(\w+)/token/([a-fA-F0-9x]+)', message)
            if gmgn_match:
                chain = gmgn_match.group(1)
                contract = gmgn_match.group(2)
                return {
                    'type': 'gmgn',
                    'chain': chain,
                    'contract': contract,
                    'url': f"https://gmgn.ai/{chain}/token/{contract}"
                }
            
            # Если GMGN ссылки нет, ищем контракт в формате CA: 0x...
            ca_match = re.search(r'CA:\s*([a-fA-F0-9x]+)', message)
            if not ca_match:
                # Ищем контракт в ссылках dexscreener
                dexscreener_match = re.search(r'dexscreener\.com/(\w+)/([a-fA-F0-9x]+)', message)
                if dexscreener_match:
                    chain = dexscreener_match.group(1)
                    contract = dexscreener_match.group(2)
                else:
                    return None
            else:
                contract = ca_match.group(1)
                # Ищем сеть в сообщении
                chain_match = re.search(r'Chain:\s*(\w+)', message)
                if chain_match:
                    chain = chain_match.group(1).lower()
                else:
                    # Пробуем найти сеть в ссылках
                    chain_match = re.search(r'dexscreener\.com/(\w+)/', message)
                    if chain_match:
                        chain = chain_match.group(1).lower()
                    else:
                        # По умолчанию ethereum
                        chain = 'ethereum'
            
            # Конвертируем названия сетей в формат GMGN
            chain_mapping = {
                'ethereum': 'eth',
                'arbitrum': 'arb',
                'bsc': 'bsc',
                'polygon': 'polygon',
                'base': 'base',
                'solana': 'sol',
                'avalanche': 'avax'
            }
            
            gmgn_chain = chain_mapping.get(chain.lower(), chain.lower())
            
            return {
                'type': 'contract',
                'chain': gmgn_chain,
                'contract': contract,
                'url': f"https://gmgn.ai/{gmgn_chain}/token/{contract}"
            }
            
        except Exception as e:
            logger.error(f"Ошибка извлечения контракта: {e}")
            return None

    def convert_ticker_to_mexc(self, ticker: str) -> str:
        """Конвертирует тикер в формат MEXC"""
        return f"MEXC:{ticker}USDT.p"

    def copy_to_clipboard(self, text: str) -> bool:
        """Копирует текст в буфер обмена"""
        try:
            if self.config['settings']['auto_copy_clipboard']:
                pyperclip.copy(text)
                return True
            return False
        except Exception as e:
            logger.error(f"Ошибка копирования в буфер обмена: {e}")
            return False

    def open_gmgn(self, dex_info: Dict) -> bool:
        """Открывает GMGN в браузере"""
        try:
            if not self.config['settings']['auto_open_gmgn'] or not dex_info:
                return False
                
            url = dex_info['url']
            webbrowser.open(url)
            return True
        except Exception as e:
            logger.error(f"Ошибка открытия GMGN: {e}")
            return False

    async def process_message(self, message: str, source_name: str, message_id: int):
        """Обрабатывает сообщение"""
        try:
            self.stats['messages_processed'] += 1
            self.stats['last_activity'] = datetime.now()
            
            logger.info(f"📨 Сообщение от {source_name}: {message[:100]}...")
            
            # Извлекаем данные тикера
            ticker_data = self.extract_ticker_data(message, source_name)
            if not ticker_data:
                logger.debug(f"Тикер не найден в сообщении от {source_name}")
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
            if self.open_gmgn(dex_info):
                logger.info(f"🌐 Открыто GMGN: {dex_info['url']}")
            
            # Логируем результат
            logger.info(f"✅ Обработано от {source_name}: {ticker} -> {mexc_ticker} ({direction})")
            
        except Exception as e:
            self.stats['errors'] += 1
            logger.error(f"Ошибка обработки сообщения от {source_name}: {e}")

    @events.register(events.NewMessage)
    async def handle_new_message(self, event):
        """Обработчик новых сообщений - показывает ВСЕ сообщения"""
        try:
            # Получаем информацию об отправителе
            sender = event.sender
            message_text = event.message.message
            message_id = event.message.id
            
            # Определяем тип отправителя и имя
            if isinstance(sender, User):
                source_name = f"@{sender.username}" if sender.username else f"User {sender.id}"
                source_type = "User"
            elif isinstance(sender, Channel):
                source_name = f"@{sender.username}" if sender.username else f"Channel {sender.id}"
                source_type = "Channel"
            elif isinstance(sender, Chat):
                source_name = f"Chat {sender.id}"
                source_type = "Chat"
            else:
                source_name = f"Unknown {type(sender).__name__}"
                source_type = "Unknown"
            
            # Логируем ВСЕ сообщения для отладки
            logger.info(f"🔍 [{source_type}] {source_name}: {message_text[:200]}...")
            
            # Проверяем, что это один из мониторимых каналов/ботов
            target_username = None
            if hasattr(sender, 'username') and sender.username:
                for bot_name, bot_config in self.config['monitored_bots'].items():
                    if bot_config['username'] == sender.username and bot_config['enabled']:
                        target_username = sender.username
                        break
            
            if target_username:
                logger.info(f"🎯 Найден мониторимый канал/бот: @{target_username}")
                await self.process_message(message_text, target_username, message_id)
            else:
                logger.debug(f"⏭️ Пропущено сообщение от {source_name} (не в списке мониторинга)")
            
        except Exception as e:
            self.stats['errors'] += 1
            logger.error(f"Ошибка обработки события: {e}")

    async def list_dialogs(self):
        """Показывает список всех диалогов для отладки"""
        logger.info("📋 Список всех диалогов:")
        async for dialog in self.client.iter_dialogs():
            if dialog.is_channel or dialog.is_group:
                logger.info(f"  📺 {dialog.name} (@{dialog.entity.username}) - {dialog.entity.id}")
            elif dialog.is_user:
                logger.info(f"  👤 {dialog.name} (@{dialog.entity.username}) - {dialog.entity.id}")

    async def run(self):
        """Основной цикл работы"""
        try:
            await self.start()
            
            # Показываем список диалогов
            await self.list_dialogs()
            
            # Регистрируем обработчик событий
            self.client.add_event_handler(self.handle_new_message)
            
            # Выводим информацию о мониторинге
            enabled_bots = [f"@{config['username']}" for name, config in self.config['monitored_bots'].items() if config['enabled']]
            logger.info(f"🔍 Мониторинг каналов/ботов: {', '.join(enabled_bots)}")
            logger.info("⏳ Ожидание сообщений... (Ctrl+C для остановки)")
            logger.info("💡 Все входящие сообщения будут показаны для отладки")
            
            # Запускаем клиент
            await self.client.run_until_disconnected()
            
        except KeyboardInterrupt:
            logger.info("🛑 Получен сигнал остановки")
        except Exception as e:
            logger.error(f"❌ Критическая ошибка: {e}")
        finally:
            await self.stop()
            logger.info(f"📊 Статистика: Обработано {self.stats['messages_processed']} сообщений, "
                       f"найдено {self.stats['tickers_found']} тикеров, "
                       f"ошибок {self.stats['errors']}")

def main():
    """Основная функция"""
    print("🔍 Отладочный монитор Telegram каналов/ботов")
    print("=" * 50)
    
    try:
        monitor = DebugMonitor()
        asyncio.run(monitor.run())
    except Exception as e:
        print(f"❌ Ошибка запуска: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
