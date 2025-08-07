# Configuração do Google Maps API
# 
# Para obter uma chave de API do Google Maps:
# 1. Acesse: https://console.cloud.google.com/
# 2. Crie um projeto ou selecione um existente
# 3. Ative as seguintes APIs:
#    - Maps JavaScript API
#    - Places API
#    - Geocoding API
# 4. Crie uma chave de API em "Credenciais"
# 5. Configure as restrições da chave para seu domínio
# 6. Substitua "YOUR_GOOGLE_MAPS_API_KEY" pela sua chave real

# Configuração para desenvolvimento local
GOOGLE_MAPS_API_KEY = "YOUR_GOOGLE_MAPS_API_KEY"

# APIs necessárias para o funcionamento completo:
# - Maps JavaScript API: Para exibir o mapa interativo
# - Places API: Para busca de localizações com autocomplete  
# - Geocoding API: Para converter endereços em coordenadas

# Exemplo de uso no template:
# <script async defer 
#     src="https://maps.googleapis.com/maps/api/js?key={{config.GOOGLE_MAPS_API_KEY}}&libraries=places&callback=initMap">
# </script>

# IMPORTANTE: 
# - Mantenha sua chave de API segura
# - Configure restrições adequadas no Console do Google Cloud
# - Para produção, use variáveis de ambiente
# - Monitore o uso da API para evitar custos inesperados

# Configuração de produção (recomendado):
# Use variáveis de ambiente:
# export GOOGLE_MAPS_API_KEY="sua_chave_aqui"
# 
# No Flask app:
# import os
# app.config['GOOGLE_MAPS_API_KEY'] = os.environ.get('GOOGLE_MAPS_API_KEY')
