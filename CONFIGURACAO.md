# Configuração do SimplesVet Scraper

## ⚠️ IMPORTANTE - Configuração de Credenciais

Para usar este projeto, você precisa configurar suas credenciais do SimplesVet.

### Passos para configuração:

1. **Copie o arquivo template:**
   ```bash
   cp config/config.json.template config/config.json
   ```

2. **Edite o arquivo `config/config.json`** e substitua:
   - `SEU_EMAIL_AQUI@gmail.com` pelo seu email de login do SimplesVet
   - `SUA_SENHA_AQUI` pela sua senha do SimplesVet

3. **Configure o período de datas** (opcional):
   - `start_date`: Data de início no formato YYYY-MM-DD
   - `end_date`: Data de fim no formato YYYY-MM-DD

### Exemplo de configuração:

```json
{
  "simplesvet": {
    "credentials": {
      "email": "meu.email@gmail.com",
      "password": "minha.senha.super.secreta"
    },
    "date_range": {
      "start_date": "2025-10-01",
      "end_date": "2025-10-31"
    }
  }
}
```

### ⚠️ Segurança

- **NUNCA** faça commit do arquivo `config/config.json` com suas credenciais reais
- O arquivo `config/config.json` está no `.gitignore` para proteger suas credenciais
- Use apenas o template (`config.json.template`) para compartilhar a estrutura

### Configurações adicionais:

- **Browser**: Tipo de navegador (chrome/firefox)
- **Headless**: `true` para execução sem interface gráfica, `false` para ver o navegador
- **Wait timeout**: Tempo limite para esperar elementos carregarem (em segundos)

### Exemplo completo:

```json
{
  "simplesvet": {
    "urls": {
      "login": "https://app.simples.vet/login/login.php",
      "agenda": "https://app.simples.vet/agenda/index.php"
    },
    "credentials": {
      "email": "meu.email@veterinaria.com",
      "password": "MinhaSenh@Segur@123"
    },
    "date_range": {
      "start_date": "2025-01-01",
      "end_date": "2025-12-31"
    }
  },
  "browser": {
    "type": "chrome",
    "headless": false,
    "wait_timeout": 10
  },
  "logging": {
    "level": "INFO",
    "file_enabled": true
  }
}
```