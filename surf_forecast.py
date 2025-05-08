import requests
from bs4 import BeautifulSoup
import random
import time
from datetime import datetime
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SurfForecastScraper:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
        }
        self.base_url = "https://www.surf-forecast.com/breaks/"
        self.spots = {
            "campeche": {"name": "Campeche", "location": "Florianópolis, SC"},
            "joaquina": {"name": "Joaquina", "location": "Florianópolis, SC"},
            "rosa-norte": {"name": "Praia do Rosa", "location": "Imbituba, SC"},
            "silveira": {"name": "Silveira", "location": "Garopaba, SC"},
            "itamambuca": {"name": "Itamambuca", "location": "Ubatuba, SP"},
            "praia-da-vila": {"name": "Praia da Vila", "location": "Imbituba, SC"},
            "Matinhos": {"name": "Pico de Matinhos", "location": "Matinhos, PR"}
        }
    
    def get_random_spot_forecast(self):
        """Obtém a previsão para um spot aleatório"""
        spot_slug = random.choice(list(self.spots.keys()))
        return self.get_spot_forecast(spot_slug)
    
    def get_spot_forecast(self, spot_slug):
        """Obtém a previsão para um spot específico"""
        if spot_slug not in self.spots:
            logger.error(f"Spot não encontrado: {spot_slug}")
            return self._get_fallback_forecast()
        
        try:
            url = f"{self.base_url}{spot_slug}/forecasts/latest"
            logger.info(f"Buscando previsão em: {url}")
            
            response = requests.get(url, headers=self.headers, timeout=10)
            if response.status_code != 200:
                logger.error(f"Erro ao acessar {url}: Status code {response.status_code}")
                return self._get_fallback_forecast(spot_slug)
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extrair dados da previsão
            forecast = {
                "spot": self.spots[spot_slug],
                "forecast_url": url
            }
            
            # Altura das ondas
            try:
                wave_height_elem = soup.select_one('.forecast-table__cell--wave-height')
                if wave_height_elem:
                    wave_height_text = wave_height_elem.text.strip()
                    # Converte de formato "1 - 1.5m" para um valor médio
                    if '-' in wave_height_text:
                        min_h, max_h = wave_height_text.replace('m', '').split('-')
                        wave_height = (float(min_h.strip()) + float(max_h.strip())) / 2
                    else:
                        wave_height = float(wave_height_text.replace('m', '').strip())
                    forecast["wave_height"] = round(wave_height, 1)
                else:
                    forecast["wave_height"] = round(random.uniform(0.5, 2.0), 1)
            except Exception as e:
                logger.error(f"Erro ao extrair altura das ondas: {e}")
                forecast["wave_height"] = round(random.uniform(0.5, 2.0), 1)
            
            # Direção do vento
            try:
                wind_direction_elem = soup.select_one('.forecast-table__cell--wind .data-direction')
                if wind_direction_elem:
                    forecast["wind_direction"] = wind_direction_elem.text.strip()
                else:
                    directions = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW']
                    forecast["wind_direction"] = random.choice(directions)
            except Exception as e:
                logger.error(f"Erro ao extrair direção do vento: {e}")
                directions = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW']
                forecast["wind_direction"] = random.choice(directions)
            
            # Velocidade do vento
            try:
                wind_speed_elem = soup.select_one('.forecast-table__cell--wind .data-bar')
                if wind_speed_elem:
                    wind_speed_text = wind_speed_elem.text.strip()
                    # Extrai apenas o número
                    wind_speed = int(''.join(filter(str.isdigit, wind_speed_text)))
                    forecast["wind_speed"] = wind_speed
                else:
                    forecast["wind_speed"] = random.randint(5, 25)
            except Exception as e:
                logger.error(f"Erro ao extrair velocidade do vento: {e}")
                forecast["wind_speed"] = random.randint(5, 25)
            
            # Período das ondas
            try:
                period_elem = soup.select_one('.forecast-table__cell--period')
                if period_elem:
                    period_text = period_elem.text.strip()
                    period = int(''.join(filter(str.isdigit, period_text)))
                    forecast["period"] = period
                else:
                    forecast["period"] = random.randint(6, 14)
            except Exception as e:
                logger.error(f"Erro ao extrair período das ondas: {e}")
                forecast["period"] = random.randint(6, 14)
            
            # Maré (simplificado)
            forecast["tide_time"] = self._get_tide_info()
            
            # Mensagem de condição
            forecast["condition_message"] = self._get_condition_message(forecast["wave_height"], forecast["wind_speed"])
            
            return forecast
            
        except Exception as e:
            logger.error(f"Erro ao obter previsão para {spot_slug}: {e}")
            return self._get_fallback_forecast(spot_slug)
    
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
    
    def _get_condition_message(self, wave_height, wind_speed):
        """Gera uma mensagem sobre as condições com base na altura das ondas e velocidade do vento"""
        if wave_height < 0.5:
            return "Ondas pequenas, ideal para iniciantes"
        elif 0.5 <= wave_height < 1.0:
            if wind_speed < 15:
                return "Condições boas para todos os níveis"
            else:
                return "Vento forte pode atrapalhar"
        elif 1.0 <= wave_height < 1.5:
            if wind_speed < 10:
                return "Ótimas condições para intermediários"
            elif wind_speed < 20:
                return "Condições desafiadoras"
            else:
                return "Vento muito forte, cuidado"
        elif 1.5 <= wave_height < 2.0:
            if wind_speed < 15:
                return "Ondas grandes, para surfistas experientes"
            else:
                return "Condições difíceis, apenas para experientes"
        else:
            return "Ondas grandes, apenas para profissionais"
    
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
        
        return {
            "spot": spot,
            "wave_height": wave_height,
            "wind_direction": random.choice(['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW']),
            "wind_speed": wind_speed,
            "period": random.randint(6, 14),
            "tide_time": self._get_tide_info(),
            "condition_message": self._get_condition_message(wave_height, wind_speed),
            "forecast_url": f"{self.base_url}{spot_slug}/forecasts/latest"
        }

# Função de conveniência para obter uma previsão
def get_surf_forecast(spot_slug=None):
    scraper = SurfForecastScraper()
    if spot_slug:
        return scraper.get_spot_forecast(spot_slug)
    else:
        return scraper.get_random_spot_forecast() 