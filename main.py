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
from src.scraper import SimplesVetScraper

if __name__ == "__main__":
    scraper = SimplesVetScraper()
    success = scraper.run()
    print("\nPressione Enter para sair...")
    input()
    sys.exit(0 if success else 1)