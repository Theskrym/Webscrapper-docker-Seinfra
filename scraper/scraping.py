from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import pandas as pd
import requests
import io
import time
import os
import subprocess

# Tenta importar test_db, mas não falha se não conseguir
try:
    import test_db
    HAS_TEST_DB = True
except ImportError:
    print("Aviso: Não foi possível importar test_db. O banco de dados não será testado.")
    HAS_TEST_DB = False

def processar_planilha(url_planilha, municipio, ano):
    """
    Processa uma planilha Excel do SETOP, extraindo informações de códigos, descrições,
    unidades e custos unitários.
    """
    try:
        response = requests.get(url_planilha)
        
        if response.status_code == 200:
            if url_planilha.endswith('.xls') or url_planilha.endswith('.xlsx'):
                try:
                    if len(response.content) == 0:
                        print(f"Arquivo Excel vazio: {url_planilha}")
                        return None
                    
                    try:
                        excel_file = pd.ExcelFile(io.BytesIO(response.content))
                        df_raw = pd.read_excel(
                            excel_file,
                            sheet_name='Relatório',
                            header=None
                        )
                        
                        # Procura a linha que contém "CÓDIGO" e identifica as colunas
                        for idx, row in df_raw.iterrows():
                            if 'CÓDIGO' in [str(x).strip().upper() for x in row if pd.notna(x)]:
                                start_row = idx
                                
                                # Identifica os índices das colunas
                                colunas = {}
                                for col_idx, valor in enumerate(row):
                                    if pd.notna(valor):
                                        valor_str = str(valor).strip().upper()
                                        if 'CÓDIGO' in valor_str:
                                            colunas['codigo'] = col_idx
                                        elif 'DESCRIÇÃO' in valor_str:
                                            colunas['descricao'] = col_idx
                                        elif 'UNIDADE' in valor_str:
                                            colunas['unidade'] = col_idx
                                        elif 'CUSTO' in valor_str:
                                            colunas['custo'] = col_idx
                                
                                # Lê o Excel novamente a partir da linha correta
                                df = pd.read_excel(
                                    excel_file,
                                    sheet_name='Relatório',
                                    skiprows=start_row,
                                    usecols=[colunas['codigo'], colunas['descricao'], 
                                            colunas['unidade'], colunas['custo']],
                                    dtype=str
                                )
                                
                                # Renomeia as colunas
                                df.columns = ['CÓDIGO', 'DESCRIÇÃO DE SERVIÇO', 'UNIDADE', 'CUSTO UNITÁRIO']
                                
                                # Remove linhas vazias e linhas de cabeçalho
                                df = df.dropna(subset=['CÓDIGO'])
                                df = df[~df['CÓDIGO'].astype(str).str.contains('código', case=False)]
                                
                                # Remove linhas específicas
                                df = df[~df['CÓDIGO'].astype(str).str.upper().eq('SEINFRA')]
                                df = df[~df['CÓDIGO'].astype(str).str.contains('Rod. Papa João Paulo II', case=False)]
                                
                                # Ajusta o formato dos códigos
                                def formatar_codigo(codigo):
                                    codigo = str(codigo).strip()
                                    # Se o código é apenas números e tem menos de 7 caracteres
                                    if codigo.isdigit() and len(codigo) <= 7:
                                        return f"CE-{codigo}"
                                    # Se já tem o prefixo, mantém como está
                                    elif '-' in codigo:
                                        return codigo
                                    # Para outros casos, mantém o original
                                    return codigo
                                
                                df['CÓDIGO'] = df['CÓDIGO'].apply(formatar_codigo)
                                df['DESCRIÇÃO DE SERVIÇO'] = df['DESCRIÇÃO DE SERVIÇO'].fillna('').astype(str).str.strip()
                                df['UNIDADE'] = df['UNIDADE'].fillna('').astype(str).str.strip()
                                
                                # Trata o custo unitário
                                def converter_custo(valor):
                                    try:
                                        if pd.isna(valor):
                                            return 0.0
                                        valor_str = str(valor).replace('R$', '').strip()
                                        if ',' in valor_str and '.' in valor_str:
                                            valor_str = valor_str.replace('.', '').replace(',', '.')
                                        elif ',' in valor_str:
                                            valor_str = valor_str.replace(',', '.')
                                        return float(valor_str) if valor_str else 0.0
                                    except:
                                        return 0.0
                                
                                df['CUSTO UNITÁRIO'] = df['CUSTO UNITÁRIO'].apply(converter_custo)
                                
                                # Adiciona a região
                                df['REGIÃO'] = municipio
                                df['ANO'] = ano
                                
                                # Adiciona uma coluna de hash para identificar registros únicos
                                df['HASH'] = df.apply(lambda row: hash(f"{row['CÓDIGO']}_{row['REGIÃO']}_{row['ANO']}"), axis=1)
                                
                                return df
                                
                        print("Não encontrou a linha com 'CÓDIGO'")
                        return None
                        
                    except Exception as e:
                        print(f"Erro ao ler Excel: {str(e)}\nURL: {url_planilha}")
                        return None
                    
                except Exception as e:
                    print(f"Erro ao processar Excel: {str(e)}\nURL: {url_planilha}")
                    return None
            else:
                print(f"Arquivo não é Excel: {url_planilha}")
                return None
        else:
            print(f"Erro ao baixar planilha (Status {response.status_code}): {url_planilha}")
            return None
    except Exception as e:
        print(f"Erro ao processar planilha: {str(e)}\nURL: {url_planilha}")
        return None

