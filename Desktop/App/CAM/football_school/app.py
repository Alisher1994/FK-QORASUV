from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_bcrypt import Bcrypt
from werkzeug.utils import secure_filename
import os
import face_recognition
from datetime import datetime, timedelta, time, date
from sqlalchemy import func

from backend.models.models import db, User, Student, Payment, Attendance, Expense, Group, Tariff, ClubSettings, RewardType, StudentReward
from backend.services.face_service import FaceRecognitionService
from backend.data.locations import get_cities, get_districts

# Получить абсолютный путь к папке проекта
basedir = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__, 
            template_folder='frontend/templates',
            static_folder='frontend/static')

# Конфигурация для production/development
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-change-in-production')

# PostgreSQL URL для Railway (автоматически устанавливается)
database_url = os.environ.get('DATABASE_URL')
if database_url:
    # Railway PostgreSQL использует postgres://, но SQLAlchemy требует postgresql://
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
else:
    # Локальная разработка - SQLite
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'database', 'football_school.db')

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join(basedir, 'frontend', 'static', 'uploads')

UPLOAD_FOLDER = app.config['UPLOAD_FOLDER']

db.init_app(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

face_service = FaceRecognitionService()

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


DAY_LABELS = {
    1: 'Пн', 2: 'Вт', 3: 'Ср', 4: 'Чт', 5: 'Пт', 6: 'Сб', 7: 'Вс'
}


def get_club_settings_instance():
    ensure_club_settings_columns()
    settings = ClubSettings.query.first()
    if not settings:
        settings = ClubSettings(system_name='FK QORASUV')
        db.session.add(settings)
        db.session.commit()
    return settings


def ensure_club_settings_columns():
    """Добавляет отсутствующие колонки в club_settings (на случай старой БД)"""
    inspector = db.inspect(db.engine)
    tables = inspector.get_table_names()
    if 'club_settings' not in tables:
        with app.app_context():
            db.create_all()
        return

    columns = {col['name'] for col in inspector.get_columns('club_settings')}
    with db.engine.begin() as conn:
        if 'system_name' not in columns:
            conn.execute(db.text("ALTER TABLE club_settings ADD COLUMN system_name VARCHAR(200)"))
        if 'rewards_reset_period_months' not in columns:
            # SQLite использует INTEGER, PostgreSQL тоже поддерживает
            conn.execute(db.text("ALTER TABLE club_settings ADD COLUMN rewards_reset_period_months INTEGER DEFAULT 1"))
        if 'podium_display_count' not in columns:
            conn.execute(db.text("ALTER TABLE club_settings ADD COLUMN podium_display_count INTEGER DEFAULT 20"))


def calculate_student_balance(student):
    """
    Расчёт баланса ученика в занятиях.
    Баланс = (сумма оплат / стоимость 1 занятия) - количество посещений
    Стоимость 1 занятия = цена тарифа / кол-во занятий в тарифе
    """
    if not student:
        return 0
    
    # Получаем стоимость одного занятия из тарифа
    lesson_price = 0
    if student.tariff_id:
        tariff = Tariff.query.get(student.tariff_id)
        if tariff and tariff.price and tariff.lessons_count and tariff.lessons_count > 0:
            lesson_price = float(tariff.price) / float(tariff.lessons_count)
    
    if lesson_price <= 0:
        # Если тариф не задан или некорректный, возвращаем старый баланс
        return student.balance if student.balance else 0
    
    # Сумма всех оплат ученика
    total_paid = db.session.query(db.func.sum(Payment.amount_paid)).filter(
        Payment.student_id == student.id
    ).scalar() or 0
    
    # Количество посещений (занятий)
    attendance_count = Attendance.query.filter_by(student_id=student.id).count()
    
    # Баланс в занятиях = оплачено занятий - посещено занятий
    paid_lessons = int(total_paid / lesson_price)
    balance = paid_lessons - attendance_count
    
    return balance


def parse_days_list(raw_days):
    if raw_days is None:
        return []
    if isinstance(raw_days, list):
        return [int(day) for day in raw_days if str(day).isdigit()]
    if isinstance(raw_days, str):
        return [int(day) for day in raw_days.split(',') if day.strip().isdigit()]
    return []


def validate_group_schedule(schedule_time, schedule_days, exclude_group_id=None):
    if schedule_time is None:
        return False, 'Укажите время занятия'
    settings = get_club_settings_instance()
    working_days = set(settings.get_working_days_list())
    selected_days = set(schedule_days)
    if not selected_days:
        return False, 'Выберите хотя бы один день недели'
    if not selected_days.issubset(working_days):
        return False, 'Выбранные дни не входят в рабочий график клуба'
    if schedule_time < settings.work_start_time or schedule_time > settings.work_end_time:
        return False, 'Время занятия вне рабочего времени клуба'
    groups_same_time = Group.query.filter_by(schedule_time=schedule_time).all()
    for day in selected_days:
        count = 0
        for group in groups_same_time:
            if exclude_group_id and group.id == exclude_group_id:
                continue
            if day in group.get_schedule_days_list():
                count += 1
        if count >= settings.max_groups_per_slot:
            return False, f"Нет свободного поля на {DAY_LABELS.get(day, day)} {schedule_time.strftime('%H:%M')}"
    return True, ''


@app.template_filter('format_thousand')
def format_thousand(value):
    try:
        if value is None:
            return ''
        number = float(value)
        if number.is_integer():
            return '{:,.0f}'.format(number).replace(',', ' ')
        return '{:,.2f}'.format(number).replace(',', ' ')
    except (TypeError, ValueError):
        return value


@app.template_filter('format_date')
def format_date(value, fmt='%d.%m.%Y'):
    if not value:
        return ''
    if isinstance(value, str):
        try:
            value = datetime.strptime(value, '%Y-%m-%d')
        except ValueError:
            return value
    if isinstance(value, datetime):
        return value.strftime(fmt)
    try:
        return value.strftime(fmt)
    except AttributeError:
        return value


@app.context_processor
def inject_system_name():
    """Добавляет название системы во все шаблоны"""
    try:
        settings = get_club_settings_instance()
        name = settings.system_name or 'FK QORASUV'
    except Exception:
        name = 'FK QORASUV'
    return {'system_name': name}


# ===== МАРШРУТЫ АВТОРИЗАЦИИ =====

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        if user and bcrypt.check_password_hash(user.password_hash, password):
            login_user(user)
            # Перенаправление в зависимости от роли
            if user.role == 'payment_admin':
                return jsonify({'success': True, 'role': user.role, 'redirect': '/mobile-payments'})
            elif user.role == 'teacher':
                return jsonify({'success': True, 'role': user.role, 'redirect': '/teacher-attendance'})
            return jsonify({'success': True, 'role': user.role})
        else:
            return jsonify({'success': False, 'message': 'Неверный логин или пароль'}), 401
    
    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


# ===== ГЛАВНАЯ ПАНЕЛЬ =====

@app.route('/dashboard')
@login_required
def dashboard():
    # Статистика
    total_students = Student.query.filter_by(status='active').count()
    # Подсчет студентов с низким балансом (<=2 занятия)
    active_students = Student.query.filter_by(status='active').all()
    students_low_balance = sum(1 for s in active_students if calculate_student_balance(s) <= 2)
    
    today = datetime.utcnow().date()
    today_attendance = Attendance.query.filter_by(date=today).count()
    
    # Доходы за месяц
    month_start = datetime.utcnow().replace(day=1)
    month_income = db.session.query(db.func.sum(Payment.amount_paid)).filter(
        Payment.payment_date >= month_start
    ).scalar() or 0
    
    # Расходы за месяц
    month_expenses = db.session.query(db.func.sum(Expense.amount)).filter(
        Expense.expense_date >= month_start
    ).scalar() or 0
    
    return render_template('dashboard.html',
                         total_students=total_students,
                         students_low_balance=students_low_balance,
                         today_attendance=today_attendance,
                         month_income=month_income,
                         month_expenses=month_expenses,
                         profit=month_income - month_expenses)


# ===== УЧЕНИКИ =====

@app.route('/students')
@login_required
def students():
    from datetime import date
    all_students = Student.query.order_by(Student.full_name.asc()).all()
    balances = {s.id: calculate_student_balance(s) for s in all_students}

    latest_payment_subquery = db.session.query(
        Payment.student_id,
        db.func.max(Payment.payment_date).label('latest_date')
    ).group_by(Payment.student_id).subquery()

    latest_payments = db.session.query(Payment).join(
        latest_payment_subquery,
        Payment.student_id == latest_payment_subquery.c.student_id
    ).filter(Payment.payment_date == latest_payment_subquery.c.latest_date).all()

    payment_info = {}
    for payment in latest_payments:
        payment_info[payment.student_id] = {
            'date': payment.payment_date.strftime('%d.%m.%Y') if payment.payment_date else None,
            'amount': payment.amount_paid,
            'debt': payment.amount_due
        }
    
    # Подсчет баллов для текущего месяца
    current_month = date.today().month
    current_year = date.today().year
    student_points = {}
    for student in all_students:
        total_points = db.session.query(func.sum(StudentReward.points)).filter(
            StudentReward.student_id == student.id,
            StudentReward.month == current_month,
            StudentReward.year == current_year
        ).scalar() or 0
        student_points[student.id] = total_points

    return render_template('students.html',
                           students=all_students,
                           payment_info=payment_info,
                           balances=balances,
                           student_points=student_points)


@app.route('/groups')
@login_required
def groups_page():
    return render_template('groups.html')


@app.route('/api/students', methods=['GET'])
@login_required
def get_students_list():
    """Возвращает всех учеников для фильтров"""
    students = Student.query.order_by(Student.full_name.asc()).all()
    result = []
    for student in students:
        result.append({
            'id': student.id,
            'full_name': student.full_name,
            'student_number': student.student_number,
            'group_id': student.group_id,
            'group_name': student.group.name if student.group else None,
            'status': student.status,
            'photo_path': student.photo_path,
            'admission_date': student.admission_date.isoformat() if student.admission_date else None
        })
    return jsonify(result)


@app.route('/api/students/add', methods=['POST'])
@login_required
def add_student():
    try:
        full_name = request.form.get('full_name')
        phone = request.form.get('phone')
        parent_phone = request.form.get('parent_phone')
        photo = request.files.get('photo')
        
        # Новые поля
        group_id = request.form.get('group_id')
        tariff_id = request.form.get('tariff_id')
        school_number = request.form.get('school_number')
        city = request.form.get('city')
        district = request.form.get('district')
        street = request.form.get('street')
        house_number = request.form.get('house_number')
        
        birth_year = request.form.get('birth_year')
        passport_series = request.form.get('passport_series')
        passport_number = request.form.get('passport_number')
        passport_issued_by = request.form.get('passport_issued_by')
        passport_issue_date = request.form.get('passport_issue_date')
        passport_expiry_date = request.form.get('passport_expiry_date')
        admission_date_raw = request.form.get('admission_date')
        
        club_funded = request.form.get('club_funded') == 'true'
        status = request.form.get('status', 'active')
        blacklist_reason = request.form.get('blacklist_reason')
        student_number = (request.form.get('student_number') or '').strip()
        
        if not student_number:
            return jsonify({'success': False, 'message': 'Номер ученика обязателен'}), 400

        existing_number = Student.query.filter_by(student_number=student_number).first()
        if existing_number:
            return jsonify({'success': False, 'message': 'Ученик с таким номером уже существует'}), 400
        
        # Проверить, не переполнена ли группа
        if group_id:
            group = db.session.get(Group, int(group_id))
            if group and group.is_full():
                current_count = group.get_current_students_count()
                return jsonify({
                    'success': False, 
                    'message': f'Группа "{group.name}" заполнена ({current_count}/{group.max_students})'
                }), 400
        
        if admission_date_raw:
            try:
                admission_date = datetime.strptime(admission_date_raw, '%Y-%m-%d').date()
            except ValueError:
                return jsonify({'success': False, 'message': 'Некорректная дата принятия'}), 400
        else:
            admission_date = datetime.utcnow().date()

        # Создать ученика
        student = Student(
            student_number=student_number,
            school_number=school_number,
            full_name=full_name,
            phone=phone,
            parent_phone=parent_phone,
            balance=0,
            status=status,
            blacklist_reason=blacklist_reason if status == 'blacklist' else None,
            group_id=int(group_id) if group_id else None,
            tariff_id=int(tariff_id) if tariff_id else None,
            city=city,
            district=district,
            street=street,
            house_number=house_number,
            birth_year=int(birth_year) if birth_year else None,
            passport_series=passport_series,
            passport_number=passport_number,
            passport_issued_by=passport_issued_by,
            passport_issue_date=datetime.strptime(passport_issue_date, '%Y-%m-%d').date() if passport_issue_date else None,
            passport_expiry_date=datetime.strptime(passport_expiry_date, '%Y-%m-%d').date() if passport_expiry_date else None,
            admission_date=admission_date,
            club_funded=club_funded
        )
        db.session.add(student)
        db.session.flush()
        
        # Сохранить фото и извлечь face encoding
        if photo:
            photo_path = face_service.save_student_photo(photo, student.id)
            student.photo_path = photo_path
            
            encoding = face_service.extract_face_encoding(photo_path)
            if encoding is not None:
                student.set_face_encoding(encoding)
            else:
                return jsonify({'success': False, 'message': 'Лицо не обнаружено на фото'}), 400
        
        db.session.commit()
        
        # Перезагрузить encodings
        reload_face_encodings()
        
        return jsonify({'success': True, 'student_id': student.id, 'student_number': student_number})
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/students/<int:student_id>', methods=['GET'])
@login_required
def get_student(student_id):
    student = Student.query.get_or_404(student_id)
    tariff_price = student.tariff.price if student.tariff else 500000  # Дефолтная цена
    return jsonify({
        'id': student.id,
        'student_number': student.student_number,
        'school_number': student.school_number,
        'full_name': student.full_name,
        'phone': student.phone,
        'parent_phone': student.parent_phone,
        'balance': calculate_student_balance(student),
        'status': student.status,
        'blacklist_reason': student.blacklist_reason,
        'group_id': student.group_id,
        'tariff_id': student.tariff_id,
        'tariff_price': float(tariff_price),
        'city': student.city,
        'district': student.district,
        'street': student.street,
        'house_number': student.house_number,
        'birth_year': student.birth_year,
        'passport_series': student.passport_series,
        'passport_number': student.passport_number,
        'passport_issued_by': student.passport_issued_by,
        'passport_issue_date': student.passport_issue_date.isoformat() if student.passport_issue_date else None,
        'passport_expiry_date': student.passport_expiry_date.isoformat() if student.passport_expiry_date else None,
        'admission_date': student.admission_date.isoformat() if student.admission_date else None,
        'club_funded': student.club_funded,
        'photo_path': student.photo_path
    })


@app.route('/api/students/<int:student_id>', methods=['PUT'])
@login_required
def update_student(student_id):
    try:
        student = Student.query.get_or_404(student_id)
        
        if 'student_number' in request.form:
            new_student_number = request.form['student_number'].strip()
            if not new_student_number:
                return jsonify({'success': False, 'message': 'Номер ученика не может быть пустым'}), 400
            if new_student_number != student.student_number:
                existing_number = Student.query.filter_by(student_number=new_student_number).first()
                if existing_number and existing_number.id != student.id:
                    return jsonify({'success': False, 'message': 'Ученик с таким номером уже существует'}), 400
                student.student_number = new_student_number

        # Обновить поля из формы
        if 'full_name' in request.form:
            student.full_name = request.form['full_name']
        if 'school_number' in request.form:
            student.school_number = request.form['school_number'] or None
        if 'phone' in request.form:
            student.phone = request.form['phone'] or None
        if 'parent_phone' in request.form:
            student.parent_phone = request.form['parent_phone'] or None
        if 'status' in request.form:
            student.status = request.form['status']
            if request.form['status'] != 'blacklist':
                student.blacklist_reason = None
        if 'blacklist_reason' in request.form:
            student.blacklist_reason = request.form['blacklist_reason'] or None
        if 'group_id' in request.form:
            new_group_id = int(request.form['group_id']) if request.form['group_id'] else None
            # Проверить, не переполнена ли новая группа (если группа меняется)
            if new_group_id and new_group_id != student.group_id:
                new_group = db.session.get(Group, new_group_id)
                if new_group and new_group.is_full():
                    current_count = new_group.get_current_students_count()
                    return jsonify({
                        'success': False, 
                        'message': f'Группа "{new_group.name}" заполнена ({current_count}/{new_group.max_students})'
                    }), 400
            student.group_id = new_group_id
        if 'tariff_id' in request.form:
            student.tariff_id = int(request.form['tariff_id']) if request.form['tariff_id'] else None
        if 'city' in request.form:
            student.city = request.form['city'] or None
        if 'district' in request.form:
            student.district = request.form['district'] or None
        if 'street' in request.form:
            student.street = request.form['street'] or None
        if 'house_number' in request.form:
            student.house_number = request.form['house_number'] or None
        if 'birth_year' in request.form:
            student.birth_year = int(request.form['birth_year']) if request.form['birth_year'] else None
        if 'passport_series' in request.form:
            student.passport_series = request.form['passport_series'] or None
        if 'passport_number' in request.form:
            student.passport_number = request.form['passport_number'] or None
        if 'passport_issued_by' in request.form:
            student.passport_issued_by = request.form['passport_issued_by'] or None
        if 'passport_issue_date' in request.form and request.form['passport_issue_date']:
            student.passport_issue_date = datetime.strptime(request.form['passport_issue_date'], '%Y-%m-%d').date()
        if 'passport_expiry_date' in request.form and request.form['passport_expiry_date']:
            student.passport_expiry_date = datetime.strptime(request.form['passport_expiry_date'], '%Y-%m-%d').date()
        if 'admission_date' in request.form:
            if request.form['admission_date']:
                try:
                    student.admission_date = datetime.strptime(request.form['admission_date'], '%Y-%m-%d').date()
                except ValueError:
                    return jsonify({'success': False, 'message': 'Некорректная дата принятия'}), 400
            else:
                student.admission_date = None
        
        # Обработать чекбокс club_funded
        student.club_funded = 'club_funded' in request.form and request.form['club_funded'] == 'true'
        
        # Обработать новое фото (если загружено)
        if 'photo' in request.files:
            photo = request.files['photo']
            if photo and photo.filename:
                # Удалить старое фото
                if student.photo_path and os.path.exists(student.photo_path):
                    os.remove(student.photo_path)
                
                # Сохранить новое фото
                filename = secure_filename(photo.filename)
                photo_filename = f"student_{student.id}_{filename}"
                photo_path = os.path.join(UPLOAD_FOLDER, photo_filename)
                photo.save(photo_path)
                student.photo_path = photo_path
                
                # Создать новый face encoding
                try:
                    image = face_recognition.load_image_file(photo_path)
                    encodings = face_recognition.face_encodings(image)
                    if encodings:
                        student.face_encoding = encodings[0].tobytes()
                        reload_face_encodings()
                except Exception as e:
                    print(f"Ошибка обработки фото: {e}")
        
        db.session.commit()
        return jsonify({'success': True})
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/students/<int:student_id>', methods=['DELETE'])
@login_required
def delete_student(student_id):
    try:
        student = Student.query.get_or_404(student_id)
        student_name = student.full_name
        
        db.session.delete(student)
        db.session.commit()
        
        # Перезагрузить encodings
        reload_face_encodings()
        
        return jsonify({'success': True, 'message': f'Ученик {student_name} удалён'})
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


# ===== ПЛАТЕЖИ =====

@app.route('/api/payments/add', methods=['POST'])
@login_required
def add_payment():
    try:
        data = request.get_json()
        student_id = data.get('student_id')
        tariff_id = data.get('tariff_id')
        amount_paid = float(data.get('amount_paid'))
        amount_due = float(data.get('amount_due', 0))
        lessons_added = int(data.get('lessons_added', 0))
        is_full_payment = data.get('is_full_payment', True)
        notes = data.get('notes', '')
        
        student = Student.query.get_or_404(student_id)
        tariff = db.session.get(Tariff, tariff_id) if tariff_id else None
        
        # Создать платёж
        payment = Payment(
            student_id=student_id,
            tariff_id=tariff_id,
            amount_paid=amount_paid,
            amount_due=amount_due,
            lessons_added=lessons_added,
            is_full_payment=is_full_payment,
            tariff_name=tariff.name if tariff else None,
            notes=notes,
            created_by=current_user.id
        )
        db.session.add(payment)
        
        # Обновить тип тарифа при полной оплате
        if is_full_payment:
            student.tariff_type = tariff.name if tariff else None
        
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'new_balance': calculate_student_balance(student),
            'is_full_payment': is_full_payment,
            'amount_due': amount_due
        })
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


