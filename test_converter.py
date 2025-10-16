"""Script para testar apenas a conversão do PDF para Excel"""

from src.pdf_converter import PDFConverter
from src.logger import logger

def test_conversion():
    pdf_path = r"downloads\202510-agendamentos.pdf"
    month_str = "202510"
    
    converter = PDFConverter()
    
    print("🧪 Testando conversão do PDF para Excel...")
    print(f"PDF: {pdf_path}")
    print()
    
    excel_path = converter.convert_pdf_to_excel(pdf_path, month_str)
    
    if excel_path:
        print(f"\n✅ Excel criado com sucesso: {excel_path}")
        
        # Mostra os dados extraídos
        import pandas as pd
        df = pd.read_excel(excel_path)
        print(f"\n📊 Total de linhas: {len(df)}")
        print(f"📋 Colunas: {list(df.columns)}")
        print("\n🔍 Dados:")
        print(df.to_string())
    else:
        print("\n❌ Falha na conversão")

if __name__ == "__main__":
    test_conversion()
    print("\nPressione Enter para sair...")
    input()
