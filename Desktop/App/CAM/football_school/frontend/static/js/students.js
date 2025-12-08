// Переключение поля причины для чёрного списка
function toggleBlacklistReason() {
    const statusSelect = document.getElementById('statusSelect');
    const blacklistBlock = document.getElementById('blacklistReasonBlock');
    
    if (statusSelect && blacklistBlock) {
        if (statusSelect.value === 'blacklist') {
            blacklistBlock.style.display = 'block';
        } else {
            blacklistBlock.style.display = 'none';
        }
    }
}

// Переключение поля причины для редактирования
function toggleEditBlacklistReason() {
    const statusSelect = document.getElementById('edit_statusSelect');
    const blacklistBlock = document.getElementById('edit_blacklistReasonBlock');
    
    if (statusSelect && blacklistBlock) {
        if (statusSelect.value === 'blacklist') {
            blacklistBlock.style.display = 'block';
        } else {
            blacklistBlock.style.display = 'none';
        }
    }
}

function buildFullName(lastName, firstName, middleName) {
    const parts = [lastName, firstName, middleName]
        .map(part => (part || '').trim())
        .filter(Boolean);
    return parts.join(' ');
}

function splitFullName(fullName) {
    if (!fullName) {
        return { last: '', first: '', middle: '' };
    }
    const parts = fullName.trim().split(/\s+/);
    const last = parts.shift() || '';
    const first = parts.shift() || '';
    const middle = parts.join(' ');
    return { last, first, middle };
}

// Загрузка списков при открытии формы
async function loadFormData() {
    // Загрузить города
    try {
        const citiesResponse = await fetch('/api/locations/cities');
        const cities = await citiesResponse.json();
        
        const citySelect = document.getElementById('citySelect');
        citySelect.innerHTML = '<option value="">Выберите город</option>' +
            cities.map(city => `<option value="${city}">${city}</option>`).join('');
    } catch (error) {
        console.error('Ошибка загрузки городов:', error);
    }
    
    // Загрузить группы
    try {
        const groupsResponse = await fetch('/api/groups');
        const groups = await groupsResponse.json();
        
        const groupSelect = document.getElementById('groupSelect');
        groupSelect.innerHTML = '<option value="">Без группы</option>' +
            groups.map(g => `<option value="${g.id}">${g.name} (${g.schedule_time})</option>`).join('');
    } catch (error) {
        console.error('Ошибка загрузки групп:', error);
    }

    // Загрузить тарифы
    try {
        const tariffsResponse = await fetch('/api/tariffs');
        const tariffs = await tariffsResponse.json();
        
        const tariffSelect = document.getElementById('tariffSelect');
        tariffSelect.innerHTML = '<option value="">Без тарифа</option>' +
            tariffs.map(t => `<option value="${t.id}">${t.name} - ${parseInt(t.price).toLocaleString('ru-RU')} сум (${t.lessons_count} занятий)</option>`).join('');
    } catch (error) {
        console.error('Ошибка загрузки тарифов:', error);
    }
}

// Обработчик выбора города
document.getElementById('citySelect')?.addEventListener('change', async (e) => {
    const city = e.target.value;
    const districtSelect = document.getElementById('districtSelect');
    
    if (!city) {
        districtSelect.innerHTML = '<option value="">Сначала выберите город</option>';
        districtSelect.disabled = true;
        return;
    }
    
    try {
        const response = await fetch(`/api/locations/districts/${encodeURIComponent(city)}`);
        const districts = await response.json();
        
        districtSelect.innerHTML = '<option value="">Выберите район</option>' +
            districts.map(d => `<option value="${d}">${d}</option>`).join('');
        districtSelect.disabled = false;
    } catch (error) {
        console.error('Ошибка загрузки районов:', error);
    }
});

// Загрузка данных для формы редактирования
async function loadEditFormData() {
    // Загрузить города
    try {
        const citiesResponse = await fetch('/api/locations/cities');
        const cities = await citiesResponse.json();
        
        const citySelect = document.getElementById('edit_citySelect');
        citySelect.innerHTML = '<option value="">Выберите город</option>' +
            cities.map(city => `<option value="${city}">${city}</option>`).join('');
    } catch (error) {
        console.error('Ошибка загрузки городов:', error);
    }
    
    // Загрузить группы
    try {
        const groupsResponse = await fetch('/api/groups');
        const groups = await groupsResponse.json();
        
        const groupSelect = document.getElementById('edit_groupSelect');
        groupSelect.innerHTML = '<option value="">Без группы</option>' +
            groups.map(g => `<option value="${g.id}">${g.name} (${g.schedule_time})</option>`).join('');
    } catch (error) {
        console.error('Ошибка загрузки групп:', error);
    }

    // Загрузить тарифы
    try {
        const tariffsResponse = await fetch('/api/tariffs');
        const tariffs = await tariffsResponse.json();
        
        const tariffSelect = document.getElementById('edit_tariffSelect');
        tariffSelect.innerHTML = '<option value="">Без тарифа</option>' +
            tariffs.map(t => `<option value="${t.id}">${t.name} - ${parseInt(t.price).toLocaleString('ru-RU')} сум (${t.lessons_count} занятий)</option>`).join('');
    } catch (error) {
        console.error('Ошибка загрузки тарифов:', error);
    }
}

