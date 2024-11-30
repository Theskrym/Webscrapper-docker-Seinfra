#!/bin/bash

# Espera pelo banco de dados (se necessário)
# python manage.py wait_for_db

# Aplica as migrações
python manage.py migrate --noinput

# Coleta arquivos estáticos (se necessário)
# python manage.py collectstatic --noinput

# Executa o comando passado para o container
exec "$@" 