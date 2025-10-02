# -*- coding: utf-8 -*-
"""
МЕНЕДЖЕР БРАУЗЕРА
Управление браузером, вкладками и настройками Selenium
"""

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
import time
from typing import List, Optional, Dict, Any

from config import Конфигурация
from utils import Логгер, ОбработчикОшибок


class МенеджерВкладок:
    """Класс для управления вкладками браузера"""
    
    def __init__(self, драйвер):
        self.драйвер = драйвер
        self.активные_вкладки = []
        self.максимальное_количество = Конфигурация.МАКСИМАЛЬНОЕ_КОЛИЧЕСТВО_ВКЛАДОК
        self.логгер = Логгер()
    
    def создать_новую_вкладку(self, url: str = None) -> str:
        """
        Создание новой вкладки
        
        Args:
            url: URL для загрузки (опционально)
            
        Returns:
            str: ID новой вкладки
        """
        try:
            # Закрываем старые вкладки если превышен лимит
            if len(self.активные_вкладки) >= self.максимальное_количество:
                self.закрыть_самую_старую_вкладку()
            
            # Сохраняем текущую вкладку
            исходная_вкладка = self.драйвер.current_window_handle
            
            # Создаем новую вкладку
            self.драйвер.execute_script("window.open();")
            новые_вкладки = [в for в in self.драйвер.window_handles if в not in self.активные_вкладки]
            
            if not новые_вкладки:
                raise Exception("Не удалось создать новую вкладку")
            
            новая_вкладка = новые_вкладки[0]
            self.драйвер.switch_to.window(новая_вкладка)
            self.активные_вкладки.append(новая_вкладка)
            
            # Загружаем URL если указан
            if url:
                self.драйвер.get(url)
                time.sleep(2)  # Базовая задержка для загрузки
            
            # Возвращаемся к исходной вкладке
            self.драйвер.switch_to.window(исходная_вкладка)
            
            self.логгер.отладка(f"Создана новая вкладка: {новая_вкладка}")
            return новая_вкладка
            
        except Exception as e:
            self.логгер.ошибка(f"Ошибка при создании вкладки: {str(e)}")
            return None
    
    def переключиться_на_вкладку(self, идентификатор_вкладки: str) -> bool:
        """
        Переключение на указанную вкладку
        
        Args:
            идентификатор_вкладки: ID вкладки
            
        Returns:
            bool: Успешность переключения
        """
        try:
            if идентификатор_вкладки in self.драйвер.window_handles:
                self.драйвер.switch_to.window(идентификатор_вкладки)
                return True
            return False
        except Exception as e:
            self.логгер.ошибка(f"Ошибка переключения на вкладку: {str(e)}")
            return False
    
    def закрыть_вкладку(self, идентификатор_вкладки: str) -> bool:
        """
        Закрытие указанной вкладки
        
        Args:
            идентификатор_вкладки: ID вкладки
            
        Returns:
            bool: Успешность закрытия
        """
        try:
            if идентификатор_вкладки in self.активные_вкладки:
                self.активные_вкладки.remove(идентификатор_вкладки)
            
            if идентификатор_вкладки in self.драйвер.window_handles:
                self.драйвер.switch_to.window(идентификатор_вкладки)
                self.драйвер.close()
                
                # Переключаемся на оставшуюся вкладку если есть
                if self.драйвер.window_handles:
                    self.драйвер.switch_to.window(self.драйвер.window_handles[0])
                
                return True
            return False
        except Exception as e:
            self.логгер.ошибка(f"Ошибка закрытия вкладки: {str(e)}")
            return False
    
    def закрыть_самую_старую_вкладку(self) -> bool:
        """Закрытие самой старой активной вкладки"""
        if self.активные_вкладки:
            return self.закрыть_вкладку(self.активные_вкладки[0])
        return False
    
    def получить_количество_активных_вкладок(self) -> int:
        """Получение количества активных вкладок"""
        return len(self.активные_вкладки)
    
    def закрыть_все_вкладки_кроме_основной(self):
        """Закрытие всех вкладок кроме основной"""
        try:
            основная_вкладка = self.драйвер.window_handles[0] if self.драйвер.window_handles else None
            
            for вкладка in self.драйвер.window_handles[1:]:
                self.закрыть_вкладку(вкладка)
            
            if основная_вкладка:
                self.переключиться_на_вкладку(основная_вкладка)
            
            self.активные_вкладки = [основная_вкладка] if основная_вкладка else []
            
        except Exception as e:
            self.логгер.ошибка(f"Ошибка при закрытии вкладок: {str(e)}")


