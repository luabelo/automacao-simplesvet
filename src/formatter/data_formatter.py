import os
import pandas as pd
from datetime import datetime
from typing import Dict, List, Tuple
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill
from ..scrapper.logger import logger
from .vaccine_test_processor import VaccineTestProcessor


class CastrationValidator:
    """Classe responsável por validar os dados de castrações."""
    
    def __init__(self, appointments_df: pd.DataFrame, sales_df: pd.DataFrame):
        """
        Inicializa o validador de castrações.
        
        Args:
            appointments_df: DataFrame com os dados de agendamentos
            sales_df: DataFrame com os dados de vendas
        """
        self.appointments_df = appointments_df
        self.sales_df = sales_df
        self.validation_messages = []
    
    def validate_castration_type(
        self,
        castration_type: str,
        appointment_type: str,
        sales_patterns: Dict[str, str]
    ) -> Tuple[int, int, bool]:
        """
        Valida se o total de vendas bate com o total de agendamentos atendidos.
        
        Args:
            castration_type: Nome do tipo de castração para logs
            appointment_type: Tipo de atendimento no arquivo de agendamentos
            sales_patterns: Dicionário com os padrões de vendas (femea_adulto, femea_filhote, etc)
        
        Returns:
            Tupla com (total_vendas, total_atendimentos, validacao_ok)
        """
        # Conta atendimentos concluídos
        total_atendimentos = len(
            self.appointments_df[
                (self.appointments_df['tipo_atendimento'].str.contains(appointment_type, case=False, na=False, regex=False)) &
                (self.appointments_df['status'].str.contains('Atendido', case=False, na=False, regex=False))
            ]
        )
        
        # Conta vendas por categoria
        total_vendas = 0
        for category, pattern in sales_patterns.items():
            count = len(self.sales_df[
                self.sales_df['procedimento'].str.contains(pattern, case=False, na=False, regex=False)
            ])
            total_vendas += count
        
        # Valida se batem
        validation_ok = total_vendas == total_atendimentos
        
        if not validation_ok:
            diferenca = total_atendimentos - total_vendas
            if diferenca > 0:
                message = f"⚠️  {castration_type}: Existem {diferenca} vendas a menos"
            else:
                message = f"⚠️  {castration_type}: Existem {abs(diferenca)} vendas a mais"
            self.validation_messages.append(message)
            logger.warning(message)
        else:
            message = f"✓ {castration_type}: Vendas e atendimentos estão corretos ({total_vendas}/{total_atendimentos})"
            self.validation_messages.append(message)
            logger.info(message)
        
        return total_vendas, total_atendimentos, validation_ok
    
    def get_summary(self) -> str:
        """Retorna um resumo das validações realizadas."""
        if not self.validation_messages:
            return "Nenhuma validação realizada."
        
        errors = [msg for msg in self.validation_messages if "⚠️" in msg]
        
        if errors:
            return f"\n{'='*60}\n⚠️  ATENÇÃO: Inconsistências encontradas no lançamento de vendas\n{'='*60}\n" + "\n".join(self.validation_messages)
        else:
            return f"\n{'='*60}\n✓ Está tudo certo com o lançamento das vendas!\n{'='*60}\n" + "\n".join(self.validation_messages)


