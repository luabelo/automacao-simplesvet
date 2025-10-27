"""
Módulo responsável pelo processamento de dados de vacinas e testes.

Este módulo contém a classe VaccineTestProcessor que processa os dados
de vacinas e testes FIV/FeLV, separando por tipo (interno/externo) e
calculando os totais conforme os critérios especificados.
"""

import pandas as pd
from typing import Dict, Tuple
from ..scrapper.logger import logger


class VaccineTestProcessor:
    """Classe responsável por processar dados de vacinas e testes."""
    
    # Configuração dos tipos de vacinas e testes
    VACCINE_TYPES = {
        'felv_v1': 'FeLV - V1',
        'raiva': 'Antirrábica',
        'v3': 'Triplice - V3',
        'v4': 'Quádrupla - V4',
        'v5': 'Quíntupla - V5'
    }
    
    TEST_TYPES = {
        'fiv_felv': 'Teste FIV/FeLV'
    }
    
    # Usuários autorizados para contagem
    AUTHORIZED_USERS = ['Nathália Coelho', 'Mislene Ribeiro']
    
    # Clientes internos (Catland/Petz)
    INTERNAL_CLIENTS = ['Catland', 'Petz']
    
    def __init__(self, year_month: str, downloads_folder: str = "downloads"):
        """
        Inicializa o processador de vacinas e testes.
        
        Args:
            year_month: String no formato YYYYMM (ex: 202509)
            downloads_folder: Pasta onde estão os arquivos XLS
        """
        self.year_month = year_month
        self.downloads_folder = downloads_folder
        self.vaccines_df = None
        self.exams_df = None
        self.data = {}
        
        logger.info(f"Inicializando processador de vacinas e testes para o período {year_month}")
    
    def load_data(self) -> bool:
        """
        Carrega os arquivos XLS de vacinas e exames.
        
        Returns:
            True se carregou com sucesso, False caso contrário
        """
        try:
            import os
            
            vaccines_file = os.path.join(
                self.downloads_folder,
                f"{self.year_month}-vacina.xls"
            )
            exams_file = os.path.join(
                self.downloads_folder,
                f"{self.year_month}-exames.xls"
            )
            
            if not os.path.exists(vaccines_file):
                logger.error(f"Arquivo de vacinas não encontrado: {vaccines_file}")
                return False
            
            if not os.path.exists(exams_file):
                logger.error(f"Arquivo de exames não encontrado: {exams_file}")
                return False
            
            logger.info(f"Carregando arquivo de vacinas: {vaccines_file}")
            # Ler arquivo de vacinas (formato HTML disfarçado de XLS)
            self.vaccines_df = pd.read_excel(
                vaccines_file, 
                engine='xlrd',
                engine_kwargs={'ignore_workbook_corruption': True},
                skiprows=2
            )
            
            # A primeira linha contém os cabeçalhos
            self.vaccines_df.columns = self.vaccines_df.iloc[0]
            self.vaccines_df = self.vaccines_df[1:].reset_index(drop=True)
            
            # Normalizar nomes de colunas removendo problemas de encoding
            self.vaccines_df.columns = [self._normalize_column_name(col) for col in self.vaccines_df.columns]
            
            logger.info(f"Carregando arquivo de exames: {exams_file}")
            # Ler arquivo de exames
            self.exams_df = pd.read_excel(
                exams_file,
                engine='xlrd',
                engine_kwargs={'ignore_workbook_corruption': True},
                skiprows=2
            )
            
            # A primeira linha contém os cabeçalhos
            self.exams_df.columns = self.exams_df.iloc[0]
            self.exams_df = self.exams_df[1:].reset_index(drop=True)
            
            # Normalizar nomes de colunas
            self.exams_df.columns = [self._normalize_column_name(col) for col in self.exams_df.columns]
            
            logger.info(f"Dados carregados: {len(self.vaccines_df)} vacinas, {len(self.exams_df)} exames")
            logger.info(f"Colunas vacinas: {self.vaccines_df.columns.tolist()}")
            logger.info(f"Colunas exames: {self.exams_df.columns.tolist()}")
            
            return True
            
        except Exception as e:
            logger.error(f"Erro ao carregar dados de vacinas e testes: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    def _normalize_column_name(self, col_name: str) -> str:
        """
        Normaliza o nome da coluna removendo problemas de encoding.
        
        Args:
            col_name: Nome original da coluna
        
        Returns:
            Nome normalizado da coluna
        """
        # Mapeamento de nomes problemáticos
        mapping = {
            'Usu': 'Usuario',
            'Usu�rio': 'Usuario',
            'Usuário': 'Usuario',
            'Esp': 'Especie',
            'Esp�cie': 'Especie',
            'Espécie': 'Especie'
        }
        
        col_str = str(col_name)
        
        # Tenta mapear diretamente
        for old, new in mapping.items():
            if old in col_str:
                return new
        
        return col_str
    
    def _is_internal_client(self, client_name: str) -> bool:
        """
        Verifica se o cliente é interno (Catland ou Petz).
        
        Args:
            client_name: Nome do cliente
        
        Returns:
            True se for cliente interno, False caso contrário
        """
        if pd.isna(client_name):
            return False
        
        client_str = str(client_name).lower()
        return any(internal.lower() in client_str for internal in self.INTERNAL_CLIENTS)
    
    def _is_authorized_user(self, user_name: str) -> bool:
        """
        Verifica se o usuário está autorizado.
        
        Args:
            user_name: Nome do usuário
        
        Returns:
            True se for usuário autorizado, False caso contrário
        """
        if pd.isna(user_name):
            return False
        
        user_str = str(user_name)
        return user_str in self.AUTHORIZED_USERS
    
    def _count_vaccine(
        self, 
        vaccine_type: str, 
        is_internal: bool = True
    ) -> int:
        """
        Conta quantas vacinas de um tipo específico foram aplicadas.
        
        Args:
            vaccine_type: Tipo da vacina (ex: 'FeLV - V1', 'Antirrábica')
            is_internal: Se True, conta apenas clientes internos (Catland/Petz)
                        Se False, conta apenas clientes externos
        
        Returns:
            Número de vacinas aplicadas
        """
        if self.vaccines_df is None:
            return 0
        
        # Filtro base: vacina do tipo especificado e usuário autorizado
        mask = (
            (self.vaccines_df['Resumo'].str.contains(vaccine_type, case=False, na=False, regex=False)) &
            (self.vaccines_df['Usuario'].isin(self.AUTHORIZED_USERS))
        )
        
        # Aplica filtro de cliente interno ou externo
        if is_internal:
            mask &= self.vaccines_df['Cliente'].apply(self._is_internal_client)
        else:
            mask &= ~self.vaccines_df['Cliente'].apply(self._is_internal_client)
        
        count = mask.sum()
        
        logger.debug(
            f"Vacina {vaccine_type} ({'interna' if is_internal else 'externa'}): {count}"
        )
        
        return count
    
    def _count_test(
        self,
        test_type: str,
        is_internal: bool = True
    ) -> int:
        """
        Conta quantos testes de um tipo específico foram realizados.
        
        Args:
            test_type: Tipo do teste (ex: 'Teste FIV/FeLV')
            is_internal: Se True, conta apenas clientes internos (Catland/Petz)
                        Se False, conta apenas clientes externos
        
        Returns:
            Número de testes realizados
        """
        if self.exams_df is None:
            return 0
        
        # Filtro base: teste do tipo especificado e usuário autorizado
        mask = (
            (self.exams_df['Resumo'].str.contains(test_type, case=False, na=False, regex=False)) &
            (self.exams_df['Usuario'].isin(self.AUTHORIZED_USERS))
        )
        
        # Aplica filtro de cliente interno ou externo
        if is_internal:
            mask &= self.exams_df['Cliente'].apply(self._is_internal_client)
        else:
            mask &= ~self.exams_df['Cliente'].apply(self._is_internal_client)
        
        count = mask.sum()
        
        logger.debug(
            f"Teste {test_type} ({'interno' if is_internal else 'externo'}): {count}"
        )
        
        return count
    
    def process_vaccines_and_tests(self):
        """Processa os dados de vacinas e testes."""
        logger.info("Processando dados de vacinas e testes...")
        
        # Processa testes internos
        self.data['test_fiv_felv_internal'] = self._count_test('Teste FIV/FeLV', is_internal=True)
        
        # Processa vacinas internas
        self.data['vaccine_felv_v1_internal'] = self._count_vaccine('FeLV - V1', is_internal=True)
        self.data['vaccine_raiva_internal'] = self._count_vaccine('Antirrábica', is_internal=True)
        self.data['vaccine_v3_internal'] = self._count_vaccine('Triplice - V3', is_internal=True)
        self.data['vaccine_v4_internal'] = self._count_vaccine('Quádrupla - V4', is_internal=True)
        self.data['vaccine_v5_internal'] = self._count_vaccine('Quíntupla - V5', is_internal=True)
        
        # Processa testes externos
        self.data['test_fiv_felv_external'] = self._count_test('Teste FIV/FeLV', is_internal=False)
        
        # Processa vacinas externas
        self.data['vaccine_felv_v1_external'] = self._count_vaccine('FeLV - V1', is_internal=False)
        self.data['vaccine_raiva_external'] = self._count_vaccine('Antirrábica', is_internal=False)
        self.data['vaccine_v3_external'] = self._count_vaccine('Triplice - V3', is_internal=False)
        self.data['vaccine_v4_external'] = self._count_vaccine('Quádrupla - V4', is_internal=False)
        self.data['vaccine_v5_external'] = self._count_vaccine('Quíntupla - V5', is_internal=False)
        
        # Log dos totais
        logger.info("="*60)
        logger.info("VACINAS E TESTES INTERNOS (Catland/Petz)")
        logger.info("="*60)
        logger.info(f"Teste FIV/FeLV: {self.data['test_fiv_felv_internal']}")
        logger.info(f"FeLV - V1: {self.data['vaccine_felv_v1_internal']}")
        logger.info(f"Vacinas Raiva: {self.data['vaccine_raiva_internal']}")
        logger.info(f"Vacinas V3: {self.data['vaccine_v3_internal']}")
        logger.info(f"Vacinas V4: {self.data['vaccine_v4_internal']}")
        logger.info(f"Vacinas V5: {self.data['vaccine_v5_internal']}")
        
        logger.info("="*60)
        logger.info("VACINAS E TESTES EXTERNOS")
        logger.info("="*60)
        logger.info(f"Teste FIV/FeLV: {self.data['test_fiv_felv_external']}")
        logger.info(f"FeLV - V1: {self.data['vaccine_felv_v1_external']}")
        logger.info(f"Vacinas Raiva: {self.data['vaccine_raiva_external']}")
        logger.info(f"Vacinas V3: {self.data['vaccine_v3_external']}")
        logger.info(f"Vacinas V4: {self.data['vaccine_v4_external']}")
        logger.info(f"Vacinas V5: {self.data['vaccine_v5_external']}")
        
        logger.info("Processamento de vacinas e testes concluído")
    
    def get_data(self) -> Dict[str, int]:
        """
        Retorna os dados processados.
        
        Returns:
            Dicionário com os totais de vacinas e testes
        """
        return self.data
    
    def run(self) -> bool:
        """
        Executa o processo completo de processamento.
        
        Returns:
            True se executou com sucesso, False caso contrário
        """
        logger.info("="*60)
        logger.info("Iniciando processamento de vacinas e testes")
        logger.info("="*60)
        
        # Carrega os dados
        if not self.load_data():
            logger.error("Falha ao carregar dados de vacinas e testes")
            return False
        
        # Processa vacinas e testes
        self.process_vaccines_and_tests()
        
        logger.info("="*60)
        logger.info("Processamento de vacinas e testes concluído com sucesso!")
        logger.info("="*60)
        
        return True
