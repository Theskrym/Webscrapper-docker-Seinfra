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

def fechar_navegador_com_timeout(driver, timeout=10):
    """
    Fecha o navegador com um timeout
    """
    try:
        print("Tentando fechar navegador normalmente...")
        driver.quit()
        print("Navegador fechado com sucesso")
        return True
    except Exception as e:
        print(f"Erro ao fechar navegador: {str(e)}")
        try:
            print("Tentando forçar fechamento...")
            driver.quit()
        except:
            print("Não foi possível fechar o navegador")
        return False

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
    driver = None
    
    # Define o caminho absoluto para salvar o CSV na pasta data
    csv_path = os.path.join('/app/data', 'planilhas_consolidadas.csv')
    
    # Cria o diretório se não existir
    os.makedirs('/app/data', exist_ok=True)
    
    print(f"Tentando salvar em: {os.path.abspath(csv_path)}")
    print(f"Diretório atual é: {os.getcwd()}")
    
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
            
            print("Salvando CSV...")
            df_final.to_csv(csv_path, index=False, encoding='utf-8-sig')
            print(f"Dados salvos em: {csv_path}")
            
            print("Preparando para fechar navegador...")
            if driver:
                print("Iniciando fechamento do navegador...")
                fechar_navegador_com_timeout(driver)
                driver = None
            print("Navegador fechado")
            
            print("Retornando caminho do CSV...")
            return csv_path
            
    except Exception as e:
        print(f"Erro em scraper_seinfra: {str(e)}")
        raise
    finally:
        if driver:
            print("Fechando navegador no finally...")
            fechar_navegador_com_timeout(driver)
            driver = None
        print("Finalizando scraper_seinfra...")

def iniciar_scraping(request=None):
    def log_message(message):
        # Envia mensagem tanto para console quanto para web
        print(message)
        if request and hasattr(request, 'send_event'):
            request.send_event({'message': message})

    try:
        log_message("\n" + "="*50)
        log_message("INICIANDO PROCESSO DE SCRAPING")
        log_message("="*50)
        
        inicio = time.time()
        log_message("Chamando scraper_seinfra...")
        
        try:
            csv_path = scraper_seinfra()
            log_message("scraper_seinfra retornou com sucesso!")
            log_message(f"CSV Path retornado: {csv_path}")
        except Exception as e:
            log_message(f"Erro durante scraper_seinfra: {str(e)}")
            raise
            
        log_message("\nVerificando arquivo CSV...")
        if csv_path and os.path.exists(csv_path):
            log_message(f"Arquivo CSV encontrado em: {csv_path}")
            log_message("\n" + "="*50)
            log_message("INICIANDO IMPORTAÇÃO PARA O BANCO")
            log_message("="*50)
            
            log_message("Importando módulo test_db...")
            import test_db
            
            log_message("\nIniciando importação para o banco de dados...")
            resultado = test_db.importar_csv_direto(csv_path, request)
            
            if resultado:
                log_message("\nImportação concluída com sucesso!")
            else:
                log_message("\nErro durante a importação!")
                return {
                    'status': 'error',
                    'message': 'Erro na importação para o banco',
                    'tempo_execucao': '0:0'
                }
        else:
            log_message(f"\nERRO: Arquivo CSV não encontrado em {csv_path}")
            return {
                'status': 'error',
                'message': 'Arquivo CSV não encontrado',
                'tempo_execucao': '0:0'
            }
        
        fim = time.time()
        tempo_total = fim - inicio
        minutos = int(tempo_total // 60)
        segundos = int(tempo_total % 60)
        
        log_message("\n" + "="*50)
        log_message("PROCESSO COMPLETO")
        log_message(f"Tempo total: {minutos}min {segundos}s")
        log_message("="*50)
        
        return {
            'status': 'success',
            'message': 'PROCESSO CONCLUÍDO COM SUCESSO',
            'tempo_execucao': f'{minutos}:{segundos}'
        }
        
    except Exception as e:
        log_message("\n" + "="*50)
        log_message("ERRO DURANTE O PROCESSO")
        log_message("="*50)
        log_message(f"Erro: {str(e)}")
        import traceback
        log_message(traceback.format_exc())
        return {
            'status': 'error',
            'message': f'ERRO: {str(e)}',
            'tempo_execucao': '0:0'
        }

if __name__ == "__main__":
    resultado = iniciar_scraping()
    print(f"\n{resultado['message']}")