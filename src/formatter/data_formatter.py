import os
import pandas as pd
from datetime import datetime
from typing import Dict, List, Tuple
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill
from ..scrapper.logger import setup_logger

logger = setup_logger(__name__)

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
                (self.appointments_df['tipo_atendimento'].str.contains(appointment_type, case=False, na=False)) &
                (self.appointments_df['status'].str.contains('Atendido', case=False, na=False))
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
        'femea_adulto': 'Fêmea / Adulto',
        'femea_filhote': 'Fêmea / Filhote',
        'macho_adulto': 'Macho / Adulto',
        'macho_filhote': 'Macho/ Filhote'  
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
        ("Fêmea / Adulto", "indent"),
        ("Fêmea / Filhote", "indent"),
        ("Macho/ Adulto", "indent"),
        ("Macho/ Filhote", "indent"),
        ("Castrações Lar Temporário", None),
        ("Fêmea / Adulto", "indent"),
        ("Fêmea / Filhote", "indent"),
        ("Macho/ Adulto", "indent"),
        ("Macho/ Filhote", "indent"),
        ("Castrações Solidárias*", None),
        ("Castrações - Solidária", "indent"),
        ("Fêmea / Adulto", "indent2"),
        ("Fêmea / Filhote", "indent2"),
        ("Macho/ Adulto", "indent2"),
        ("Macho/ Filhote", "indent2"),
        ("Castrações - Preço de Custo", "indent"),
        ("Fêmea / Adulto", "indent2"),
        ("Fêmea / Filhote", "indent2"),
        ("Macho/ Adulto", "indent2"),
        ("Macho/ Filhote", "indent2"),
        ("Castrações Externas Pagas", None),
        ("Castrações Paga Gato Externo", "indent"),
        ("Fêmea / Adulto", "indent2"),
        ("Fêmea / Filhote", "indent2"),
        ("Macho/ Adulto", "indent2"),
        ("Macho/ Filhote", "indent2"),
        ("Castrações LT Resgatante", "indent"),
        ("Fêmea / Adulto", "indent2"),
        ("Fêmea / Filhote", "indent2"),
        ("Macho/ Adulto", "indent2"),
        ("Macho/ Filhote", "indent2"),
        ("Total de Castrações", None),
        ("Castrações agendadas", "indent"),
        ("Castrações realizadas/atendimentos", "indent"),
        ("Castrações canceladas", "indent"),
        ("Custo total das castrações realizadas", None),
        ("Castrações - preço de custo - valor unitário", None),
        ("Castrações externas pagas - valor unitário", None),
        ("Valor arrecadado com as castrações", None),
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
            
            for item_name, indent_type in self.REPORT_STRUCTURE:
                ws[f'A{row}'] = item_name
                
                # Aplica indentação
                if indent_type == "indent":
                    ws[f'A{row}'].alignment = Alignment(indent=2)
                    current_parent = item_name  # Atualiza o contexto pai
                elif indent_type == "indent2":
                    ws[f'A{row}'].alignment = Alignment(indent=4)
                else:
                    # Se não tem indentação, pode ser um novo contexto pai
                    if item_name not in ["Vacinas e Testes Internos", "Vacinas e Testes Externos", 
                                         "Valor arrecadado com as vacinas e testes pagos",
                                         "Castrações Solidárias*", "Castrações Externas Pagas",
                                         "Total de Castrações", "Custo total das castrações realizadas",
                                         "Castrações - preço de custo - valor unitário",
                                         "Castrações externas pagas - valor unitário",
                                         "Valor arrecadado com as castrações"]:
                        current_parent = item_name
                
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
        # Se não tem contexto pai, não há valor para retornar
        if not parent_context:
            return None
        
        # Mapeia o contexto pai para o tipo de castração
        report_label_to_key = {
            config['report_label']: key 
            for key, config in self.CASTRATION_TYPES.items()
        }
        
        # Verifica se o contexto pai é um tipo de castração conhecido
        if parent_context not in report_label_to_key:
            return None
        
        castration_key = report_label_to_key[parent_context]
        
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
