# Web Scraper SEINFRA-MG

Aplicação Django para coletar e armazenar dados das planilhas de preço da SEINFRA-MG (Secretaria de Estado de Infraestrutura e Mobilidade de Minas Gerais).

## 🚀 Funcionalidades

- Coleta automática de planilhas de preços de todas as regiões
- Interface web para acompanhamento em tempo real
- Processamento assíncrono em background
- Merge automático de dados para evitar duplicatas
- Exportação para CSV
- Compatível com Docker

## 📋 Pré-requisitos

- Python 3.12+
- Firefox (para execução local)
- Docker (opcional)
- Git

## 🔧 Instalação

### Usando Docker (Recomendado)

1. Clone o repositório:

        bash

        git clone https://github.com/Theskrym/Webscrapper-docker-Seinfra.git

        cd Webscrapper-docker-Seinfra


2. Construa e inicie os containers:

        bash
        docker compose up --build

3. Acesse http://localhost:8000/scraper/

### Instalação Local

1. Clone o repositório:

        bash
        git clone https://github.com/Theskrym/Webscrapper-docker-Seinfra.git
        cd Webscrapper-docker-Seinfra

2. Crie e ative um ambiente virtual:

        bash
        python -m venv venv
        source venv/bin/activate

    Windows

        venv\Scripts\activate

    Linux/Mac

        source venv/bin/activate

3. Instale as dependências:

        bash
        pip install -r requirements.txt

4. Execute as migrações:

        bash
        python manage.py makemigrations
        python manage.py migrate

5. Inicie o servidor:

        bash
        python manage.py runserver

6. Acesse http://localhost:8000/scraper/

## 🛠️ Como Usar

1. Acesse a interface web em http://localhost:8000/scraper/
2. Clique no botão "Iniciar Scraping"
3. Acompanhe o progresso em tempo real na página
4. Os dados serão salvos em `planilhas_consolidadas.csv`

### Endpoints Disponíveis

- `/scraper/` - Interface principal
- `/scraper/progress/` - Stream de progresso em tempo real

## 📊 Dados Coletados

O scraper coleta as seguintes informações:
- Código do item
- Descrição do serviço
- Unidade de medida
- Custo unitário
- Região
- Ano de referência

Os dados são salvos em formato CSV com as seguintes colunas:
- CÓDIGO
- DESCRIÇÃO DE SERVIÇO
- UNIDADE
- CUSTO UNITÁRIO
- REGIÃO
- ANO

## 🔄 Processo de Merge

O sistema realiza merge automático dos dados para evitar duplicatas:
1. Gera hash único para cada registro baseado em código, região e ano
2. Compara com dados existentes
3. Atualiza registros existentes
4. Adiciona novos registros
5. Remove duplicatas mantendo versão mais recente

## ⚠️ Notas Importantes

- Certifique-se de ter o Firefox instalado para execução local
- O Docker deve estar instalado e rodando para usar a versão containerizada
- O processo de scraping pode levar alguns minutos dependendo da quantidade de dados
- Os dados são salvos automaticamente após cada execução

## 🐛 Resolução de Problemas

### Erro de Conexão
Se encontrar erros de conexão:
1. Verifique sua conexão com a internet
2. Confirme se o site da SEINFRA está acessível
3. Tente novamente em alguns minutos

### Erro no Firefox
Se o Firefox não iniciar:
1. Verifique se está instalado
2. Atualize para a última versão
3. No Docker, certifique-se que a imagem foi construída corretamente

## 📄 Licença

Este projeto está sob a licença MIT. Veja o arquivo [LICENSE](LICENSE) para mais detalhes.

## 🤝 Contribuindo

1. Faça um Fork do projeto
2. Crie uma Branch para sua Feature (`git checkout -b feature/AmazingFeature`)
3. Faça o Commit de suas mudanças (`git commit -m 'Add some AmazingFeature'`)
4. Faça o Push para a Branch (`git push origin feature/AmazingFeature`)
5. Abra um Pull Request