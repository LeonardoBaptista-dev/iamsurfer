import json
import random
from datetime import datetime
import os
import logging
import re  # Adicionei a importação de re que estava faltando

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SurfForecast:
    def __init__(self):
        self.spots = {
            "matinhos": {"name": "Matinhos (Pico)", "location": "Paraná, Brasil", "windguru_id": "468811"},
            "campeche": {"name": "Campeche", "location": "Florianópolis, SC", "windguru_id": "49208"},
            "joaquina": {"name": "Joaquina", "location": "Florianópolis, SC", "windguru_id": "49194"},
            "praia-da-vila": {"name": "Praia da Vila", "location": "Imbituba, SC", "windguru_id": "49191"},
            "silveira": {"name": "Silveira", "location": "Garopaba, SC", "windguru_id": "49175"},
            "rosa-norte": {"name": "Rosa Norte", "location": "Imbituba, SC", "windguru_id": "49189"},
            "itamambuca": {"name": "Itamambuca", "location": "Ubatuba, SP", "windguru_id": "107"}
        }
        
        # Caminho para o arquivo de dados do Windguru
        self.windguru_data_file = "windguru_forecast.json"
        self.windguru_js_file = "windguru_js_data.json"
    
    def get_spot_forecast(self, spot_slug):
        """Obtém a previsão para um spot específico"""
        if spot_slug not in self.spots:
            logger.error(f"Spot não encontrado: {spot_slug}")
            return self._get_fallback_forecast()
        
        try:
            # Verificar se temos dados do Windguru
            windguru_data = self._load_windguru_data()
            
            if windguru_data:
                # Formatar os dados do Windguru para o nosso formato padrão
                forecast = self._format_windguru_data(windguru_data, spot_slug)
                return forecast
            else:
                logger.error("Dados do Windguru não encontrados")
                return self._get_fallback_forecast(spot_slug)
                
        except Exception as e:
            logger.error(f"Erro ao obter previsão para {spot_slug}: {e}")
            return self._get_fallback_forecast(spot_slug)
    
    def _load_windguru_data(self):
        """Carrega os dados do Windguru a partir do arquivo JSON"""
        try:
            # Verificar se o arquivo existe
            if not os.path.exists(self.windguru_data_file):
                logger.error(f"Arquivo de dados do Windguru não encontrado: {self.windguru_data_file}")
                return None
            
            # Carregar os dados do arquivo
            with open(self.windguru_data_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Tentar carregar dados JS também se disponíveis
            js_data = {}
            if os.path.exists(self.windguru_js_file):
                with open(self.windguru_js_file, 'r', encoding='utf-8') as f:
                    js_data = json.load(f)
            
            # Combinar os dados
            combined_data = {
                "table_data": data,
                "js_data": js_data
            }
            
            return combined_data
            
        except Exception as e:
            logger.error(f"Erro ao carregar dados do Windguru: {e}")
            return None
    
    def _format_windguru_data(self, windguru_data, spot_slug):
        """Formata os dados do Windguru para o formato padrão usado pela aplicação"""
        spot_info = self.spots[spot_slug]
        
        # Dados da tabela do Windguru
        table_data = windguru_data.get("table_data", {})
        
        # Obter o primeiro índice de tempo (previsão atual)
        index = 0  # Primeiro horário disponível
        
        # Extrair altura das ondas
        wave_height = 0.0
        if "tabid_0_0_HTSGW" in table_data and table_data["tabid_0_0_HTSGW"]["values"]:
            try:
                wave_height = float(table_data["tabid_0_0_HTSGW"]["values"][index])
            except (ValueError, IndexError):
                wave_height = self._extract_fallback_value(table_data, "tabid_0_0_HTSGW")
        
        # Extrair período das ondas
        period = 0
        if "tabid_0_0_PERPW" in table_data and table_data["tabid_0_0_PERPW"]["values"]:
            try:
                period = int(float(table_data["tabid_0_0_PERPW"]["values"][index]))
            except (ValueError, IndexError):
                period = self._extract_fallback_value(table_data, "tabid_0_0_PERPW")
        
        # Extrair direção das ondas
        wave_direction = "N/A"
        if "tabid_0_0_DIRPW" in table_data and table_data["tabid_0_0_DIRPW"]["values"]:
            try:
                dir_value = table_data["tabid_0_0_DIRPW"]["values"][index]
                wave_direction = self._convert_direction_angle(dir_value)
            except (ValueError, IndexError):
                wave_direction = "VARIÁVEL"
        
        # Extrair velocidade do vento
        wind_speed = 0
        if "tabid_0_0_WINDSPD" in table_data and table_data["tabid_0_0_WINDSPD"]["values"]:
            try:
                wind_speed = int(float(table_data["tabid_0_0_WINDSPD"]["values"][index]))
            except (ValueError, IndexError):
                wind_speed = self._extract_fallback_value(table_data, "tabid_0_0_WINDSPD")
        
        # Extrair direção do vento
        wind_direction = "N/A"
        if "tabid_0_0_SMER" in table_data and table_data["tabid_0_0_SMER"]["values"]:
            try:
                dir_value = table_data["tabid_0_0_SMER"]["values"][index]
                wind_direction = dir_value if dir_value else "VARIÁVEL"
            except (ValueError, IndexError):
                wind_direction = "VARIÁVEL"
        
        # Extrair temperatura
        temperature = 0
        if "tabid_0_0_TMPE" in table_data and table_data["tabid_0_0_TMPE"]["values"]:
            try:
                temperature = int(float(table_data["tabid_0_0_TMPE"]["values"][index]))
            except (ValueError, IndexError):
                temperature = 25  # Valor padrão
        
        # Construir objeto de previsão
        forecast = {
            "spot": {
                "name": spot_info["name"],
                "location": spot_info["location"],
                "windguru_id": spot_info["windguru_id"]
            },
            "wave_height": wave_height,
            "period": period,
            "wave_direction": wave_direction,
            "wind_speed": wind_speed,
            "wind_direction": wind_direction,
            "temperature": temperature,
            "tide_time": self._get_tide_info(),
            "condition_message": self._get_condition_message(wave_height, wind_speed, period),
            "forecast_url": f"https://www.windguru.cz/{spot_info['windguru_id']}",
            "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        return forecast
    
    def _extract_fallback_value(self, data, key):
        """Extrai um valor de fallback para um campo específico, usando o primeiro valor disponível"""
        if key in data and data[key]["values"] and len(data[key]["values"]) > 0:
            for value in data[key]["values"]:
                try:
                    return float(value)
                except (ValueError, TypeError):
                    continue
        return 0
    
    def _convert_direction_angle(self, angle_value):
        """Converte um ângulo em texto para direção cardinal"""
        try:
            # Tentar extrair o ângulo se for da forma "rotate(X)"
            if isinstance(angle_value, str) and "rotate" in angle_value:
                match = re.search(r'rotate\(([^,]+)', angle_value)
                if match:
                    angle = float(match.group(1))
                else:
                    return "VARIÁVEL"
            else:
                # Tentar converter diretamente para float
                angle = float(angle_value)
            
            # Converter ângulo para direção cardinal
            directions = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", 
                          "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
            index = round(((angle % 360) / 22.5)) % 16
            return directions[index]
        except (ValueError, TypeError):
            return "VARIÁVEL"
    
    def _get_tide_info(self):
        """Retorna informação de maré (simplificada)"""
        current_hour = datetime.now().hour
        if 5 <= current_hour < 11:
            return "Enchente"
        elif 11 <= current_hour < 14:
            return "Cheia"
        elif 14 <= current_hour < 20:
            return "Vazante"
        else:
            return "Baixa"
    
    def _get_condition_message(self, wave_height, wind_speed, period=0):
        """Gera uma mensagem sobre as condições com base na altura das ondas e velocidade do vento"""
        # Avaliação baseada no período
        period_quality = ""
        if period >= 12:
            period_quality = "com excelente formação"
        elif period >= 10:
            period_quality = "bem formadas"
        elif period >= 8:
            period_quality = "com boa formação"
        
        # Avaliação baseada na altura das ondas
        if wave_height < 0.5:
            base_msg = "Ondas pequenas, ideal para iniciantes"
        elif 0.5 <= wave_height < 1.0:
            if wind_speed < 15:
                base_msg = f"Ondas de {wave_height}m {period_quality}, boas para todos os níveis"
            else:
                base_msg = f"Ondas de {wave_height}m, mas vento forte pode atrapalhar"
        elif 1.0 <= wave_height < 1.5:
            if wind_speed < 10:
                base_msg = f"Ótimas condições! Ondas de {wave_height}m {period_quality}"
            elif wind_speed < 20:
                base_msg = f"Ondas de {wave_height}m {period_quality}, condições desafiadoras"
            else:
                base_msg = f"Ondas de {wave_height}m, mas vento muito forte, cuidado"
        elif 1.5 <= wave_height < 2.0:
            if wind_speed < 15:
                base_msg = f"Ondas grandes de {wave_height}m {period_quality}, para surfistas experientes"
            else:
                base_msg = f"Ondas de {wave_height}m, condições difíceis, apenas para experientes"
        else:
            base_msg = f"Ondas grandes de {wave_height}m, apenas para profissionais"
        
        return base_msg
    
    def _get_fallback_forecast(self, spot_slug=None):
        """Retorna dados de previsão de fallback quando o scraping falha"""
        if spot_slug and spot_slug in self.spots:
            spot = self.spots[spot_slug]
        else:
            # Escolhe um spot aleatório se nenhum for especificado ou o especificado não existir
            spot_slug = random.choice(list(self.spots.keys()))
            spot = self.spots[spot_slug]
        
        wave_height = round(random.uniform(0.5, 2.0), 1)
        wind_speed = random.randint(5, 25)
        period = random.randint(6, 14)
        
        return {
            "spot": {
                "name": spot["name"],
                "location": spot["location"],
                "windguru_id": spot["windguru_id"]
            },
            "wave_height": wave_height,
            "wave_direction": random.choice(['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW']),
            "wind_direction": random.choice(['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW']),
            "wind_speed": wind_speed,
            "period": period,
            "temperature": random.randint(20, 30),
            "tide_time": self._get_tide_info(),
            "condition_message": self._get_condition_message(wave_height, wind_speed, period),
            "forecast_url": f"https://www.windguru.cz/{spot['windguru_id']}",
            "is_fallback": True,  # Indicador que estes são dados de fallback
            "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    
    def get_random_spot_forecast(self):
        """Obtém a previsão para um spot aleatório"""
        spot_slug = random.choice(list(self.spots.keys()))
        return self.get_spot_forecast(spot_slug)

# Função de conveniência para obter uma previsão
def get_surf_forecast(spot_slug=None):
    scraper = SurfForecast()
    if spot_slug:
        return scraper.get_spot_forecast(spot_slug)
    else:
        return scraper.get_random_spot_forecast()

# Para teste independente
if __name__ == "__main__":
    # Configurar o caminho para os arquivos JSON
    forecast = SurfForecast()
    
    # Imprimir informações dos arquivos
    print(f"Verificando arquivos de previsão:")
    print(f"- Arquivo de dados principal: {os.path.exists(forecast.windguru_data_file)}")
    print(f"- Arquivo de dados JS: {os.path.exists(forecast.windguru_js_file)}")
    
    # Testar carregamento de dados
    data = forecast._load_windguru_data()
    if data:
        print(f"\nDados carregados com sucesso!")
        print(f"- Variáveis na tabela: {len(data['table_data'])}")
        
        # Mostrar as primeiras entradas de dados
        if 'tabid_0_0_HTSGW' in data['table_data']:
            print(f"\nAmostra de altura das ondas (HTSGW):")
            height_data = data['table_data']['tabid_0_0_HTSGW']['values']
            print(f"- Primeiros 5 valores: {height_data[:5]}")
    else:
        print("Falha ao carregar dados.")
    
    # Testar a obtenção de previsão para Matinhos
    print("\n=== Previsão para Matinhos ===")
    forecast_data = forecast.get_spot_forecast("matinhos")
    print(json.dumps(forecast_data, indent=2, ensure_ascii=False))
    
    # Testar previsão aleatória
    print("\n=== Previsão aleatória ===")
    random_forecast = forecast.get_random_spot_forecast()
    print(json.dumps(random_forecast, indent=2, ensure_ascii=False))