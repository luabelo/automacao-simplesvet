import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional


class Logger:
    def __init__(self, name: str = "SimplesVetScraper", level: str = "INFO", file_enabled: bool = True):
        """
        Inicializa o sistema de logging
        
        Args:
            name: Nome do logger
            level: Nível de logging (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            file_enabled: Se deve salvar logs em arquivo
        """
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, level.upper()))
        
        # Remove handlers existentes para evitar duplicação
        self.logger.handlers.clear()
        
        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
        
        # File handler (se habilitado)
        if file_enabled:
            self._setup_file_handler(formatter)
    
    def _setup_file_handler(self, formatter: logging.Formatter):
        """
        Configura o handler de arquivo
        
        Args:
            formatter: Formatter para os logs
        """
        try:
            # Diretório de logs (agora em scrapper, precisa subir 2 níveis)
            log_dir = Path(__file__).parent.parent.parent / 'logs'
            log_dir.mkdir(exist_ok=True)
            
            # Nome do arquivo com timestamp
            timestamp = datetime.now().strftime('%Y%m%d')
            log_file = log_dir / f'simplesvet_scraper_{timestamp}.log'
            
            # File handler com rotação por tamanho
            from logging.handlers import RotatingFileHandler
            file_handler = RotatingFileHandler(
                log_file,
                maxBytes=10*1024*1024,  # 10MB
                backupCount=5,
                encoding='utf-8'
            )
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)
            
        except Exception as e:
            self.logger.warning(f"Não foi possível configurar log em arquivo: {e}")
    
    def debug(self, message: str):
        """Log de debug"""
        self.logger.debug(message)
    
    def info(self, message: str):
        """Log de informação"""
        self.logger.info(message)
    
    def warning(self, message: str):
        """Log de aviso"""
        self.logger.warning(message)
    
    def error(self, message: str):
        """Log de erro"""
        self.logger.error(message)
    
    def critical(self, message: str):
        """Log crítico"""
        self.logger.critical(message)


# Instância global do logger
logger = Logger()