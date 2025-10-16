# Automação SimplesVet

Automação para extração de dados do sistema SimplesVet usando Python e Selenium.

Este sistema automatiza o login no SimplesVet, acessa a agenda e faz download dos relatórios em PDF, convertendo-os para Excel com dados estruturados.

## 🚀 Instalação e Configuração

### 1. Instalar Dependências

```bash
pip install -r requirements.txt
```

### 2. Configurar Credenciais

⚠️ **IMPORTANTE**: Configure suas credenciais antes de executar o sistema.

1. Copie o arquivo template:
   ```bash
   cp config/config.json.template config/config.json
   ```

2. Edite o arquivo `config/config.json` e substitua:
   - `SEU_EMAIL_AQUI` pelo seu email do SimplesVet
   - `SUA_SENHA_AQUI` pela sua senha do SimplesVet
   - Configure as datas de início e fim conforme necessário

**Exemplo:**
```json
{
  "simplesvet": {
    "credentials": {
      "email": "meu.email@gmail.com",
      "password": "minha.senha"
    },
    "date_range": {
      "start_date": "2025-10-01",
      "end_date": "2025-10-31"
    }
  }
}
```

### 3. Executar

```bash
python main.py
```

## 📁 Arquivos Gerados

O sistema gera os seguintes arquivos na pasta `downloads/`:

- **PDF**: Relatório original baixado do SimplesVet
- **Excel**: Dados estruturados extraídos do PDF com:
  - Nome da veterinária
  - Nome do cliente  
  - Nome do animal
  - Tipo de atendimento
  - Data e hora
  - Status do atendimento
