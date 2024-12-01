import psycopg2
import pandas as pd
import os

def importar_csv_direto(arquivo_csv, request=None):
    def log_message(message):
        print(message)
        if request and hasattr(request, 'send_event'):
            request.send_event({'message': message})

    try:
        log_message("\n" + "="*50)
        log_message("INICIANDO IMPORTAÇÃO DO CSV PARA O BANCO")
        log_message("="*50)
        
        # Primeiro testa a conexão
        log_message("\nTestando conexão com o banco...")
        conn_str = "postgresql://postgres:postgres@db:5432/postgres"
        conn = psycopg2.connect(conn_str)
        log_message("Conexão bem sucedida!")
        
        cursor = conn.cursor()
        
        # Agora tenta ler o CSV
        log_message(f"\nTentando ler arquivo: {arquivo_csv}")
        df = pd.read_csv(arquivo_csv, encoding='utf-8-sig')
        log_message(f"CSV lido com sucesso! Total de registros: {len(df)}")
        
        # Cria a tabela se não existir
        log_message("\nCriando tabela se não existir...")
        create_table_query = """
        CREATE TABLE IF NOT EXISTS precos_setop (
            id SERIAL PRIMARY KEY,
            codigo VARCHAR(50),
            descricao_servico TEXT,
            unidade VARCHAR(20),
            custo_unitario DECIMAL(10,2),
            regiao VARCHAR(50),
            data_importacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        
        # Drop a tabela antiga e cria nova
        log_message("Removendo tabela antiga...")
        cursor.execute("DROP TABLE IF EXISTS precos_setop;")
        cursor.execute(create_table_query)
        log_message("Tabela recriada!")
        
        # Prepara e insere os dados
        log_message("\nPreparando dados para inserção...")
        valores = []
        for _, row in df.iterrows():
            valores.append((
                str(row['CÓDIGO'])[:50],
                row['DESCRIÇÃO DO SERVIÇO'],
                str(row['UNIDADE'])[:20],
                float(row['CUSTO UNITÁRIO']),
                row['regiao'][:50]
            ))
        
        log_message(f"Inserindo {len(valores)} registros...")
        insert_query = """
        INSERT INTO precos_setop (codigo, descricao_servico, unidade, custo_unitario, regiao)
        VALUES (%s, %s, %s, %s, %s);
        """
        cursor.executemany(insert_query, valores)
        
        # Commit e fechamento
        conn.commit()
        log_message("Dados commitados com sucesso!")
        
        cursor.close()
        conn.close()
        log_message("Conexão fechada!")
        
        log_message("\n" + "="*50)
        log_message("IMPORTAÇÃO CONCLUÍDA COM SUCESSO")
        log_message("="*50)
        return True
        
    except Exception as e:
        log_message(f"Erro: {str(e)}")
        import traceback
        log_message(traceback.format_exc())
        return False

if __name__ == "__main__":
    # Para teste direto no container
    csv_path = '/app/data/planilhas_consolidadas.csv'
    resultado = importar_csv_direto(csv_path)
    print("Sucesso!" if resultado else "Falha!")