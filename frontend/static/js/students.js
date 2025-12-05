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
    document.getElementById('last_name').value = '';
    document.getElementById('first_name').value = '';
    document.getElementById('middle_name').value = '';
    document.getElementById('full_name_hidden').value = '';
    const admissionInput = document.getElementById('admission_date');
    if (admissionInput) {
        admissionInput.value = new Date().toISOString().split('T')[0];
    }
    addStudentModal.style.display = 'block';
});

// Закрыть модалки
closeBtns.forEach(btn => {
    btn.addEventListener('click', () => {
        addStudentModal.style.display = 'none';
        editStudentModal.style.display = 'none';
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

// Инициализация помесячного отображения оплаты
async function initMonthlyPaymentView(studentId, tariffPrice) {
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
        const isDisabled = isBeforeAdmission;
        
        const monthCard = document.createElement('div');
        monthCard.className = 'month-payment-card';
        monthCard.style.cssText = `
            border: 2px solid ${isDisabled ? '#e0e0e0' : (isPaid ? '#27ae60' : '#95a5a6')};
            border-radius: 8px;
            padding: 15px;
            cursor: ${isDisabled ? 'not-allowed' : 'pointer'};
            background: ${isDisabled ? '#f5f5f5' : (isPaid ? '#e8f8f0' : '#ffffff')};
            transition: all 0.2s;
            opacity: ${isDisabled ? '0.5' : '1'};
        `;
        
        monthCard.innerHTML = `
            <div style="font-weight: bold; margin-bottom: 8px; color: ${isDisabled ? '#bbb' : (isPaid ? '#27ae60' : '#2c3e50')};">
                ${monthName}
            </div>
            <div style="font-size: 13px; color: #7f8c8d;">
                ${isDisabled ? '🔒 Недоступно' : (isPaid ? '✓ Оплачено' : 'Не оплачено')}
            </div>
            <div style="margin-top: 5px; font-size: 12px;">
                Сумма: <strong>${totalPaid.toLocaleString('ru-RU')}</strong>
            </div>
            <div style="font-size: 12px;">
                Остаток: <strong style="color: ${remainder > 0 ? '#e74c3c' : '#27ae60'};">${remainder.toLocaleString('ru-RU')}</strong>
            </div>
        `;
        
        if (!isDisabled) {
            monthCard.addEventListener('mouseover', () => {
                monthCard.style.transform = 'translateY(-2px)';
                monthCard.style.boxShadow = '0 4px 12px rgba(0,0,0,0.15)';
            });
            monthCard.addEventListener('mouseout', () => {
                monthCard.style.transform = '';
                monthCard.style.boxShadow = '';
            });
            
            monthCard.addEventListener('click', () => {
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
    
    document.getElementById('selectedMonthName').textContent = monthName;
    document.getElementById('paymentInputSection').style.display = 'block';
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
        historyDiv.innerHTML = '<h4 style="margin: 0 0 10px 0; font-size: 14px;">История оплат:</h4>' +
            existingPayments.map(p => `
                <div style="background: #fff; padding: 8px; border-left: 3px solid #3498db; margin-bottom: 8px; border-radius: 4px;">
                    <strong>${new Date(p.date).toLocaleDateString('ru-RU')}</strong>: ${p.amount.toLocaleString('ru-RU')} сум
                    ${p.notes ? `<br><small style="color: #7f8c8d;">${p.notes}</small>` : ''}
                </div>
            `).join('');
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
    document.getElementById('noMonthSelected').style.display = 'block';
    selectedMonth = null;
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
