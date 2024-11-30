from django.shortcuts import render
from django.http import JsonResponse, StreamingHttpResponse
import json
import subprocess
import os
import queue
import threading
import sys
from datetime import datetime

# Fila global para mensagens
message_queue = queue.Queue()

class StreamToQueue:
    def __init__(self, queue):
        self.queue = queue

    def write(self, text):
        if text.strip():  # Ignora linhas vazias
            timestamp = datetime.now().strftime('%H:%M:%S')
            self.queue.put(f"[{timestamp}] {text.strip()}")

    def flush(self):
        pass

def scraper_view(request):
    if request.method == 'POST':
        try:
            print("Iniciando processo de scraping...")
            
            # Configura o redirecionamento da saída
            original_stdout = sys.stdout
            sys.stdout = StreamToQueue(message_queue)
            
            # Inicia o processo em uma thread separada
            def run_scraper():
                try:
                    script_dir = os.path.dirname(os.path.abspath(__file__))
                    script_path = os.path.join(script_dir, 'scraping.py')
                    
                    # Configura o ambiente para o subprocess
                    env = os.environ.copy()
                    env['PYTHONPATH'] = os.path.dirname(script_dir)  # Adiciona o diretório pai ao PYTHONPATH
                    
                    # Executa o script como módulo Python
                    process = subprocess.Popen(
                        ['python', '-c', 
                         f'import sys; sys.path.append("{os.path.dirname(script_dir)}"); '
                         f'from scraper.scraping import scraper_seinfra; '
                         'scraper_seinfra()'],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        universal_newlines=True,
                        bufsize=1,
                        env=env,
                        cwd=script_dir
                    )
                    
                    # Lê a saída em tempo real
                    while True:
                        output = process.stdout.readline()
                        if output == '' and process.poll() is not None:
                            break
                        if output:
                            message_queue.put(output.strip())
                    
                    # Captura erros
                    _, stderr = process.communicate()
                    if stderr:
                        message_queue.put(f"ERRO: {stderr}")
                        
                finally:
                    sys.stdout = original_stdout
            
            # Inicia a thread
            thread = threading.Thread(target=run_scraper)
            thread.daemon = True
            thread.start()
            
            return JsonResponse({
                'status': 'started',
                'message': 'Processo iniciado'
            })
                
        except Exception as e:
            print(f"Erro na view: {str(e)}")
            return JsonResponse({
                'status': 'error',
                'message': f'Erro ao executar scraping: {str(e)}'
            })
    return render(request, 'scraper/index.html')

def progress_stream(request):
    def event_stream():
        while True:
            try:
                # Pega mensagem da fila com timeout
                message = message_queue.get(timeout=1)
                yield f"data: {json.dumps({'message': message})}\n\n"
            except queue.Empty:
                # Se não houver mensagens, envia heartbeat
                yield f"data: {json.dumps({'heartbeat': True})}\n\n"
    
    return StreamingHttpResponse(event_stream(), content_type='text/event-stream')