# ===== ПОСЕЩАЕМОСТЬ =====

@app.route('/attendance')
@login_required
def attendance_page():
    return render_template('attendance.html')


@app.route('/api/attendance/checkin', methods=['POST'])
def attendance_checkin():
    """Отметить вход ученика (вызывается из камеры)"""
    try:
        data = request.get_json()
        student_id = data.get('student_id')
        
        student = Student.query.get_or_404(student_id)
        today = datetime.utcnow().date()
        now = datetime.utcnow()
        
        # Проверить, был ли уже чекин сегодня
        existing = Attendance.query.filter_by(
            student_id=student_id,
            date=today
        ).first()
        
        if existing:
            return jsonify({'success': False, 'message': 'Уже отмечен сегодня'})
        
        # Проверка баланса: пропускаем даже при нуле/минусе, админ решает
        current_balance = calculate_student_balance(student)
        low_balance = (not student.club_funded and current_balance <= 0)
        
        # Определить опоздание
        is_late = False
        late_minutes = 0
        
        if student.group_id:
            group = db.session.get(Group, student.group_id)
            if group and group.schedule_time:
                scheduled_time = datetime.combine(today, group.schedule_time)
                time_diff = (now - scheduled_time).total_seconds() / 60
                
                if time_diff > group.late_threshold:
                    is_late = True
                    late_minutes = int(time_diff)
        
        # Создать запись посещения
        attendance = Attendance(
            student_id=student_id,
            date=today,
            lesson_deducted=not student.club_funded,
            is_late=is_late,
            late_minutes=late_minutes
        )
        db.session.add(attendance)
        
        # Баланс теперь рассчитывается динамически (оплачено занятий - посещено)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'student_name': student.full_name,
            'remaining_balance': calculate_student_balance(student),
            'is_late': is_late,
            'late_minutes': late_minutes,
            'club_funded': student.club_funded,
            'low_balance': low_balance
        })
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/attendance/today')
@login_required
def today_attendance():
    """Список присутствующих сегодня"""
    today = datetime.utcnow().date()
    records = Attendance.query.filter_by(date=today).all()
    
    result = []
    for record in records:
        photo_url = None
        if record.student.photo_path:
            normalized_path = record.student.photo_path.replace('frontend/static/', '').replace('\\', '/').lstrip('/')
            photo_url = url_for('static', filename=normalized_path)
        group_name = record.student.group.name if record.student.group else 'Без группы'
        student_balance = calculate_student_balance(record.student)
        low_balance = (not record.student.club_funded) and (student_balance <= 0)
        result.append({
            'id': record.id,
            'student_name': record.student.full_name,
            'photo_url': photo_url,
            'group_name': group_name,
            'check_in': record.check_in.strftime('%H:%M'),
            'balance': student_balance,
            'low_balance': low_balance
        })
    
    return jsonify(result)


