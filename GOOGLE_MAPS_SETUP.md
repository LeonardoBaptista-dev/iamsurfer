# 🗺️ Como Configurar o Google Maps Interativo

## 📋 Resumo

Este guia explica como configurar o Google Maps API para ter um mapa interativo completo onde você pode:
- ✅ Visualizar spots em um mapa real do Google
- ✅ Clicar no mapa para adicionar novos spots
- ✅ Usar busca com autocomplete do Google Places
- ✅ Ver spots próximos à sua localização

## 🔑 Passo 1: Obter Chave da API do Google Maps

### 1.1. Acesse o Google Cloud Console
- Vá para: https://console.cloud.google.com/
- Faça login com sua conta Google

### 1.2. Crie ou selecione um projeto
- Clique em "Selecionar projeto" no topo
- Clique em "Novo projeto" ou selecione um existente

### 1.3. Ative as APIs necessárias
No painel de APIs, ative:
- **Maps JavaScript API** (obrigatório)
- **Places API** (para busca)
- **Geocoding API** (para conversão de endereços)

### 1.4. Crie uma chave de API
- Vá em "Credenciais" no menu lateral
- Clique em "Criar credenciais" > "Chave de API"
- Copie a chave gerada

### 1.5. Configure restrições (recomendado)
- Restrinja por domínio: `localhost:5000`, seu domínio de produção
- Restrinja APIs: apenas as APIs listadas acima

## 🛠️ Passo 2: Configurar no Sistema

### Opção A: Variável de Ambiente (Recomendado)
```bash
# Windows (PowerShell)
$env:GOOGLE_MAPS_API_KEY="sua_chave_aqui"

# Linux/Mac
export GOOGLE_MAPS_API_KEY="sua_chave_aqui"
```

### Opção B: Arquivo de Configuração
Edite `google_maps_config.py`:
```python
GOOGLE_MAPS_API_KEY = "sua_chave_aqui"
```

### Opção C: Direto no Template
Edite `templates/spots/map_interactive.html`, linha final:
```html
<script async defer 
    src="https://maps.googleapis.com/maps/api/js?key=SUA_CHAVE_AQUI&libraries=places&callback=initMap">
```

## 🚀 Passo 3: Testar o Sistema

1. **Inicie a aplicação**
   ```bash
   python app.py
   ```

2. **Acesse o mapa**
   - URL: http://localhost:5000/spots/map
   - Você deve ver um mapa do Google real

3. **Teste as funcionalidades**:
   - ✅ Visualização dos spots existentes
   - ✅ Busca de localização (digite "São Paulo" por exemplo)
   - ✅ Botão "Obter Minha Localização"
   - ✅ Modo Adicionar (clique no botão verde, depois no mapa)

## 🎯 Funcionalidades Disponíveis

### 🗺️ **Mapa Interativo**
- Mapa real do Google Maps
- Marcadores azuis para spots aprovados
- InfoWindows com detalhes dos spots
- Controles de zoom e navegação

### 🔍 **Busca Inteligente**
- Autocomplete do Google Places
- Busca por cidade, praia, endereço
- Move o mapa automaticamente para o local

### 📍 **Localização do Usuário**
- Botão "Obter Minha Localização"
- Marcador vermelho para sua posição
- Lista de spots próximos ordenados por distância

### ➕ **Modo Adicionar Rápido**
- Botão verde "Modo Adicionar"
- Clique no mapa para escolher localização
- Modal com formulário rápido
- Submissão via AJAX (sem recarregar a página)

### 🎛️ **Filtros**
- Filtro por dificuldade
- Filtro por tipo de onda
- Contadores de spots (total vs. visíveis)

## 🔧 Troubleshooting

### Problema: "For development purposes only" no mapa
**Solução:** Configure restrições adequadas na sua chave de API

### Problema: Mapa não carrega
**Solução:** Verifique se:
- A chave de API está correta
- As APIs estão ativadas no Google Cloud
- Não há bloqueadores de anúncio interferindo

### Problema: Busca não funciona
**Solução:** Certifique-se de que a Places API está ativada

### Problema: Erro de quota
**Solução:** O Google oferece $200 gratuitos por mês. Configure alertas de billing.

## 💰 Custos

- **Gratuito:** $200 de crédito mensal do Google
- **Maps JavaScript API:** $7 por 1000 carregamentos
- **Places API:** $32 por 1000 consultas
- **Geocoding API:** $5 por 1000 consultas

Para um site pequeno/médio, o crédito gratuito é suficiente.

## 🔒 Segurança

- ✅ Use restrições de domínio
- ✅ Use variáveis de ambiente
- ✅ Monitore o uso da API
- ❌ Nunca exponha a chave em repositórios públicos

## 📚 Recursos Adicionais

- [Documentação Google Maps API](https://developers.google.com/maps/documentation)
- [Google Cloud Console](https://console.cloud.google.com/)
- [Preços do Google Maps](https://cloud.google.com/maps-platform/pricing)

---

**🎉 Depois de configurado, você terá um mapa profissional e interativo para seu sistema de spots!**
