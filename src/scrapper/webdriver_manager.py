from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.firefox import GeckoDriverManager
import time
import os
from typing import Optional
from .logger import logger


class WebDriverManager:
    def __init__(self, browser_type: str = 'chrome', headless: bool = False, wait_timeout: int = 10):
        """
        Inicializa o gerenciador do WebDriver
        
        Args:
            browser_type: Tipo do navegador ('chrome' ou 'firefox')
            headless: Se deve executar em modo headless
            wait_timeout: Timeout padrão para esperas
        """
        self.browser_type = browser_type.lower()
        self.headless = headless
        self.wait_timeout = wait_timeout
        self.driver: Optional[webdriver.Chrome | webdriver.Firefox] = None
        self.wait: Optional[WebDriverWait] = None
    
    def start_browser(self) -> bool:
        """
        Inicia o navegador
        
        Returns:
            True se o navegador foi iniciado com sucesso
        """
        try:
            if self.browser_type == 'chrome':
                self._start_chrome()
            elif self.browser_type == 'firefox':
                self._start_firefox()
            else:
                logger.error(f"Tipo de navegador não suportado: {self.browser_type}")
                return False
            
            self.wait = WebDriverWait(self.driver, self.wait_timeout)
            logger.info(f"Navegador {self.browser_type} iniciado com sucesso")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao iniciar navegador: {e}")
            return False
    
    def _start_chrome(self):
        """Inicia o Chrome"""
        options = ChromeOptions()
        
        if self.headless:
            options.add_argument('--headless')
        
        # Configura diretório de download
        download_dir = self._get_download_directory()
        if download_dir:
            prefs = {
                "download.default_directory": download_dir,
                "download.prompt_for_download": False,
                "download.directory_upgrade": True,
                "safebrowsing.enabled": True
            }
            options.add_experimental_option("prefs", prefs)
        
        # Opções para melhor compatibilidade e performance
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        service = ChromeService(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=options)
    
    def _get_download_directory(self) -> Optional[str]:
        """Obtém o diretório de download do projeto"""
        try:
            # Cria diretório 'downloads' no projeto se não existir (agora em scrapper, precisa subir 3 níveis)
            current_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            download_dir = os.path.join(current_dir, "downloads")
            
            if not os.path.exists(download_dir):
                os.makedirs(download_dir)
                logger.info(f"Diretório de download criado: {download_dir}")
            
            return download_dir
            
        except Exception as e:
            logger.error(f"Erro ao configurar diretório de download: {str(e)}")
            return None
    
    def _start_firefox(self):
        """Inicia o Firefox"""
        options = FirefoxOptions()
        
        if self.headless:
            options.add_argument('--headless')
        
        options.set_preference("general.useragent.override", 
                             "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0")
        
        service = FirefoxService(GeckoDriverManager().install())
        self.driver = webdriver.Firefox(service=service, options=options)
    
    def navigate_to(self, url: str) -> bool:
        """
        Navega para uma URL
        
        Args:
            url: URL de destino
            
        Returns:
            True se a navegação foi bem-sucedida
        """
        try:
            if not self.driver:
                logger.error("Navegador não foi iniciado")
                return False
            
            logger.info(f"Navegando para: {url}")
            self.driver.get(url)
            time.sleep(2)  # Aguarda a página carregar
            return True
            
        except Exception as e:
            logger.error(f"Erro ao navegar para {url}: {e}")
            return False
    
    def find_element_by_selectors(self, selectors: list, timeout: Optional[int] = None) -> Optional[object]:
        """
        Encontra um elemento usando múltiplos seletores
        
        Args:
            selectors: Lista de seletores CSS para tentar
            timeout: Timeout personalizado (usa self.wait_timeout se None)
            
        Returns:
            Elemento encontrado ou None
        """
        if not self.driver:
            return None
        
        timeout = timeout or self.wait_timeout
        
        for selector in selectors:
            try:
                wait = WebDriverWait(self.driver, timeout)
                element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
                logger.debug(f"Elemento encontrado com seletor: {selector}")
                return element
            except TimeoutException:
                logger.debug(f"Elemento não encontrado com seletor: {selector}")
                continue
        
        logger.warning(f"Nenhum elemento encontrado com os seletores fornecidos")
        return None
    
    def wait_for_element_clickable(self, selector: str, timeout: Optional[int] = None) -> Optional[object]:
        """
        Aguarda um elemento ficar clicável
        
        Args:
            selector: Seletor CSS do elemento
            timeout: Timeout personalizado
            
        Returns:
            Elemento clicável ou None
        """
        if not self.driver:
            return None
        
        try:
            timeout = timeout or self.wait_timeout
            wait = WebDriverWait(self.driver, timeout)
            element = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, selector)))
            return element
        except TimeoutException:
            logger.warning(f"Elemento não ficou clicável: {selector}")
            return None
    
    def get_current_url(self) -> Optional[str]:
        """
        Obtém a URL atual
        
        Returns:
            URL atual ou None
        """
        if self.driver:
            return self.driver.current_url
        return None
    
    def get_page_title(self) -> Optional[str]:
        """
        Obtém o título da página
        
        Returns:
            Título da página ou None
        """
        if self.driver:
            return self.driver.title
        return None
    
    def close_browser(self):
        """Fecha o navegador"""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("Navegador fechado com sucesso")
            except Exception as e:
                logger.error(f"Erro ao fechar navegador: {e}")
            finally:
                self.driver = None
                self.wait = None
    
    def __del__(self):
        """Destrutor - garante que o navegador seja fechado"""
        self.close_browser()