#!/usr/bin/env python3
"""
SimplesVet Scraper - Executável Principal

Antes de executar:
1. Configure suas credenciais no arquivo config/config.json
2. Instale as dependências: pip install -r requirements.txt
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
from src.scraper.scraper import SimplesVetScraper
from src.scraper.config import Config
from src.formatter import format_data
from src.scraper.logger import logger

if __name__ == "__main__":
    scraper = SimplesVetScraper()
    success = scraper.run()
    
    # Se o scraping foi bem-sucedido, executa a formatação
    if success:
        print("\n" + "="*60)
        print("📊 FORMATAÇÃO DE DADOS")
        print("="*60)
        
        try:
            # Carrega a configuração para obter os meses
            config = Config()
            months = config.get_months()
            
            # Formata os dados para cada mês processado
            for month_str in months:
                print(f"\n📝 Formatando dados do mês {month_str}...")
                formatter_success = format_data(month_str, "downloads")
                
                if not formatter_success:
                    print(f"⚠️  Erro ao formatar dados do mês {month_str}")
                    logger.warning(f"Erro ao formatar dados do mês {month_str}")
            
            print("\n" + "="*60)
            print("✅ Processo completo finalizado!")
            print("="*60)
            
        except Exception as e:
            print(f"\n❌ Erro durante a formatação: {e}")
            logger.error(f"Erro durante a formatação: {e}")
            success = False
    
    print("\nPressione Enter para sair...")
    input()
    sys.exit(0 if success else 1)
