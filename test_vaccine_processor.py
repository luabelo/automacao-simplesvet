"""
Script de teste para o processador de vacinas e testes.
"""

from src.formatter.vaccine_test_processor import VaccineTestProcessor

def main():
    print("="*60)
    print("TESTE DO PROCESSADOR DE VACINAS E TESTES")
    print("="*60)
    
    # Cria o processador
    processor = VaccineTestProcessor("202509", "downloads")
    
    # Executa o processamento
    if processor.run():
        print("\n" + "="*60)
        print("DADOS PROCESSADOS")
        print("="*60)
        
        data = processor.get_data()
        
        print("\nVACINAS E TESTES INTERNOS:")
        print(f"  Teste FIV/FeLV: {data.get('test_fiv_felv_internal', 0)}")
        print(f"  FeLV - V1: {data.get('vaccine_felv_v1_internal', 0)}")
        print(f"  Vacinas Raiva: {data.get('vaccine_raiva_internal', 0)}")
        print(f"  Vacinas V3: {data.get('vaccine_v3_internal', 0)}")
        print(f"  Vacinas V4: {data.get('vaccine_v4_internal', 0)}")
        print(f"  Vacinas V5: {data.get('vaccine_v5_internal', 0)}")
        
        print("\nVACINAS E TESTES EXTERNOS:")
        print(f"  Teste FIV/FeLV: {data.get('test_fiv_felv_external', 0)}")
        print(f"  FeLV - V1: {data.get('vaccine_felv_v1_external', 0)}")
        print(f"  Vacinas Raiva: {data.get('vaccine_raiva_external', 0)}")
        print(f"  Vacinas V3: {data.get('vaccine_v3_external', 0)}")
        print(f"  Vacinas V4: {data.get('vaccine_v4_external', 0)}")
        print(f"  Vacinas V5: {data.get('vaccine_v5_external', 0)}")
        
        print("\n" + "="*60)
        print("TESTE CONCLUIDO COM SUCESSO!")
        print("="*60)
    else:
        print("\n" + "="*60)
        print("ERRO NO PROCESSAMENTO")
        print("="*60)

if __name__ == "__main__":
    main()
