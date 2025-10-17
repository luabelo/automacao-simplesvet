import os
import re
from typing import List, Dict, Optional
import pandas as pd
import pdfplumber
from datetime import datetime
from .logger import logger


class PDFConverter:
    """Conversor de PDFs de agendamentos para Excel"""
    
    def __init__(self):
        pass
    
    def convert_pdf_to_excel(self, pdf_path: str, month_str: str = None) -> Optional[str]:
        """Converte PDF de agendamentos para Excel com dados estruturados"""
        logger.info(f"Iniciando conversão do PDF: {pdf_path}")
        
        if not os.path.exists(pdf_path):
            logger.error(f"Arquivo PDF não encontrado: {pdf_path}")
            return None
        
        try:
            # Extrai dados do PDF
            appointments_data = self._extract_appointments_from_pdf(pdf_path)
            
            if not appointments_data:
                logger.warning("Nenhum agendamento encontrado no PDF")
                return None
            
            # Converte para DataFrame
            df = pd.DataFrame(appointments_data)
            
            # Reordena as colunas para ficar mais organizado
            column_order = ['veterinario', 'cliente', 'animal', 'tipo_atendimento', 'data', 'hora', 'status']
            existing_columns = [col for col in column_order if col in df.columns]
            df = df[existing_columns]
            
            # Cria nome do arquivo Excel
            if month_str:
                # Remove extensão .pdf e adiciona .xlsx
                base_path = pdf_path.replace('.pdf', '')
                excel_path = f"{base_path}.xlsx"
            else:
                excel_path = pdf_path.replace('.pdf', '.xlsx')
            
            # Salva como Excel
            with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Agendamentos', index=False)
                
                # Ajusta largura das colunas
                worksheet = writer.sheets['Agendamentos']
                for column in worksheet.columns:
                    max_length = 0
                    column_letter = column[0].column_letter
                    for cell in column:
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(str(cell.value))
                        except:
                            pass
                    adjusted_width = min(max_length + 2, 50)
                    worksheet.column_dimensions[column_letter].width = adjusted_width
            
            logger.info(f"✅ Excel criado com sucesso: {excel_path}")
            logger.info(f"Total de agendamentos processados: {len(appointments_data)}")
            
            return excel_path
            
        except Exception as e:
            logger.error(f"Erro ao converter PDF para Excel: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    def _extract_appointments_from_pdf(self, pdf_path: str) -> List[Dict]:
        """Extrai dados de agendamentos do PDF"""
        appointments = []
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                logger.info(f"PDF aberto. Total de páginas: {len(pdf.pages)}")
                
                for page_num, page in enumerate(pdf.pages):
                    logger.info(f"Processando página {page_num + 1}...")
                    
                    # Extrai tabelas da página (método mais eficiente para PDFs estruturados)
                    tables = page.extract_tables()
                    
                    if tables:
                        logger.info(f"Encontradas {len(tables)} tabelas na página {page_num + 1}")
                        
                        # Extrai também o texto para pegar os nomes dos veterinários
                        text = page.extract_text()
                        veterinarios = self._extract_veterinario_names(text)
                        
                        vet_index = 0
                        for table_idx, table in enumerate(tables):
                            if not table or len(table) < 2:
                                continue
                            
                            # Pega o nome do veterinário correspondente
                            veterinario = veterinarios[vet_index] if vet_index < len(veterinarios) else ''
                            
                            # Processa a tabela
                            table_appointments = self._parse_simplesvet_table(table, veterinario)
                            appointments.extend(table_appointments)
                            
                            logger.info(f"Tabela {table_idx + 1}: {len(table_appointments)} agendamentos extraídos")
                            vet_index += 1
                    else:
                        logger.warning("Nenhuma tabela encontrada na página")
                    
                    logger.info(f"Total de agendamentos na página {page_num + 1}: {len(appointments)}")
        
        except Exception as e:
            logger.error(f"Erro ao processar PDF: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
        
        return appointments
    
    def _extract_veterinario_names(self, text: str) -> List[str]:
        """Extrai nomes dos veterinários do texto"""
        veterinarios = []
        lines = text.split('\n')
        
        for line in lines:
            line = line.strip()
            # Veterinários geralmente estão em linhas com fundo colorido, em maiúsculas
            if line.isupper() and len(line) > 5 and not any(x in line.lower() for x in ['cliente', 'animal', 'data', 'hora', 'status', 'agenda']):
                veterinarios.append(line)
        
        logger.info(f"Veterinários encontrados: {veterinarios}")
        return veterinarios
    
    def _parse_simplesvet_table(self, table: List[List], veterinario: str = '') -> List[Dict]:
        """Processa uma tabela do SimplesVet e extrai agendamentos"""
        appointments = []
        
        try:
            if not table or len(table) < 2:
                return appointments
            
            # Procura pela linha de cabeçalho real (contém "Cliente", "Animal", etc)
            header_row_idx = None
            headers = None
            
            for idx, row in enumerate(table):
                if row and any(cell and 'cliente' in str(cell).lower() for cell in row):
                    header_row_idx = idx
                    headers = row
                    break
            
            if header_row_idx is None or headers is None:
                logger.warning(f"Cabeçalho não encontrado na tabela. Primeira linha: {table[0] if table else 'vazio'}")
                return appointments
            
            logger.info(f"Cabeçalhos encontrados na linha {header_row_idx}: {headers}")
            
            # Identifica índices das colunas baseado no cabeçalho
            col_indices = {}
            for idx, header in enumerate(headers):
                if not header:
                    continue
                header_lower = str(header).strip().lower()
                
                if 'cliente' in header_lower:
                    col_indices['cliente'] = idx
                elif 'animal' in header_lower:
                    col_indices['animal'] = idx
                elif 'tipo' in header_lower or 'atendimento' in header_lower:
                    col_indices['tipo_atendimento'] = idx
                elif 'data' in header_lower:
                    col_indices['data'] = idx
                elif 'hora' in header_lower:
                    col_indices['hora'] = idx
                elif 'status' in header_lower:
                    col_indices['status'] = idx
            
            logger.info(f"Mapeamento de colunas: {col_indices}")
            
            # Processa cada linha de dados (após o cabeçalho)
            for row_idx, row in enumerate(table[header_row_idx + 1:], start=header_row_idx + 1):
                if not row or all(not cell or str(cell).strip() == '' for cell in row):
                    continue
                
                # Pula linhas que são observações (ex: "Paga na hora", "Vacinação", etc)
                first_cell = str(row[0]).strip() if row and row[0] else ''
                if any(x in first_cell.lower() for x in [
                    'paga na hora', 
                    'valor normal',
                    'valor',
                    'observ',
                    'v4', 
                    'v5',
                    'queixa:',
                    'contato de quem',
                    'endereço completo',
                    'sem custo',
                    '2° dose',
                    'dose v'
                ]):
                    continue
                
                # Extrai dados usando os índices identificados
                appointment = {
                    'veterinario': veterinario,
                    'cliente': self._get_cell_value(row, col_indices.get('cliente')),
                    'animal': self._get_cell_value(row, col_indices.get('animal')),
                    'tipo_atendimento': self._get_cell_value(row, col_indices.get('tipo_atendimento')),
                    'data': self._get_cell_value(row, col_indices.get('data')),
                    'hora': self._get_cell_value(row, col_indices.get('hora')),
                    'status': self._get_cell_value(row, col_indices.get('status'))
                }
                
                # Validação: só adiciona se tiver data válida (formato DD/MM/YYYY)
                # Isso filtra linhas de observação que não têm data
                if not self._is_valid_date(appointment['data']):
                    logger.debug(f"Linha ignorada (sem data válida): {first_cell[:50]}")
                    continue
                
                # Só adiciona se tiver pelo menos cliente ou animal
                if appointment['cliente'] or appointment['animal']:
                    appointments.append(appointment)
                    logger.debug(f"Agendamento extraído: {appointment}")
        
        except Exception as e:
            logger.error(f"Erro ao processar tabela: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
        
        return appointments
    
    def _get_cell_value(self, row: List, col_index: Optional[int]) -> str:
        """Obtém valor de uma célula com segurança"""
        if col_index is None or col_index >= len(row):
            return ''
        
        value = row[col_index]
        if value is None:
            return ''
        
        return str(value).strip()
    
    def _is_valid_date(self, date_str: str) -> bool:
        """Verifica se a string é uma data válida no formato DD/MM/YYYY"""
        if not date_str or date_str.strip() == '':
            return False
        
        # Verifica se tem o formato DD/MM/YYYY
        import re
        date_pattern = r'^\d{2}/\d{2}/\d{4}$'
        if not re.match(date_pattern, date_str):
            return False
        
        # Tenta parsear a data para ver se é válida
        try:
            datetime.strptime(date_str, '%d/%m/%Y')
            return True
        except:
            return False
