#!/bin/bash
# start.sh

# Aplica as migrações
python manage.py migrate

# Inicia o scheduler em segundo plano
python manage.py start_scheduler &

# Inicia o servidor Django
python manage.py runserver 0.0.0.0:8000