@app.route('/api/attendance/years')
@login_required
def attendance_years():
    """Возвращает список годов, в которых есть записи посещаемости"""
    from sqlalchemy import extract
    years_query = db.session.query(extract('year', Attendance.check_in).label('year')) \
        .distinct() \
        .order_by(extract('year', Attendance.check_in).desc()) \
        .all()
    years = []
    for item in years_query:
        raw_value = item.year if hasattr(item, 'year') else item[0]
        if raw_value is None:
            continue
        years.append(int(raw_value))
    current_year = datetime.utcnow().year
    return jsonify({'years': years, 'current_year': current_year})


@app.route('/api/attendance/all')
@login_required
def all_attendance():
    """Список посещаемости с фильтрами"""
    from sqlalchemy import extract
    
    # Получение параметров фильтров
    year = request.args.get('year')
    month = request.args.get('month')
    group_id = request.args.get('group_id')
    student_id = request.args.get('student_id')
    
    # Базовый запрос
    query = db.session.query(Attendance).join(Student)
    
    # Применение фильтров
    if year:
        query = query.filter(extract('year', Attendance.check_in) == int(year))
    
    if month:
        query = query.filter(extract('month', Attendance.check_in) == int(month))
    
    if student_id:
        query = query.filter(Attendance.student_id == int(student_id))
    
    if group_id:
        query = query.filter(Student.group_id == int(group_id))
    
    # Сортировка по дате (сначала новые)
    records = query.order_by(Attendance.check_in.desc()).all()
    
    result = []
    for record in records:
        result.append({
            'id': record.id,
            'student_id': record.student_id,
            'student_name': record.student.full_name,
            'group_name': record.student.group.name if record.student.group else None,
            'check_in_time': record.check_in.isoformat(),
            'balance': calculate_student_balance(record.student)
        })
    
    return jsonify(result)


@app.route('/api/attendance/analytics', methods=['GET'])
@login_required
def get_attendance_analytics():
    """Аналитика посещаемости"""
    from sqlalchemy import func, extract
    from datetime import date
    
    year = request.args.get('year', type=int)
    if not year:
        year = date.today().year
    
    # Посещаемость по месяцам
    monthly_data = []
    for month in range(1, 13):
        count = db.session.query(func.count(Attendance.id)).filter(
            extract('year', Attendance.check_in) == year,
            extract('month', Attendance.check_in) == month
        ).scalar() or 0
        
        month_names = ['Янв', 'Фев', 'Мар', 'Апр', 'Май', 'Июн', 
                      'Июл', 'Авг', 'Сен', 'Окт', 'Ноя', 'Дек']
        monthly_data.append({
            'month': month,
            'month_name': month_names[month - 1],
            'count': count
        })
    
    # Посещаемость по дням недели (1=Пн, 7=Вс)
    # Получаем все записи за год и группируем по дням недели в Python
    all_attendance = Attendance.query.filter(
        extract('year', Attendance.check_in) == year
    ).all()
    
    weekday_counts = {i: 0 for i in range(1, 8)}  # 1=Пн, 7=Вс
    for att in all_attendance:
        if att.check_in:
            # weekday() возвращает 0=Пн, 6=Вс, конвертируем в 1-7
            weekday = att.check_in.weekday() + 1
            weekday_counts[weekday] = weekday_counts.get(weekday, 0) + 1
    
    weekday_data = [{
        'weekday': weekday,
        'count': weekday_counts[weekday]
    } for weekday in range(1, 8)]
    
    # Посещаемость по группам
    group_stats = db.session.query(
        Group.name.label('group_name'),
        func.count(Attendance.id).label('count')
    ).join(Student, Group.id == Student.group_id)\
     .join(Attendance, Student.id == Attendance.student_id)\
     .filter(extract('year', Attendance.check_in) == year)\
     .group_by(Group.id, Group.name)\
     .all()
    
    groups_data = [{
        'group_name': g.group_name,
        'count': g.count
    } for g in group_stats]
    
    # Статистика опозданий
    total_attendance = db.session.query(func.count(Attendance.id)).filter(
        extract('year', Attendance.check_in) == year
    ).scalar() or 0
    
    total_late = db.session.query(func.count(Attendance.id)).filter(
        extract('year', Attendance.check_in) == year,
        Attendance.is_late == True
    ).scalar() or 0
    
    avg_late = db.session.query(func.avg(Attendance.late_minutes)).filter(
        extract('year', Attendance.check_in) == year,
        Attendance.is_late == True,
        Attendance.late_minutes.isnot(None)
    ).scalar() or 0
    
    late_percentage = round((total_late / total_attendance * 100) if total_attendance > 0 else 0, 1)
    
    return jsonify({
        'monthly': monthly_data,
        'weekdays': weekday_data,
        'groups': groups_data,
        'late_stats': {
            'total_late': total_late,
            'late_percentage': late_percentage,
            'avg_late_minutes': round(avg_late, 1) if avg_late else 0
        }
    })


