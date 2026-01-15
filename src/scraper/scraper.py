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
        
        months = config.get_months()
        if not months or len(months) == 0:
            logger.error("❌ Lista de meses não configurada!")
            logger.error("   Configure a lista 'months' no arquivo config/config.json")
            logger.error("   Exemplo: \"months\": [\"202509\", \"202510\"]")
            return False
        
        # Valida cada mês
        for month_str in months:
            try:
                config.get_date_range_from_month(month_str)
            except ValueError as e:
                logger.error(f"❌ {e}")
                return False
        
        logger.info("✅ Configuração válida!")
        logger.info(f"   Email: {config.get_credential('simplesvet', 'email')}")
        logger.info(f"   Meses para processar: {', '.join(months)}")
        
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
                
                # Obtém lista de meses configurados
                months = self.config.get_months()
                
                # Processa cada mês individualmente
                for month_str in months:
                    try:
                        # Converte mês em range de datas
                        start_date, end_date = self.config.get_date_range_from_month(month_str)
                        
                        # Extrai dados de atendimentos para o mês
                        print(f"\n📋 Processando mês {month_str} ({start_date} até {end_date})...")
                        appointments = self.simplesvet.get_appointments_data(
                            start_date, end_date, month_str
                        )
                        
                        if appointments:
                            # Calcula o total de agendamentos extraídos
                            total_appointments = sum(item.get('appointments_count', 0) for item in appointments)
                            print(f"✅ {total_appointments} agendamentos extraídos para {month_str}!")
                            logger.info(f"Dados extraídos para {month_str}: {total_appointments} agendamentos em {len(appointments)} arquivo(s)")
                        else:
                            print(f"⚠️  Nenhum atendimento encontrado para {month_str}")
                        
                        # Extrai dados de vendas para o mês
                        print(f"\n💰 Processando vendas de {month_str}...")
                        vendas = self.simplesvet.get_vendas_data(
                            start_date, end_date, month_str
                        )
                        
                        if vendas:
                            print(f"✅ Vendas extraídas e salvas em: {vendas[0]}")
                            logger.info(f"Vendas extraídas para {month_str}: {vendas[0]}")
                        else:
                            print(f"⚠️  Nenhuma venda encontrada para {month_str}")
                        
                        # Extrai dados de procedimentos (vacinas e exames) para o mês
                        print(f"\n💉 Processando procedimentos de {month_str}...")
                        procedures = self.simplesvet.get_procedures_data(
                            start_date, end_date, month_str
                        )
                        
                        if procedures:
                            if procedures.get('vacinas'):
                                print(f"✅ Vacinas extraídas: {procedures['vacinas']}")
                            else:
                                print(f"⚠️  Nenhuma vacina encontrada para {month_str}")
                            
                            if procedures.get('exames'):
                                print(f"✅ Exames extraídos: {procedures['exames']}")
                            else:
                                print(f"⚠️  Nenhum exame encontrado para {month_str}")
                        else:
                            print(f"⚠️  Nenhum procedimento encontrado para {month_str}")
                    
                    except Exception as e:
                        logger.error(f"Erro ao processar mês {month_str}: {e}")
                        print(f"❌ Erro ao processar mês {month_str}: {e}")
                
                # Não realiza logout, apenas fecha o navegador no final
                
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