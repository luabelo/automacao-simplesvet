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
            return None
    
    def _extract_appointments_from_pdf(self, pdf_path: str) -> List[Dict]:
        """Extrai dados de agendamentos do PDF"""
        appointments = []
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                logger.info(f"PDF aberto. Total de páginas: {len(pdf.pages)}")
                
                for page_num, page in enumerate(pdf.pages):
                    logger.info(f"Processando página {page_num + 1}...")
                    
                    # Extrai texto da página
                    text = page.extract_text()
                    if not text:
                        continue
                    
                    # Tenta extrair dados usando diferentes padrões
                    page_appointments = self._parse_appointments_from_text(text)
                    appointments.extend(page_appointments)
                    
                    logger.info(f"Encontrados {len(page_appointments)} agendamentos na página {page_num + 1}")
        
        except Exception as e:
            logger.error(f"Erro ao processar PDF: {str(e)}")
        
        return appointments
    
    def _parse_appointments_from_text(self, text: str) -> List[Dict]:
        """Analisa texto e extrai informações de agendamentos"""
        appointments = []
        
        try:
            # Remove quebras de linha excessivas e normaliza espaços
            text = re.sub(r'\n+', '\n', text)
            text = re.sub(r'\s+', ' ', text)
            
            lines = text.split('\n')
            
            # Procura por padrões de agendamentos
            for i, line in enumerate(lines):
                line = line.strip()
                if not line:
                    continue
                
                # Tenta identificar linhas que contêm agendamentos
                appointment = self._extract_appointment_from_line(line, lines[i:i+5])
                if appointment:
                    appointments.append(appointment)
        
        except Exception as e:
            logger.error(f"Erro ao analisar texto: {str(e)}")
        
        return appointments
    
    def _extract_appointment_from_line(self, main_line: str, context_lines: List[str]) -> Optional[Dict]:
        """Extrai dados de agendamento de uma linha e contexto"""
        try:
            # Padrões para identificar agendamentos
            # Adapte estes padrões conforme o formato real do seu PDF
            
            # Padrão para data (DD/MM/YYYY ou DD-MM-YYYY)
            date_pattern = r'(\d{1,2}[/-]\d{1,2}[/-]\d{4})'
            
            # Padrão para hora (HH:MM)
            time_pattern = r'(\d{1,2}:\d{2})'
            
            # Junta todas as linhas do contexto para análise
            full_text = ' '.join(context_lines)
            
            # Busca por data
            date_match = re.search(date_pattern, full_text)
            
            # Busca por hora
            time_match = re.search(time_pattern, full_text)
            
            # Se encontrou data, considera como um possível agendamento
            if date_match:
                appointment = {
                    'veterinaria': self._extract_veterinaria(full_text),
                    'cliente': self._extract_cliente(full_text),
                    'animal': self._extract_animal(full_text),
                    'tipo_atendimento': self._extract_tipo_atendimento(full_text),
                    'data': date_match.group(1) if date_match else '',
                    'hora': time_match.group(1) if time_match else '',
                    'status': self._extract_status(full_text),
                    'texto_original': full_text[:200] + '...' if len(full_text) > 200 else full_text
                }
                
                # Só retorna se tiver informações mínimas
                if appointment['data'] or appointment['cliente'] or appointment['animal']:
                    return appointment
        
        except Exception as e:
            logger.debug(f"Erro ao processar linha: {str(e)}")
        
        return None
    
    def _extract_veterinaria(self, text: str) -> str:
        """Extrai nome da veterinária"""
        # Padrões comuns para identificar nome da veterinária
        patterns = [
            r'Veterinária\s*:?\s*([^,\n]+)',
            r'Clínica\s*:?\s*([^,\n]+)',
            r'Hospital\s*:?\s*([^,\n]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return ''
    
    def _extract_cliente(self, text: str) -> str:
        """Extrai nome do cliente"""
        patterns = [
            r'Cliente\s*:?\s*([^,\n]+)',
            r'Proprietário\s*:?\s*([^,\n]+)',
            r'Tutor\s*:?\s*([^,\n]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return ''
    
    def _extract_animal(self, text: str) -> str:
        """Extrai nome do animal"""
        patterns = [
            r'Animal\s*:?\s*([^,\n]+)',
            r'Pet\s*:?\s*([^,\n]+)',
            r'Paciente\s*:?\s*([^,\n]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return ''
    
    def _extract_tipo_atendimento(self, text: str) -> str:
        """Extrai tipo de atendimento"""
        patterns = [
            r'Tipo\s*:?\s*([^,\n]+)',
            r'Atendimento\s*:?\s*([^,\n]+)',
            r'Serviço\s*:?\s*([^,\n]+)',
            r'Consulta\s*:?\s*([^,\n]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        # Palavras-chave comuns para tipos de atendimento
        keywords = ['consulta', 'cirurgia', 'vacina', 'exame', 'retorno', 'emergência']
        for keyword in keywords:
            if re.search(r'\b' + keyword + r'\b', text, re.IGNORECASE):
                return keyword.title()
        
        return ''
    
    def _extract_status(self, text: str) -> str:
        """Extrai status do agendamento"""
        patterns = [
            r'Status\s*:?\s*([^,\n]+)',
            r'Situação\s*:?\s*([^,\n]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        # Palavras-chave comuns para status
        status_keywords = ['agendado', 'confirmado', 'realizado', 'cancelado', 'pendente']
        for status in status_keywords:
            if re.search(r'\b' + status + r'\b', text, re.IGNORECASE):
                return status.title()
        
        return 'Não informado'