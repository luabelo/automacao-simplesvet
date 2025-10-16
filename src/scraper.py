from datetime import datetime
from .config import Config
from .logger import logger
from .simplesvet_actions import SimplesVetActions


class SimplesVetScraper:
    """Classe principal para orquestrar o scraping do SimplesVet"""
    
    def __init__(self):
        self.config = None
        self.simplesvet = None
    
    def validate_configuration(self, config: Config) -> bool:
        """
        Valida se a configuração está correta antes de executar
        
        Args:
            config: Instância da configuração
            
        Returns:
            True se a configuração está válida
        """
        logger.info("Validando configuração...")

        if not config.validate_credentials():
            logger.error("❌ Credenciais não configuradas corretamente!")
            logger.error("   Por favor, edite o arquivo config/config.json e configure:")
            logger.error("   - email: Seu email de login do SimplesVet")
            logger.error("   - password: Sua senha do SimplesVet")
            return False
        
        start_date, end_date = config.get_date_range()
        if not start_date or not end_date:
            logger.error("❌ Período de datas não configurado!")
            logger.error("   Configure start_date e end_date no arquivo config/config.json")
            return False
        
        try:
            datetime.strptime(start_date, '%Y-%m-%d')
            datetime.strptime(end_date, '%Y-%m-%d')
        except ValueError:
            logger.error("❌ Formato de data inválido! Use o formato YYYY-MM-DD")
            return False
        
        logger.info("✅ Configuração válida!")
        logger.info(f"   Email: {config.get_credential('simplesvet', 'email')}")
        logger.info(f"   Período: {start_date} até {end_date}")
        
        return True
    
    def run(self) -> bool:
        """
        Executa o processo completo de scraping
        
        Returns:
            True se executado com sucesso
        """
        print("=" * 60)
        print("🏥 SIMPLESVET SCRAPER")
        print("=" * 60)
        print()
        
        try:
            # Carrega configuração
            logger.info("Carregando configurações...")
            self.config = Config()
            
            # Valida configuração
            if not self.validate_configuration(self.config):
                print("\n❌ Erro na configuração. Verifique o arquivo config/config.json")
                return False
            
            print("\n🚀 Iniciando automação...")
            
            # Inicializa as ações do SimplesVet
            self.simplesvet = SimplesVetActions(self.config)
            
            try:
                # Inicia o navegador
                logger.info("Iniciando navegador...")
                if not self.simplesvet.start_browser():
                    logger.error("❌ Falha ao iniciar o navegador")
                    return False
                
                print("✅ Navegador iniciado com sucesso")
                
                # Realiza login
                print("🔐 Realizando login...")
                if not self.simplesvet.login():
                    logger.error("❌ Falha no login")
                    print("❌ Falha no login. Verifique suas credenciais.")
                    return False
                
                print("✅ Login realizado com sucesso!")
                
                # Obtém período configurado
                start_date, end_date = self.config.get_date_range()
                
                # Extrai dados de atendimentos
                print(f"📋 Extraindo atendimentos de {start_date} até {end_date}...")
                appointments = self.simplesvet.get_appointments_data(start_date, end_date)
                
                if appointments:
                    print(f"✅ {len(appointments)} atendimentos extraídos com sucesso!")
                    logger.info(f"Dados extraídos: {len(appointments)} registros")
                else:
                    print("⚠️  Nenhum atendimento encontrado no período especificado")
                
                # Realiza logout
                print("🚪 Realizando logout...")
                self.simplesvet.logout()
                
            finally:
                # Fecha o navegador
                if self.simplesvet:
                    self.simplesvet.close_browser()
                    print("🔒 Navegador fechado")
            
            print("\n✅ Automação concluída com sucesso!")
            return True
            
        except KeyboardInterrupt:
            print("\n\n⏹️  Automação interrompida pelo usuário")
            logger.info("Automação interrompida pelo usuário")
            return False
            
        except Exception as e:
            logger.error(f"Erro inesperado: {e}")
            print(f"\n❌ Erro inesperado: {e}")
            return False