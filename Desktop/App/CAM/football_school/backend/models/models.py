from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime, time
import json

db = SQLAlchemy()

class User(UserMixin, db.Model):
    """Пользователи системы (администратор, финансист)"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'admin', 'financier', 'payment_admin', или 'teacher'
    group_id = db.Column(db.Integer, db.ForeignKey('groups.id'), nullable=True)  # Для учителей - их группа
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<User {self.username}>'


class Group(db.Model):
    """Группы занятий"""
    __tablename__ = 'groups'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)  # Например: "Группа 1", "Младшая"
    schedule_time = db.Column(db.Time, nullable=False)  # Время занятия (13:00, 15:00)
    duration_minutes = db.Column(db.Integer, default=60)  # Длительность занятия в минутах
    schedule_days = db.Column(db.String(50))  # Дни недели в формате "1,3,5" (Пн, Ср, Пт)
    late_threshold = db.Column(db.Integer, default=15)  # Опоздание в минутах
    max_students = db.Column(db.Integer)  # Максимальное количество учеников
    field_blocks = db.Column(db.Integer, default=1)  # Количество блоков поля, которые занимает группа
    field_block_indices = db.Column(db.Text)  # Индексы блоков поля (JSON-массив, напр. [0,1,2])
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Связи
    students = db.relationship('Student', backref='group', lazy=True)
    
    def get_schedule_days_list(self):
        """Получить список дней недели (1=Пн, 7=Вс)"""
        if self.schedule_days:
            return [int(d) for d in self.schedule_days.split(',') if d]
        return []
    
    def set_schedule_days_list(self, days_list):
        """Сохранить список дней недели"""
        self.schedule_days = ','.join(map(str, sorted(days_list)))

    def get_field_block_indices(self):
        """Получить список индексов блоков поля, которые занимает группа"""
        if not self.field_block_indices:
            # Если нет сохранённых индексов, считаем, что заняты первые field_blocks блоков
            return list(range(self.field_blocks or 0))
        try:
            data = json.loads(self.field_block_indices)
            return [int(i) for i in data]
        except Exception:
            return list(range(self.field_blocks or 0))

    def set_field_block_indices(self, indices):
        """Сохранить индексы блоков поля как JSON"""
        if not indices:
            self.field_block_indices = None
            self.field_blocks = 0
            return
        sorted_indices = sorted(set(int(i) for i in indices))
        self.field_block_indices = json.dumps(sorted_indices, ensure_ascii=False)
        self.field_blocks = len(sorted_indices)

    def is_full(self):
        """Проверить, заполнена ли группа"""
        if not self.max_students:
            return False
        active_students = sum(1 for s in self.students if s.status == 'active')
        return active_students >= self.max_students
    
    def get_current_students_count(self):
        """Получить текущее количество активных учеников"""
        return sum(1 for s in self.students if s.status == 'active')

    def get_schedule_days_display(self):
        days_map = {
            1: 'Пн', 2: 'Вт', 3: 'Ср', 4: 'Чт', 5: 'Пт', 6: 'Сб', 7: 'Вс'
        }
        return ', '.join(days_map.get(day, str(day)) for day in self.get_schedule_days_list())
    
    def __repr__(self):
        return f'<Group {self.name} at {self.schedule_time}>'


class Tariff(db.Model):
    """Тарифные планы"""
    __tablename__ = 'tariffs'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)  # "Тариф 8 занятий"
    lessons_count = db.Column(db.Integer, nullable=False)  # Количество занятий
    price = db.Column(db.Float, nullable=False)  # Стоимость тарифа
    description = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Tariff {self.name}: {self.lessons_count} lessons for {self.price}>'


class Student(db.Model):
    """Ученики футбольной школы"""
    __tablename__ = 'students'
    
    id = db.Column(db.Integer, primary_key=True)
    student_number = db.Column(db.String(20), unique=True, nullable=False)  # Уникальный номер ученика
    school_number = db.Column(db.String(100))  # Номер школы
    full_name = db.Column(db.String(200), nullable=False)
    phone = db.Column(db.String(20))
    parent_phone = db.Column(db.String(20))
    photo_path = db.Column(db.String(300))
    face_encoding = db.Column(db.Text)  # JSON строка с encoding лица
    balance = db.Column(db.Integer, default=0)  # Оставшиеся занятия
    tariff_type = db.Column(db.String(50))  # Например: "8 занятий"
    tariff_id = db.Column(db.Integer, db.ForeignKey('tariffs.id'), nullable=True)  # Связь с тарифом
    status = db.Column(db.String(20), default='active')  # active, inactive, blacklist
    blacklist_reason = db.Column(db.Text)  # Причина добавления в чёрный список
    admission_date = db.Column(db.Date)  # Дата принятия в клуб
    
    # Группа
    group_id = db.Column(db.Integer, db.ForeignKey('groups.id'), nullable=True)
    
    # Адрес
    city = db.Column(db.String(100))
    district = db.Column(db.String(100))
    street = db.Column(db.String(200))
    house_number = db.Column(db.String(50))
    
    # Паспортные данные
    birth_year = db.Column(db.Integer)
    passport_series = db.Column(db.String(10))
    passport_number = db.Column(db.String(20))
    passport_issued_by = db.Column(db.String(200))
    passport_issue_date = db.Column(db.Date)
    passport_expiry_date = db.Column(db.Date)
    
    # Финансирование
    club_funded = db.Column(db.Boolean, default=False)  # Финансирование за счёт клуба
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Связи
    payments = db.relationship('Payment', backref='student', lazy=True, cascade='all, delete-orphan')
    attendances = db.relationship('Attendance', backref='student', lazy=True, cascade='all, delete-orphan')
    tariff = db.relationship('Tariff', backref='students', lazy=True)
    
    def get_face_encoding(self):
        """Получить face encoding как numpy array"""
        if self.face_encoding:
            return json.loads(self.face_encoding)
        return None
    
    def set_face_encoding(self, encoding):
        """Сохранить face encoding"""
        if encoding is not None:
            self.face_encoding = json.dumps(encoding.tolist())
    
    def __repr__(self):
        return f'<Student {self.full_name}>'


class Payment(db.Model):
    """Платежи учеников"""
    __tablename__ = 'payments'
    
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    tariff_id = db.Column(db.Integer, db.ForeignKey('tariffs.id'), nullable=True)  # Связь с тарифом
    amount_paid = db.Column(db.Float, nullable=False)  # Сколько заплатил ученик
    amount_due = db.Column(db.Float, default=0)  # Сколько осталось доплатить (долг)
    lessons_added = db.Column(db.Integer, nullable=False)  # Сколько занятий добавлено
    is_full_payment = db.Column(db.Boolean, default=True)  # Полная оплата или частичная
    payment_date = db.Column(db.DateTime, default=datetime.utcnow)
    tariff_name = db.Column(db.String(100))  # Дублируем название тарифа для истории
    notes = db.Column(db.Text)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    # Для помесячной системы оплаты
    payment_month = db.Column(db.Integer)  # Месяц оплаты (1-12)
    payment_year = db.Column(db.Integer)  # Год оплаты
    
    # Связь с тарифом
    tariff = db.relationship('Tariff', foreign_keys=[tariff_id])
    
    def __repr__(self):
        return f'<Payment {self.amount_paid} for Student {self.student_id}>'


class Attendance(db.Model):
    """Посещаемость"""
    __tablename__ = 'attendance'
    
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    check_in = db.Column(db.DateTime, default=datetime.utcnow)
    check_out = db.Column(db.DateTime, nullable=True)
    date = db.Column(db.Date, default=datetime.utcnow().date)
    lesson_deducted = db.Column(db.Boolean, default=False)  # Списано ли занятие
    is_late = db.Column(db.Boolean, default=False)  # Опоздал ли ученик
    late_minutes = db.Column(db.Integer, default=0)  # На сколько минут опоздал
    
    def __repr__(self):
        return f'<Attendance Student {self.student_id} on {self.date}>'


class Expense(db.Model):
    """Расходы школы"""
    __tablename__ = 'expenses'
    
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(100), nullable=False)  # аренда, зарплата, оборудование
    amount = db.Column(db.Float, nullable=False)
    description = db.Column(db.Text)
    expense_date = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    def __repr__(self):
        return f'<Expense {self.category} {self.amount}>'


class ClubSettings(db.Model):
    """Настройки клуба (рабочие часы и вместимость поля)"""
    __tablename__ = 'club_settings'

    id = db.Column(db.Integer, primary_key=True)
    system_name = db.Column(db.String(200), default='FK QORASUV')
    working_days = db.Column(db.String(50), default='1,2,3,4,5')  # Дни недели, когда клуб работает
    work_start_time = db.Column(db.Time, default=time(9, 0))
    work_end_time = db.Column(db.Time, default=time(21, 0))
    max_groups_per_slot = db.Column(db.Integer, default=4)
    block_future_payments = db.Column(db.Boolean, default=False)  # Запрет оплаты за будущие месяцы
    rewards_reset_period_months = db.Column(db.Integer, default=1)  # Период сброса вознаграждений (1-12 месяцев)
    podium_display_count = db.Column(db.Integer, default=20)  # Количество учеников для отображения в пьедестале (5-50 с шагом 5)

    def get_working_days_list(self):
        if self.working_days:
            return [int(d) for d in self.working_days.split(',') if d]
        return []

    def set_working_days_list(self, days_list):
        self.working_days = ','.join(map(str, sorted(days_list)))


class RewardType(db.Model):
    """Типы вознаграждений"""
    __tablename__ = 'reward_types'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)  # Название вознаграждения (например, "Дисциплина")
    points = db.Column(db.Integer, nullable=False, default=1)  # Количество баллов
    description = db.Column(db.Text)  # Описание (опционально)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<RewardType {self.name}: {self.points} баллов>'


class StudentReward(db.Model):
    """Выданные вознаграждения ученикам"""
    __tablename__ = 'student_rewards'
    
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    reward_type_id = db.Column(db.Integer, db.ForeignKey('reward_types.id'), nullable=False)
    points = db.Column(db.Integer, nullable=False)  # Количество баллов (копия из reward_type для истории)
    reward_name = db.Column(db.String(200), nullable=False)  # Название вознаграждения (копия для истории)
    issued_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # Кто выдал
    issued_at = db.Column(db.DateTime, default=datetime.utcnow)
    month = db.Column(db.Integer, nullable=False)  # Месяц выдачи (1-12)
    year = db.Column(db.Integer, nullable=False)  # Год выдачи
    
    # Связи
    student = db.relationship('Student', backref='rewards')
    reward_type = db.relationship('RewardType')
    issuer = db.relationship('User')
    
    def __repr__(self):
        return f'<StudentReward Student {self.student_id}: {self.points} баллов за {self.reward_name}>'


class CashTransfer(db.Model):
    """Передача денег из кассы управляющему"""
    __tablename__ = 'cash_transfers'
    
    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Float, nullable=False)  # Сумма передачи
    recipient = db.Column(db.String(200), nullable=False)  # Кому передано
    transfer_date = db.Column(db.DateTime, nullable=False)  # Дата передачи
    notes = db.Column(db.Text)  # Примечания
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))  # Кто создал запись
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Связи
    creator = db.relationship('User')
    
    def __repr__(self):
        return f'<CashTransfer {self.amount} to {self.recipient} on {self.transfer_date}>'
