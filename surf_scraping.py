#!/usr/bin/env python
import json
import time
import re
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from webdriver_manager.chrome import ChromeDriverManager

class WindguruScraper:
    def __init__(self):
        # Configurando o Chrome em modo headless
        self.options = Options()
        self.options.add_argument('--headless')
        self.options.add_argument('--disable-gpu')
        self.options.add_argument('--no-sandbox')
        self.options.add_argument('--disable-dev-shm-usage')
        self.options.add_argument('--window-size=1920,1080')
        
        # Inicializar o driver do Chrome
        print("Inicializando o driver do Chrome...")
        self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=self.options)
    
    def scrape(self, url):
        print(f"Acessando {url}...")
        self.driver.get(url)
        
        # Aguardar o carregamento da tabela de previsão (importante para o Windguru)
        try:
            wait = WebDriverWait(self.driver, 20)
            table = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "table.tabulka")))
            print("Tabela de previsão carregada!")
        except Exception as e:
            print(f"Erro ao aguardar carregamento da tabela: {e}")
            # Vamos continuar mesmo com erro, pois parte dos dados pode ter carregado
        
        # Dar um tempo extra para carregar scripts JS
        time.sleep(5)
        
        # Extrair o HTML completo após carregamento
        html_source = self.driver.page_source
        
        # Salvar o HTML para análise
        with open("windguru_full_page.html", "w", encoding="utf-8") as f:
            f.write(html_source)
            print("HTML da página completa salvo em 'windguru_full_page.html'")
        
        # Extrair dados de previsão
        forecast = self.extract_forecast_data(html_source)
        
        # Extrair scripts JavaScript
        self.extract_javascript_data()
        
        # Fechar o navegador
        self.driver.quit()
        print("Driver do Chrome fechado.")
        
        return forecast
    
    def extract_forecast_data(self, html_source):
        print("Extraindo dados da tabela de previsão...")
        soup = BeautifulSoup(html_source, "html.parser")
        forecast = {}
        
        # Tentar encontrar a tabela principal de previsão
        table = soup.find("table", {"class": "tabulka"})
        if not table:
            print("Tabela de previsão não encontrada!")
            return forecast
        
        # Encontrar todos os cabeçalhos (datas/horas)
        headers = table.find("tr", {"class": "tr_dates"})
        if headers:
            date_cells = headers.find_all("td")
            dates = [cell.get_text().strip() for cell in date_cells]
            forecast["dates"] = dates
            print(f"Encontradas {len(dates)} datas/horas na previsão")
        
        # Encontrar todas as linhas de dados
        try:
            tbody = table.find("tbody")
            if tbody:
                rows = tbody.find_all("tr")
            else:
                rows = table.find_all("tr")
            
            print(f"Encontradas {len(rows)} linhas de dados")
            
            for row in rows:
                # Pular linhas sem ID (como separadores, etc)
                if not row.get('id'):
                    continue
                
                row_id = row.get('id')
                cells = row.find_all("td")
                row_data = []
                
                # Nome da variável (primeira célula)
                var_name_cell = cells[0] if cells else None
                var_name = var_name_cell.get_text().strip() if var_name_cell else "Desconhecido"
                
                for i, cell in enumerate(cells[1:], 1):  # Pular primeira célula (nome)
                    # Tratamento especial para direção de vento/ondas (vetores)
                    if ('DIRPW' in row_id) or ('DIR' in row_id and 'DIRPW' not in row_id):
                        try:
                            svg = cell.find('svg')
                            if svg:
                                g_element = svg.find('g')
                                if g_element and g_element.has_attr('transform'):
                                    transform_value = g_element['transform']
                                    # Extrair ângulo da transformação
                                    angle_match = re.search(r'rotate\(([^,]+)', transform_value)
                                    if angle_match:
                                        value = angle_match.group(1)
                                    else:
                                        value = transform_value
                                else:
                                    value = "N/A"
                            else:
                                value = cell.get_text().strip()
                        except Exception as e:
                            print(f"Erro ao extrair direção: {e}")
                            value = "Erro"
                    else:
                        value = cell.get_text().strip()
                    
                    row_data.append(value)
                
                # Adicionar ao forecast
                forecast[row_id] = {
                    "name": var_name,
                    "values": row_data
                }
        
        except Exception as e:
            print(f"Erro ao processar linhas da tabela: {e}")
        
        # Salvar os dados extraídos em JSON
        with open("windguru_forecast.json", "w", encoding="utf-8") as f:
            json.dump(forecast, f, indent=2, ensure_ascii=False)
            print("Dados da previsão salvos em 'windguru_forecast.json'")
        
        return forecast
    
    def extract_javascript_data(self):
        print("Extraindo dados dos scripts JavaScript...")
        
        # Extrair variáveis JavaScript que contêm dados da previsão
        js_variables = [
            "fcst_hour", "fcst_date", 
            "fcst_WINDSPD", "fcst_WINDDIR", 
            "fcst_SMER", "fcst_GUST", 
            "fcst_PCPT", "fcst_TEMP",
            "fcst_WAVES", "fcst_SWELL1_DIR", "fcst_SWELL1_PER", "fcst_SWELL1_HT",
            "wg_fcst_tab_data", "model_alt", "spot"
        ]
        
        js_data = {}
        
        for var_name in js_variables:
            try:
                # Executar script para obter o valor da variável
                result = self.driver.execute_script(f"return typeof {var_name} !== 'undefined' ? {var_name} : null;")
                if result is not None:
                    js_data[var_name] = result
                    print(f"Variável JavaScript extraída: {var_name}")
            except Exception as e:
                print(f"Erro ao extrair variável {var_name}: {e}")
        
        # Tentar extrair o objeto principal de dados
        try:
            main_data = self.driver.execute_script("return typeof wg_fcst_tab_data !== 'undefined' ? JSON.stringify(wg_fcst_tab_data) : null;")
            if main_data:
                js_data["wg_fcst_tab_data"] = json.loads(main_data)
                print("Dados principais extraídos com sucesso (wg_fcst_tab_data)")
        except Exception as e:
            print(f"Erro ao extrair dados principais: {e}")
        
        # Salvar os dados JavaScript em um arquivo
        with open("windguru_js_data.json", "w", encoding="utf-8") as f:
            json.dump(js_data, f, indent=2, ensure_ascii=False)
            print("Dados JavaScript salvos em 'windguru_js_data.json'")
        
        return js_data
    
if __name__ == '__main__':
    # Definir URL para Matinhos (Pico)
    url = 'https://www.windguru.cz/468811'  
    
    print(f"Iniciando scraping do Windguru para {url}")
    scraper = WindguruScraper()
    data = scraper.scrape(url)
    
    # Mostrar um resumo dos dados coletados
    if data:
        print("\nScraping concluído com sucesso!")
        print(f"Variáveis extraídas: {len(data)}")
        for key in data.keys():
            if key == "dates":
                print(f"Datas/horas: {len(data[key])} pontos de previsão")
            else:
                print(f"Variável: {key} ({data[key].get('name', 'N/A')})")
    else:
        print("\nFalha no scraping. Não foi possível extrair dados.")