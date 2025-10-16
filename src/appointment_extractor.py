from typing import List, Dict, Optional
import os
import time
from datetime import datetime
from .config import Config
from .webdriver_manager import WebDriverManager
from .pdf_converter import PDFConverter
from .logger import logger


class AppointmentExtractor:
    """Extrator de agendamentos do SimplesVet"""
    
    def __init__(self, webdriver_manager: WebDriverManager, config: Config):
        self.webdriver_manager = webdriver_manager
        self.config = config
        self.pdf_converter = PDFConverter()
    
    def extract_appointments(self, start_date: str, end_date: str, month_str: str = None) -> List[Dict]:
        """Extrai agendamentos do período especificado via URL direta do relatório"""
        logger.info(f"Iniciando extração de agendamentos de {start_date} até {end_date}")
        
        # Converte as datas para o formato esperado pela URL (DD/MM/YYYY)
        formatted_start = self._format_date_for_url(start_date)
        formatted_end = self._format_date_for_url(end_date)
        
        if not formatted_start or not formatted_end:
            logger.error("Erro ao formatar datas")
            return []
        
        # Faz o download do PDF diretamente via URL
        pdf_file = self.download_appointments_pdf_direct(formatted_start, formatted_end, month_str)
        if not pdf_file:
            logger.error("Falha ao fazer download do PDF de agendamentos")
            return []
        
        # Converte PDF para Excel e extrai dados estruturados
        excel_file = self.pdf_converter.convert_pdf_to_excel(pdf_file, month_str)
        
        appointments = []
        
        if excel_file:
            logger.info(f"✅ Excel criado com sucesso: {excel_file}")
            appointments.append({
                "pdf_file": pdf_file,
                "excel_file": excel_file,
                "download_time": time.time(),
                "date_range": f"{start_date} to {end_date}",
                "formatted_date_range": f"{formatted_start}-{formatted_end}",
                "month": month_str,
                "status": "converted_to_excel"
            })
        else:
            logger.warning("Falha na conversão para Excel, retornando apenas PDF")
            appointments.append({
                "pdf_file": pdf_file,
                "excel_file": None,
                "download_time": time.time(),
                "date_range": f"{start_date} to {end_date}",
                "formatted_date_range": f"{formatted_start}-{formatted_end}",
                "month": month_str,
                "status": "pdf_only"
            })
        
        return appointments
    
    def _format_date_for_url(self, date_str: str) -> Optional[str]:
        """Converte data de YYYY-MM-DD para DD/MM/YYYY"""
        try:
            # Parse da data no formato YYYY-MM-DD
            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
            # Retorna no formato DD/MM/YYYY
            return date_obj.strftime('%d/%m/%Y')
        except ValueError as e:
            logger.error(f"Erro ao converter data {date_str}: {str(e)}")
            return None
    
    def download_appointments_pdf_direct(self, start_date: str, end_date: str, month_str: str = None) -> Optional[str]:
        """Faz o download do PDF através da URL direta do relatório"""
        logger.info(f"Fazendo download direto do PDF para período {start_date} - {end_date}")
        
        driver = self.webdriver_manager.driver
        if not driver:
            logger.error("Driver não disponível")
            return None
        
        try:
            # Constrói a URL direta do relatório
            report_url = f"https://app.simples.vet/agenda/agenda_relatorio_v2.php?tipo=lista&data={start_date}-{end_date}"
            logger.info(f"Acessando URL do relatório: {report_url}")
            
            # Configura diretório de download
            download_dir = self._setup_download_directory()
            if not download_dir:
                logger.error("Erro ao configurar diretório de download")
                return None
            
            # Define o nome base do arquivo
            if month_str:
                base_filename = f"{month_str}-agendamentos"
            else:
                base_filename = f"agendamentos_{start_date.replace('/', '_')}_{end_date.replace('/', '_')}"
            
            # Método 1: Tenta forçar download via JavaScript
            try:
                logger.info("Tentando forçar download via JavaScript...")
                js_download = f"""
                var link = document.createElement('a');
                link.href = '{report_url}';
                link.download = '{base_filename}.pdf';
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);
                """
                driver.execute_script(js_download)
                
                # Aguarda um pouco para o download iniciar
                time.sleep(3)
                
                # Verifica se o download começou
                pdf_file = self._wait_for_pdf_download(download_dir, timeout=15, expected_name=base_filename)
                if pdf_file:
                    logger.info(f"✅ PDF baixado via JavaScript: {pdf_file}")
                    return pdf_file
                
            except Exception as e:
                logger.warning(f"Método JavaScript falhou: {str(e)}")
            
            # Método 2: Navega para URL e tenta Ctrl+S
            logger.info("Tentando navegação direta e Ctrl+S...")
            if not self.webdriver_manager.navigate_to(report_url):
                logger.error("Erro ao navegar para URL do relatório")
                return None
            
            # Aguarda a página carregar
            time.sleep(5)
            
            # Tenta usar Ctrl+S para salvar
            try:
                from selenium.webdriver.common.keys import Keys
                from selenium.webdriver.common.action_chains import ActionChains
                
                # Pressiona Ctrl+S
                actions = ActionChains(driver)
                actions.key_down(Keys.CONTROL).send_keys('s').key_up(Keys.CONTROL).perform()
                
                logger.info("Comando Ctrl+S enviado")
                time.sleep(2)
                
                # Pressiona Enter para confirmar o salvamento (caso abra diálogo)
                actions.send_keys(Keys.ENTER).perform()
                time.sleep(2)
                
                pdf_file = self._wait_for_pdf_download(download_dir, timeout=15, expected_name=base_filename)
                if pdf_file:
                    logger.info(f"✅ PDF baixado via Ctrl+S: {pdf_file}")
                    return pdf_file
                    
            except Exception as e:
                logger.warning(f"Método Ctrl+S falhou: {str(e)}")
            
            # Método 3: Usa requests para baixar diretamente
            logger.info("Tentando download direto via requests...")
            try:
                import requests
                
                # Obter cookies da sessão do Selenium
                cookies = driver.get_cookies()
                session = requests.Session()
                
                for cookie in cookies:
                    session.cookies.set(cookie['name'], cookie['value'])
                
                # Headers similares ao navegador
                headers = {
                    'User-Agent': driver.execute_script("return navigator.userAgent;"),
                    'Referer': 'https://app.simples.vet/'
                }
                
                response = session.get(report_url, headers=headers, stream=True)
                
                if response.status_code == 200:
                    filename = f"{base_filename}.pdf"
                    file_path = os.path.join(download_dir, filename)
                    
                    with open(file_path, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            f.write(chunk)
                    
                    logger.info(f"✅ PDF baixado via requests: {file_path}")
                    return file_path
                else:
                    logger.error(f"Erro no download via requests: {response.status_code}")
                    
            except Exception as e:
                logger.error(f"Método requests falhou: {str(e)}")
            
            logger.error("Todos os métodos de download falharam")
            return None
            
        except Exception as e:
            logger.error(f"Erro ao fazer download do PDF: {str(e)}")
            return None
    
    def _setup_download_directory(self) -> Optional[str]:
        """Configura e cria diretório para downloads"""
        try:
            # Cria diretório 'downloads' no projeto se não existir
            project_root = os.path.dirname(os.path.dirname(__file__))
            download_dir = os.path.join(project_root, "downloads")
            
            if not os.path.exists(download_dir):
                os.makedirs(download_dir)
                logger.info(f"Diretório de download criado: {download_dir}")
            
            return download_dir
            
        except Exception as e:
            logger.error(f"Erro ao configurar diretório de download: {str(e)}")
            return None
    
    def _wait_for_pdf_download(self, download_dir: str, timeout: int = 30, expected_name: str = None) -> Optional[str]:
        """Aguarda o download do PDF ser concluído"""
        logger.info(f"Aguardando download do PDF em: {download_dir}")
        
        start_time = time.time()
        initial_files = set(os.listdir(download_dir)) if os.path.exists(download_dir) else set()
        
        while time.time() - start_time < timeout:
            time.sleep(2)
            
            if not os.path.exists(download_dir):
                continue
                
            current_files = set(os.listdir(download_dir))
            new_files = current_files - initial_files
            
            # Procura por arquivos PDF que não sejam temporários
            for file in new_files:
                if file.endswith('.pdf') and not file.endswith('.tmp'):
                    file_path = os.path.join(download_dir, file)
                    # Verifica se o arquivo não está sendo escrito (tamanho estável)
                    if self._is_file_complete(file_path):
                        # Se temos um nome esperado e o arquivo não tem esse nome, renomeia
                        if expected_name and not file.startswith(expected_name):
                            new_path = os.path.join(download_dir, f"{expected_name}.pdf")
                            try:
                                # Se já existe um arquivo com esse nome, remove
                                if os.path.exists(new_path):
                                    os.remove(new_path)
                                os.rename(file_path, new_path)
                                logger.info(f"Arquivo renomeado para: {new_path}")
                                return new_path
                            except Exception as e:
                                logger.warning(f"Erro ao renomear arquivo: {e}")
                                return file_path
                        return file_path
            
            # Verifica se existe algum arquivo .crdownload (Chrome) sendo baixado
            downloading_files = [f for f in current_files if f.endswith('.crdownload')]
            if downloading_files:
                logger.info("Download em progresso...")
                continue
        
        logger.warning(f"Timeout aguardando download do PDF ({timeout}s)")
        return None
    
    def _is_file_complete(self, file_path: str) -> bool:
        """Verifica se o arquivo foi completamente baixado"""
        try:
            # Verifica o tamanho do arquivo duas vezes com intervalo
            size1 = os.path.getsize(file_path)
            time.sleep(1)
            size2 = os.path.getsize(file_path)
            
            # Se o tamanho não mudou e é maior que 0, provavelmente terminou
            return size1 == size2 and size1 > 0
            
        except Exception:
            return False

    def set_date_filter(self, start_date: str, end_date: str) -> bool:
        """Método mantido para compatibilidade - não usado na nova implementação"""
        logger.info(f"Método set_date_filter não é mais necessário com URL direta")
        return True