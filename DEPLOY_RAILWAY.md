# Деплой на Railway - Пошаговая инструкция

## Шаг 1: Подготовка GitHub репозитория

### 1.1 Инициализация Git (если ещё не сделано)

```bash
cd C:\Users\LOQ\Desktop\App\CAM\football_school
git init
```

### 1.2 Создание репозитория на GitHub

1. Откройте https://github.com
2. Нажмите "New repository"
3. Название: `football-school-crm` (или любое другое)
4. Сделайте его приватным или публичным
5. НЕ создавайте README, .gitignore (у вас уже есть)
6. Нажмите "Create repository"

### 1.3 Загрузка кода на GitHub

```bash
git add .
git commit -m "Initial commit - Football School CRM"
git branch -M main
git remote add origin https://github.com/Alisher1994/football-school-crm.git
git push -u origin main
```

⚠️ **Замените** `Alisher1994/football-school-crm` на ваше имя пользователя и название репозитория!

## Шаг 2: Регистрация на Railway

1. Откройте https://railway.app
2. Нажмите "Login" → "Login with GitHub"
3. Авторизуйтесь через GitHub
4. Разрешите доступ к репозиториям

## Шаг 3: Создание проекта на Railway

### 3.1 Новый проект

1. На главной странице Railway нажмите "New Project"
2. Выберите "Deploy from GitHub repo"
3. Найдите ваш репозиторий `football-school-crm`
4. Нажмите "Deploy Now"

### 3.2 Railway автоматически:

- Обнаружит Python проект
- Установит зависимости из `requirements.txt`
- Запустит через `gunicorn` (из `Procfile`)
- Назначит публичный URL

## Шаг 4: Настройка переменных окружения

### 4.1 В Railway:

1. Откройте ваш проект
2. Перейдите на вкладку "Variables"
3. Добавьте переменные:

```
SECRET_KEY=ваш_случайный_секретный_ключ_минимум_32_символа
FLASK_ENV=production
```

### 4.2 Генерация SECRET_KEY:

В PowerShell выполните:
```powershell
python -c "import secrets; print(secrets.token_hex(32))"
```

Скопируйте полученную строку и используйте как `SECRET_KEY`

## Шаг 5: Получение публичного URL

1. В Railway откройте вкладку "Settings"
2. В разделе "Domains" нажмите "Generate Domain"
3. Railway создаст URL типа: `https://football-school-crm-production.up.railway.app`
4. Сохраните этот URL!

## Шаг 6: Проверка деплоя

1. Откройте ваш Railway URL
2. Вы должны увидеть страницу входа
3. Войдите с учётными данными:
   - Username: `admin`
   - Password: `admin123`

## Шаг 7: Создание пользователей (опционально)

Если нужно создать дополнительных пользователей:

1. В Railway откройте ваш проект
2. Перейдите в "Deployments"
3. Нажмите на последний деплой
4. Откройте "View Logs"
5. Нажмите "Open Shell"
6. Выполните команды:

```bash
# Создать админа
python -c "from backend.models.models import db, User; from app import app, bcrypt; app.app_context().push(); u = User(username='admin2', password_hash=bcrypt.generate_password_hash('password123').decode('utf-8'), role='admin'); db.session.add(u); db.session.commit(); print('✅ Admin created')"

# Создать финансиста
python -c "from backend.models.models import db, User; from app import app, bcrypt; app.app_context().push(); u = User(username='financier', password_hash=bcrypt.generate_password_hash('password123').decode('utf-8'), role='financier'); db.session.add(u); db.session.commit(); print('✅ Financier created')"

# Создать мобильного администратора оплат
python -c "from backend.models.models import db, User; from app import app, bcrypt; app.app_context().push(); u = User(username='payment', password_hash=bcrypt.generate_password_hash('payment123').decode('utf-8'), role='payment_admin'); db.session.add(u); db.session.commit(); print('✅ Payment admin created')"

# Создать учителя
python -c "from backend.models.models import db, User; from app import app, bcrypt; app.app_context().push(); u = User(username='teacher', password_hash=bcrypt.generate_password_hash('teacher123').decode('utf-8'), role='teacher', group_id=1); db.session.add(u); db.session.commit(); print('✅ Teacher created')"
```

## Шаг 8: База данных

### SQLite (по умолчанию)

Railway сохраняет SQLite файл, НО при каждом редеплое он может удалиться!

### PostgreSQL (рекомендуется для production)

1. В Railway проекте нажмите "New" → "Database" → "Add PostgreSQL"
2. Railway автоматически создаст переменную `DATABASE_URL`
3. Обновите `requirements.txt`, добавив:
```
psycopg2-binary==2.9.9
```
4. Закоммитьте и запушьте изменения
5. Railway автоматически редеплоит

## Шаг 9: Обновление приложения

При любых изменениях в коде:

```bash
git add .
git commit -m "Описание изменений"
git push
```

Railway автоматически обнаружит изменения и редеплоит проект!

## Полезные команды Railway CLI (опционально)

### Установка Railway CLI:

```bash
npm install -g @railway/cli
```

### Вход:

```bash
railway login
```

### Просмотр логов:

```bash
railway logs
```

### Открытие shell:

```bash
railway shell
```

## Проблемы и решения

### ❌ Ошибка "Application failed to respond"

**Решение:** Проверьте логи в Railway. Убедитесь, что:
- `gunicorn` установлен в `requirements.txt`
- `Procfile` содержит правильную команду
- Порт берётся из `$PORT` переменной

### ❌ База данных пустая после редеплоя

**Решение:** Используйте PostgreSQL вместо SQLite для production

### ❌ Ошибки с face_recognition

**Решение:** Railway может не поддерживать `dlib`. Варианты:
- Отключите распознавание лиц для production
- Используйте Docker деплой
- Перейдите на другой хостинг (Heroku, DigitalOcean)

## Мобильный доступ

Ваш Railway URL доступен с любого устройства:

- **Мобильные оплаты**: `https://ваш-url.up.railway.app/mobile-payments`
- **Перекличка учителя**: `https://ваш-url.up.railway.app/teacher-attendance`

Учителя и payment_admin могут открыть эти страницы на телефоне!

## Готово! 🎉

Теперь ваша система доступна 24/7 из любой точки мира!