def merge_dataframes(novo_df, arquivo_existente='planilhas_consolidadas.csv'):
    """
    Realiza o merge entre o novo dataframe e os dados existentes
    """
    try:
        # Tenta ler o arquivo existente
        df_existente = pd.read_csv(arquivo_existente)
        df_existente['HASH'] = df_existente.apply(
            lambda row: hash(f"{row['CÓDIGO']}_{row['REGIÃO']}_{row['ANO']}"), 
            axis=1
        )
        
        # Merge baseado no HASH, mantendo todos os registros
        df_merged = pd.concat([df_existente, novo_df])
        
        # Remove duplicatas mantendo a versão mais recente
        df_final = df_merged.drop_duplicates(subset=['HASH'], keep='last')
        
        # Remove a coluna de HASH antes de salvar
        df_final = df_final.drop('HASH', axis=1)
        
        return df_final
        
    except FileNotFoundError:
        # Se o arquivo não existe, retorna apenas o novo dataframe sem a coluna HASH
        return novo_df.drop('HASH', axis=1)

def iniciar_scraping(message_queue=None):
    """
    Scraper principal que coleta dados de preços do SETOP para todas as regiões.
    """
    def send_message(msg):
        if message_queue:
            message_queue.put(msg)
        print(msg)

    firefox_options = webdriver.FirefoxOptions()
    firefox_options.add_argument('--ignore-certificate-errors')
    firefox_options.add_argument('--ignore-ssl-errors')
    firefox_options.log.level = 'fatal'
    firefox_options.add_argument('--headless')
    firefox_options.add_argument('--no-sandbox')
    firefox_options.add_argument('--disable-dev-shm-usage')
    
    try:
        send_message("Iniciando o navegador...")
        driver = webdriver.Firefox(options=firefox_options)
        driver.implicitly_wait(10)
        wait = WebDriverWait(driver, 10)
        
        url = "http://www.infraestrutura.mg.gov.br/component/gmg/page/102-consulta-a-planilha-preco-setop"
        dados_processados = []
        
        driver.get(url)
        time.sleep(1)
        
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
        
        send_message(f"Encontradas {len(regioes_info)} regiões")
        total_planilhas = 0
        planilha_atual = 0
        
        # Conta total de planilhas
        for regiao in regioes_info:
            driver.get(regiao['href'])
            time.sleep(1)
            
            try:
                links_planilhas = wait.until(
                    EC.presence_of_all_elements_located(
                        (By.CSS_SELECTOR, "a[href$='.xls'], a[href$='.xlsx']")
                    )
                )
                total_planilhas += len(links_planilhas)
            except:
                continue
        
        # Processa planilhas
        for regiao in regioes_info:
            try:
                driver.get(regiao['href'])
                time.sleep(1)
                
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
                        
                        send_message(f"Baixando planilha {planilha_atual} de {total_planilhas}: {regiao['nome']}")
                        df_processado = processar_planilha(url_planilha, regiao['nome'], ano)
                        
                        if df_processado is not None:
                            dados_processados.append(df_processado)
                            
            except Exception as e:
                send_message(f"Erro ao processar região {regiao['nome']}: {str(e)}")
                continue
        
        if dados_processados:
            df_final = pd.concat(dados_processados, ignore_index=True)
            
            # Realiza o merge com dados existentes
            df_merged = merge_dataframes(df_final)
            
            # Salva o resultado
            df_merged.to_csv('planilhas_consolidadas.csv', index=False, encoding='utf-8-sig')
            send_message("\nDados consolidados e mesclados em 'planilhas_consolidadas.csv'")
            
            if HAS_TEST_DB:
                send_message("\nExecutando test_db...")
                script_dir = os.path.dirname(os.path.abspath(__file__))
                test_db_path = os.path.join(script_dir, 'test_db.py')
                result = subprocess.run(['python', test_db_path], 
                                     capture_output=True, 
                                     text=True, 
                                     check=True)
                send_message(result.stdout)
                if result.stderr:
                    send_message("Erros: " + result.stderr)
            
        else:
            send_message("Nenhuma planilha processada com sucesso!")
            
    except Exception as e:
        send_message(f"Erro durante a execução: {str(e)}")
    finally:
        if 'driver' in locals():
            driver.quit()

if __name__ == "__main__":
    iniciar_scraping()
