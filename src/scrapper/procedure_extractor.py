import os
import time
import pandas as pd
import warnings
from datetime import datetime
from .logger import logger
from .config import Config
from .webdriver_manager import WebDriverManager

# Suprime warnings do pandas
warnings.filterwarnings('ignore', category=pd.errors.SettingWithCopyWarning)
warnings.filterwarnings('ignore', message='.*SettingWithCopyWarning.*')

class ProcedureExtractor:
    """Extrator de atendimentos realizados (vacinas e exames) do SimplesVet"""
    def __init__(self, webdriver_manager: WebDriverManager, config: Config):
        self.webdriver_manager = webdriver_manager
        self.config = config

    def extract_procedures(self, start_date: str, end_date: str, month_str: str = None) -> dict:
        """
        Extrai vacinas e exames do SimplesVet para o período informado
        Retorna um dicionário com os caminhos dos arquivos Excel gerados
        """
        logger.info(f"Iniciando extração de atendimentos de {start_date} até {end_date}")
        
        results = {
            'vacinas': None,
            'exames': None
        }
        
        # Extrai primeiro Vacinas
        logger.info("=" * 60)
        logger.info("EXTRAINDO VACINAS")
        logger.info("=" * 60)
        results['vacinas'] = self._extract_by_event_type(
            start_date, end_date, month_str, 
            event_type='5', 
            event_name='Vacina'
        )
        
        # Aguarda um pouco entre as extrações
        time.sleep(2)
        
        # Extrai depois Exames
        logger.info("=" * 60)
        logger.info("EXTRAINDO EXAMES")
        logger.info("=" * 60)
        results['exames'] = self._extract_by_event_type(
            start_date, end_date, month_str, 
            event_type='7', 
            event_name='Exames'
        )
        
        return results

    def _extract_by_event_type(self, start_date: str, end_date: str, month_str: str, 
                                event_type: str, event_name: str) -> str:
        """
        Extrai atendimentos de um tipo específico (Vacina ou Exames)
        event_type: '5' para Vacina, '7' para Exames
        """
        logger.info(f"Iniciando extração de {event_name} de {start_date} até {end_date}")
        driver = self.webdriver_manager.driver
        if not driver:
            logger.error("Driver não disponível")
            return None

        # Navega para página de atendimentos
        atendimentos_url = "https://app.simples.vet/consulta/atendimento/atendimento.php"
        self.webdriver_manager.navigate_to(atendimentos_url)
        time.sleep(3)

        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.webdriver.support.ui import Select
        
        try:
            # 1. Seleciona o tipo de evento (Vacina ou Exames)
            logger.info(f"Selecionando evento: {event_name}")
            event_select = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "p__tev_int_codigo"))
            )
            select = Select(event_select)
            select.select_by_value(event_type)
            time.sleep(2)

            # 2. Clica no campo de data
            date_field = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.ID, "p__eve_dat_data_text"))
            )
            date_field.click()
            time.sleep(1)

            # 3. Seleciona "Selecionar período" no menu (se disponível)
            try:
                periodo_btn = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, "//li[contains(text(),'Selecionar período')]"))
                )
                periodo_btn.click()
                time.sleep(1)
            except:
                logger.info("Botão 'Selecionar período' não encontrado, calendário já deve estar aberto")

            # 4. Seleciona datas nos minicalendários
            def select_calendar_date(calendar_side, target_date):
                """
                Seleciona uma data em um dos calendários
                calendar_side: 'left' ou 'right'
                target_date: datetime.date
                """
                # Mapeamento de meses
                month_map = {
                    'Janeiro': 1, 'Fevereiro': 2, 'Março': 3, 'Abril': 4, 
                    'Maio': 5, 'Junho': 6, 'Julho': 7, 'Agosto': 8, 
                    'Setembro': 9, 'Outubro': 10, 'Novembro': 11, 'Dezembro': 12
                }
                
                # Navega até o mês/ano correto
                max_attempts = 24  # Evita loops infinitos
                attempts = 0
                while attempts < max_attempts:
                    attempts += 1
                    try:
                        # Lê o mês/ano atual do calendário
                        month_header = driver.find_element(
                            By.CSS_SELECTOR, 
                            f".calendar.{calendar_side} th[colspan='5']"
                        )
                        month_text = month_header.text.strip()
                        
                        # Exemplo: 'Outubro 2025'
                        parts = month_text.split()
                        if len(parts) != 2:
                            logger.warning(f"Formato de mês inesperado: {month_text}")
                            break
                            
                        mes_nome, ano = parts
                        mes_atual = month_map.get(mes_nome, 0)
                        ano_atual = int(ano)
                        
                        # Verifica se já estamos no mês/ano correto
                        if mes_atual == target_date.month and ano_atual == target_date.year:
                            break
                        
                        # Navega para o mês correto
                        if (ano_atual, mes_atual) < (target_date.year, target_date.month):
                            # Próximo mês
                            next_btn = driver.find_element(
                                By.CSS_SELECTOR, 
                                f".calendar.{calendar_side} th.next"
                            )
                            next_btn.click()
                            time.sleep(0.5)
                        else:
                            # Mês anterior
                            prev_btn = driver.find_element(
                                By.CSS_SELECTOR, 
                                f".calendar.{calendar_side} th.prev"
                            )
                            prev_btn.click()
                            time.sleep(0.5)
                    except Exception as e:
                        logger.warning(f"Erro ao navegar calendário: {e}")
                        break
                
                # Seleciona o dia
                try:
                    day_cells = driver.find_elements(
                        By.CSS_SELECTOR, 
                        f".calendar.{calendar_side} td.available"
                    )
                    for cell in day_cells:
                        if cell.text.strip() == str(target_date.day):
                            cell.click()
                            time.sleep(0.5)
                            logger.info(f"Data selecionada: {target_date}")
                            return True
                except Exception as e:
                    logger.error(f"Erro ao selecionar dia: {e}")
                return False

            # Converte datas para datetime.date
            from datetime import datetime as dt
            start_dt = dt.strptime(start_date, "%Y-%m-%d").date()
            end_dt = dt.strptime(end_date, "%Y-%m-%d").date()

            # Seleciona data inicial (calendário da esquerda)
            logger.info(f"Selecionando data inicial: {start_dt}")
            select_calendar_date('left', start_dt)
            
            # Seleciona data final (calendário da direita)
            logger.info(f"Selecionando data final: {end_dt}")
            select_calendar_date('right', end_dt)
            
            time.sleep(1)

        except Exception as e:
            logger.error(f"Erro ao configurar filtros: {e}")
            return None

        # 5. Clica no botão de relatório
        try:
            relatorio_btn = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.ID, "p__btn_relatorio"))
            )
            relatorio_btn.click()
            logger.info("Botão de relatório clicado")
            time.sleep(1)
        except Exception as e:
            logger.error(f"Não foi possível clicar no botão de relatório: {e}")
            return None

        # 6. Remove arquivos "atendimentos" antigos antes de baixar novos
        download_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "downloads")
        self._cleanup_old_atendimentos_files(download_dir)
        
        # 7. Clica em exportar para Excel
        try:
            export_btn = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "a.p__btn_exportar[rel='xls']"))
            )
            export_btn.click()
            logger.info(f"Exportando {event_name} para Excel...")
            time.sleep(5)
        except Exception as e:
            logger.error(f"Não foi possível exportar para Excel: {e}")
            return None

        # 8. Aguarda download do arquivo Excel
        excel_file = self._wait_for_excel_download(download_dir, timeout=30)
        if not excel_file:
            logger.error(f"Excel de {event_name} não encontrado")
            return None

        # 9. Renomeia o arquivo para incluir o tipo e período
        renamed_file = self._rename_excel_file(excel_file, month_str, event_name)
        
        return renamed_file

    def _cleanup_old_atendimentos_files(self, download_dir: str):
        """Remove arquivos 'atendimentos' antigos para evitar confusão"""
        try:
            if os.path.exists(download_dir):
                for filename in os.listdir(download_dir):
                    if 'atendimento' in filename.lower() and filename.endswith(('.xls', '.xlsx')):
                        file_path = os.path.join(download_dir, filename)
                        try:
                            os.remove(file_path)
                            logger.info(f"🗑️  Arquivo antigo removido: {filename}")
                        except Exception as e:
                            logger.warning(f"Não foi possível remover {filename}: {e}")
        except Exception as e:
            logger.warning(f"Erro ao limpar arquivos antigos: {e}")

    def _wait_for_excel_download(self, download_dir: str, timeout: int = 10) -> str:
        """Aguarda o download do arquivo Excel"""
        start_time = time.time()
        
        # Registra os arquivos Excel que já existem com seus tamanhos
        existing_files = {}
        if os.path.exists(download_dir):
            for f in os.listdir(download_dir):
                if f.endswith(('.xls', '.xlsx')):
                    file_path = os.path.join(download_dir, f)
                    existing_files[f] = os.path.getmtime(file_path)
        
        while time.time() - start_time < timeout:
            time.sleep(2)
            if os.path.exists(download_dir):
                current_files = {}
                for f in os.listdir(download_dir):
                    if f.endswith(('.xls', '.xlsx')):
                        file_path = os.path.join(download_dir, f)
                        current_files[f] = os.path.getmtime(file_path)
                
                # Procura por arquivos novos ou modificados
                for filename, mtime in current_files.items():
                    # Arquivo novo ou modificado recentemente
                    if filename not in existing_files or mtime > existing_files.get(filename, 0):
                        file_path = os.path.join(download_dir, filename)
                        
                        # Verifica se o arquivo não está mais sendo escrito
                        try:
                            initial_size = os.path.getsize(file_path)
                            time.sleep(1)
                            if os.path.getsize(file_path) == initial_size and initial_size > 0:
                                return file_path
                        except:
                            continue
        
        # Como fallback, tenta pegar o arquivo mais recente que contém "atendimento" no nome
        if os.path.exists(download_dir):
            excel_files = [f for f in os.listdir(download_dir) 
                          if f.lower().endswith(('.xls', '.xlsx')) and 'atendimento' in f.lower()]
            if excel_files:
                excel_files = sorted(
                    excel_files, 
                    key=lambda f: os.path.getmtime(os.path.join(download_dir, f)), 
                    reverse=True
                )
                file_path = os.path.join(download_dir, excel_files[0])
                return file_path
        
        return None

    def _rename_excel_file(self, excel_path: str, month_str: str, event_name: str) -> str:
        """Renomeia o arquivo Excel para um padrão consistente"""
        try:
            dir_path = os.path.dirname(excel_path)
            
            # Mantém a extensão original do arquivo
            original_extension = os.path.splitext(excel_path)[1]  # .xls ou .xlsx
            
            # Normaliza o nome do evento
            event_name_normalized = event_name.lower().replace(' ', '-')
            
            # Define novo nome mantendo a extensão original
            if month_str:
                new_name = f"{month_str}-{event_name_normalized}{original_extension}"
            else:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                new_name = f"{timestamp}-{event_name_normalized}{original_extension}"
            
            new_path = os.path.join(dir_path, new_name)
            
            # Renomeia o arquivo
            if os.path.exists(new_path):
                os.remove(new_path)
            os.rename(excel_path, new_path)
            
            logger.info(f"✅ Excel de {event_name} criado: {new_path}")
            return new_path
            
        except Exception as e:
            logger.warning(f"Erro ao renomear arquivo: {e}")
            return excel_path