// Загрузка районов для формы редактирования
async function loadEditDistricts(city) {
    const districtSelect = document.getElementById('edit_districtSelect');
    
    if (!city) {
        districtSelect.innerHTML = '<option value="">Сначала выберите город</option>';
        districtSelect.disabled = true;
        return;
    }
    
    try {
        const response = await fetch(`/api/locations/districts/${encodeURIComponent(city)}`);
        const districts = await response.json();
        
        districtSelect.innerHTML = '<option value="">Выберите район</option>' +
            districts.map(d => `<option value="${d}">${d}</option>`).join('');
        districtSelect.disabled = false;
    } catch (error) {
        console.error('Ошибка загрузки районов:', error);
    }
}

// Обработчик выбора города в форме редактирования
document.getElementById('edit_citySelect')?.addEventListener('change', async (e) => {
    const city = e.target.value;
    await loadEditDistricts(city);
});

// Модальные окна
const addStudentModal = document.getElementById('addStudentModal');
const editStudentModal = document.getElementById('editStudentModal');
const paymentModal = document.getElementById('paymentModal');
const addStudentBtn = document.getElementById('addStudentBtn');
const closeBtns = document.querySelectorAll('.close');

// Открыть модалку добавления ученика
addStudentBtn.addEventListener('click', () => {
    loadFormData();
    document.getElementById('addStudentForm').reset();
    document.getElementById('last_name').value = '';
    document.getElementById('first_name').value = '';
    document.getElementById('middle_name').value = '';
    document.getElementById('full_name_hidden').value = '';
    const admissionInput = document.getElementById('admission_date');
    if (admissionInput) {
        admissionInput.value = new Date().toISOString().split('T')[0];
    }
    // Сброс превью фото
    const addPreview = document.getElementById('add-photo-preview');
    if (addPreview) {
        addPreview.innerHTML = `
            <div class="photo-placeholder">
                <button type="button" class="photo-select-btn" id="add-photo-select-btn">
                    <span class="photo-select-icon">+</span>
                    <span class="photo-select-text">Выбрать</span>
                </button>
                <small class="photo-hint">Или нажмите в любом месте и вставьте фото (Ctrl+V)</small>
            </div>
        `;
        // Переинициализировать компонент
        setTimeout(() => {
            initPhotoUpload('add-photo-upload', 'add_photo_input', 'add-photo-preview', 'add-photo-area', 'add-photo-select-btn');
        }, 100);
    }
    addStudentModal.style.display = 'block';
});

// Закрыть модалки
closeBtns.forEach(btn => {
    btn.addEventListener('click', () => {
        if (addStudentModal.style.display === 'block') {
            addStudentModal.style.display = 'none';
            document.getElementById('addStudentForm').reset();
            // Сброс превью фото
            const addPreview = document.getElementById('add-photo-preview');
            if (addPreview) {
                addPreview.innerHTML = `
                    <div class="photo-placeholder">
                        <button type="button" class="photo-select-btn" id="add-photo-select-btn">
                            <span class="photo-select-icon">+</span>
                            <span class="photo-select-text">Выбрать</span>
                        </button>
                        <small class="photo-hint">Или нажмите в любом месте и вставьте фото (Ctrl+V)</small>
                    </div>
                `;
                // Переинициализировать компонент
                setTimeout(() => {
                    initPhotoUpload('add-photo-upload', 'add_photo_input', 'add-photo-preview', 'add-photo-area', 'add-photo-select-btn');
                }, 100);
            }
        }
        if (editStudentModal.style.display === 'block') {
            editStudentModal.style.display = 'none';
        }
        paymentModal.style.display = 'none';
    });
});

// Закрыть при клике вне модалки
window.addEventListener('click', (e) => {
    if (e.target === addStudentModal) addStudentModal.style.display = 'none';
    if (e.target === editStudentModal) editStudentModal.style.display = 'none';
    if (e.target === paymentModal) paymentModal.style.display = 'none';
});

// Добавить ученика
document.getElementById('addStudentForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const lastName = document.getElementById('last_name').value;
    const firstName = document.getElementById('first_name').value;
    const middleName = document.getElementById('middle_name').value;
    const fullName = buildFullName(lastName, firstName, middleName);
    document.getElementById('full_name_hidden').value = fullName;
    
    // Проверка наличия фото
    const photoInput = document.getElementById('add_photo_input');
    if (!photoInput.files || photoInput.files.length === 0) {
        alert('Пожалуйста, загрузите фото ученика');
        const container = document.getElementById('add-photo-upload');
        if (container) {
            container.focus();
            container.classList.add('error');
            setTimeout(() => container.classList.remove('error'), 2000);
        }
        return;
    }
    
    const formData = new FormData(e.target);
    
    try {
        const response = await fetch('/api/students/add', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (data.success) {
            alert('Ученик успешно добавлен!');
            location.reload();
        } else {
            alert('Ошибка: ' + data.message);
        }
    } catch (error) {
        alert('Ошибка: ' + error.message);
    }
});

