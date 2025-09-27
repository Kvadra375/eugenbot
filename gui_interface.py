#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GUI интерфейс для Telegram Bot Parser
Простой интерфейс для вставки сообщений и обработки
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
from telegram_bot_parser import TelegramBotParser

class TelegramParserGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Telegram Bot Parser - EugenBot")
        self.root.geometry("800x600")
        
        self.parser = TelegramBotParser()
        self.setup_ui()
        
    def setup_ui(self):
        """Настройка пользовательского интерфейса"""
        # Главный фрейм
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Заголовок
        title_label = ttk.Label(main_frame, text="Telegram Bot Parser", 
                               font=("Arial", 16, "bold"))
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 20))
        
        # Инструкции
        instructions = """
Инструкция:
1. Скопируйте сообщение из одного из ботов:
   - @mexcTracker
   - @kormushka_mexc  
   - @pumply_futures_dex
2. Вставьте в поле ниже
3. Нажмите "Обработать сообщение"
4. Тикер будет скопирован в буфер обмена в формате MEXC
5. DEX ссылка откроется в браузере (GMGN)
        """
        
        instructions_label = ttk.Label(main_frame, text=instructions, 
                                     justify=tk.LEFT, wraplength=750)
        instructions_label.grid(row=1, column=0, columnspan=2, pady=(0, 20))
        
        # Поле для ввода сообщения
        ttk.Label(main_frame, text="Сообщение от бота:").grid(row=2, column=0, sticky=tk.W, pady=(0, 5))
        
        self.message_text = scrolledtext.ScrolledText(main_frame, height=15, width=80)
        self.message_text.grid(row=3, column=0, columnspan=2, pady=(0, 10), sticky=(tk.W, tk.E))
        
        # Кнопки
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=4, column=0, columnspan=2, pady=10)
        
        self.process_button = ttk.Button(button_frame, text="Обработать сообщение", 
                                       command=self.process_message)
        self.process_button.pack(side=tk.LEFT, padx=(0, 10))
        
        self.clear_button = ttk.Button(button_frame, text="Очистить", 
                                     command=self.clear_text)
        self.clear_button.pack(side=tk.LEFT, padx=(0, 10))
        
        self.test_button = ttk.Button(button_frame, text="Тестовые данные", 
                                    command=self.load_test_data)
        self.test_button.pack(side=tk.LEFT)
        
        # Результат
        ttk.Label(main_frame, text="Результат:").grid(row=5, column=0, sticky=tk.W, pady=(20, 5))
        
        self.result_text = scrolledtext.ScrolledText(main_frame, height=8, width=80, 
                                                   state=tk.DISABLED)
        self.result_text.grid(row=6, column=0, columnspan=2, sticky=(tk.W, tk.E))
        
        # Статус
        self.status_var = tk.StringVar()
        self.status_var.set("Готов к работе")
        status_label = ttk.Label(main_frame, textvariable=self.status_var)
        status_label.grid(row=7, column=0, columnspan=2, pady=(10, 0))
        
        # Настройка растягивания
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(3, weight=1)
        main_frame.rowconfigure(6, weight=1)
        
    def process_message(self):
        """Обработка сообщения в отдельном потоке"""
        def process():
            try:
                self.status_var.set("Обработка...")
                self.process_button.config(state=tk.DISABLED)
                
                message = self.message_text.get("1.0", tk.END).strip()
                if not message:
                    self.update_result("Ошибка: Сообщение пустое")
                    return
                
                # Обрабатываем сообщение
                success = self.parser.handle_message(message)
                
                if success:
                    self.update_result("✅ Сообщение успешно обработано!\nТикер скопирован в буфер обмена.")
                else:
                    self.update_result("❌ Не удалось обработать сообщение.\nПроверьте формат сообщения.")
                    
            except Exception as e:
                self.update_result(f"❌ Ошибка: {str(e)}")
            finally:
                self.process_button.config(state=tk.NORMAL)
                self.status_var.set("Готов к работе")
        
        # Запускаем в отдельном потоке
        thread = threading.Thread(target=process)
        thread.daemon = True
        thread.start()
        
    def update_result(self, text):
        """Обновление поля результата"""
        self.result_text.config(state=tk.NORMAL)
        self.result_text.delete("1.0", tk.END)
        self.result_text.insert("1.0", text)
        self.result_text.config(state=tk.DISABLED)
        
    def clear_text(self):
        """Очистка полей"""
        self.message_text.delete("1.0", tk.END)
        self.result_text.config(state=tk.NORMAL)
        self.result_text.delete("1.0", tk.END)
        self.result_text.config(state=tk.DISABLED)
        self.status_var.set("Готов к работе")
        
    def load_test_data(self):
        """Загрузка тестовых данных"""
        test_message = """Arbitrage (https://t.me/c/2447107119/77592) with DEXE ended 1m, 5s

DEXE | 8.17% | Long 

Price Gate (https://www.gate.io/futures/USDT/DEXE_USDT?ref=VLMQUL9YCA): 8.944
Price Dexscreener (https://dexscreener.com/ethereum/0xde4EE8057785A7e8e800Db58F9784845A5C2Cbd6): 9.74

CA: 0xde4EE8057785A7e8e800Db58F9784845A5C2Cbd6
Chain: ethereum

Lim/V24h: $894.40K / $30.57M;
DLiq/V1h/V24h: $704.04K / $60.75K / $161.42K
Deposit (https://www.gate.io/wallet/withdraw/DEXE?ref=VLMQUL9YCA) / Withdrawal (https://www.gate.io/wallet/deposit/DEXE?ref=VLMQUL9YCA) Spot: 9.417

Chain         Deposit   Withdraw
ethereum        ✅        ✅

Found: 15m: 1 | 3h: 1 | 24h: 1
Avg Duration (24h): N/A

source (https://t.me/mexcTracker) // chat (https://t.me/deadblog_chat) // trackers (https://t.me/addlist/M1erkgA8OXM4NWZi) // support me (https://t.me/send?start=SBKj-I3ep4UE82MGQy)"""
        
        self.message_text.delete("1.0", tk.END)
        self.message_text.insert("1.0", test_message)
        self.status_var.set("Тестовые данные загружены")

def main():
    """Запуск GUI приложения"""
    root = tk.Tk()
    app = TelegramParserGUI(root)
    
    try:
        root.mainloop()
    except KeyboardInterrupt:
        print("Приложение закрыто")

if __name__ == "__main__":
    main()

