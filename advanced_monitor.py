#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Продвинутый мониторинг Telegram ботов с конфигурацией
Автоматически обрабатывает все сообщения от настроенных ботов
"""

import asyncio
import json
import logging
import os
import sys
import time
from datetime import datetime
from typing import Dict, List, Optional
import webbrowser
import pyperclip
import re

try:
    from telethon import TelegramClient, events
    from telethon.tl.types import User
except ImportError:
    print("❌ Ошибка: Необходимо установить telethon")
    print("Выполните: pip install telethon")
    sys.exit(1)

class AdvancedBotMonitor:
    def __init__(self, config_file: str = 'config.json'):
        """Инициализация монитора с конфигурацией"""
        self.config = self.load_config(config_file)
        
        # Настройка логирования
        log_level = getattr(logging, self.config['settings']['log_level'])
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('bot_monitor.log', encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
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
            'blacklisted_tickers': 0,
            'errors': 0,
            'start_time': None,
            'last_activity': None
        }
        
        # Черный список
        self.blacklist_enabled = self.config.get('blacklist', {}).get('enabled', False)
        self.blacklisted_tickers = set(self.config.get('blacklist', {}).get('tickers', []))
        if self.blacklist_enabled:
            self.logger.info(f"🚫 Черный список активен: {len(self.blacklisted_tickers)} тикеров")
            self.logger.info(f"📋 Заблокированные тикеры: {', '.join(sorted(self.blacklisted_tickers))}")
        else:
            self.logger.info("✅ Черный список отключен")
        
        # Кэш для избежания дублирования
        self.processed_messages = set()
        self.max_cache_size = 1000

    def load_config(self, config_file: str) -> Dict:
        """Загружает конфигурацию из файла"""
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            self.logger.error(f"Файл конфигурации {config_file} не найден")
            sys.exit(1)
        except json.JSONDecodeError as e:
            self.logger.error(f"Ошибка парсинга конфигурации: {e}")
            sys.exit(1)

    async def start(self):
        """Запуск клиента"""
        await self.client.start()
        self.logger.info("🚀 Продвинутый монитор ботов запущен")
        self.stats['start_time'] = datetime.now()

    async def stop(self):
        """Остановка клиента"""
        await self.client.disconnect()
        self.logger.info("🛑 Монитор остановлен")

    def is_ticker_blacklisted(self, ticker: str) -> bool:
        """Проверяет, находится ли тикер в черном списке"""
        if not self.blacklist_enabled:
            return False
        
        ticker_upper = ticker.upper()
        is_blacklisted = ticker_upper in self.blacklisted_tickers
        
        if is_blacklisted:
            self.stats['blacklisted_tickers'] += 1
            self.logger.info(f"🚫 Тикер {ticker} в черном списке - игнорируем")
        
        return is_blacklisted

    def extract_ticker_data(self, message: str, bot_name: str) -> Optional[Dict]:
        """Извлекает данные тикера из сообщения"""
        try:
            bot_config = self.config['monitored_bots'][bot_name]
            pattern = bot_config['pattern']
            
            # Ищем тикер
            ticker_match = re.search(pattern, message)
            if not ticker_match:
                return None
            
            ticker = None
            direction = None
            
            if bot_name == 'pumply_futures_dex':
                direction = ticker_match.group(1)
                ticker = ticker_match.group(2)
            elif bot_name == 'mexcTracker':
                ticker = ticker_match.group(1)
                direction = ticker_match.group(2)
            elif bot_name == 'MexcDexSpreadTracker':
                direction = ticker_match.group(2)
                ticker = ticker_match.group(3)
            else:  # kormushka_mexc
                ticker = ticker_match.group(1)
            
            # Проверяем черный список
            if self.is_ticker_blacklisted(ticker):
                return None
            
            # Ищем контракт и сеть в сообщении
            dex_info = self.extract_contract_info(message)
            
            return {
                'ticker': ticker,
                'direction': direction,
                'dex_info': dex_info,
                'bot_name': bot_name,
                'timestamp': datetime.now()
            }
            
        except Exception as e:
            self.logger.error(f"Ошибка извлечения данных из {bot_name}: {e}")
            return None

    def extract_contract_info(self, message: str) -> Optional[Dict]:
        """Извлекает информацию о контракте и сети из сообщения"""
        try:
            # 0. Детект одиночного солана-минта по присутствию #SOLANA/sol/solana и base58-адреса
            solana_mint_match = re.search(r'\b([1-9A-HJ-NP-Za-km-z]{32,44})\b', message)
            if solana_mint_match and re.search(r'(#?SOLANA|\bsolana\b|\bSOL\b)', message, re.IGNORECASE):
                contract = solana_mint_match.group(1)
                chain = 'sol'
                self.logger.info(f"🔍 Найден Solana mint: {contract}")
                return {
                    'type': 'gmgn',
                    'chain': chain,
                    'contract': contract,
                    'url': f"https://gmgn.ai/{chain}/token/{contract}"
                }

            # 1. Сначала ищем прямую ссылку на GMGN в сообщении
            gmgn_match = re.search(r'gmgn\.ai/(\w+)/token/([a-fA-F0-9x]+|[1-9A-HJ-NP-Za-km-z]+)', message)
            if gmgn_match:
                chain = gmgn_match.group(1)
                contract = gmgn_match.group(2)
                self.logger.info(f"🔍 Найдена GMGN ссылка: {chain}/{contract}")
                return {
                    'type': 'gmgn',
                    'chain': chain,
                    'contract': contract,
                    'url': f"https://gmgn.ai/{chain}/token/{contract}"
                }
            
            # 2. Ищем контракт в формате CA: (полный контракт)
            ca_match = re.search(r'CA:\s*([^\s\n]+)', message)
            if ca_match:
                contract = ca_match.group(1)
                self.logger.info(f"🔍 Найден контракт CA: {contract}")
                
                # Ищем сеть в сообщении
                chain_match = re.search(r'Chain:\s*(\w+)', message)
                if chain_match:
                    chain = chain_match.group(1).lower()
                    self.logger.info(f"🔍 Найдена сеть Chain: {chain}")
                else:
                    # Пробуем найти сеть в ссылках dexscreener
                    chain_match = re.search(r'dexscreener\.com/(\w+)/', message)
                    if chain_match:
                        chain = chain_match.group(1).lower()
                        self.logger.info(f"🔍 Найдена сеть в dexscreener: {chain}")
                    else:
                        # По умолчанию ethereum
                        chain = 'ethereum'
                        self.logger.info(f"🔍 Используем сеть по умолчанию: {chain}")
                
                # Конвертируем названия сетей в формат GMGN
                chain_mapping = {
                    'ethereum': 'eth',
                    'arbitrum': 'arb',
                    'bsc': 'bsc',
                    'polygon': 'polygon',
                    'base': 'base',
                    'solana': 'sol',
                    'avalanche': 'avax',
                    'sol': 'sol',  # Добавляем для network: SOL
                    'bep20': 'bsc'  # Добавляем для network: BEP20
                }
                
                gmgn_chain = chain_mapping.get(chain.lower(), chain.lower())
                self.logger.info(f"🔍 GMGN сеть: {gmgn_chain}")
                
                return {
                    'type': 'contract',
                    'chain': gmgn_chain,
                    'contract': contract,
                    'url': f"https://gmgn.ai/{gmgn_chain}/token/{contract}"
                }
            
            # 3. Ищем контракт в формате contract: (для pumply_futures_dex)
            contract_match = re.search(r'contract:\s*([^\s\n]+)', message, re.IGNORECASE)
            if contract_match:
                contract = contract_match.group(1)
                self.logger.info(f"🔍 Найден контракт contract: {contract}")
                
                # Ищем сеть в сообщении
                network_match = re.search(r'network:\s*(\w+)', message, re.IGNORECASE)
                if network_match:
                    chain = network_match.group(1).lower()
                    self.logger.info(f"🔍 Найдена сеть network: {chain}")
                else:
                    # Пробуем найти сеть в ссылках dexscreener
                    chain_match = re.search(r'dexscreener\.com/(\w+)/', message)
                    if chain_match:
                        chain = chain_match.group(1).lower()
                        self.logger.info(f"🔍 Найдена сеть в dexscreener: {chain}")
                    else:
                        # По умолчанию ethereum
                        chain = 'ethereum'
                        self.logger.info(f"🔍 Используем сеть по умолчанию: {chain}")
                
                # Конвертируем названия сетей в формат GMGN
                chain_mapping = {
                    'ethereum': 'eth',
                    'arbitrum': 'arb',
                    'bsc': 'bsc',
                    'polygon': 'polygon',
                    'base': 'base',
                    'solana': 'sol',
                    'avalanche': 'avax',
                    'sol': 'sol',  # Добавляем для network: SOL
                    'bep20': 'bsc'  # Добавляем для network: BEP20
                }
                
                gmgn_chain = chain_mapping.get(chain.lower(), chain.lower())
                self.logger.info(f"🔍 GMGN сеть: {gmgn_chain}")
                
                return {
                    'type': 'contract',
                    'chain': gmgn_chain,
                    'contract': contract,
                    'url': f"https://gmgn.ai/{gmgn_chain}/token/{contract}"
                }
            
            
            # 4. Если ничего не найдено, ищем в ссылках dexscreener
            dexscreener_match = re.search(r'dexscreener\.com/(\w+)/([^)]+)', message)
            if dexscreener_match:
                chain = dexscreener_match.group(1)
                contract = dexscreener_match.group(2)
                self.logger.info(f"🔍 Найден контракт в dexscreener: {contract} на сети {chain}")
                
                # Конвертируем названия сетей в формат GMGN
                chain_mapping = {
                    'ethereum': 'eth',
                    'arbitrum': 'arb',
                    'bsc': 'bsc',
                    'polygon': 'polygon',
                    'base': 'base',
                    'solana': 'sol',
                    'avalanche': 'avax',
                    'sol': 'sol',
                    'bep20': 'bsc'  # Добавляем для network: BEP20
                }
                
                gmgn_chain = chain_mapping.get(chain.lower(), chain.lower())
                
                return {
                    'type': 'dexscreener',
                    'chain': gmgn_chain,
                    'contract': contract,
                    'url': f"https://gmgn.ai/{gmgn_chain}/token/{contract}"
                }
            
            self.logger.info("🔍 Контракт не найден в сообщении")
            return None
            
        except Exception as e:
            self.logger.error(f"Ошибка извлечения контракта: {e}")
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
            self.logger.error(f"Ошибка копирования в буфер обмена: {e}")
            return False

    def open_gmgn(self, dex_info: Dict) -> bool:
        """Открывает GMGN в браузере"""
        try:
            self.logger.info(f"🔍 Попытка открыть GMGN: auto_open_gmgn={self.config['settings']['auto_open_gmgn']}, dex_info={dex_info is not None}")
            
            if not self.config['settings']['auto_open_gmgn']:
                self.logger.info("⏭️ Автооткрытие GMGN отключено в настройках")
                return False
                
            if not dex_info:
                self.logger.info("⏭️ Нет информации о DEX для открытия")
                return False
                
            url = dex_info['url']
            self.logger.info(f"🌐 Открываем URL: {url}")
            
            # Пробуем разные способы открытия браузера
            try:
                webbrowser.open(url)
                self.logger.info("✅ Браузер открыт через webbrowser.open()")
                return True
            except Exception as e:
                self.logger.warning(f"⚠️ webbrowser.open() не сработал: {e}")
                
                # Пробуем через subprocess
                import subprocess
                try:
                    subprocess.run(['start', url], shell=True, check=True)
                    self.logger.info("✅ Браузер открыт через subprocess")
                    return True
                except Exception as e2:
                    self.logger.warning(f"⚠️ subprocess тоже не сработал: {e2}")
                    
                    # Пробуем через os.startfile
                    import os
                    try:
                        os.startfile(url)
                        self.logger.info("✅ Браузер открыт через os.startfile()")
                        return True
                    except Exception as e3:
                        self.logger.error(f"❌ Все способы открытия браузера не сработали: {e3}")
                        return False
                        
        except Exception as e:
            self.logger.error(f"❌ Критическая ошибка открытия GMGN: {e}")
            return False

    def send_notification(self, message: str):
        """Отправляет уведомление"""
        if not self.config['notifications']['enabled']:
            return
        
        try:
            if self.config['notifications']['desktop']:
                # Простое уведомление в консоль
                self.logger.info(f"🔔 {message}")
            
            if self.config['notifications']['sound']:
                # Звуковое уведомление (Windows)
                try:
                    import winsound
                    winsound.Beep(1000, 200)
                except ImportError:
                    pass
        except Exception as e:
            self.logger.error(f"Ошибка отправки уведомления: {e}")

    async def process_message(self, message: str, bot_name: str, message_id: int):
        """Обрабатывает сообщение от бота"""
        try:
            # Проверяем дублирование
            message_hash = hash(f"{bot_name}_{message_id}_{message[:100]}")
            if message_hash in self.processed_messages:
                return
            
            # Добавляем в кэш
            self.processed_messages.add(message_hash)
            if len(self.processed_messages) > self.max_cache_size:
                # Очищаем старые записи
                self.processed_messages = set(list(self.processed_messages)[-self.max_cache_size//2:])
            
            self.stats['messages_processed'] += 1
            self.stats['last_activity'] = datetime.now()
            
            # Извлекаем данные тикера
            ticker_data = self.extract_ticker_data(message, bot_name)
            if not ticker_data:
                self.logger.debug(f"Тикер не найден в сообщении от {bot_name}")
                return
            
            self.stats['tickers_found'] += 1
            ticker = ticker_data['ticker']
            direction = ticker_data.get('direction', 'N/A')
            dex_info = ticker_data.get('dex_info')
            
            # Конвертируем тикер
            mexc_ticker = self.convert_ticker_to_mexc(ticker)
            
            # Копируем в буфер обмена
            if self.copy_to_clipboard(mexc_ticker):
                self.logger.info(f"📋 Скопировано: {mexc_ticker}")
            
            # Открываем GMGN
            self.logger.info(f"🔍 Пытаемся открыть GMGN с данными: {dex_info}")
            if self.open_gmgn(dex_info):
                self.logger.info(f"🌐 Открыто GMGN: {dex_info['url']}")
            else:
                self.logger.warning("⚠️ Не удалось открыть GMGN")
            
            # Отправляем уведомление
            notification_msg = f"Новый тикер от @{bot_name}: {ticker} -> {mexc_ticker}"
            self.send_notification(notification_msg)
            
            # Логируем результат
            self.logger.info(f"✅ Обработано от @{bot_name}: {ticker} -> {mexc_ticker} ({direction})")
            
            # Выводим статистику
            if self.stats['messages_processed'] % self.config['settings']['stats_interval'] == 0:
                self.print_stats()
                
        except Exception as e:
            self.stats['errors'] += 1
            self.logger.error(f"Ошибка обработки сообщения от {bot_name}: {e}")
            
            # Останавливаем при критическом количестве ошибок
            if self.stats['errors'] >= self.config['settings']['max_errors']:
                self.logger.critical(f"Достигнуто максимальное количество ошибок: {self.stats['errors']}")
                await self.stop()
                sys.exit(1)

    def print_stats(self):
        """Выводит статистику"""
        uptime = datetime.now() - self.stats['start_time'] if self.stats['start_time'] else "N/A"
        last_activity = self.stats['last_activity'].strftime("%H:%M:%S") if self.stats['last_activity'] else "N/A"
        
        self.logger.info(f"📊 Статистика: Обработано {self.stats['messages_processed']} сообщений, "
                        f"найдено {self.stats['tickers_found']} тикеров, "
                        f"заблокировано {self.stats['blacklisted_tickers']} тикеров, "
                        f"ошибок {self.stats['errors']}, время работы: {uptime}, "
                        f"последняя активность: {last_activity}")

    def _collect_embedded_urls(self, event) -> List[str]:
        """Извлекает встроенные URL из сущностей Telegram (включая скрытые ссылки)."""
        urls: List[str] = []
        try:
            from telethon.tl.types import MessageEntityTextUrl, MessageEntityUrl
            if getattr(event, 'message', None) is None:
                return urls
            entities = getattr(event.message, 'entities', None) or []
            message_text = event.message.message or ""
            for ent in entities:
                # Явные URL в тексте
                if isinstance(ent, MessageEntityUrl):
                    try:
                        urls.append(message_text[ent.offset: ent.offset + ent.length])
                    except Exception:
                        pass
                # Скрытые ссылки вида [GMGN](https://gmgn.ai/..)
                if isinstance(ent, MessageEntityTextUrl) and getattr(ent, 'url', None):
                    urls.append(ent.url)
        except Exception:
            # Безопасно игнорируем ошибки извлечения
            return urls
        return urls

    def _collect_button_urls(self, event) -> List[str]:
        """Извлекает URL из inline-кнопок под сообщением (reply_markup)."""
        urls: List[str] = []
        try:
            reply_markup = getattr(event.message, 'reply_markup', None)
            if not reply_markup or not getattr(reply_markup, 'rows', None):
                return urls
            for row in reply_markup.rows:
                buttons = getattr(row, 'buttons', []) or []
                for btn in buttons:
                    # У кнопки с URL атрибут обычно называется url
                    url = getattr(btn, 'url', None)
                    if url:
                        urls.append(url)
        except Exception:
            return urls
        return urls

    @events.register(events.NewMessage)
    async def handle_new_message(self, event):
        """Обработчик новых сообщений"""
        try:
            # Проверяем, что это сообщение от канала или пользователя
            from telethon.tl.types import User, Channel, Chat
            
            if not isinstance(event.sender, (User, Channel, Chat)):
                return
            
            sender_username = getattr(event.sender, 'username', None)
            if not sender_username:
                return
            
            # Проверяем, что это один из мониторимых каналов/ботов
            bot_name = None
            for name, config in self.config['monitored_bots'].items():
                if config['username'] == sender_username and config['enabled']:
                    bot_name = name
                    break
            
            if not bot_name:
                return
            
            message_text = event.message.message
            # Дополняем текст встроенными ссылками из сущностей и кнопок, чтобы парсер видел GMGN/DEX ссылки
            extra_urls: List[str] = []
            extra_urls.extend(self._collect_embedded_urls(event))
            extra_urls.extend(self._collect_button_urls(event))
            if extra_urls:
                message_text = f"{message_text}\n" + " \n".join(extra_urls)
            message_id = event.message.id
            
            self.logger.info(f"📨 Новое сообщение от @{sender_username}")
            
            # Обрабатываем сообщение
            await self.process_message(message_text, bot_name, message_id)
            
        except Exception as e:
            self.stats['errors'] += 1
            self.logger.error(f"Ошибка обработки события: {e}")

    async def run(self):
        """Основной цикл работы"""
        try:
            await self.start()
            
            # Регистрируем обработчик событий
            self.client.add_event_handler(self.handle_new_message)
            
            # Выводим информацию о мониторинге
            enabled_bots = [f"@{config['username']}" for name, config in self.config['monitored_bots'].items() if config['enabled']]
            self.logger.info(f"🔍 Мониторинг ботов: {', '.join(enabled_bots)}")
            self.logger.info("⏳ Ожидание сообщений... (Ctrl+C для остановки)")
            
            # Запускаем клиент
            await self.client.run_until_disconnected()
            
        except KeyboardInterrupt:
            self.logger.info("🛑 Получен сигнал остановки")
        except Exception as e:
            self.logger.error(f"❌ Критическая ошибка: {e}")
        finally:
            await self.stop()
            self.print_stats()

def main():
    """Основная функция"""
    print("🤖 Продвинутый монитор Telegram ботов")
    print("=" * 50)
    
    try:
        monitor = AdvancedBotMonitor()
        asyncio.run(monitor.run())
    except Exception as e:
        print(f"❌ Ошибка запуска: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