// Редактировать ученика (отправка формы)
document.getElementById('editStudentForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const studentId = document.getElementById('edit_student_id').value;
    const lastName = document.getElementById('edit_last_name').value;
    const firstName = document.getElementById('edit_first_name').value;
    const middleName = document.getElementById('edit_middle_name').value;
    const fullName = buildFullName(lastName, firstName, middleName);
    document.getElementById('edit_full_name').value = fullName;
    const formData = new FormData(e.target);
    
    try {
        const response = await fetch(`/api/students/${studentId}`, {
            method: 'PUT',
            body: formData
        });
        
        const data = await response.json();
        
        if (data.success) {
            alert('✓ Данные ученика обновлены!');
            location.reload();
        } else {
            alert('Ошибка: ' + data.message);
        }
    } catch (error) {
        alert('Ошибка: ' + error.message);
    }
});

// Открыть модалку оплаты
document.querySelectorAll('.add-payment-btn').forEach(btn => {
    btn.addEventListener('click', async () => {
        const studentId = btn.getAttribute('data-student-id');
        document.getElementById('payment_student_id').value = studentId;
        
        // Загрузить информацию об ученике и его тарифе
        try {
            const response = await fetch(`/api/students/${studentId}`);
            const student = await response.json();
            
            // Сохранить цену тарифа если есть
            const tariffPrice = student.tariff_price || 500000; // Дефолт
            document.getElementById('student_tariff_price').value = tariffPrice;
            
            // Инициализировать помесячное отображение
            await initMonthlyPaymentView(studentId, tariffPrice);
            
            paymentModal.style.display = 'block';
        } catch (error) {
            console.error('Ошибка загрузки ученика:', error);
            alert('Ошибка загрузки данных');
        }
    });
});

// Глобальные переменные для управления годом и выбранным месяцем
let currentPaymentYear = new Date().getFullYear();
let selectedMonth = null;
let studentPaymentsData = {};
let selectedMonthInfo = null; // хранит остаток и тариф для проверки суммы
let paymentClubSettings = { block_future_payments: false };

async function ensurePaymentSettingsLoaded() {
    if (paymentClubSettings.__loaded) return;
    try {
        const resp = await fetch('/api/club-settings');
        const data = await resp.json();
        paymentClubSettings = { ...data, __loaded: true };
    } catch (e) {
        console.error('Не удалось загрузить настройки клуба для оплат:', e);
        paymentClubSettings = { block_future_payments: false, __loaded: true };
    }
}

// Инициализация помесячного отображения оплаты
async function initMonthlyPaymentView(studentId, tariffPrice) {
    await ensurePaymentSettingsLoaded();
    currentPaymentYear = new Date().getFullYear();
    selectedMonth = null;
    
    // Загрузить данные о платежах ученика
    try {
        const response = await fetch(`/api/students/${studentId}/monthly-payments`);
        const data = await response.json();
        // Новый формат API возвращает объект с payments_by_month
        studentPaymentsData = data.payments_by_month || {};
    } catch (error) {
        console.error('Ошибка загрузки платежей:', error);
        studentPaymentsData = {};
    }
    
    // Загрузить дату принятия ученика
    let admissionDate = null;
    try {
        const studentResponse = await fetch(`/api/students/${studentId}`);
        const studentData = await studentResponse.json();
        admissionDate = studentData.admission_date ? new Date(studentData.admission_date) : null;
    } catch (error) {
        console.error('Ошибка загрузки данных ученика:', error);
    }
    
    // Сохранить дату принятия глобально
    window.studentAdmissionDate = admissionDate;
    
    // Обновить интерфейс
    updateYearDisplay();
    renderMonthlyGrid(tariffPrice);
    hidePaymentInput();
}

// Обновить отображение года
function updateYearDisplay() {
    document.getElementById('currentYear').textContent = currentPaymentYear;
    document.getElementById('prevYear').textContent = currentPaymentYear - 1;
    document.getElementById('nextYear').textContent = currentPaymentYear + 1;
}