@app.route('/api/attendance/delete/<int:attendance_id>', methods=['DELETE'])
@login_required
def delete_attendance(attendance_id):
    """Удалить запись посещаемости"""
    record = db.session.get(Attendance, attendance_id)
    
    if not record:
        return jsonify({'success': False, 'message': 'Запись не найдена'}), 404
    
    student = record.student
    
    db.session.delete(record)
    db.session.commit()
    
    # Баланс пересчитывается автоматически после удаления посещения
    return jsonify({
        'success': True,
        'message': f'Запись удалена, баланс {student.full_name}: {calculate_student_balance(student)}'
    })


# ===== РАСХОДЫ =====

@app.route('/expenses')
@login_required
def expenses_page():
    if current_user.role not in ['admin', 'financier']:
        return redirect(url_for('dashboard'))
    
    expenses = Expense.query.order_by(Expense.expense_date.desc()).limit(50).all()
    return render_template('expenses.html', expenses=expenses)


@app.route('/api/expenses/add', methods=['POST'])
@login_required
def add_expense():
    if current_user.role not in ['admin', 'financier']:
        return jsonify({'success': False, 'message': 'Нет доступа'}), 403
    
    try:
        data = request.get_json()
        expense = Expense(
            category=data.get('category'),
            amount=float(data.get('amount')),
            description=data.get('description'),
            created_by=current_user.id
        )
        db.session.add(expense)
        db.session.commit()
        
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/expenses/<int:expense_id>', methods=['PUT'])
@login_required
def update_expense(expense_id):
    if current_user.role not in ['admin', 'financier']:
        return jsonify({'success': False, 'message': 'Нет доступа'}), 403

    try:
        data = request.get_json() or {}
        expense = Expense.query.get(expense_id)
        if not expense:
            return jsonify({'success': False, 'message': 'Расход не найден'}), 404

        if 'category' in data:
            expense.category = data.get('category')
        if 'amount' in data:
            expense.amount = float(data.get('amount'))
        if 'description' in data:
            expense.description = data.get('description')

        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/expenses/<int:expense_id>', methods=['DELETE'])
@login_required
def delete_expense(expense_id):
    """Удалить расход"""
    if current_user.role not in ['admin', 'financier']:
        return jsonify({'success': False, 'message': 'Нет доступа'}), 403

    try:
        expense = Expense.query.get(expense_id)
        if not expense:
            return jsonify({'success': False, 'message': 'Расход не найден'}), 404

        db.session.delete(expense)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Расход удалён'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


# ===== ФИНАНСЫ =====

@app.route('/finances')
@login_required
def finances_page():
    """Страница финансов"""
    return render_template('finances.html')


@app.route('/settings')
@login_required
def club_settings_page():
    """Страница настроек клуба"""
    if getattr(current_user, 'role', None) not in ['admin', 'financier']:
        return redirect(url_for('dashboard'))
    return render_template('settings.html')


# ===== МОБИЛЬНАЯ ВЕРСИЯ ДЛЯ ОПЛАТ =====

@app.route('/mobile-payments')
@login_required
def mobile_payments():
    """Мобильная страница для добавления оплат"""
    if current_user.role not in ['payment_admin', 'admin']:
        return redirect(url_for('dashboard'))
    return render_template('mobile_payment.html')


@app.route('/mobile-payment-history')
@login_required
def mobile_payment_history():
    """История оплат для мобильной версии"""
    if current_user.role not in ['payment_admin', 'admin']:
        return redirect(url_for('dashboard'))
    return render_template('mobile_payment_history.html')


@app.route('/api/mobile/payment-history', methods=['GET'])
@login_required
def get_mobile_payment_history():
    """Получить историю оплат для мобильной версии"""
    if current_user.role not in ['payment_admin', 'admin']:
        return jsonify({'error': 'Доступ запрещен'}), 403
    
    # Получить все оплаты, отсортированные по дате
    payments = db.session.query(
        Payment.id,
        Payment.student_id,
        Payment.amount_paid,
        Payment.payment_date,
        Payment.payment_month,
        Payment.payment_year,
        Payment.notes,
        Payment.created_by,
        Student.full_name.label('student_name')
    ).join(Student).order_by(Payment.payment_date.desc()).limit(100).all()
    
    result = []
    for p in payments:
        result.append({
            'id': p.id,
            'student_id': p.student_id,
            'student_name': p.student_name,
            'amount_paid': p.amount_paid,
            'payment_date': p.payment_date.isoformat(),
            'payment_month': p.payment_month,
            'payment_year': p.payment_year,
            'notes': p.notes,
            'created_by': p.created_by
        })
    
    return jsonify(result)


# ===== МОБИЛЬНАЯ ВЕРСИЯ ДЛЯ УЧИТЕЛЯ =====

@app.route('/teacher-attendance')
@login_required
def teacher_attendance():
    """Мобильная страница переклички для учителя"""
    if current_user.role not in ['teacher', 'admin']:
        return redirect(url_for('dashboard'))
    return render_template('teacher_attendance.html')


@app.route('/api/teacher/mark-attendance', methods=['POST'])
@login_required
def teacher_mark_attendance():
    """Отметить посещаемость ученика"""
    if current_user.role not in ['teacher', 'admin']:
        return jsonify({'error': 'Доступ запрещен'}), 403
    
    try:
        data = request.json
        student_id = data.get('student_id')
        status = data.get('status')  # 'present', 'absent', 'late'
        date_str = data.get('date')
        
        if not all([student_id, status, date_str]):
            return jsonify({'error': 'Недостаточно данных'}), 400
        
        # Проверить, существует ли уже запись на сегодня
        attendance_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        existing = Attendance.query.filter_by(
            student_id=student_id,
            date=attendance_date
        ).first()
        
        if existing:
            # Обновить существующую запись
            existing.status = status
            existing.check_in_time = datetime.now().time() if status == 'present' else None
        else:
            # Создать новую запись
            attendance = Attendance(
                student_id=student_id,
                date=attendance_date,
                status=status,
                check_in_time=datetime.now().time() if status == 'present' else None
            )
            db.session.add(attendance)
        
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Статус сохранен'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@app.route('/api/teacher/today-attendance', methods=['GET'])
@login_required
def teacher_today_attendance():
    """Получить сегодняшнюю посещаемость для группы учителя"""
    if current_user.role not in ['teacher', 'admin']:
        return jsonify({'error': 'Доступ запрещен'}), 403
    
    # Получить group_id учителя
    group_id = current_user.group_id if current_user.role == 'teacher' else request.args.get('group_id', type=int)
    
    if not group_id:
        return jsonify({'error': 'Группа не указана'}), 400
    
    today = date.today()
    
    # Получить сегодняшнюю посещаемость
    attendance_records = Attendance.query.filter_by(date=today).all()
    
    result = {}
    for record in attendance_records:
        if record.student and record.student.group_id == group_id:
            result[record.student_id] = {
                'status': record.status,
                'check_in_time': record.check_in_time.strftime('%H:%M') if record.check_in_time else None
            }
    
    return jsonify(result)


@app.route('/api/finances/income', methods=['GET'])
@login_required
def get_income_stats():
    """Статистика прихода"""
    from datetime import date
    from sqlalchemy import func, extract
    
    today = date.today()
    
    # Сегодня
    income_today = db.session.query(func.sum(Payment.amount_paid)).filter(
        func.date(Payment.payment_date) == today
    ).scalar() or 0
    
    # Этот месяц
    income_month = db.session.query(func.sum(Payment.amount_paid)).filter(
        extract('year', Payment.payment_date) == today.year,
        extract('month', Payment.payment_date) == today.month
    ).scalar() or 0
    
    # Всего
    income_total = db.session.query(func.sum(Payment.amount_paid)).scalar() or 0
    
    # Последние платежи
    payments = db.session.query(
        Payment,
        Student.full_name.label('student_name'),
        Student.group_id.label('group_id'),
        Group.name.label('group_name')
    ).join(Student, Payment.student_id == Student.id, isouter=True) \
     .join(Group, Student.group_id == Group.id, isouter=True) \
     .order_by(Payment.payment_date.desc()).limit(50).all()
    
    payments_list = [{
        'payment_date': p.Payment.payment_date.isoformat(),
        'student_name': p.student_name,
        'group_id': p.group_id,
        'group_name': p.group_name,
        'tariff_name': p.Payment.tariff_name,
        'amount_paid': p.Payment.amount_paid,
        'amount_due': p.Payment.amount_due,
        'is_full_payment': p.Payment.is_full_payment,
        'notes': p.Payment.notes
    } for p in payments]
    
    return jsonify({
        'today': income_today,
        'month': income_month,
        'total': income_total,
        'payments': payments_list
    })


