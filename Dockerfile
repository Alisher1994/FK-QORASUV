# Используем Python образ с предустановленными библиотеками для face_recognition
FROM python:3.11-slim

# Устанавливаем системные зависимости
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    libopenblas-dev \
    liblapack-dev \
    libx11-dev \
    libgtk-3-dev \
    libboost-python-dev \
    libboost-thread-dev \
    && rm -rf /var/lib/apt/lists/*

# Создаем рабочую директорию
WORKDIR /app

# Копируем файлы requirements
COPY requirements.txt .

# Возвращаем face_recognition в requirements
RUN pip install --no-cache-dir \
    Flask==3.0.0 \
    Flask-SQLAlchemy==3.1.1 \
    Flask-Login==0.6.3 \
    Flask-Bcrypt==1.0.1 \
    Pillow==10.1.0 \
    numpy==1.26.2 \
    python-dotenv==1.0.0 \
    Werkzeug==3.0.1 \
    gunicorn==21.2.0 \
    dlib==19.24.2 \
    face-recognition==1.3.0 \
    opencv-python-headless==4.8.1.78

# Копируем весь проект
COPY . .

# Создаем необходимые директории
RUN mkdir -p database frontend/static/uploads

# Указываем порт
EXPOSE 8080

# Запускаем приложение
CMD gunicorn app:app --bind 0.0.0.0:$PORT --timeout 120 --workers 2