// Отрисовать сетку месяцев
function renderMonthlyGrid(tariffPrice) {
    const monthNames = ['Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь', 
                        'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь'];
    const monthlyGrid = document.getElementById('monthlyPayments');
    monthlyGrid.innerHTML = '';
    
    // Определить минимально доступный месяц на основе admission_date
    let minYear = 1900;
    let minMonth = 1;
    if (window.studentAdmissionDate) {
        const admission = new Date(window.studentAdmissionDate);
        minYear = admission.getFullYear();
        minMonth = admission.getMonth() + 1; // JS месяцы 0-based
    }
    
    const today = new Date();
    const todayYear = today.getFullYear();
    const todayMonth = today.getMonth() + 1;

    monthNames.forEach((monthName, index) => {
        const monthNumber = index + 1;
        const monthKey = `${currentPaymentYear}-${String(monthNumber).padStart(2, '0')}`;
        const monthData = studentPaymentsData[monthKey];
        
        // Получить данные из нового формата API
        const totalPaid = monthData ? monthData.total_paid : 0;
        const remainder = monthData ? monthData.remainder : tariffPrice;
        const isPaid = remainder === 0;
        
        // Проверить доступность месяца
        const isBeforeAdmission = (currentPaymentYear < minYear) || 
                                  (currentPaymentYear === minYear && monthNumber < minMonth);
        const isFuture = paymentClubSettings.block_future_payments && (
            currentPaymentYear > todayYear ||
            (currentPaymentYear === todayYear && monthNumber > todayMonth)
        );
        const isDisabled = isBeforeAdmission || isFuture;
        
        const monthCard = document.createElement('div');
        monthCard.className = 'month-payment-card';
        
        // Добавить классы для стилизации
        if (isDisabled) {
            monthCard.classList.add('disabled');
        } else if (isPaid) {
            monthCard.classList.add('paid');
        }
        
        // Определить статус и иконку
        let statusIcon = '';
        let statusText = '';
        let statusColor = '';
        
        if (isDisabled) {
            statusIcon = '🔒';
            statusText = 'Недоступно';
            statusColor = '#94a3b8';
        } else if (isPaid) {
            statusIcon = '✓';
            statusText = 'Оплачено';
            statusColor = '#10b981';
        } else {
            statusIcon = '⏳';
            statusText = 'Не оплачено';
            statusColor = '#f59e0b';
        }
        
        monthCard.innerHTML = `
            <div style="flex: 1; display: flex; flex-direction: column; gap: 8px;">
                <div style="display: flex; align-items: center; gap: 12px;">
                    <div style="font-weight: 700; font-size: 16px; color: ${isDisabled ? '#94a3b8' : '#1e293b'};">
                        ${monthName}
                    </div>
                    <div style="font-size: 14px; color: ${statusColor}; display: flex; align-items: center; gap: 6px;">
                        <span style="font-size: 16px;">${statusIcon}</span>
                        <span style="font-weight: 600;">${statusText}</span>
                    </div>
                </div>
                <div style="display: flex; gap: 20px; font-size: 13px;">
                    <div style="color: #64748b;">
                        Сумма: <strong style="color: #475569; font-weight: 600;">${totalPaid.toLocaleString('ru-RU')} сум</strong>
                    </div>
                    <div style="font-weight: 600;">
                        Остаток: <strong style="color: ${remainder > 0 ? '#ef4444' : '#10b981'}; font-size: 14px;">${remainder.toLocaleString('ru-RU')} сум</strong>
                    </div>
                </div>
            </div>
            <div style="font-size: 20px; color: #cbd5e1; margin-left: 16px;">
                →
            </div>
        `;
        
        if (!isDisabled) {
            monthCard.addEventListener('click', () => {
                // Убрать выделение с других карточек
                document.querySelectorAll('.month-payment-card').forEach(card => {
                    card.classList.remove('selected');
                });
                // Добавить выделение к выбранной карточке
                monthCard.classList.add('selected');
                
                selectedMonth = { year: currentPaymentYear, month: monthNumber, name: monthName, key: monthKey };
                showPaymentInput(monthName, monthData, tariffPrice);
            });
        }
        
        monthlyGrid.appendChild(monthCard);
    });
}

// Показать форму ввода оплаты за выбранный месяц
function showPaymentInput(monthName, monthData, tariffPrice) {
    // monthData теперь это объект с payments, total_paid, remainder
    const existingPayments = monthData ? monthData.payments : [];
    const remainder = monthData ? monthData.remainder : tariffPrice;
    selectedMonthInfo = {
        remainder,
        tariffPrice
    };
    
    document.getElementById('selectedMonthName').textContent = monthName;
    document.getElementById('paymentInputSection').style.display = 'flex';
    document.getElementById('noMonthSelected').style.display = 'none';
    
    // Установить сегодняшнюю дату
    const today = new Date().toISOString().split('T')[0];
    document.getElementById('payment_date').value = today;
    
    // Очистить поля
    document.getElementById('payment_amount').value = '';
    document.getElementById('payment_notes').value = '';
    
    // Отобразить историю частичных платежей
    const historyDiv = document.getElementById('partialPaymentsHistory');
    if (existingPayments.length > 0) {
        historyDiv.innerHTML = `
            <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 16px; padding-bottom: 12px; border-bottom: 2px solid #e2e8f0;">
                <span style="font-size: 18px;">📋</span>
                <h4 style="margin: 0; font-size: 15px; font-weight: 600; color: #1e293b;">История оплат</h4>
            </div>
            <div style="display: flex; flex-direction: column; gap: 10px;">
                ${existingPayments.map(p => `
                    <div class="payment-history-row" data-payment-id="${p.id || ''}" data-amount="${p.amount}" data-date="${p.date || ''}" data-notes="${p.notes || ''}" style="background: white; padding: 14px 16px; border-left: 4px solid #667eea; border-radius: 10px; display: flex; justify-content: space-between; align-items: center; gap: 16px; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05); transition: all 0.2s ease;">
                        <div style="flex: 1;">
                            <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 6px;">
                                <span style="font-size: 14px; color: #64748b;">📅</span>
                                <strong style="color: #1e293b; font-size: 14px;">${p.date ? new Date(p.date).toLocaleDateString('ru-RU') : '—'}</strong>
                                <span style="color: #64748b;">•</span>
                                <strong style="color: #667eea; font-size: 15px; font-weight: 700;">${p.amount.toLocaleString('ru-RU')} сум</strong>
                            </div>
                            ${p.notes ? `<div style="margin-top: 6px; padding-left: 28px;"><small style="color: #64748b; font-size: 12px;">${p.notes}</small></div>` : ''}
                        </div>
                        ${p.id ? `
                            <div style="display: flex; gap: 6px;">
                                <button type="button" class="btn-small btn-info payment-edit-btn" data-payment-id="${p.id}" data-amount="${p.amount}" data-date="${p.date || ''}" data-notes="${p.notes || ''}" style="border-radius: 8px;">✏️</button>
                                <button type="button" class="btn-small btn-danger payment-delete-btn" data-payment-id="${p.id}" style="border-radius: 8px;">🗑️</button>
                            </div>
                        ` : ''}
                    </div>
                `).join('')}
            </div>
        `;
        historyDiv.style.display = 'block';
    } else {
        historyDiv.style.display = 'none';
    }
    
    // Подсказка по остатку
    if (remainder > 0) {
        document.getElementById('payment_amount').placeholder = `Осталось: ${remainder.toLocaleString('ru-RU')} сум`;
    } else {
        document.getElementById('payment_amount').placeholder = 'Дополнительная оплата';
    }
}

