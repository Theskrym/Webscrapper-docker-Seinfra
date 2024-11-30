import os
import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from io import BytesIO

def download_planilha(url, max_retries=3, backoff_factor=0.5):
    """
    Tenta baixar a planilha com sistema de retry
    """
    session = requests.Session()
    retry_strategy = Retry(
        total=max_retries,
        backoff_factor=backoff_factor,
        status_forcelist=[500, 502, 503, 504, 429]
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    try:
        response = session.get(url, timeout=30)  # Aumentado timeout para 30 segundos
        if response.status_code == 200:
            return response.content
        else:
            print(f"Erro ao baixar planilha. Status code: {response.status_code}")
            return None
    except Exception as e:
        print(f"Erro ao baixar planilha: {str(e)}")
        return None

def processar_planilha(url_planilha, regiao):
    try:
        # Tenta baixar a planilha com retry
        content = download_planilha(url_planilha)
        if content is None:
            return None
            
        # Lê o conteúdo da planilha usando BytesIO
        df = pd.read_excel(BytesIO(content), sheet_name='Relatório')
        
        # Define a linha 25 como cabeçalho
        header_row = 25
        
        # Pega os dados após o cabeçalho
        df = df.iloc[header_row+1:].reset_index(drop=True)
        
        # Verifica o número de colunas e ajusta conforme necessário
        num_columns = len(df.columns)
        if num_columns >= 8:  # Garante que temos pelo menos 8 colunas
            # Se tivermos mais que 8 colunas, pegamos apenas as primeiras 8
            df = df.iloc[:, :8]
            
            # Renomeia as colunas manualmente
            new_columns = ['CÓDIGO', None, 'DESCRIÇÃO DO SERVIÇO', None, None, None, 'UNIDADE', 'CUSTO UNITÁRIO']
            df.columns = new_columns
            
            # Remove colunas None/nan
            df = df.drop(columns=[col for col in df.columns if col is None])
            
            # Adiciona a coluna região
            df['regiao'] = regiao
            
            # Remove linhas totalmente vazias
            df = df.dropna(how='all')
            
            # Garante que os tipos de dados estejam corretos
            df['CÓDIGO'] = df['CÓDIGO'].astype(str)
            df['DESCRIÇÃO DO SERVIÇO'] = df['DESCRIÇÃO DO SERVIÇO'].astype(str)
            df['UNIDADE'] = df['UNIDADE'].astype(str)
            df['CUSTO UNITÁRIO'] = pd.to_numeric(df['CUSTO UNITÁRIO'], errors='coerce')
            
            return df
        else:
            print(f"Erro: número insuficiente de colunas ({num_columns}) na planilha {url_planilha}")
            return None
            
    except Exception as e:
        print(f"Erro ao processar planilha {url_planilha}: {str(e)}")
        return None

def scraper_seinfra():
    """
    Scraper principal que coleta dados de preços do SETOP para todas as regiões.
    """
    print("Iniciando scraper_seinfra...")
    dados_processados = []
    try:
        firefox_options = webdriver.FirefoxOptions()
        firefox_options.add_argument('--headless')
        firefox_options.add_argument('--ignore-certificate-errors')
        firefox_options.add_argument('--ignore-ssl-errors')
        firefox_options.log.level = 'fatal'
        
        print("Configurando Firefox...")
        driver = webdriver.Firefox(options=firefox_options)
        driver.implicitly_wait(10)  # Aumentado para 10 segundos
        wait = WebDriverWait(driver, 10)  # Aumentado para 10 segundos
        
        url = "http://www.infraestrutura.mg.gov.br/component/gmg/page/102-consulta-a-planilha-preco-setop"
        print(f"Tentando acessar: {url}")
        driver.get(url)
        time.sleep(0.5)
        
        try:
            wait.until(EC.presence_of_element_located((By.CLASS_NAME, "map-container")))
        except TimeoutException:
            wait.until(EC.presence_of_element_located((By.TAG_NAME, "map")))
        
        regioes_info = []
        municipios = driver.find_elements(By.CSS_SELECTOR, "area[title]")
        
        for municipio in municipios:
            regioes_info.append({
                'nome': municipio.get_attribute("title"),
                'href': municipio.get_attribute("href")
            })
        
        print(f"Encontradas {len(regioes_info)} regiões")
        total_planilhas = 0
        planilha_atual = 0
        
        # Processa planilhas
        for regiao in regioes_info:
            try:
                print(f"\nProcessando região: {regiao['nome']}")
                driver.get(regiao['href'])
                time.sleep(0.5)
                
                links_planilhas = wait.until(
                    EC.presence_of_all_elements_located(
                        (By.CSS_SELECTOR, "a[href$='.xls'], a[href$='.xlsx']")
                    )
                )
                
                if links_planilhas:
                    for link in links_planilhas:
                        planilha_atual += 1
                        url_planilha = link.get_attribute("href")
                        texto = link.text.strip()
                        ano = texto.split()[0] if texto else "N/A"
                        
                        print(f"Baixando planilha {planilha_atual}: {regiao['nome']}")
                        df_processado = processar_planilha(url_planilha, regiao['nome'])
                        
                        if df_processado is not None:
                            dados_processados.append(df_processado)
                            
            except Exception as e:
                print(f"Erro ao processar região {regiao['nome']}: {str(e)}")
                continue
        
        if dados_processados:
            print("\nConsolidando dados...")
            df_final = pd.concat(dados_processados, ignore_index=True)
            script_dir = os.path.dirname(os.path.abspath(__file__))
            csv_path = os.path.join(script_dir, 'planilhas_consolidadas.csv')
            df_final.to_csv(csv_path, index=False, encoding='utf-8-sig')
            print("Dados salvos em 'planilhas_consolidadas.csv'")
            
    except Exception as e:
        print(f"Erro em scraper_seinfra: {str(e)}")
        raise
    finally:
        if 'driver' in locals():
            print("Fechando navegador...")
            driver.quit()

def iniciar_scraping(request=None):
    try:
        inicio = time.time()
        scraper_seinfra()
        fim = time.time()
        tempo_total = fim - inicio
        minutos = int(tempo_total // 60)
        segundos = int(tempo_total % 60)
        
        return {
            'status': 'success',
            'message': f'Scraping concluído em {minutos} minutos e {segundos} segundos',
            'tempo_execucao': f'{minutos}:{segundos}'
        }
    except Exception as e:
        return {
            'status': 'error',
            'message': f'Erro durante o scraping: {str(e)}',
            'tempo_execucao': '0:0'
        }

if __name__ == "__main__":
    resultado = iniciar_scraping()
    print(f"\n{resultado['message']}")
    
    # Chama o script test_db.py com o caminho correto do CSV
    import test_db
    import os
    
    # Obtém o diretório do script atual
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Define o caminho completo do CSV
    csv_path = os.path.join(script_dir, 'planilhas_consolidadas.csv')
    
    # Chama a nova função com o caminho do CSV
    test_db.importar_csv_direto(csv_path)