@app.route('/api/finances/debtors', methods=['GET'])
@login_required
def get_debtors():
    """Список должников с помесячной детализацией"""
    from datetime import date, datetime
    from sqlalchemy import func, extract
    
    # Получить всех активных учеников с тарифами
    students = Student.query.filter(
        Student.status == 'active',
        Student.tariff_id.isnot(None)
    ).all()
    
    current_year = date.today().year
    current_month = date.today().month
    
    debtors_list = []
    total_debt = 0
    
    for student in students:
        if not student.tariff:
            continue
            
        tariff_price = float(student.tariff.price)
        
        # Определить с какого месяца начинать проверку
        if student.admission_date:
            start_year = student.admission_date.year
            start_month = student.admission_date.month
        else:
            start_year = current_year
            start_month = 1
        
        # Проверить каждый месяц от даты принятия до текущего месяца
        year = start_year
        month = start_month
        
        while (year < current_year) or (year == current_year and month <= current_month):
            month_key = f"{year}-{str(month).zfill(2)}"
            
            # Получить платежи за этот месяц
            month_payments = Payment.query.filter(
                Payment.student_id == student.id,
                Payment.payment_year == year,
                Payment.payment_month == month
            ).all()
            
            total_paid = sum(p.amount_paid for p in month_payments)
            debt = max(0, tariff_price - total_paid)
            
            if debt > 0:
                total_debt += debt
                debtors_list.append({
                    'student_id': student.id,
                    'student_name': student.full_name,
                    'student_phone': student.phone or student.parent_phone or '-',
                    'tariff_name': student.tariff.name,
                    'tariff_price': tariff_price,
                    'amount_paid': total_paid,
                    'amount_due': debt,
                    'month': month,
                    'year': year,
                    'month_label': f"{month}/{year}"
                })
            
            # Следующий месяц
            month += 1
            if month > 12:
                month = 1
                year += 1
    
    return jsonify({
        'total_debt': total_debt,
        'count': len(debtors_list),
        'debtors': debtors_list
    })


@app.route('/api/finances/expenses', methods=['GET'])
@login_required
def get_expense_stats():
    """Статистика расходов"""
    from datetime import date
    from sqlalchemy import func, extract
    
    today = date.today()
    
    # Сегодня
    expense_today = db.session.query(func.sum(Expense.amount)).filter(
        func.date(Expense.expense_date) == today
    ).scalar() or 0
    
    # Этот месяц
    expense_month = db.session.query(func.sum(Expense.amount)).filter(
        extract('year', Expense.expense_date) == today.year,
        extract('month', Expense.expense_date) == today.month
    ).scalar() or 0
    
    # Всего
    expense_total = db.session.query(func.sum(Expense.amount)).scalar() or 0
    
    # Последние расходы
    expenses = Expense.query.order_by(Expense.expense_date.desc()).limit(50).all()
    
    expenses_list = [{
        'id': e.id,
        'expense_date': e.expense_date.isoformat(),
        'category': e.category,
        'amount': e.amount,
        'description': e.description
    } for e in expenses]
    
    return jsonify({
        'today': expense_today,
        'month': expense_month,
        'total': expense_total,
        'expenses': expenses_list
    })


@app.route('/api/finances/analytics', methods=['GET'])
@login_required
def get_analytics():
    """Аналитика по месяцам"""
    from sqlalchemy import func, extract
    from datetime import datetime, date
    
    # Получить данные за последние 12 месяцев
    months_data = []
    
    for i in range(11, -1, -1):
        target_date = date.today().replace(day=1)
        month = target_date.month - i
        year = target_date.year
        
        if month <= 0:
            month += 12
            year -= 1
        
        # Приход за месяц
        income = db.session.query(func.sum(Payment.amount_paid)).filter(
            extract('year', Payment.payment_date) == year,
            extract('month', Payment.payment_date) == month
        ).scalar() or 0
        
        # Расход за месяц
        expense = db.session.query(func.sum(Expense.amount)).filter(
            extract('year', Expense.expense_date) == year,
            extract('month', Expense.expense_date) == month
        ).scalar() or 0
        
        # Название месяца
        month_names = ['Янв', 'Фев', 'Мар', 'Апр', 'Май', 'Июн', 
                      'Июл', 'Авг', 'Сен', 'Окт', 'Ноя', 'Дек']
        month_name = f"{month_names[month - 1]} {year}"
        
        months_data.append({
            'month_name': month_name,
            'income': income,
            'expense': expense
        })
    
    return jsonify({'months': months_data})


@app.route('/api/finances/monthly', methods=['GET'])
@login_required
def get_finances_monthly():
    """Данные по месяцам: приход, расход, остаток (приход - расход)"""
    from sqlalchemy import func, extract
    from datetime import date

    # Получаем год из параметра запроса или используем текущий
    year = request.args.get('year', type=int)
    if not year:
        year = date.today().year

    months = []
    # Последовательность месяцев: январь..декабрь выбранного года
    for month in range(1, 12 + 1):
        income = db.session.query(func.sum(Payment.amount_paid)).filter(
            extract('year', Payment.payment_date) == year,
            extract('month', Payment.payment_date) == month
        ).scalar() or 0
        expense = db.session.query(func.sum(Expense.amount)).filter(
            extract('year', Expense.expense_date) == year,
            extract('month', Expense.expense_date) == month
        ).scalar() or 0
        balance = float(income) - float(expense)
        months.append({
            'income': float(income),
            'expense': float(expense),
            'balance': balance
        })

    return jsonify({'months': months})


# ===== ГРУППЫ =====

@app.route('/api/groups', methods=['GET'])
@login_required
def get_groups():
    """Получить список всех групп"""
    groups = Group.query.all()
    return jsonify([{
        'id': g.id,
        'name': g.name,
        'schedule_time': g.schedule_time.strftime('%H:%M') if g.schedule_time else '--:--',
        'duration_minutes': g.duration_minutes or 60,
        'field_blocks': g.field_blocks or 1,
        'field_block_indices': g.get_field_block_indices(),
        'late_threshold': g.late_threshold,
        'max_students': g.max_students,
        'notes': g.notes,
        'schedule_days': g.get_schedule_days_list(),
        'schedule_days_label': g.get_schedule_days_display(),
        'student_count': len(g.students),
        'active_student_count': g.get_current_students_count(),
        'is_full': g.is_full()
    } for g in groups])


@app.route('/api/club-settings', methods=['GET'])
@login_required
def get_club_settings():
    settings = get_club_settings_instance()
    return jsonify({
        'system_name': settings.system_name or 'FK QORASUV',
        'working_days': settings.get_working_days_list(),
        'work_start_time': settings.work_start_time.strftime('%H:%M'),
        'work_end_time': settings.work_end_time.strftime('%H:%M'),
        'max_groups_per_slot': settings.max_groups_per_slot,
        'block_future_payments': bool(getattr(settings, 'block_future_payments', False)),
        'rewards_reset_period_months': getattr(settings, 'rewards_reset_period_months', 1),
        'podium_display_count': getattr(settings, 'podium_display_count', 20)
    })


@app.route('/api/club-settings', methods=['PUT'])
@login_required
def update_club_settings():
    try:
        data = request.get_json()
        system_name = (data.get('system_name') or '').strip() or 'FK QORASUV'
        working_days = parse_days_list(data.get('working_days'))
        work_start_time = datetime.strptime(data.get('work_start_time'), '%H:%M').time()
        work_end_time = datetime.strptime(data.get('work_end_time'), '%H:%M').time()
        max_groups_per_slot = int(data.get('max_groups_per_slot', 1))
        block_future_payments = bool(data.get('block_future_payments', False))
        rewards_reset_period_months = int(data.get('rewards_reset_period_months', 1))
        podium_display_count = int(data.get('podium_display_count', 20))

        if not working_days:
            return jsonify({'success': False, 'message': 'Выберите рабочие дни'}), 400
        if work_end_time <= work_start_time:
            return jsonify({'success': False, 'message': 'Время окончания должно быть позже начала'}), 400
        if max_groups_per_slot <= 0:
            return jsonify({'success': False, 'message': 'Вместимость должна быть положительной'}), 400
        if rewards_reset_period_months < 1 or rewards_reset_period_months > 12:
            return jsonify({'success': False, 'message': 'Период сброса вознаграждений должен быть от 1 до 12 месяцев'}), 400
        if podium_display_count < 5 or podium_display_count > 50 or podium_display_count % 5 != 0:
            return jsonify({'success': False, 'message': 'Отображение пьедестала должно быть от 5 до 50 учеников с шагом 5'}), 400

        settings = get_club_settings_instance()
        settings.system_name = system_name
        settings.set_working_days_list(working_days)
        settings.work_start_time = work_start_time
        settings.work_end_time = work_end_time
        settings.max_groups_per_slot = max_groups_per_slot
        settings.block_future_payments = block_future_payments
        settings.rewards_reset_period_months = rewards_reset_period_months
        settings.podium_display_count = podium_display_count
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/admin-credentials', methods=['GET'])
@login_required
def get_admin_credentials():
    """Получить текущий логин администратора"""
    if current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Доступ запрещен'}), 403
    
    admin = User.query.filter_by(role='admin').first()
    if not admin:
        return jsonify({'success': False, 'message': 'Администратор не найден'}), 404
    
    return jsonify({
        'success': True,
        'username': admin.username
    })