// Скрыть форму ввода
function hidePaymentInput() {
    document.getElementById('paymentInputSection').style.display = 'none';
    document.getElementById('noMonthSelected').style.display = 'flex';
    selectedMonth = null;
    selectedMonthInfo = null;
    
    // Убрать выделение со всех карточек
    document.querySelectorAll('.month-payment-card').forEach(card => {
        card.classList.remove('selected');
    });
}

// Обработчики кнопок переключения года
document.getElementById('prevYearBtn')?.addEventListener('click', () => {
    currentPaymentYear--;
    updateYearDisplay();
    const tariffPrice = parseInt(document.getElementById('student_tariff_price').value) || 500000;
    renderMonthlyGrid(tariffPrice);
    hidePaymentInput();
});

document.getElementById('nextYearBtn')?.addEventListener('click', () => {
    currentPaymentYear++;
    updateYearDisplay();
    const tariffPrice = parseInt(document.getElementById('student_tariff_price').value) || 500000;
    renderMonthlyGrid(tariffPrice);
    hidePaymentInput();
});

// Отправка формы оплаты
document.getElementById('paymentForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    if (!selectedMonth) {
        alert('Выберите месяц для оплаты');
        return;
    }
    
    const studentId = document.getElementById('payment_student_id').value;
    const paymentDate = document.getElementById('payment_date').value;
    const amount = parseFloat(document.getElementById('payment_amount').value);
    const notes = document.getElementById('payment_notes').value;
    
    if (!amount || amount <= 0) {
        alert('Введите корректную сумму оплаты');
        return;
    }

    // Проверка превышения тарифа/остатка
    const tariffPrice = parseInt(document.getElementById('student_tariff_price').value) || 0;
    const allowed = selectedMonthInfo ? selectedMonthInfo.remainder : tariffPrice;
    if (allowed >= 0 && amount > allowed && tariffPrice > 0) {
        alert(`Сумма превышает остаток по тарифу. Доступно не более ${allowed.toLocaleString('ru-RU')} сум`);
        return;
    }
    
    try {
        const response = await fetch('/api/students/add-monthly-payment', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                student_id: studentId,
                year: selectedMonth.year,
                month: selectedMonth.month,
                payment_date: paymentDate,
                amount: amount,
                notes: notes
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            alert(`✓ Оплата за ${selectedMonth.name} добавлена!`);
            location.reload();
        } else {
            alert('Ошибка: ' + data.message);
        }
    } catch (error) {
        alert('Ошибка: ' + error.message);
    }
});

// Редактирование оплаты: открытие модалки по кнопке в истории
document.getElementById('partialPaymentsHistory').addEventListener('click', (e) => {
    const btn = e.target.closest('.payment-edit-btn');
    if (!btn) return;
    const id = btn.dataset.paymentId;
    const amount = btn.dataset.amount || '';
    const date = btn.dataset.date ? btn.dataset.date.split('T')[0] : '';
    const notes = btn.dataset.notes || '';

    document.getElementById('edit_payment_id').value = id;
    document.getElementById('edit_payment_amount').value = amount;
    document.getElementById('edit_payment_date').value = date || new Date().toISOString().split('T')[0];
    document.getElementById('edit_payment_notes').value = notes;

    document.getElementById('editPaymentModal').style.display = 'block';
});

// Закрытие модалки редактирования оплаты
document.querySelector('.edit-payment-close')?.addEventListener('click', () => {
    document.getElementById('editPaymentModal').style.display = 'none';
});

// Сохранение изменений оплаты
document.getElementById('editPaymentForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const paymentId = document.getElementById('edit_payment_id').value;
    const amount = parseFloat(document.getElementById('edit_payment_amount').value);
    const paymentDate = document.getElementById('edit_payment_date').value;
    const notes = document.getElementById('edit_payment_notes').value;

    if (!amount || amount <= 0) {
        alert('Введите корректную сумму');
        return;
    }

    try {
        const resp = await fetch(`/api/payments/${paymentId}/update`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                amount_paid: amount,
                payment_date: paymentDate,
                notes: notes
            })
        });
        const data = await resp.json();
        if (data.success) {
            alert('Оплата обновлена');
            location.reload();
        } else {
            alert('Ошибка: ' + data.message);
        }
    } catch (error) {
        alert('Ошибка: ' + error.message);
    }
});