class CatlandFormatter:
    """Classe principal para formatação dos dados no padrão Catland."""
    
    # Configuração centralizada de tipos de castração
    CASTRATION_TYPES = {
        'ong': {
            'name': 'Castração Sede (ONG)',
            'appointment_pattern': 'Castração Sede (ONG)',
            'sales_prefix': 'Castração Sede (ONG)',
            'report_label': 'Castrações ONG'
        },
        'lt': {
            'name': 'Castração Lar Temporário',
            'appointment_pattern': 'Castração Lar...',
            'sales_prefix': 'Castração Lar Temporário (Cafofinho)',
            'report_label': 'Castrações Lar Temporário'
        },
        'solidaria': {
            'name': 'Castração Solidária',
            'appointment_pattern': 'Castração Solidária',
            'sales_prefix': 'Castração Solidária',
            'report_label': 'Castrações - Solidária'
        },
        'preco_custo': {
            'name': 'Castração Preço de Custo',
            'appointment_pattern': 'Castração Preço de...',
            'sales_prefix': 'Castração Preço de Custo',
            'report_label': 'Castrações - Preço de Custo'
        },
        'gato_externo': {
            'name': 'Castração Paga Gato Externo',
            'appointment_pattern': 'Castração Paga Gato...',
            'sales_prefix': 'Castração paga Gato externo',
            'report_label': 'Castrações Paga Gato Externo'
        },
        'lt_resgatante': {
            'name': 'Castração Paga LT Resgatante',
            'appointment_pattern': 'Castração Paga LT...',
            'sales_prefix': 'Castração paga LT resgatante',
            'report_label': 'Castrações LT Resgatante'
        }
    }
    
    # Categorias padrão para todas as castrações
    CATEGORIES = {
        'femea_adulto': 'Fêmea / Adulta',
        'femea_filhote': 'Fêmea / Filhote',
        'macho_adulto': 'Macho / Adulto', 
        'macho_filhote': 'Macho / Filhote'  
    }
    
    # Estrutura do relatório
    REPORT_STRUCTURE = [
        ("Vacinas e Testes Internos", None),
        ("Teste FIV / FeLV", "indent"),
        ("FeLV - V1", "indent"),
        ("Vacinas Raiva", "indent"),
        ("Vacinas V3", "indent"),
        ("Vacinas V4", "indent"),
        ("Vacinas V5", "indent"),
        ("Vacinas e Testes Externos", None),
        ("Teste FIV / FeLV", "indent"),
        ("FeLV - V1", "indent"),
        ("Vacinas Raiva", "indent"),
        ("Vacinas V3", "indent"),
        ("Vacinas V4", "indent"),
        ("Vacinas V5", "indent"),
        ("Valor arrecadado com as vacinas e testes pagos", None),
        ("Castrações ONG", None),
        ("Fêmea / Adulta", "indent"),
        ("Fêmea / Filhote", "indent"),
        ("Macho / Adulto", "indent"),
        ("Macho / Filhote", "indent"),
        ("Castrações Lar Temporário", None),
        ("Fêmea / Adulta", "indent"),
        ("Fêmea / Filhote", "indent"),
        ("Macho / Adulto", "indent"),
        ("Macho / Filhote", "indent"),
        ("Castrações Solidárias*", None),
        ("Castrações - Solidária", "indent"),
        ("Fêmea / Adulta", "indent2"),
        ("Fêmea / Filhote", "indent2"),
        ("Macho / Adulto", "indent2"),
        ("Macho / Filhote", "indent2"),
        ("Castrações - Preço de Custo", "indent"),
        ("Fêmea / Adulta", "indent2"),
        ("Fêmea / Filhote", "indent2"),
        ("Macho / Adulto", "indent2"),
        ("Macho / Filhote", "indent2"),
        ("Castrações Externas Pagas", None),
        ("Castrações Paga Gato Externo", "indent"),
        ("Fêmea / Adulta", "indent2"),
        ("Fêmea / Filhote", "indent2"),
        ("Macho / Adulto", "indent2"),
        ("Macho / Filhote", "indent2"),
        ("Castrações LT Resgatante", "indent"),
        ("Fêmea / Adulta", "indent2"),
        ("Fêmea / Filhote", "indent2"),
        ("Macho / Adulto", "indent2"),
        ("Macho / Filhote", "indent2"),
        ("Total de Castrações", None),
        ("Castrações agendadas", "indent"),
        ("Castrações realizadas/atendimentos", "indent"),
        ("Castrações canceladas", "indent")
    ]
    
    def __init__(self, year_month: str, downloads_folder: str = "downloads"):
        """
        Inicializa o formatador.
        
        Args:
            year_month: String no formato YYYYMM (ex: 202509)
            downloads_folder: Pasta onde estão os arquivos XLSX
        """
        self.year_month = year_month
        self.downloads_folder = downloads_folder
        self.appointments_df = None
        self.sales_df = None
        self.validator = None
        self.vaccine_test_processor = None
        self.data = {}
        
        logger.info(f"Inicializando formatador para o período {year_month}")
    
    def load_data(self) -> bool:
        """
        Carrega os arquivos XLSX necessários.
        
        Returns:
            True se carregou com sucesso, False caso contrário
        """
        try:
            appointments_file = os.path.join(
                self.downloads_folder,
                f"{self.year_month}-agendamentos.xlsx"
            )
            sales_file = os.path.join(
                self.downloads_folder,
                f"{self.year_month}-vendas.xlsx"
            )
            
            if not os.path.exists(appointments_file):
                logger.error(f"Arquivo de agendamentos não encontrado: {appointments_file}")
                return False
            
            if not os.path.exists(sales_file):
                logger.error(f"Arquivo de vendas não encontrado: {sales_file}")
                return False
            
            logger.info(f"Carregando arquivo de agendamentos: {appointments_file}")
            self.appointments_df = pd.read_excel(appointments_file)
            
            logger.info(f"Carregando arquivo de vendas: {sales_file}")
            self.sales_df = pd.read_excel(sales_file)
            
            # Renomeia a coluna "Produto/serviço" para "procedimento" para facilitar o código
            if 'Produto/serviço' in self.sales_df.columns:
                self.sales_df.rename(columns={'Produto/serviço': 'procedimento'}, inplace=True)
            
            # Inicializa o validador
            self.validator = CastrationValidator(self.appointments_df, self.sales_df)
            
            logger.info(f"Dados carregados: {len(self.appointments_df)} agendamentos, {len(self.sales_df)} vendas")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao carregar dados: {e}")
            return False
    
    def _count_sales(self, pattern: str) -> int:
        """
        Conta quantas vendas correspondem ao padrão especificado.
        
        Args:
            pattern: String exata a ser procurada
        
        Returns:
            Número de ocorrências
        """
        return len(self.sales_df[
            self.sales_df['procedimento'].str.contains(pattern, case=False, na=False, regex=False)
        ])
    
    def _build_sales_patterns(self, castration_type_key: str) -> Dict[str, str]:
        """
        Constrói os padrões de venda para um tipo de castração.
        
        Args:
            castration_type_key: Chave do tipo de castração (ex: 'ong', 'solidaria')
        
        Returns:
            Dicionário com os padrões de venda para cada categoria
        """
        config = self.CASTRATION_TYPES[castration_type_key]
        sales_prefix = config['sales_prefix']
        
        patterns = {}
        for category_key, category_label in self.CATEGORIES.items():
            patterns[category_key] = f"{sales_prefix} - {category_label}"
        
        return patterns
    
    def _process_castration_type(self, castration_type_key: str):
        """
        Processa um tipo específico de castração.
        
        Args:
            castration_type_key: Chave do tipo de castração (ex: 'ong', 'solidaria')
        """
        config = self.CASTRATION_TYPES[castration_type_key]
        sales_patterns = self._build_sales_patterns(castration_type_key)
        
        # Conta vendas para cada categoria
        for category_key, pattern in sales_patterns.items():
            data_key = f"{castration_type_key}_{category_key}"
            self.data[data_key] = self._count_sales(pattern)
        
        # Valida com os agendamentos
        self.validator.validate_castration_type(
            config['name'],
            config['appointment_pattern'],
            sales_patterns
        )
    
    def process_castrations(self):
        """Processa os dados de castrações."""
        logger.info("Processando dados de castrações...")
        
        # Processa todos os tipos de castração de forma genérica
        for castration_type_key in self.CASTRATION_TYPES.keys():
            self._process_castration_type(castration_type_key)
        
        logger.info("Processamento de castrações concluído")
    
    def process_vaccines_and_tests(self):
        """Processa os dados de vacinas e testes."""
        logger.info("Processando dados de vacinas e testes...")
        
        # Inicializa e executa o processador de vacinas e testes
        self.vaccine_test_processor = VaccineTestProcessor(
            self.year_month,
            self.sales_df,  # Passa o DataFrame de vendas para verificar se é pago ou não
            self.downloads_folder
        )
        
        if not self.vaccine_test_processor.run():
            logger.warning("Falha ao processar vacinas e testes")
            return
        
        # Integra os dados processados
        vaccine_test_data = self.vaccine_test_processor.get_data()
        self.data.update(vaccine_test_data)
        
        logger.info("Integração de dados de vacinas e testes concluída")
    
    def create_formatted_file(self) -> bool:
        """
        Cria o arquivo formatado em XLSX.
        
        Returns:
            True se criou com sucesso, False caso contrário
        """
        try:
            output_file = os.path.join(
                self.downloads_folder,
                f"{self.year_month}-formatado.xlsx"
            )
            
            logger.info(f"Criando arquivo formatado: {output_file}")
            
            # Cria o workbook
            wb = Workbook()
            ws = wb.active
            ws.title = f"Relatório {self.year_month}"
            
            # Estilos
            header_font = Font(bold=True, size=12)
            indent_font = Font(size=11)
            header_fill = PatternFill(start_color="CCE5FF", end_color="CCE5FF", fill_type="solid")
            
            # Cabeçalho
            ws['A1'] = "Item"
            ws['B1'] = "Valor"
            ws['A1'].font = header_font
            ws['B1'].font = header_font
            ws['A1'].fill = header_fill
            ws['B1'].fill = header_fill
            
            # Preenche os dados
            row = 2
            current_parent = None  # Rastreia o contexto do item pai atual
            
            # Lista de títulos gerais que não têm valores (apenas cabeçalhos)
            header_only_titles = [
                "Castrações Solidárias*", "Castrações Externas Pagas",
                "Total de Castrações", "Custo total das castrações realizadas",
                "Castrações - preço de custo - valor unitário",
                "Castrações externas pagas - valor unitário",
                "Valor arrecadado com as castrações"
            ]
            
            # Lista de contextos que devem ser definidos como parent
            parent_contexts = [
                "Vacinas e Testes Internos", "Vacinas e Testes Externos"
            ]
            
            # Lista de todos os tipos de castração (pais de categorias)
            castration_types = [config['report_label'] for config in self.CASTRATION_TYPES.values()]
            castration_types.extend(["Castrações - Solidária", "Castrações - Preço de Custo",
                                    "Castrações Paga Gato Externo", "Castrações LT Resgatante"])
            
            for item_name, indent_type in self.REPORT_STRUCTURE:
                ws[f'A{row}'] = item_name
                
                # Atualiza o contexto pai
                if item_name in parent_contexts:
                    # Títulos de seção de vacinas/testes
                    current_parent = item_name
                elif item_name in castration_types:
                    # Tipos de castração
                    current_parent = item_name
                elif indent_type is None and item_name not in header_only_titles:
                    # Outros itens sem indentação que podem ser contexto pai
                    current_parent = item_name
                
                # Aplica indentação
                if indent_type == "indent":
                    ws[f'A{row}'].alignment = Alignment(indent=2)
                elif indent_type == "indent2":
                    ws[f'A{row}'].alignment = Alignment(indent=4)
                
                # Preenche valores das castrações
                value = self._get_value_for_item(item_name, current_parent)
                if value is not None:
                    ws[f'B{row}'] = value
                
                row += 1
            
            # Ajusta largura das colunas
            ws.column_dimensions['A'].width = 50
            ws.column_dimensions['B'].width = 15
            
            # Salva o arquivo
            wb.save(output_file)
            logger.info(f"Arquivo formatado criado com sucesso: {output_file}")
            
            return True
            
        except Exception as e:
            logger.error(f"Erro ao criar arquivo formatado: {e}")
            return False
    
    def _get_value_for_item(self, item_name: str, parent_context: str = None) -> int:
        """
        Retorna o valor correspondente ao item do relatório.
        
        Args:
            item_name: Nome do item
            parent_context: Contexto do item pai (para identificar subitens)
        
        Returns:
            Valor numérico ou None se não houver valor
        """
        # ===== VALORES ARRECADADOS =====
        
        # Valor arrecadado com vacinas e testes pagos
        if item_name == "Valor arrecadado com as vacinas e testes pagos":
            return self.data.get('vaccine_test_revenue', 0.0)
        
        # ===== VACINAS E TESTES =====
        
        # Testes e Vacinas Internos
        if parent_context == "Vacinas e Testes Internos":
            vaccine_test_map = {
                "Teste FIV / FeLV": "test_fiv_felv_internal",
                "FeLV - V1": "vaccine_felv_v1_internal",
                "Vacinas Raiva": "vaccine_raiva_internal",
                "Vacinas V3": "vaccine_v3_internal",
                "Vacinas V4": "vaccine_v4_internal",
                "Vacinas V5": "vaccine_v5_internal"
            }
            if item_name in vaccine_test_map:
                return self.data.get(vaccine_test_map[item_name], 0)
        
        # Testes e Vacinas Externos
        if parent_context == "Vacinas e Testes Externos":
            vaccine_test_map = {
                "Teste FIV / FeLV": "test_fiv_felv_external",
                "FeLV - V1": "vaccine_felv_v1_external",
                "Vacinas Raiva": "vaccine_raiva_external",
                "Vacinas V3": "vaccine_v3_external",
                "Vacinas V4": "vaccine_v4_external",
                "Vacinas V5": "vaccine_v5_external"
            }
            if item_name in vaccine_test_map:
                return self.data.get(vaccine_test_map[item_name], 0)
        
        # ===== CASTRAÇÕES =====
        
        # Mapeia o label do relatório para o tipo de castração
        report_label_to_key = {
            config['report_label']: key 
            for key, config in self.CASTRATION_TYPES.items()
        }
        
        # Se o item é um título de castração, retorna o total
        if item_name in report_label_to_key:
            castration_key = report_label_to_key[item_name]
            total = 0
            for category_key in self.CATEGORIES.keys():
                data_key = f"{castration_key}_{category_key}"
                total += self.data.get(data_key, 0)
            return total if total > 0 else 0
        
        # Verifica se é um subtipo de castração (Solidária, Preço de Custo, etc)
        subtypes = {
            "Castrações - Solidária": "solidaria",
            "Castrações - Preço de Custo": "preco_custo",
            "Castrações Paga Gato Externo": "gato_externo",
            "Castrações LT Resgatante": "lt_resgatante"
        }
        
        if item_name in subtypes:
            castration_key = subtypes[item_name]
            total = 0
            for category_key in self.CATEGORIES.keys():
                data_key = f"{castration_key}_{category_key}"
                total += self.data.get(data_key, 0)
            return total if total > 0 else 0
        
        # Verifica se é um título agrupador que soma seus filhos
        if item_name == "Castrações Solidárias*":
            # Soma: Solidária + Preço de Custo
            total = 0
            for castration_key in ["solidaria", "preco_custo"]:
                for category_key in self.CATEGORIES.keys():
                    data_key = f"{castration_key}_{category_key}"
                    total += self.data.get(data_key, 0)
            return total if total > 0 else 0
        
        if item_name == "Castrações Externas Pagas":
            # Soma: Gato Externo + LT Resgatante
            total = 0
            for castration_key in ["gato_externo", "lt_resgatante"]:
                for category_key in self.CATEGORIES.keys():
                    data_key = f"{castration_key}_{category_key}"
                    total += self.data.get(data_key, 0)
            return total if total > 0 else 0
        
        # Verifica se é "Castrações agendadas" - conta todos os agendamentos de castração
        if item_name == "Castrações agendadas":
            # Filtra apenas os agendamentos que são de castração (contém "Castração" no tipo)
            castracoes = self.appointments_df[
                self.appointments_df['tipo_atendimento'].str.contains('Castração', case=False, na=False, regex=False)
            ]
            return len(castracoes)
        
        # Verifica se é "Castrações realizadas/atendimentos" - conta só os atendidos
        if item_name == "Castrações realizadas/atendimentos":
            castracoes = self.appointments_df[
                (self.appointments_df['tipo_atendimento'].str.contains('Castração', case=False, na=False, regex=False)) &
                (self.appointments_df['status'].str.contains('Atendido', case=False, na=False, regex=False))
            ]
            return len(castracoes)
        
        # Verifica se é "Castrações canceladas" - conta só os cancelados
        if item_name == "Castrações canceladas":
            castracoes = self.appointments_df[
                (self.appointments_df['tipo_atendimento'].str.contains('Castração', case=False, na=False, regex=False)) &
                (self.appointments_df['status'].str.contains('Cancelado', case=False, na=False, regex=False))
            ]
            return len(castracoes)
        
        # Se não tem contexto pai, não há valor para retornar
        if not parent_context:
            return None
        
        # Verifica se o contexto pai é um tipo de castração conhecido
        if parent_context not in report_label_to_key and parent_context not in subtypes:
            return None
        
        # Obtém a chave do tipo de castração
        if parent_context in report_label_to_key:
            castration_key = report_label_to_key[parent_context]
        else:
            castration_key = subtypes[parent_context]
        
        # Mapeia o nome do item para a categoria
        category_label_to_key = {
            label: key 
            for key, label in self.CATEGORIES.items()
        }
        
        # Verifica se o item é uma categoria conhecida
        if item_name not in category_label_to_key:
            return None
        
        category_key = category_label_to_key[item_name]
        
        # Constrói a chave de dados e retorna o valor
        data_key = f"{castration_key}_{category_key}"
        return self.data.get(data_key, 0)
    
    def run(self) -> bool:
        """
        Executa o processo completo de formatação.
        
        Returns:
            True se executou com sucesso, False caso contrário
        """
        logger.info("="*60)
        logger.info("Iniciando formatação de dados")
        logger.info("="*60)
        
        # Carrega os dados
        if not self.load_data():
            logger.error("Falha ao carregar dados")
            return False
        
        # Processa castrações
        self.process_castrations()
        
        # Processa vacinas e testes
        self.process_vaccines_and_tests()
        
        # Cria o arquivo formatado
        if not self.create_formatted_file():
            logger.error("Falha ao criar arquivo formatado")
            return False
        
        # Exibe resumo das validações
        print(self.validator.get_summary())
        
        logger.info("="*60)
        logger.info("Formatação concluída com sucesso!")
        logger.info("="*60)
        
        return True


def format_data(year_month: str, downloads_folder: str = "downloads") -> bool:
    """
    Função principal para formatar os dados.
    
    Args:
        year_month: String no formato YYYYMM (ex: 202509)
        downloads_folder: Pasta onde estão os arquivos XLSX
    
    Returns:
        True se formatou com sucesso, False caso contrário
    """
    formatter = CatlandFormatter(year_month, downloads_folder)
    return formatter.run()
