import time
from typing import Optional
from .config import Config
from .webdriver_manager import WebDriverManager
from .appointment_extractor import AppointmentExtractor
from .venda_extractor import VendaExtractor
from .logger import logger


class SimplesVetActions:
    def __init__(self, config: Config):
        """
        Inicializa as ações do SimplesVet
        
        Args:
            config: Instância de configuração
        """
        self.config = config
        self.webdriver_manager: Optional[WebDriverManager] = None
        self.appointment_extractor: Optional[AppointmentExtractor] = None
        self.venda_extractor: Optional[VendaExtractor] = None
        self.is_logged_in = False
        
        # Inicializa o WebDriver com configurações do config.json
        browser_config = self.config.get_browser_config()
        self.webdriver_manager = WebDriverManager(
            browser_type=browser_config.get('type', 'chrome'),
            headless=browser_config.get('headless', False),
            wait_timeout=browser_config.get('wait_timeout', 10)
        )
        
        # Inicializa AppointmentExtractor
        self.appointment_extractor = AppointmentExtractor(self.webdriver_manager, self.config)
        # Inicializa VendaExtractor
        self.venda_extractor = VendaExtractor(self.webdriver_manager, self.config)
    
    def start_browser(self) -> bool:
        """
        Inicia o navegador
        
        Returns:
            True se o navegador foi iniciado com sucesso
        """
        if not self.webdriver_manager:
            logger.error("WebDriver Manager não foi inicializado")
            return False
        
        return self.webdriver_manager.start_browser()
    
    def close_browser(self):
        """Fecha o navegador"""
        if self.webdriver_manager:
            self.webdriver_manager.close_browser()
            self.is_logged_in = False
    
    def _find_element_by_selectors(self, selectors: list, timeout: Optional[int] = None):
        """
        Método auxiliar para encontrar elementos usando múltiplos seletores
        
        Args:
            selectors: Lista de seletores para tentar
            timeout: Timeout personalizado
            
        Returns:
            Elemento encontrado ou None
        """
        if not self.webdriver_manager:
            return None
        
        return self.webdriver_manager.find_element_by_selectors(selectors, timeout)
    
    def login(self) -> bool:
        """
        Realiza o login no SimplesVet
        
        Returns:
            True se o login foi realizado com sucesso
        """
        try:
            logger.info("Iniciando processo de login...")
            
            # Obtém a URL de login corretamente
            urls = self.config.get_config('simplesvet', 'urls')
            login_url = urls.get('login') if urls else None
            
            if not login_url:
                logger.error("URL de login não configurada")
                return False
            
            if not self.webdriver_manager.navigate_to(login_url):
                return False
            
            time.sleep(1)
            
            # Obtém credenciais
            email = self.config.get_credential('simplesvet', 'email')
            password = self.config.get_credential('simplesvet', 'password')
            
            if not email or not password:
                logger.error("Credenciais não configuradas")
                return False
            
            email_selectors = [
                'input[name="l_usu_var_email"]',
                'input[id="l_usu_var_email"]',
                '#l_usu_var_email',
                'input[type="email"]'
            ]
            
            password_selectors = [
                'input[name="l_usu_var_senha"]',
                'input[id="l_usu_var_senha"]',
                '#l_usu_var_senha',
                'input[type="password"]'
            ]
            
            login_button_selectors = [
                'button[id="btn_login"]',
                '#btn_login',
                'button[type="submit"]',
                'input[type="submit"]',
                '.btn-login'
            ]
            
            email_field = self._find_element_by_selectors(email_selectors)
            if not email_field:
                logger.error("Campo de email não encontrado")
                return False
            
            email_field.clear()
            email_field.send_keys(email)
            logger.info("Email preenchido")
            
            password_field = self._find_element_by_selectors(password_selectors)
            if not password_field:
                logger.error("Campo de senha não encontrado")
                return False
            
            password_field.clear()
            password_field.send_keys(password)
            logger.info("Senha preenchida")
            
            time.sleep(1)
            
            login_button = self._find_element_by_selectors(login_button_selectors)
            if not login_button:
                logger.error("Botão de login não encontrado")
                return False
            
            login_button.click()
            logger.info("Botão de login clicado")
            
            time.sleep(1)
            
            if self._verify_login():
                logger.info("Login realizado com sucesso!")
                self.is_logged_in = True
                return True
            else:
                logger.error("Falha no login")
                return False
                
        except Exception as e:
            logger.error(f"Erro durante o login: {e}")
            return False
    
    def _verify_login(self) -> bool:
        """
        Verifica se o login foi realizado com sucesso
        
        Returns:
            True se o usuário está logado
        """
        try:
            current_url = self.webdriver_manager.get_current_url()
            page_title = self.webdriver_manager.get_page_title()
            
            # Verifica se não está mais na página de login
            if current_url and 'login' not in current_url.lower():
                logger.debug(f"URL atual: {current_url}")
                return True
            
            # Verifica elementos que indicam sucesso no login
            success_selectors = [
                '.dashboard',
                '#dashboard',
                '.main-content',
                '.user-menu',
                '[data-testid="dashboard"]',
                '.sidebar'
            ]
            
            success_element = self._find_element_by_selectors(success_selectors, timeout=3)
            if success_element:
                return True
            
            # Verifica título da página
            if page_title and 'login' not in page_title.lower():
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Erro ao verificar login: {e}")
            return False
    
    
    def get_appointments_data(self, start_date: str = None, end_date: str = None, month_str: str = None) -> list:
        """
        Extrai dados de atendimentos do SimplesVet
        
        Args:
            start_date: Data de início (formato YYYY-MM-DD)
            end_date: Data de fim (formato YYYY-MM-DD)
            month_str: Mês no formato YYYYMM (usado para nome do arquivo)
            
        Returns:
            Lista com dados dos atendimentos
        """
        try:
            if not self.is_logged_in:
                logger.error("Usuário não está logado")
                return []
            
            logger.info(f"Buscando atendamentos de {start_date} até {end_date}")
            
            # Usa o AppointmentExtractor para extrair os agendamentos
            if self.appointment_extractor:
                appointments = self.appointment_extractor.extract_appointments(
                    start_date, end_date, month_str
                )
            else:
                logger.error("AppointmentExtractor não foi inicializado")
                appointments = []
            
            # Calcula o total de agendamentos extraídos
            total_appointments = sum(item.get('appointments_count', 0) for item in appointments)
            logger.info(f"Encontrados {total_appointments} agendamentos em {len(appointments)} arquivo(s)")
            return appointments
            
        except Exception as e:
            logger.error(f"Erro ao extrair dados de atendimentos: {e}")
            return []
    
    def get_vendas_data(self, start_date: str = None, end_date: str = None, month_str: str = None) -> list:
        """
        Extrai dados de vendas do SimplesVet
        
        Args:
            start_date: Data de início (formato YYYY-MM-DD)
            end_date: Data de fim (formato YYYY-MM-DD)
            month_str: Mês no formato YYYYMM (usado para nome do arquivo)
            
        Returns:
            Lista com caminho do arquivo Excel gerado
        """
        try:
            if not self.is_logged_in:
                logger.error("Usuário não está logado")
                return []
            
            logger.info(f"Buscando vendas de {start_date} até {end_date}")
            
            if self.venda_extractor:
                excel_file = self.venda_extractor.extract_vendas(start_date, end_date, month_str)
                if excel_file:
                    logger.info(f"Vendas extraídas e salvas em: {excel_file}")
                    return [excel_file]
                else:
                    logger.warning("Nenhuma venda extraída")
                    return []
            else:
                logger.error("VendaExtractor não foi inicializado")
                return []
            
        except Exception as e:
            logger.error(f"Erro ao extrair dados de vendas: {e}")
            return []
    
    def navigate_to_appointments(self) -> bool:
        """
        Navega para a página de atendimentos
        
        Returns:
            True se a navegação foi bem-sucedida
        """
        try:
            if not self.is_logged_in:
                logger.error("Usuário não está logado")
                return False
            
            # Seletores para encontrar o menu/link de atendimentos
            appointments_selectors = [
                'a[href*="atendimento"]',
                'a[href*="consulta"]',
                'a[href*="appointment"]',
                '.menu-atendimentos',
                '#menu-atendimentos'
            ]
            
            appointments_link = self._find_element_by_selectors(appointments_selectors)
            if appointments_link:
                appointments_link.click()
                time.sleep(3)
                logger.info("Navegado para página de atendimentos")
                return True
            else:
                logger.error("Link de atendimentos não encontrado")
                return False
                
        except Exception as e:
            logger.error(f"Erro ao navegar para atendimentos: {e}")
            return False