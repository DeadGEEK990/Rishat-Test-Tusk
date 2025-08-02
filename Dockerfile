FROM python:3.12-slim

# Устанавливаем системные зависимости и netcat (если нужен wait-for-db)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Копируем requirements.txt и устанавливаем зависимости
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь проект
COPY . /app/

# Устанавливаем переменную окружения для Django
ENV DJANGO_SETTINGS_MODULE=config.settings

# Копируем entrypoint и даём права на исполнение
COPY ./entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000"]
