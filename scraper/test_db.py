import os
import sys
from pathlib import Path
from decimal import Decimal
import pandas as pd
import numpy as np

# Adiciona o diretório raiz do projeto ao PYTHONPATH
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

# Configura as variáveis de ambiente do Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

from django.db import connection
from django.core.management import call_command
from app.models import SEINFRA_MG

def criar_tabela_se_nao_existir():
    try:
        # Verifica se a tabela existe
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='SEINFRA_MG';
            """)
            tabela_existe = cursor.fetchone() is not None

        if not tabela_existe:
            print("Tabela não encontrada. Criando...")
            # Executa as migrações
            call_command('makemigrations', 'app')
            call_command('migrate')
            print("Tabela criada com sucesso!")
        else:
            print("Tabela já existe!")
        
        return True
    except Exception as e:
        print(f"Erro ao verificar/criar tabela: {str(e)}")
        return False

def importar_csv():
    try:
        if not criar_tabela_se_nao_existir():
            return

        arquivo_csv = 'planilhas_consolidadas.csv'
        if not os.path.exists(arquivo_csv):
            print(f"Arquivo {arquivo_csv} não encontrado!")
            return

        print(f"\nLendo arquivo {arquivo_csv}...")
        df = pd.read_csv(arquivo_csv, encoding='utf-8-sig')
        
        # Debug: mostrar as colunas e primeiras linhas
        print("\nColunas do DataFrame:")
        print(df.columns.tolist())
        print("\nPrimeiras linhas do DataFrame:")
        print(df.head())
        
        # Remove linhas que contêm 'CÓDIGO' ou 'DESCRIÇÃO DO SERVIÇO' na coluna CÓDIGO
        df = df[~df['CÓDIGO'].astype(str).str.contains('CÓDIGO|DESCRIÇÃO DO SERVIÇO', na=False)]
        df = df.dropna(subset=['CÓDIGO'])
        
        print("\nPrimeiras linhas após limpeza:")
        print(df.head())
        
        print(f"Total de linhas para importação após limpeza: {len(df)}")

        # Limpa a tabela antes de inserir novos dados
        SEINFRA_MG.objects.all().delete()
        print("Tabela limpa com sucesso!")

        # Lista para armazenar os objetos antes do bulk create
        objetos_para_criar = []
        erros = 0

        for _, row in df.iterrows():
            try:
                # Verifica se o código é válido antes de criar o objeto
                codigo = str(row['CÓDIGO']).strip()
                if codigo and codigo != 'nan':
                    objeto = SEINFRA_MG(
                        REGIAO=str(row['REGIÃO']).strip(),
                        CODIGO=codigo,
                        DESCRICAO_DE_SERVICO=str(row['DESCRIÇÃO DE SERVIÇO']).strip(),
                        UNIDADE=str(row['UNIDADE']).strip() if pd.notna(row['UNIDADE']) else '',
                        CUSTO_UNITARIO=Decimal(str(row['CUSTO UNITÁRIO']).replace('R$', '').strip().replace(',', '.')) if pd.notna(row['CUSTO UNITÁRIO']) else Decimal('0.00')
                    )
                    objetos_para_criar.append(objeto)

                if len(objetos_para_criar) % 1000 == 0:
                    print(f"Preparados {len(objetos_para_criar)} registros...")

            except Exception as e:
                print(f"Erro ao processar linha: {str(e)}")
                print(f"Dados da linha: {row.to_dict()}")
                erros += 1

        # Faz o bulk create com batch_size para melhor performance
        print("\nInserindo registros no banco de dados...")
        SEINFRA_MG.objects.bulk_create(objetos_para_criar, batch_size=1000)
        
        print(f"\nImportação concluída!")
        print(f"Registros importados com sucesso: {len(objetos_para_criar)}")
        print(f"Registros com erro: {erros}")

        print("\nAmostra dos registros importados (primeiros 5 válidos):")
        registros_validos = SEINFRA_MG.objects.exclude(
            DESCRICAO_DE_SERVICO__isnull=True
        ).exclude(
            DESCRICAO_DE_SERVICO__exact=''
        ).order_by('CODIGO')[:5]

        for reg in registros_validos:
            print(f"\nREGIAO: {reg.REGIAO}")
            print(f"CODIGO: {reg.CODIGO}")
            print(f"DESCRICAO: {reg.DESCRICAO_DE_SERVICO}")
            print(f"UNIDADE: {reg.UNIDADE}")
            print(f"CUSTO: R$ {reg.CUSTO_UNITARIO:.2f}")

    except Exception as e:
        print(f"Erro durante a importação: {str(e)}")

if __name__ == "__main__":
    importar_csv()