// Удаление оплаты из истории платежей
document.getElementById('partialPaymentsHistory').addEventListener('click', async (e) => {
    const btn = e.target.closest('.payment-delete-btn');
    if (!btn) return;
    
    const paymentId = btn.dataset.paymentId;
    
    if (!confirm('Вы уверены, что хотите удалить этот платеж?')) {
        return;
    }
    
    try {
        const response = await fetch(`/api/payments/${paymentId}/delete`, {
            method: 'DELETE'
        });
        
        if (response.ok) {
            alert('Платеж успешно удален!');
            location.reload(); // Перезагружаем страницу для обновления данных
        } else {
            const error = await response.json();
            alert('Ошибка: ' + (error.error || 'Не удалось удалить платеж'));
        }
    } catch (error) {
        console.error('Error:', error);
        alert('Ошибка при удалении платежа');
    }
});

// Редактировать ученика
document.querySelectorAll('.edit-student-btn').forEach(btn => {
    btn.addEventListener('click', async () => {
        const studentId = btn.getAttribute('data-student-id');
        
        try {
            const response = await fetch(`/api/students/${studentId}`);
            const student = await response.json();
            
            // Заполнить форму редактирования
            document.getElementById('edit_student_id').value = student.id;
            const nameParts = splitFullName(student.full_name || '');
            document.getElementById('edit_last_name').value = nameParts.last;
            document.getElementById('edit_first_name').value = nameParts.first;
            document.getElementById('edit_middle_name').value = nameParts.middle;
            document.getElementById('edit_full_name').value = student.full_name || '';
            document.getElementById('edit_student_number').value = student.student_number || '';
            document.getElementById('edit_phone').value = student.phone || '';
            document.getElementById('edit_parent_phone').value = student.parent_phone || '';
            document.getElementById('edit_street').value = student.street || '';
            document.getElementById('edit_house_number').value = student.house_number || '';
            document.getElementById('edit_birth_year').value = student.birth_year || '';
            document.getElementById('edit_passport_series').value = student.passport_series || '';
            document.getElementById('edit_passport_number').value = student.passport_number || '';
            document.getElementById('edit_passport_issued_by').value = student.passport_issued_by || '';
            document.getElementById('edit_passport_issue_date').value = student.passport_issue_date || '';
            document.getElementById('edit_passport_expiry_date').value = student.passport_expiry_date || '';
            document.getElementById('edit_admission_date').value = student.admission_date || '';
            document.getElementById('edit_club_funded').checked = student.club_funded || false;
            document.getElementById('edit_statusSelect').value = student.status || 'active';
            document.getElementById('edit_blacklist_reason').value = student.blacklist_reason || '';
            
            // Загрузить города и группы
            await loadEditFormData();
            
            // Установить город
            if (student.city) {
                document.getElementById('edit_citySelect').value = student.city;
                // Загрузить районы
                await loadEditDistricts(student.city);
                if (student.district) {
                    document.getElementById('edit_districtSelect').value = student.district;
                }
            }
            
            // Установить группу
            if (student.group_id) {
                document.getElementById('edit_groupSelect').value = student.group_id;
            }
            
            // Установить тариф
            if (student.tariff_id) {
                document.getElementById('edit_tariffSelect').value = student.tariff_id;
            }
            
            // Показать/скрыть блок причины ЧС
            toggleEditBlacklistReason();
            
            // Открыть модальное окно
            document.getElementById('editStudentModal').style.display = 'block';
            
        } catch (error) {
            console.error('Ошибка загрузки ученика:', error);
            alert('Ошибка загрузки данных ученика');
        }
    });
});

// Удалить ученика
document.querySelectorAll('.delete-student-btn').forEach(btn => {
    btn.addEventListener('click', async () => {
        const studentId = btn.getAttribute('data-student-id');
        const studentName = btn.getAttribute('data-student-name');
        
        if (!confirm(`Вы уверены, что хотите удалить ученика "${studentName}"?\n\nЭто действие необратимо и удалит все связанные данные (платежи, посещения).`)) {
            return;
        }
        
        try {
            const response = await fetch(`/api/students/${studentId}`, {
                method: 'DELETE'
            });
            
            const data = await response.json();
            
            if (data.success) {
                alert('✓ ' + data.message);
                location.reload();
            } else {
                alert('Ошибка: ' + data.message);
            }
        } catch (error) {
            console.error('Ошибка удаления:', error);
            alert('Ошибка при удалении ученика');
        }
    });
});

// ==================== PHOTO UPLOAD COMPONENT ====================

// Глобальная функция для удаления фото
window.deletePhoto = function(containerId, inputId, previewId, areaId, selectBtnId) {
    const input = document.getElementById(inputId);
    const preview = document.getElementById(previewId);
    
    if (!input || !preview) return;
    
    // Очистить input
    input.value = '';
    
    // Вернуть placeholder
    preview.innerHTML = `
        <div class="photo-placeholder">
            <button type="button" class="photo-select-btn" id="${selectBtnId}">
                <span class="photo-select-icon">+</span>
                <span class="photo-select-text">Выбрать</span>
            </button>
            <small class="photo-hint">Или нажмите в любом месте и вставьте фото (Ctrl+V)</small>
        </div>
    `;
    
    // Переинициализировать кнопку
    const newSelectBtn = document.getElementById(selectBtnId);
    if (newSelectBtn) {
        newSelectBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            document.getElementById(inputId).click();
        });
    }
};

