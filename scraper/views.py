from django.shortcuts import render
from django.http import JsonResponse, StreamingHttpResponse
from .scraping import iniciar_scraping
import queue
import threading

# Fila global para mensagens
message_queue = queue.Queue()

def scraper_view(request):
    if request.method == 'POST':
        # Limpa a fila antes de iniciar novo scraping
        while not message_queue.empty():
            message_queue.get()
            
        thread = threading.Thread(target=iniciar_scraping, args=(message_queue,))
        thread.start()
        return render(request, 'scraper/resultado.html')
    return render(request, 'scraper/index.html')

def progress_stream(request):
    def event_stream():
        while True:
            try:
                message = message_queue.get(timeout=60)  # Timeout de 60 segundos
                yield f"data: {message}\n\n"
            except queue.Empty:
                yield "data: [FIM]\n\n"
                break
            
    response = StreamingHttpResponse(event_stream(), content_type='text/event-stream')
    response['Cache-Control'] = 'no-cache'
    return response