@app.route('/api/admin-credentials', methods=['PUT'])
@login_required
def update_admin_credentials():
    """Обновить логин и/или пароль администратора"""
    if current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Доступ запрещен'}), 403
    
    try:
        data = request.get_json()
        new_username = (data.get('username') or '').strip()
        new_password = data.get('password', '').strip()
        confirm_password = data.get('confirm_password', '').strip()
        
        admin = User.query.filter_by(role='admin').first()
        if not admin:
            return jsonify({'success': False, 'message': 'Администратор не найден'}), 404
        
        # Проверка нового логина
        if new_username:
            if len(new_username) < 3:
                return jsonify({'success': False, 'message': 'Логин должен содержать минимум 3 символа'}), 400
            
            # Проверить, не занят ли логин другим пользователем
            existing_user = User.query.filter_by(username=new_username).first()
            if existing_user and existing_user.id != admin.id:
                return jsonify({'success': False, 'message': 'Этот логин уже занят'}), 400
            
            admin.username = new_username
        
        # Проверка нового пароля
        if new_password:
            if len(new_password) < 6:
                return jsonify({'success': False, 'message': 'Пароль должен содержать минимум 6 символов'}), 400
            
            if new_password != confirm_password:
                return jsonify({'success': False, 'message': 'Пароли не совпадают'}), 400
            
            admin.password_hash = bcrypt.generate_password_hash(new_password).decode('utf-8')
        
        # Если ничего не изменилось
        if not new_username and not new_password:
            return jsonify({'success': False, 'message': 'Не указаны данные для изменения'}), 400
        
        db.session.commit()
        return jsonify({'success': True, 'message': 'Учетные данные успешно обновлены'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/groups/add', methods=['POST'])
@login_required
def add_group():
    """Добавить новую группу"""
    try:
        data = request.get_json()
        name = data.get('name')
        schedule_time_str = data.get('schedule_time')  # "13:00"
        duration_minutes = int(data.get('duration_minutes', 60))
        # Количество блоков (на случай старых клиентов)
        field_blocks = int(data.get('field_blocks', 1))
        # Индексы блоков, которые занимает группа
        field_block_indices = data.get('field_block_indices') or []
        late_threshold = int(data.get('late_threshold', 15))
        max_students = data.get('max_students')
        if max_students:
            max_students = int(max_students)
        notes = data.get('notes', '')
        schedule_days = parse_days_list(data.get('schedule_days'))
        if not schedule_time_str:
            return jsonify({'success': False, 'message': 'Укажите время занятия'}), 400
        if not schedule_days:
            return jsonify({'success': False, 'message': 'Выберите дни недели'}), 400
        
        # Парсинг времени
        schedule_time = datetime.strptime(schedule_time_str, '%H:%M').time()
        is_valid, error_message = validate_group_schedule(schedule_time, schedule_days)
        if not is_valid:
            return jsonify({'success': False, 'message': error_message}), 400
        
        group = Group(
            name=name,
            schedule_time=schedule_time,
            duration_minutes=duration_minutes,
            late_threshold=late_threshold,
            max_students=max_students,
            notes=notes
        )
        # Если передали конкретные индексы блоков — используем их,
        # иначе считаем, что заняты первые field_blocks блока
        if field_block_indices:
            group.set_field_block_indices(field_block_indices)
        else:
            group.set_field_block_indices(list(range(field_blocks)))
        group.set_schedule_days_list(schedule_days)
        db.session.add(group)
        db.session.commit()
        
        return jsonify({'success': True, 'group_id': group.id})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/groups/<int:group_id>', methods=['PUT'])
@login_required
def update_group(group_id):
    """Обновить группу"""
    try:
        group = db.session.get(Group, group_id)
        if not group:
            return jsonify({'success': False, 'message': 'Группа не найдена'}), 404
        
        data = request.get_json()
        new_schedule_time = group.schedule_time
        new_schedule_days = group.get_schedule_days_list()
        if 'name' in data:
            group.name = data['name']
        if 'duration_minutes' in data:
            group.duration_minutes = int(data['duration_minutes'])
        # Обновление блоков поля
        if 'field_block_indices' in data:
            # Если пришёл массив индексов — сохраняем его
            group.set_field_block_indices(data['field_block_indices'])
        elif 'field_blocks' in data:
            # Старый формат: только количество блоков
            count = int(data['field_blocks'])
            group.set_field_block_indices(list(range(count)))
        if 'schedule_time' in data:
            new_schedule_time = datetime.strptime(data['schedule_time'], '%H:%M').time()
        if 'late_threshold' in data:
            group.late_threshold = int(data['late_threshold'])
        if 'max_students' in data:
            max_students = data['max_students']
            group.max_students = int(max_students) if max_students else None
        if 'notes' in data:
            group.notes = data['notes']
        if 'schedule_days' in data:
            new_schedule_days = parse_days_list(data['schedule_days'])
        needs_validation = ('schedule_time' in data) or ('schedule_days' in data) or not new_schedule_days
        if needs_validation:
            effective_days = new_schedule_days or group.get_schedule_days_list()
            if not effective_days:
                effective_days = get_club_settings_instance().get_working_days_list()
            is_valid, error_message = validate_group_schedule(new_schedule_time, effective_days, exclude_group_id=group.id)
            if not is_valid:
                return jsonify({'success': False, 'message': error_message}), 400
            if not new_schedule_days:
                new_schedule_days = effective_days
        if new_schedule_days:
            group.set_schedule_days_list(new_schedule_days)
        group.schedule_time = new_schedule_time
        
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/groups/<int:group_id>', methods=['DELETE'])
@login_required
def delete_group(group_id):
    """Удалить группу"""
    try:
        group = db.session.get(Group, group_id)
        if not group:
            return jsonify({'success': False, 'message': 'Группа не найдена'}), 404
        
        # Переводим всех учеников группы в состояние "без группы"
        for student in group.students:
            student.group_id = None
        
        db.session.delete(group)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


# ===== ТАРИФЫ =====

@app.route('/tariffs')
@login_required
def tariffs_page():
    return render_template('tariffs.html')


@app.route('/api/tariffs', methods=['GET'])
@login_required
def get_tariffs():
    """Получить список всех тарифов"""
    tariffs = Tariff.query.filter_by(is_active=True).order_by(Tariff.lessons_count).all()
    return jsonify([{
        'id': t.id,
        'name': t.name,
        'lessons_count': t.lessons_count,
        'price': t.price,
        'description': t.description,
        'price_per_lesson': round(t.price / t.lessons_count, 2) if t.lessons_count > 0 else 0
    } for t in tariffs])


@app.route('/api/tariffs/add', methods=['POST'])
@login_required
def add_tariff():
    """Добавить новый тариф"""
    try:
        data = request.get_json()
        name = data.get('name')
        lessons_count = int(data.get('lessons_count'))
        price = float(data.get('price'))
        description = data.get('description', '')
        
        tariff = Tariff(
            name=name,
            lessons_count=lessons_count,
            price=price,
            description=description
        )
        
        db.session.add(tariff)
        db.session.commit()
        
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/tariffs/<int:tariff_id>', methods=['PUT'])
@login_required
def update_tariff(tariff_id):
    """Обновить тариф"""
    try:
        tariff = db.session.get(Tariff, tariff_id)
        if not tariff:
            return jsonify({'success': False, 'message': 'Тариф не найден'}), 404
        
        data = request.get_json()
        if 'name' in data:
            tariff.name = data['name']
        if 'lessons_count' in data:
            tariff.lessons_count = int(data['lessons_count'])
        if 'price' in data:
            tariff.price = float(data['price'])
        if 'description' in data:
            tariff.description = data['description']
        
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/tariffs/<int:tariff_id>', methods=['DELETE'])
@login_required
def delete_tariff(tariff_id):
    """Удалить (деактивировать) тариф"""
    try:
        tariff = db.session.get(Tariff, tariff_id)
        if not tariff:
            return jsonify({'success': False, 'message': 'Тариф не найден'}), 404
        
        # Не удаляем физически, а деактивируем
        tariff.is_active = False
        db.session.commit()
        
        return jsonify({'success': True, 'message': f'Тариф "{tariff.name}" деактивирован'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


# ===== ВОЗНАГРАЖДЕНИЯ =====

@app.route('/rewards')
@login_required
def rewards_page():
    """Страница управления вознаграждениями"""
    if current_user.role != 'admin':
        return redirect(url_for('dashboard'))
    return render_template('rewards.html')


@app.route('/api/rewards', methods=['GET'])
@login_required
def get_rewards():
    """Получить список всех типов вознаграждений"""
    if current_user.role != 'admin':
        return jsonify({'error': 'Доступ запрещен'}), 403
    
    rewards = RewardType.query.order_by(RewardType.created_at.desc()).all()
    return jsonify([{
        'id': r.id,
        'name': r.name,
        'points': r.points,
        'description': r.description or '',
        'created_at': r.created_at.isoformat() if r.created_at else None,
        'updated_at': r.updated_at.isoformat() if r.updated_at else None
    } for r in rewards])


@app.route('/api/rewards/add', methods=['POST'])
@login_required
def add_reward():
    """Добавить новый тип вознаграждения"""
    if current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Доступ запрещен'}), 403
    
    try:
        data = request.get_json()
        name = data.get('name', '').strip()
        points = int(data.get('points', 1))
        description = data.get('description', '').strip()
        
        if not name:
            return jsonify({'success': False, 'message': 'Название вознаграждения не может быть пустым'}), 400
        
        if points < 1:
            return jsonify({'success': False, 'message': 'Количество баллов должно быть больше 0'}), 400
        
        reward = RewardType(
            name=name,
            points=points,
            description=description if description else None
        )
        
        db.session.add(reward)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Вознаграждение добавлено',
            'reward': {
                'id': reward.id,
                'name': reward.name,
                'points': reward.points,
                'description': reward.description or ''
            }
        })
    except ValueError:
        return jsonify({'success': False, 'message': 'Некорректное количество баллов'}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/rewards/<int:reward_id>', methods=['PUT'])
@login_required
def update_reward(reward_id):
    """Обновить тип вознаграждения"""
    if current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Доступ запрещен'}), 403
    
    try:
        reward = db.session.get(RewardType, reward_id)
        if not reward:
            return jsonify({'success': False, 'message': 'Вознаграждение не найдено'}), 404
        
        data = request.get_json()
        if 'name' in data:
            name = data['name'].strip()
            if not name:
                return jsonify({'success': False, 'message': 'Название вознаграждения не может быть пустым'}), 400
            reward.name = name
        
        if 'points' in data:
            points = int(data['points'])
            if points < 1:
                return jsonify({'success': False, 'message': 'Количество баллов должно быть больше 0'}), 400
            reward.points = points
        
        if 'description' in data:
            reward.description = data['description'].strip() if data['description'].strip() else None
        
        reward.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Вознаграждение обновлено',
            'reward': {
                'id': reward.id,
                'name': reward.name,
                'points': reward.points,
                'description': reward.description or ''
            }
        })
    except ValueError:
        return jsonify({'success': False, 'message': 'Некорректное количество баллов'}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/rewards/<int:reward_id>', methods=['DELETE'])
@login_required
def delete_reward(reward_id):
    """Удалить тип вознаграждения"""
    if current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Доступ запрещен'}), 403
    
    try:
        reward = db.session.get(RewardType, reward_id)
        if not reward:
            return jsonify({'success': False, 'message': 'Вознаграждение не найдено'}), 404
        
        reward_name = reward.name
        db.session.delete(reward)
        db.session.commit()
        
        return jsonify({'success': True, 'message': f'Вознаграждение "{reward_name}" удалено'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


# ===== ВЫДАЧА ВОЗНАГРАЖДЕНИЙ УЧЕНИКАМ =====

@app.route('/api/students/<int:student_id>/rewards', methods=['POST'])
@login_required
def issue_reward(student_id):
    """Выдать вознаграждение ученику"""
    if current_user.role not in ['admin', 'teacher']:
        return jsonify({'success': False, 'message': 'Доступ запрещен'}), 403
    
    try:
        data = request.get_json()
        reward_type_id = int(data.get('reward_type_id'))
        
        student = db.session.get(Student, student_id)
        if not student:
            return jsonify({'success': False, 'message': 'Ученик не найден'}), 404
        
        reward_type = db.session.get(RewardType, reward_type_id)
        if not reward_type:
            return jsonify({'success': False, 'message': 'Тип вознаграждения не найден'}), 404
        
        from datetime import date
        current_date = date.today()
        
        # Создать запись о выдаче вознаграждения
        student_reward = StudentReward(
            student_id=student_id,
            reward_type_id=reward_type_id,
            points=reward_type.points,
            reward_name=reward_type.name,
            issued_by=current_user.id,
            month=current_date.month,
            year=current_date.year
        )
        
        db.session.add(student_reward)
        db.session.commit()
        
        # Подсчитать общее количество баллов за текущий месяц
        total_points = db.session.query(func.sum(StudentReward.points)).filter(
            StudentReward.student_id == student_id,
            StudentReward.month == current_date.month,
            StudentReward.year == current_date.year
        ).scalar() or 0
        
        return jsonify({
            'success': True,
            'message': f'Вознаграждение "{reward_type.name}" выдано (+{reward_type.points} баллов)',
            'total_points': total_points
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/students/<int:student_id>/rewards', methods=['GET'])
@login_required
def get_student_rewards(student_id):
    """Получить историю вознаграждений ученика"""
    try:
        month = request.args.get('month', type=int)
        year = request.args.get('year', type=int)
        
        from datetime import date
        if not month or not year:
            current_date = date.today()
            month = current_date.month
            year = current_date.year
        
        rewards = StudentReward.query.filter_by(
            student_id=student_id,
            month=month,
            year=year
        ).order_by(StudentReward.issued_at.desc()).all()
        
        return jsonify([{
            'id': r.id,
            'reward_name': r.reward_name,
            'points': r.points,
            'issued_at': r.issued_at.isoformat() if r.issued_at else None,
            'issuer_name': r.issuer.username if r.issuer else 'Система'
        } for r in rewards])
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/students/<int:student_id>/points', methods=['GET'])
@login_required
def get_student_points(student_id):
    """Получить общее количество баллов ученика за текущий месяц"""
    try:
        from datetime import date
        current_date = date.today()
        
        total_points = db.session.query(func.sum(StudentReward.points)).filter(
            StudentReward.student_id == student_id,
            StudentReward.month == current_date.month,
            StudentReward.year == current_date.year
        ).scalar() or 0
        
        return jsonify({'points': total_points})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ===== РЕЙТИНГ УЧЕНИКОВ =====

@app.route('/rating')
@login_required
def rating_page():
    """Страница рейтинга учеников"""
    return render_template('rating.html')


@app.route('/api/rating/<int:group_id>', methods=['GET'])
@login_required
def get_group_rating(group_id):
    """Получить рейтинг учеников группы за текущий месяц"""
    try:
        from datetime import date
        current_date = date.today()
        
        # Получить настройки для количества мест в пьедестале
        settings = get_club_settings_instance()
        podium_count = getattr(settings, 'podium_display_count', 20)
        
        # Подсчитать баллы для всех учеников группы за текущий месяц
        students_query = Student.query.filter_by(group_id=group_id, status='active')
        
        rating_data = []
        for student in students_query.all():
            total_points = db.session.query(func.sum(StudentReward.points)).filter(
                StudentReward.student_id == student.id,
                StudentReward.month == current_date.month,
                StudentReward.year == current_date.year
            ).scalar() or 0
            
            if total_points > 0:  # Показываем только тех, у кого есть баллы
                rating_data.append({
                    'student_id': student.id,
                    'full_name': student.full_name,
                    'photo_path': student.photo_path,
                    'points': total_points
                })
        
        # Сортировать по убыванию баллов и взять топ N
        rating_data.sort(key=lambda x: x['points'], reverse=True)
        rating_data = rating_data[:podium_count]
        
        return jsonify({
            'rating': rating_data,
            'month': current_date.month,
            'year': current_date.year
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/rating/all-groups', methods=['GET'])
@login_required
def get_all_groups_rating():
    """Получить рейтинг всех групп за текущий месяц"""
    try:
        from datetime import date
        current_date = date.today()
        
        # Получить настройки для количества мест в пьедестале
        settings = get_club_settings_instance()
        podium_count = getattr(settings, 'podium_display_count', 20)
        
        # Получить все группы
        groups = Group.query.all()
        
        result = []
        for group in groups:
            # Подсчитать баллы для всех учеников группы за текущий месяц
            students_query = Student.query.filter_by(group_id=group.id, status='active')
            
            rating_data = []
            for student in students_query.all():
                total_points = db.session.query(func.sum(StudentReward.points)).filter(
                    StudentReward.student_id == student.id,
                    StudentReward.month == current_date.month,
                    StudentReward.year == current_date.year
                ).scalar() or 0
                
                if total_points > 0:  # Показываем только тех, у кого есть баллы
                    rating_data.append({
                        'student_id': student.id,
                        'full_name': student.full_name,
                        'photo_path': student.photo_path,
                        'points': total_points
                    })
            
            # Сортировать по убыванию баллов и взять топ N
            rating_data.sort(key=lambda x: x['points'], reverse=True)
            rating_data = rating_data[:podium_count]
            
            result.append({
                'group_id': group.id,
                'group_name': group.name,
                'rating': rating_data
            })
        
        return jsonify({
            'groups': result,
            'month': current_date.month,
            'year': current_date.year
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/rating/winners-history', methods=['GET'])
@login_required
def get_winners_history():
    """Получить историю победителей (1 место) по месяцам для всех групп"""
    try:
        year = request.args.get('year', type=int)
        from datetime import date
        if not year:
            year = date.today().year
        
        # Получить все группы
        groups = Group.query.all()
        
        result = {}
        
        for group in groups:
            group_winners = []
            
            # Для каждого месяца года
            for month in range(1, 13):
                # Подсчитать баллы для всех учеников группы за этот месяц
                students_query = Student.query.filter_by(group_id=group.id, status='active')
                
                monthly_rating = []
                for student in students_query.all():
                    total_points = db.session.query(func.sum(StudentReward.points)).filter(
                        StudentReward.student_id == student.id,
                        StudentReward.month == month,
                        StudentReward.year == year
                    ).scalar() or 0
                    
                    if total_points > 0:
                        monthly_rating.append({
                            'student_id': student.id,
                            'full_name': student.full_name,
                            'photo_path': student.photo_path,
                            'points': total_points
                        })
                
                # Найти топ-3 учеников
                if monthly_rating:
                    monthly_rating.sort(key=lambda x: x['points'], reverse=True)
                    top_three = monthly_rating[:3]  # Берем топ-3
                    
                    group_winners.append({
                        'month': month,
                        'students': top_three
                    })
                else:
                    # Нет данных за этот месяц
                    group_winners.append({
                        'month': month,
                        'students': [],
                        'is_empty': True
                    })
            
            result[group.id] = {
                'group_id': group.id,
                'group_name': group.name,
                'winners': group_winners
            }
        
        return jsonify({
            'year': year,
            'groups': list(result.values())
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ===== ЛОКАЦИИ =====

@app.route('/api/locations/cities', methods=['GET'])
def get_cities_list():
    """Получить список городов"""
    return jsonify(get_cities())


@app.route('/api/locations/districts/<city>', methods=['GET'])
def get_districts_list(city):
    """Получить список районов для города"""
    return jsonify(get_districts(city))


# ===== РАСПОЗНАВАНИЕ ЛИЦ =====

@app.route('/camera')
@login_required
def camera_page():
    """Страница с камерой для распознавания"""
    return render_template('camera.html')


@app.route('/api/recognize', methods=['POST'])
def recognize_face():
    """Распознать лицо из кадра камеры"""
    try:
        # Получить изображение (base64 или файл)
        if 'image' in request.files:
            image_file = request.files['image']
            temp_path = os.path.join(app.config['UPLOAD_FOLDER'], 'temp_recognize.jpg')
            image_file.save(temp_path)
            
            student_id = face_service.recognize_face_from_image(temp_path)
            os.remove(temp_path)
            
            if student_id:
                student = Student.query.get(student_id)
                return jsonify({
                    'success': True,
                    'student_id': student.id,
                    'student_name': student.full_name,
                    'balance': calculate_student_balance(student),
                    'photo': student.photo_path
                })
            else:
                return jsonify({'success': False, 'message': 'Лицо не распознано'})
        
        return jsonify({'success': False, 'message': 'Нет изображения'}), 400
    
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/recognize_multiple', methods=['POST'])
def recognize_multiple_faces():
    """Распознать несколько лиц из кадра камеры"""
    try:
        if 'image' in request.files:
            image_file = request.files['image']
            temp_path = os.path.join(app.config['UPLOAD_FOLDER'], 'temp_recognize.jpg')
            image_file.save(temp_path)
            
            recognized = face_service.recognize_multiple_faces_from_image(temp_path)
            os.remove(temp_path)
            
            if len(recognized) > 0:
                students_data = []
                for item in recognized:
                    student = Student.query.get(item['student_id'])
                    if student:
                        students_data.append({
                            'student_id': student.id,
                            'student_name': student.full_name,
                            'balance': calculate_student_balance(student),
                            'photo': student.photo_path
                        })
                
                return jsonify({
                    'success': True,
                    'count': len(students_data),
                    'students': students_data
                })
            else:
                return jsonify({'success': False, 'message': 'Лица не распознаны'})
        
        return jsonify({'success': False, 'message': 'Нет изображения'}), 400
    
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


def reload_face_encodings():
    """Перезагрузить все face encodings в память"""
    students = Student.query.filter_by(status='active').all()
    face_service.load_student_encodings(students)


# ===== ИНИЦИАЛИЗАЦИЯ =====

def init_db():
    """Создать таблицы и первого админа"""
    with app.app_context():
        db.create_all()
        
        # Проверить, есть ли админ
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            admin = User(
                username='admin',
                password_hash=bcrypt.generate_password_hash('admin123').decode('utf-8'),
                role='admin'
            )
            db.session.add(admin)
            db.session.commit()
            print("Создан администратор: admin / admin123")
        
        # Загрузить encodings
        reload_face_encodings()


# ===== ПОМЕСЯЧНЫЕ ОПЛАТЫ =====

@app.route('/api/students/<int:student_id>/monthly-payments', methods=['GET'])
@login_required
def get_monthly_payments(student_id):
    """Получить помесячные оплаты ученика"""
    try:
        # Получить студента и его тариф
        student = Student.query.get(student_id)
        if not student:
            return jsonify({'error': 'Студент не найден'}), 404
        
        tariff_price = student.tariff.price if student.tariff else 0
        
        # Получить все платежи ученика с метаданными месяца
        payments = Payment.query.filter_by(student_id=student_id).order_by(Payment.payment_date.desc()).all()
        
        # Группировать по месяцам используя payment_month и payment_year
        payments_by_month = {}
        for payment in payments:
            # Использовать payment_month/payment_year если есть, иначе брать из payment_date
            if payment.payment_month and payment.payment_year:
                month_key = f"{payment.payment_year}-{str(payment.payment_month).zfill(2)}"
            elif payment.payment_date:
                month_key = payment.payment_date.strftime('%Y-%m')
            else:
                continue
                
            if month_key not in payments_by_month:
                payments_by_month[month_key] = {
                    'payments': [],
                    'total_paid': 0,
                    'tariff_price': tariff_price,
                    'remainder': tariff_price
                }
            
            payments_by_month[month_key]['payments'].append({
                'id': payment.id,
                'date': payment.payment_date.isoformat() if payment.payment_date else None,
                'amount': float(payment.amount_paid),
                'notes': payment.notes or ''
            })
            payments_by_month[month_key]['total_paid'] += float(payment.amount_paid)
        
        # Рассчитать остаток для каждого месяца
        for month_key in payments_by_month:
            total_paid = payments_by_month[month_key]['total_paid']
            payments_by_month[month_key]['remainder'] = max(0, tariff_price - total_paid)
        
        return jsonify({
            'payments_by_month': payments_by_month,
            'tariff_price': tariff_price
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/students/add-monthly-payment', methods=['POST'])
@login_required
def add_monthly_payment():
    """Добавить помесячную оплату"""
    try:
        data = request.json
        student_id = data.get('student_id')
        year = data.get('year')
        month = data.get('month')
        payment_date = data.get('payment_date')
        amount = float(data.get('amount', 0))
        notes = data.get('notes', '')
        
        student = Student.query.get(student_id)
        if not student:
            return jsonify({'success': False, 'message': 'Ученик не найден'})

        # Блокировка оплат за будущие месяцы, если включено в настройках клуба
        settings = get_club_settings_instance()
        if getattr(settings, 'block_future_payments', False):
            today = datetime.utcnow().date()
            if year > today.year or (year == today.year and month > today.month):
                return jsonify({'success': False, 'message': 'Оплата за будущие месяцы запрещена настройками клуба'}), 400

        # Проверка тарифа и текущих оплат за месяц
        tariff_price = None
        if student.tariff_id:
            tariff = Tariff.query.get(student.tariff_id)
            tariff_price = float(tariff.price) if tariff and tariff.price is not None else None

        if tariff_price is not None:
            existing_paid = db.session.query(db.func.sum(Payment.amount_paid)).filter(
                Payment.student_id == student_id,
                Payment.payment_year == year,
                Payment.payment_month == month
            ).scalar() or 0
            if existing_paid + amount > tariff_price:
                remainder = max(0, tariff_price - existing_paid)
                return jsonify({
                    'success': False,
                    'message': f'Оплата превышает стоимость тарифа. Осталось не более {remainder:.0f} сум'
                }), 400
        
        # Создать запись оплаты с привязкой к выбранному месяцу через notes и метаданные
        # payment_date используется только как дата фактической транзакции
        month_label = f"{month}/{year}"
        payment = Payment(
            student_id=student_id,
            tariff_id=student.tariff_id if student.tariff_id else None,
            amount_paid=amount,
            amount_due=0,
            payment_date=datetime.fromisoformat(payment_date),
            notes=f"{notes} (Оплата за {month_label})" if notes else f"Оплата за {month_label}",
            lessons_added=0,
            # Сохранить месяц в отдельном поле для корректной группировки
            payment_month=month,
            payment_year=year
        )
        
        db.session.add(payment)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Оплата добавлена',
            'payment_id': payment.id
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/payments/<int:payment_id>', methods=['PUT'])
@login_required
def update_payment(payment_id):
    """Редактирование существующей оплаты (сумма, дата, комментарий)"""
    # Разрешим роли: admin, financier, payment_admin
    if getattr(current_user, 'role', None) not in ['admin', 'financier', 'payment_admin']:
        return jsonify({'success': False, 'message': 'Нет доступа'}), 403

    try:
        data = request.get_json() or {}
        payment = Payment.query.get(payment_id)
        if not payment:
            return jsonify({'success': False, 'message': 'Оплата не найдена'}), 404

        # Валидация суммы
        if 'amount_paid' in data:
            new_amount = float(data.get('amount_paid'))
            if new_amount <= 0:
                return jsonify({'success': False, 'message': 'Сумма должна быть положительной'}), 400
            # Проверяем лимит по тарифу в рамках того же месяца
            tariff_price = None
            if payment.tariff_id:
                tariff_obj = Tariff.query.get(payment.tariff_id)
                tariff_price = float(tariff_obj.price) if tariff_obj and tariff_obj.price is not None else None
            if tariff_price is not None:
                existing_paid = db.session.query(db.func.sum(Payment.amount_paid)).filter(
                    Payment.student_id == payment.student_id,
                    Payment.payment_year == payment.payment_year,
                    Payment.payment_month == payment.payment_month,
                    Payment.id != payment.id
                ).scalar() or 0
                if existing_paid + new_amount > tariff_price:
                    remainder = max(0, tariff_price - existing_paid)
                    return jsonify({'success': False, 'message': f'Сумма превышает стоимость тарифа. Доступно не более {remainder:.0f} сум'}), 400
            payment.amount_paid = new_amount

        if 'payment_date' in data and data.get('payment_date'):
            payment.payment_date = datetime.fromisoformat(data.get('payment_date'))

        if 'notes' in data:
            payment.notes = data.get('notes')

        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/payments/<int:payment_id>/delete', methods=['DELETE'])
@login_required
def delete_payment(payment_id):
    """Удалить оплату"""
    if getattr(current_user, 'role', None) not in ['admin', 'financier', 'payment_admin']:
        return jsonify({'success': False, 'message': 'Нет доступа'}), 403

    try:
        payment = Payment.query.get(payment_id)
        if not payment:
            return jsonify({'success': False, 'message': 'Оплата не найдена'}), 404

        student = payment.student
        db.session.delete(payment)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Оплата удалена',
            'new_balance': calculate_student_balance(student) if student else None
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


if __name__ == '__main__':
    init_db()
    # Для Railway используется gunicorn, но для локальной разработки используем встроенный сервер
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV', 'development') == 'development'
    app.run(debug=debug, host='0.0.0.0', port=port)