// Инициализация компонента загрузки фото
function initPhotoUpload(containerId, inputId, previewId, areaId, selectBtnId) {
    const container = document.getElementById(containerId);
    const input = document.getElementById(inputId);
    const preview = document.getElementById(previewId);
    const area = document.getElementById(areaId);
    const selectBtn = document.getElementById(selectBtnId);
    
    if (!container || !input || !preview || !area || !selectBtn) return;
    
    // Функция для отображения превью
    function showPreview(file) {
        if (!file || !file.type.startsWith('image/')) {
            alert('Пожалуйста, выберите изображение');
            return;
        }
        
        const reader = new FileReader();
        reader.onload = function(e) {
            preview.innerHTML = `
                <img src="${e.target.result}" alt="Preview">
                <button type="button" class="photo-delete-btn" onclick="deletePhoto('${containerId}', '${inputId}', '${previewId}', '${areaId}', '${selectBtnId}')">🗑️ Удалить фото</button>
            `;
        };
        reader.readAsDataURL(file);
        
        // Создаем DataTransfer для установки файла в input
        const dataTransfer = new DataTransfer();
        dataTransfer.items.add(file);
        input.files = dataTransfer.files;
    }
    
    // Кнопка "Выбрать" - открыть проводник
    selectBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        input.click();
    });
    
    // Клик в любом месте блока (кроме кнопки) - активировать режим вставки
    area.addEventListener('click', (e) => {
        // Если клик по кнопке или по изображению, не обрабатываем
        if (e.target.closest('.photo-select-btn') || e.target.tagName === 'IMG' || e.target.closest('.photo-delete-btn')) {
            return;
        }
        // Фокусируемся на контейнере для активации Ctrl+V
        container.focus();
    });
    
    // Обработка вставки через Ctrl+V
    container.addEventListener('paste', (e) => {
        e.preventDefault();
        const items = e.clipboardData.items;
        
        for (let i = 0; i < items.length; i++) {
            if (items[i].type.indexOf('image') !== -1) {
                const blob = items[i].getAsFile();
                const file = new File([blob], 'pasted-image.png', { type: blob.type });
                showPreview(file);
                break;
            }
        }
    });
    
    // Обработка выбора файла через проводник
    input.addEventListener('change', (e) => {
        const file = e.target.files[0];
        if (file) {
            showPreview(file);
        }
    });
}

// ==================== FILTER FUNCTIONALITY ====================

// Переключение видимости панели фильтров
function toggleFilterPanel() {
    const filterPanel = document.getElementById('filterPanel');
    const filterToggleBtn = document.getElementById('filterToggleBtn');
    const filterToggleText = document.getElementById('filterToggleText');
    
    if (filterPanel.style.display === 'none') {
        filterPanel.style.display = 'block';
        filterToggleText.textContent = 'Скрыть фильтр';
        filterToggleBtn.classList.add('active');
    } else {
        filterPanel.style.display = 'none';
        filterToggleText.textContent = 'Фильтр';
        filterToggleBtn.classList.remove('active');
    }
}

// Загрузить группы для фильтра
async function loadFilterGroups() {
    try {
        const response = await fetch('/api/groups');
        const groups = await response.json();
        const groupSelect = document.getElementById('filterGroup');
        
        if (groupSelect) {
            groupSelect.innerHTML = '<option value="">Все группы</option>' +
                groups.map(g => `<option value="${g.id}">${g.name}</option>`).join('');
        }
    } catch (error) {
        console.error('Ошибка загрузки групп для фильтра:', error);
    }
}

// Применить фильтры
function applyFilters() {
    const nameFilter = document.getElementById('filterName').value.toLowerCase().trim();
    const groupFilter = document.getElementById('filterGroup').value;
    const statusFilter = document.getElementById('filterStatus').value;
    const balanceFilter = document.getElementById('filterBalance').value;
    
    const table = document.getElementById('studentsTable');
    const rows = table.querySelectorAll('tbody tr');
    
    let visibleCount = 0;
    
    rows.forEach(row => {
        let show = true;
        
        // Фильтр по имени
        if (nameFilter) {
            const nameCell = row.cells[2]; // Колонка "Имя"
            const nameText = nameCell ? nameCell.textContent.toLowerCase() : '';
            if (!nameText.includes(nameFilter)) {
                show = false;
            }
        }
        
        // Фильтр по группе
        if (groupFilter && show) {
            const groupDataId = row.dataset.groupId || '';
            if (groupDataId !== groupFilter) {
                show = false;
            }
        }
        
        // Фильтр по статусу
        if (statusFilter && show) {
            const rowStatus = row.dataset.status || '';
            if (rowStatus !== statusFilter) {
                show = false;
            }
        }
        
        // Фильтр по балансу
        if (balanceFilter && show) {
            const balanceCell = row.cells[10]; // Колонка "Баланс"
            const balanceText = balanceCell ? balanceCell.textContent.trim() : '';
            
            if (balanceFilter === 'club') {
                if (!balanceText.includes('Клуб')) {
                    show = false;
                }
            } else if (balanceFilter === 'low') {
                if (!row.classList.contains('low-balance')) {
                    show = false;
                }
            } else if (balanceFilter === 'normal') {
                if (row.classList.contains('low-balance') || balanceText.includes('Клуб')) {
                    show = false;
                }
            }
        }
        
        if (show) {
            row.style.display = '';
            visibleCount++;
        } else {
            row.style.display = 'none';
        }
    });
    
    // Показать сообщение, если ничего не найдено
    const tbody = table.querySelector('tbody');
    let noResultsMsg = table.querySelector('.no-results-message');
    
    if (visibleCount === 0) {
        if (!noResultsMsg) {
            noResultsMsg = document.createElement('tr');
            noResultsMsg.className = 'no-results-message';
            noResultsMsg.innerHTML = `
                <td colspan="14" style="text-align: center; padding: 40px; color: #94a3b8;">
                    <div style="font-size: 48px; margin-bottom: 16px;">🔍</div>
                    <div style="font-size: 18px; font-weight: 600;">Ничего не найдено</div>
                    <div style="font-size: 14px; margin-top: 8px;">Попробуйте изменить параметры фильтра</div>
                </td>
            `;
            tbody.appendChild(noResultsMsg);
        }
        noResultsMsg.style.display = '';
    } else {
        if (noResultsMsg) {
            noResultsMsg.style.display = 'none';
        }
    }
}

