import json
import os
from typing import Dict, Any, Optional
from pathlib import Path


class Config:
    def __init__(self, config_file: str = None):
        """
        Inicializa o gerenciador de configurações
        
        Args:
            config_file: Caminho para o arquivo de configuração
        """
        if config_file is None:
            config_file = os.path.join(
                Path(__file__).parent.parent, 'config', 'config.json'
            )
        
        self.config_file = config_file
        self._config_data = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """
        Carrega as configurações do arquivo JSON
        
        Returns:
            Dict contendo as configurações
        """
        try:
            with open(self.config_file, 'r', encoding='utf-8') as file:
                return json.load(file)
        except FileNotFoundError:
            raise FileNotFoundError(f"Arquivo de configuração não encontrado: {self.config_file}")
        except json.JSONDecodeError as e:
            raise ValueError(f"Erro ao parsear o arquivo de configuração: {e}")
    
    def get_config(self, section: str, key: str = None) -> Any:
        """
        Obtém uma configuração específica
        
        Args:
            section: Seção da configuração
            key: Chave específica (opcional)
            
        Returns:
            Valor da configuração
        """
        if section not in self._config_data:
            raise KeyError(f"Seção '{section}' não encontrada na configuração")
        
        if key is None:
            return self._config_data[section]
        
        if key not in self._config_data[section]:
            raise KeyError(f"Chave '{key}' não encontrada na seção '{section}'")
        
        return self._config_data[section][key]
    
    def get_credential(self, section: str, credential: str) -> Optional[str]:
        """
        Obtém uma credencial específica
        
        Args:
            section: Seção da configuração
            credential: Nome da credencial
            
        Returns:
            Valor da credencial ou None se não encontrada
        """
        try:
            credentials = self.get_config(section, 'credentials')
            value = credentials.get(credential)
            
            if value and value.upper() != f"SEU_{credential.upper()}_AQUI":
                return value
            
            return None
        except KeyError:
            return None
    
    def get_date_range(self, section: str = 'simplesvet') -> tuple:
        """
        Obtém o período de datas configurado
        
        Args:
            section: Seção da configuração
            
        Returns:
            Tupla com (data_inicio, data_fim)
        """
        try:
            date_range = self.get_config(section, 'date_range')
            return date_range['start_date'], date_range['end_date']
        except KeyError:
            return None, None
    
    def validate_credentials(self, section: str = 'simplesvet') -> bool:
        """
        Valida se as credenciais foram configuradas corretamente
        
        Args:
            section: Seção da configuração
            
        Returns:
            True se as credenciais estão válidas
        """
        email = self.get_credential(section, 'email')
        password = self.get_credential(section, 'password')
        
        if not email or not password:
            return False
        
        # Verifica se não são os valores padrão do template
        if email.upper() == "SEU_EMAIL_AQUI" or password.upper() == "SUA_SENHA_AQUI":
            return False
        
        return True
    
    def get_browser_config(self) -> Dict[str, Any]:
        """
        Obtém as configurações do navegador
        
        Returns:
            Dict com configurações do navegador
        """
        return self.get_config('browser')
    
    def get_logging_config(self) -> Dict[str, Any]:
        """
        Obtém as configurações de logging
        
        Returns:
            Dict com configurações de logging
        """
        return self.get_config('logging')