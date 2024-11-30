import os
import sys
from pathlib import Path
import pandas as pd
import sqlite3

# Adiciona o diretório raiz do projeto ao PYTHONPATH
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

# Configura as variáveis de ambiente do Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

from django.conf import settings

def importar_csv_direto(arquivo_csv):
    try:
        print(f"\nLendo arquivo {arquivo_csv}...")
        df = pd.read_csv(arquivo_csv, encoding='utf-8-sig')
        
        print("\nColunas do DataFrame:")
        print(df.columns.tolist())
        print("\nTipos de dados:")
        print(df.dtypes)
        
        # Limpa e prepara os dados
        df = df[
            df['CÓDIGO'].str.match(r'^[A-Z]{2,3}-\d+$', na=False) &
            df['DESCRIÇÃO DO SERVIÇO'].notna() &
            (df['DESCRIÇÃO DO SERVIÇO'].str.len() > 5) &
            ~df['DESCRIÇÃO DO SERVIÇO'].str.contains(r'TABELA REFERENCIAL|DESONERAÇÃO|\d{2}/\d{4}', 
                                                    na=False, regex=True, case=False) &
            df['CUSTO UNITÁRIO'].notna()
        ]
        
        # Remove duplicatas por código + região
        df = df.drop_duplicates(subset=['CÓDIGO', 'regiao'], keep='last')
        
        # Limpa e formata os dados antes de renomear
        df['UNIDADE'] = df['UNIDADE'].fillna('')
        
        # Converte CUSTO UNITÁRIO para float se necessário
        if df['CUSTO UNITÁRIO'].dtype == 'object':
            df['CUSTO UNITÁRIO'] = df['CUSTO UNITÁRIO'].str.replace('R$', '').str.strip().str.replace(',', '.').astype(float)
        
        # Renomeia as colunas para corresponder ao banco
        df = df.rename(columns={
            'CÓDIGO': 'CODIGO',
            'DESCRIÇÃO DO SERVIÇO': 'DESCRICAO_DE_SERVICO',
            'UNIDADE': 'UNIDADE',
            'CUSTO UNITÁRIO': 'CUSTO_UNITARIO',
            'regiao': 'REGIAO'
        })
        
        print(f"\nTotal de registros válidos para importação: {len(df)}")
        
        # Pega o caminho do banco SQLite das configurações do Django
        db_path = settings.DATABASES['default']['NAME']
        
        # Conecta diretamente ao SQLite
        with sqlite3.connect(db_path) as conn:
            # Apaga registros existentes (opcional)
            # conn.execute('DELETE FROM app_seinfra_mg')
            
            # Importa os dados direto do DataFrame
            df.to_sql('app_seinfra_mg', conn, if_exists='append', index=False)
        
        print("Importação concluída com sucesso!")
        
        # Verifica o total no banco
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM app_seinfra_mg')
            total = cursor.fetchone()[0]
            print(f"\nTotal de registros no banco: {total}")
            
            # Mostra total por região
            cursor.execute('''
                SELECT REGIAO, COUNT(*) as total 
                FROM app_seinfra_mg 
                GROUP BY REGIAO 
                ORDER BY REGIAO
            ''')
            print("\nDistribuição por região:")
            for regiao, count in cursor.fetchall():
                print(f"{regiao}: {count} registros")
            
    except Exception as e:
        print(f"Erro durante a importação: {str(e)}")
        import traceback
        print(traceback.format_exc())

if __name__ == "__main__":
    print("Este script deve ser importado pelo scraping.py")