// Сбросить фильтры
function clearFilters() {
    document.getElementById('filterName').value = '';
    document.getElementById('filterGroup').value = '';
    document.getElementById('filterStatus').value = '';
    document.getElementById('filterBalance').value = '';
    
    // Показать все строки
    const table = document.getElementById('studentsTable');
    const rows = table.querySelectorAll('tbody tr');
    rows.forEach(row => {
        row.style.display = '';
    });
    
    // Убрать сообщение "Ничего не найдено"
    const noResultsMsg = table.querySelector('.no-results-message');
    if (noResultsMsg) {
        noResultsMsg.style.display = 'none';
    }
}

// Инициализация при загрузке DOM
document.addEventListener('DOMContentLoaded', () => {
    // Инициализация фильтров
    const filterToggleBtn = document.getElementById('filterToggleBtn');
    if (filterToggleBtn) {
        filterToggleBtn.addEventListener('click', toggleFilterPanel);
    }
    
    const applyFiltersBtn = document.getElementById('applyFiltersBtn');
    if (applyFiltersBtn) {
        applyFiltersBtn.addEventListener('click', applyFilters);
    }
    
    const clearFiltersBtn = document.getElementById('clearFiltersBtn');
    if (clearFiltersBtn) {
        clearFiltersBtn.addEventListener('click', clearFilters);
    }
    
    // Загрузить группы для фильтра
    loadFilterGroups();
    
    // Фильтрация при вводе в поле поиска (с задержкой)
    const filterNameInput = document.getElementById('filterName');
    if (filterNameInput) {
        let filterTimeout;
        filterNameInput.addEventListener('input', () => {
            clearTimeout(filterTimeout);
            filterTimeout = setTimeout(() => {
                applyFilters();
            }, 300);
        });
    }
    
    // Фильтрация при изменении селектов
    ['filterGroup', 'filterStatus', 'filterBalance'].forEach(filterId => {
        const filterElement = document.getElementById(filterId);
        if (filterElement) {
            filterElement.addEventListener('change', applyFilters);
        }
    });
    
    // Инициализация для формы добавления
    initPhotoUpload('add-photo-upload', 'add_photo_input', 'add-photo-preview', 'add-photo-area', 'add-photo-select-btn');
    
    // Инициализация для формы редактирования
    initPhotoUpload('edit-photo-upload', 'edit_photo', 'edit-photo-preview', 'edit-photo-area', 'edit-photo-select-btn');
    
    // При открытии формы редактирования, показать текущее фото если есть
    const editStudentBtn = document.querySelectorAll('.edit-student-btn');
    editStudentBtn.forEach(btn => {
        btn.addEventListener('click', async () => {
            const studentId = btn.dataset.studentId;
            try {
                const response = await fetch(`/api/students/${studentId}`);
                const student = await response.json();
                
                const preview = document.getElementById('edit-photo-preview');
                if (preview) {
                    if (student.photo_path) {
                        const photoPath = student.photo_path.replace('frontend/static/', '').replace(/\\/g, '/');
                        preview.innerHTML = `
                            <img src="/static/${photoPath}" alt="Current photo">
                            <button type="button" class="photo-delete-btn" onclick="deletePhoto('edit-photo-upload', 'edit_photo', 'edit-photo-preview', 'edit-photo-area', 'edit-photo-select-btn')">🗑️ Удалить фото</button>
                        `;
                    } else {
                        preview.innerHTML = `
                            <div class="photo-placeholder">
                                <button type="button" class="photo-select-btn" id="edit-photo-select-btn">
                                    <span class="photo-select-icon">+</span>
                                    <span class="photo-select-text">Выбрать</span>
                                </button>
                                <small class="photo-hint">Или нажмите в любом месте и вставьте фото (Ctrl+V)</small>
                            </div>
                        `;
                        // Переинициализировать кнопку
                        const newSelectBtn = document.getElementById('edit-photo-select-btn');
                        if (newSelectBtn) {
                            newSelectBtn.addEventListener('click', (e) => {
                                e.stopPropagation();
                                document.getElementById('edit_photo').click();
                            });
                        }
                    }
                }
            } catch (error) {
                console.error('Ошибка загрузки фото ученика:', error);
            }
        });
    });
});