class МенеджерБраузера:
    """Основной класс для управления браузером"""
    
    def __init__(self):
        self.драйвер = None
        self.менеджер_вкладок = None
        self.ожидание = None
        self.логгер = Логгер()
        self.обработчик_ошибок = ОбработчикОшибок(self.логгер)
    
    def инициализировать_браузер(self) -> bool:
        """
        Инициализация и настройка браузера
        
        Returns:
            bool: Успешность инициализации
        """
        try:
            опции = self.создать_опции_браузера()
            
            # Инициализация драйвера
            self.драйвер = webdriver.Chrome(options=опции)
            self.драйвер.maximize_window()
            
            # Настройка ожиданий
            self.ожидание = WebDriverWait(
                self.драйвер, 
                Конфигурация.ТАЙМАУТ_ПОИСКА_ЭЛЕМЕНТОВ
            )
            
            # Инициализация менеджера вкладок
            self.менеджер_вкладок = МенеджерВкладок(self.драйвер)
            
            self.логгер.информация("Браузер успешно инициализирован")
            return True
            
        except Exception as e:
            сообщение = self.обработчик_ошибок.обработать_ошибку(e, "Инициализация браузера")
            return False
    
    def создать_опции_браузера(self) -> Options:
        """
        Создание настроек браузера для оптимизации
        
        Returns:
            Options: Настроенные опции Chrome
        """
        опции = Options()
        
        # Базовые настройки
        if Конфигурация.БРАУЗЕР_РЕЖИМ_БЕЗ_ГОЛОВЫ:
            опции.add_argument("--headless")
        
        опции.add_argument("--no-sandbox")
        опции.add_argument("--disable-dev-shm-usage")
        опции.add_argument("--disable-gpu")
        опции.add_argument("--window-size=1920,1080")
        
        # Оптимизации производительности
        опции.add_argument("--disable-images")
        опции.add_argument("--disable-javascript")  # Временно для скорости
        опции.add_argument("--disable-plugins")
        опции.add_argument("--disable-popup-blocking")
        опции.add_argument("--blink-settings=imagesEnabled=false")
        
        # Отключение звука и уведомлений
        опции.add_argument("--mute-audio")
        опции.add_argument("--disable-notifications")
        
        # Экспериментальные опции
        опции.add_experimental_option("excludeSwitches", ["enable-automation"])
        опции.add_experimental_option('useAutomationExtension', False)
        
        prefs = {
            "profile.default_content_setting_values": {
                "images": 2,  # Блокировать изображения
                "javascript": 1,  # Разрешить JavaScript
                "plugins": 2,  # Блокировать плагины
            },
            "profile.managed_default_content_settings": {
                "images": 2
            }
        }
        опции.add_experimental_option("prefs", prefs)
        
        return опции
    
    def загрузить_страницу(self, url: str) -> bool:
        """
        Загрузка страницы по URL
        
        Args:
            url: URL для загрузки
            
        Returns:
            bool: Успешность загрузки
        """
        try:
            self.драйвер.get(url)
            
            # Ожидание загрузки страницы
            time.sleep(Конфигурация.ОЖИДАНИЕ_ЗАГРУЗКИ_СТРАНИЦЫ)
            
            self.логгер.информация(f"Страница загружена: {url}")
            return True
            
        except Exception as e:
            сообщение = self.обработчик_ошибок.обработать_ошибку(e, f"Загрузка страницы {url}")
            return False
    
    def найти_элемент(self, селектор: str, by: By = By.CSS_SELECTOR, timeout: int = None):
        """
        Поиск элемента с ожиданием
        
        Args:
            селектор: CSS селектор или другой идентификатор
            by: Метод поиска
            timeout: Таймаут ожидания
            
        Returns:
            WebElement: Найденный элемент или None
        """
        if timeout is None:
            timeout = Конфигурация.ТАЙМАУТ_ПОИСКА_ЭЛЕМЕНТОВ
        
        try:
            ожидание = WebDriverWait(self.драйвер, timeout)
            элемент = ожидание.until(EC.presence_of_element_located((by, селектор)))
            return элемент
        except TimeoutException:
            self.логгер.отладка(f"Элемент не найден: {селектор}")
            return None
        except Exception as e:
            self.обработчик_ошибок.обработать_ошибку(e, f"Поиск элемента {селектор}")
            return None
    
    def найти_элементы(self, селектор: str, by: By = By.CSS_SELECTOR, timeout: int = None):
        """
        Поиск нескольких элементов
        
        Args:
            селектор: CSS селектор или другой идентификатор
            by: Метод поиска
            timeout: Таймаут ожидания
            
        Returns:
            List[WebElement]: Список элементов или пустой список
        """
        if timeout is None:
            timeout = Конфигурация.ТАЙМАУТ_ПОИСКА_ЭЛЕМЕНТОВ
        
        try:
            ожидание = WebDriverWait(self.драйвер, timeout)
            элементы = ожидание.until(EC.presence_of_all_elements_located((by, селектор)))
            return элементы
        except TimeoutException:
            self.логгер.отладка(f"Элементы не найдены: {селектор}")
            return []
        except Exception as e:
            self.обработчик_ошибок.обработать_ошибку(e, f"Поиск элементов {селектор}")
            return []
    
    def выполнить_javascript(self, скрипт: str, *args):
        """
        Выполнение JavaScript кода
        
        Args:
            скрипт: JavaScript код
            *args: Аргументы для скрипта
            
        Returns:
            Результат выполнения скрипта
        """
        try:
            return self.драйвер.execute_script(скрипт, *args)
        except Exception as e:
            self.обработчик_ошибок.обработать_ошибку(e, "Выполнение JavaScript")
            return None
    
    def сделать_скриншот(self, путь: str) -> bool:
        """
        Создание скриншота страницы
        
        Args:
            путь: Путь для сохранения скриншота
            
        Returns:
            bool: Успешность создания
        """
        try:
            self.драйвер.save_screenshot(путь)
            self.логгер.информация(f"Скриншот сохранен: {путь}")
            return True
        except Exception as e:
            self.обработчик_ошибок.обработать_ошибку(e, "Создание скриншота")
            return False
    
    def закрыть_браузер(self):
        """Закрытие браузера и освобождение ресурсов"""
        try:
            if self.драйвер:
                self.драйвер.quit()
                self.логгер.информация("Браузер закрыт")
        except Exception as e:
            self.обработчик_ошибок.обработать_ошибку(e, "Закрытие браузера")
    
    def получить_текущий_url(self) -> str:
        """Получение текущего URL"""
        try:
            return self.драйвер.current_url
        except Exception as e:
            self.обработчик_ошибок.обработать_ошибку(e, "Получение текущего URL")
            return ""
    
    def обновить_страницу(self):
        """Обновление текущей страницы"""
        try:
            self.драйвер.refresh()
            time.sleep(3)  # Задержка после обновления
        except Exception as e:
            self.обработчик_ошибок.обработать_ошибку(e, "Обновление страницы")
