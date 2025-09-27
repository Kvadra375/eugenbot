#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Интеграция с Telegram API для автоматического получения сообщений
Требует настройки API ключей
"""

import asyncio
import logging
from telethon import TelegramClient, events
from telegram_bot_parser import TelegramBotParser

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TelegramIntegration:
    def __init__(self, api_id: str, api_hash: str, session_name: str = 'eugenbot'):
        """
        Инициализация клиента Telegram
        
        Args:
            api_id: ID приложения Telegram
            api_hash: Hash приложения Telegram
            session_name: Имя сессии
        """
        self.client = TelegramClient(session_name, api_id, api_hash)
        self.parser = TelegramBotParser()
        
        # Список ботов для мониторинга
        self.bot_usernames = [
            'mexcTracker',
            'kormushka_mexc', 
            'pumply_futures_dex'
        ]

    async def start(self):
        """Запуск клиента"""
        await self.client.start()
        logger.info("Telegram клиент запущен")

    async def stop(self):
        """Остановка клиента"""
        await self.client.disconnect()
        logger.info("Telegram клиент остановлен")

    @events.register(events.NewMessage)
    async def handle_new_message(self, event):
        """Обработчик новых сообщений"""
        try:
            # Проверяем, что сообщение от нужного бота
            sender_username = None
            if event.sender and hasattr(event.sender, 'username'):
                sender_username = event.sender.username
            
            if sender_username not in self.bot_usernames:
                return
            
            message_text = event.message.message
            logger.info(f"Получено сообщение от @{sender_username}")
            
            # Обрабатываем сообщение
            success = self.parser.handle_message(message_text)
            if success:
                logger.info(f"Сообщение от @{sender_username} успешно обработано")
            else:
                logger.warning(f"Не удалось обработать сообщение от @{sender_username}")
                
        except Exception as e:
            logger.error(f"Ошибка обработки сообщения: {e}")

    async def run(self):
        """Основной цикл работы"""
        await self.start()
        
        # Регистрируем обработчик событий
        self.client.add_event_handler(self.handle_new_message)
        
        logger.info("Бот запущен и ожидает сообщения...")
        logger.info(f"Мониторинг ботов: {', '.join(self.bot_usernames)}")
        
        try:
            # Запускаем клиент
            await self.client.run_until_disconnected()
        except KeyboardInterrupt:
            logger.info("Получен сигнал остановки")
        finally:
            await self.stop()

def main():
    """Основная функция для запуска с API ключами"""
    # Получаем API ключи из переменных окружения или конфига
    import os
    
    api_id = os.getenv('TELEGRAM_API_ID')
    api_hash = os.getenv('TELEGRAM_API_HASH')
    
    if not api_id or not api_hash:
        print("Ошибка: Необходимо установить переменные окружения TELEGRAM_API_ID и TELEGRAM_API_HASH")
        print("Получить их можно на https://my.telegram.org/apps")
        return
    
    # Создаем и запускаем интеграцию
    integration = TelegramIntegration(api_id, api_hash)
    
    try:
        asyncio.run(integration.run())
    except Exception as e:
        logger.error(f"Ошибка запуска: {e}")

if __name__ == "__main__":
    main()

