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

class VendaExtractor:
    """Extrator de vendas do SimplesVet"""
    def __init__(self, webdriver_manager: WebDriverManager, config: Config):
        self.webdriver_manager = webdriver_manager
        self.config = config

    def extract_vendas(self, start_date: str, end_date: str, month_str: str = None) -> str:
        """
        Extrai vendas do SimplesVet para o período informado e salva como Excel filtrado
        Retorna o caminho do arquivo Excel gerado
        """
        logger.info(f"Iniciando extração de vendas de {start_date} até {end_date}")
        driver = self.webdriver_manager.driver
        if not driver:
            logger.error("Driver não disponível")
            return None

        # Navega para página de vendas
        vendas_url = "https://app.simples.vet/principal/venda/venda.php"
        self.webdriver_manager.navigate_to(vendas_url)
        time.sleep(3)

        # Seleciona o período simulando cliques no calendário
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        import calendar
        try:
            # 1. Clica no campo de data
            date_field = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.ID, "p__ven_dat_data_text"))
            )
            date_field.click()
            time.sleep(1)

            # 2. Seleciona "Selecionar período" no menu
            periodo_btn = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//li[contains(text(),'Selecionar período')]"))
            )
            periodo_btn.click()
            time.sleep(1)

            # 3. Seleciona datas nos minicalendários
            def select_calendar_date(calendar_side, target_date):
                # calendar_side: 'left' ou 'right'
                # target_date: datetime.date
                # Localiza o calendário
                cal_selector = f".calendar.{calendar_side} table"
                while True:
                    # Lê o mês/ano atual do calendário
                    month_header = driver.find_element(By.CSS_SELECTOR, f".calendar.{calendar_side} th[colspan='5']")
                    month_text = month_header.text.strip()
                    # Exemplo: 'Outubro 2025'
                    month_map = {
                        'Janeiro': 1, 'Fevereiro': 2, 'Março': 3, 'Abril': 4, 'Maio': 5, 'Junho': 6,
                        'Julho': 7, 'Agosto': 8, 'Setembro': 9, 'Outubro': 10, 'Novembro': 11, 'Dezembro': 12
                    }
                    mes_nome, ano = month_text.split()
                    mes_atual = month_map.get(mes_nome, 0)
                    ano_atual = int(ano)
                    # Compara com target_date
                    if mes_atual == target_date.month and ano_atual == target_date.year:
                        break
                    # Navega para o mês correto
                    if (ano_atual, mes_atual) < (target_date.year, target_date.month):
                        # Próximo mês
                        next_btn = driver.find_element(By.CSS_SELECTOR, f".calendar.{calendar_side} th.next")
                        next_btn.click()
                        time.sleep(0.5)
                    else:
                        # Mês anterior
                        prev_btn = driver.find_element(By.CSS_SELECTOR, f".calendar.{calendar_side} th.prev")
                        prev_btn.click()
                        time.sleep(0.5)
                # Seleciona o dia
                day_cells = driver.find_elements(By.CSS_SELECTOR, f".calendar.{calendar_side} td.available")
                for cell in day_cells:
                    if cell.text.strip() == str(target_date.day):
                        cell.click()
                        time.sleep(0.5)
                        break

            # Converte datas para datetime.date
            from datetime import datetime as dt
            start_dt = dt.strptime(start_date, "%Y-%m-%d").date()
            end_dt = dt.strptime(end_date, "%Y-%m-%d").date()

            # Seleciona data inicial (calendário da esquerda)
            select_calendar_date('left', start_dt)
            # Seleciona data final (calendário da direita)
            select_calendar_date('right', end_dt)
            time.sleep(1)
        except Exception as e:
            logger.warning(f"Não foi possível selecionar o período: {e}")

        # Clica no botão de relatório
        try:
            relatorio_btn = driver.find_element(By.ID, "p__btn_relatorio")
            relatorio_btn.click()
            time.sleep(1)
        except Exception as e:
            logger.warning(f"Não foi possível clicar no botão de relatório: {e}")

        # Clica em exportar para CSV
        try:
            export_btn = driver.find_element(By.CSS_SELECTOR, "a.p__btn_exportar[rel='xls_vendas']")
            export_btn.click()
            logger.info("Exportando vendas para CSV...")
            time.sleep(5)
        except Exception as e:
            logger.error(f"Não foi possível exportar para CSV: {e}")
            return None

        # Aguarda download do CSV (agora em scrapper, precisa subir 3 níveis para raiz)
        download_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "downloads")
        csv_file = self._wait_for_csv_download(download_dir, timeout=30)
        if not csv_file:
            logger.error("CSV de vendas não encontrado")
            return None

        # Filtra e salva como Excel
        excel_file = self._filter_and_save_csv(csv_file, month_str)
        return excel_file

    def _wait_for_csv_download(self, download_dir: str, timeout: int = 30) -> str:
        """Aguarda o download do CSV de vendas"""
        logger.info(f"Aguardando download do CSV em: {download_dir}")
        start_time = time.time()
        while time.time() - start_time < timeout:
            time.sleep(2)
            files = [f for f in os.listdir(download_dir) if f.endswith('.csv')]
            if files:
                # Pega o mais recente
                files = sorted(files, key=lambda f: os.path.getmtime(os.path.join(download_dir, f)), reverse=True)
                file_path = os.path.join(download_dir, files[0])
                logger.info(f"CSV encontrado: {file_path}")
                return file_path
        return None

    def _filter_and_save_csv(self, csv_path: str, month_str: str = None) -> str:
        """Filtra colunas do CSV e salva como Excel"""
        logger.info(f"Filtrando CSV: {csv_path}")
        # Tenta ler em utf-8, se falhar tenta latin1
        try:
            df = pd.read_csv(csv_path, sep=';', encoding='utf-8')
        except UnicodeDecodeError:
            logger.debug("CSV não está em UTF-8, usando latin1...")
            df = pd.read_csv(csv_path, sep=';', encoding='latin1')
        # Colunas desejadas
        columns = [
            'Data e hora', 'Venda', 'Status da venda', 'Funcionário', 'Cliente', 'Animal',
            'Tipo do Item', 'Grupo', 'Produto/serviço', 'Valor Unitário', 'Quantidade', 'Bruto', 'Desconto', 'Líquido'
        ]
        # Filtra e cria uma cópia explícita para evitar SettingWithCopyWarning
        df_filtered = df[[col for col in columns if col in df.columns]].copy()
        
        # Converte colunas financeiras e quantidade para número
        num_cols = ['Valor Unitário', 'Quantidade', 'Bruto', 'Desconto', 'Líquido']
        for col in num_cols:
            if col in df_filtered.columns:
                df_filtered[col] = (
                    df_filtered[col]
                    .astype(str)
                    .str.replace('.', '', regex=False)
                    .str.replace(',', '.', regex=False)
                    .str.replace(r'[^0-9.-]', '', regex=True)
                )
                df_filtered[col] = pd.to_numeric(df_filtered[col], errors='coerce')
        # Salva como Excel
        if month_str:
            excel_path = os.path.join(os.path.dirname(csv_path), f"{month_str}-vendas.xlsx")
        else:
            excel_path = csv_path.replace('.csv', '.xlsx')
        df_filtered.to_excel(excel_path, index=False)
        logger.info(f"✅ Excel de vendas criado: {excel_path}")
        # Remove o CSV original se for Vendas.csv
        try:
            base_csv = os.path.basename(csv_path).lower()
            if base_csv == "vendas.csv" and os.path.exists(csv_path):
                os.remove(csv_path)
                logger.info(f"🗑️  Vendas.csv removido após conversão!")
        except Exception as e:
            logger.warning(f"Erro ao remover Vendas.csv: {e}")
        return excel_path
