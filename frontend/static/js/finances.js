// Переключение вкладок
document.querySelectorAll('.tab').forEach(tab => {
    tab.addEventListener('click', () => {
        const tabName = tab.getAttribute('data-tab');
        
        // Убрать активный класс со всех вкладок
        document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(tc => tc.classList.remove('active'));
        
        // Активировать выбранную вкладку
        tab.classList.add('active');
        document.getElementById(`${tabName}-tab`).classList.add('active');
    });
});

// Загрузка данных прихода
async function loadIncome() {
    try {
        const response = await fetch('/api/finances/income');
        const data = await response.json();
        
        // Статистика
        document.getElementById('income-today').textContent = data.today.toLocaleString('ru-RU') + ' сум';
        document.getElementById('income-month').textContent = data.month.toLocaleString('ru-RU') + ' сум';
        document.getElementById('income-total').textContent = data.total.toLocaleString('ru-RU') + ' сум';
        
        // Таблица
        const tbody = document.getElementById('income-table-body');
        if (data.payments.length === 0) {
            tbody.innerHTML = '<tr><td colspan="7" style="text-align: center; color: #95a5a6;">Нет данных</td></tr>';
            return;
        }
        
        tbody.innerHTML = data.payments.map(p => {
            const date = new Date(p.payment_date).toLocaleDateString('ru-RU');
            const status = p.is_full_payment 
                ? '<span style="color: #27ae60;">✓ Полная</span>' 
                : '<span style="color: #f39c12;">⚠️ Частичная</span>';
            const debt = p.amount_due > 0 
                ? `<span class="debt-badge">${p.amount_due.toLocaleString('ru-RU')} сум</span>`
                : '-';
            
            return `
                <tr>
                    <td>${date}</td>
                    <td>${p.student_name}</td>
                    <td>${p.tariff_name || '-'}</td>
                    <td><strong>${p.amount_paid.toLocaleString('ru-RU')} сум</strong></td>
                    <td>${debt}</td>
                    <td>${status}</td>
                    <td>${p.notes || '-'}</td>
                </tr>
            `;
        }).join('');
    } catch (error) {
        console.error('Ошибка загрузки прихода:', error);
    }
}

// Загрузка должников
async function loadDebtors() {
    try {
        const response = await fetch('/api/finances/debtors');
        const data = await response.json();
        
        // Статистика
        document.getElementById('total-debt').textContent = data.total_debt.toLocaleString('ru-RU') + ' сум';
        document.getElementById('debtors-count').textContent = data.count;
        
        // Таблица
        const tbody = document.getElementById('debtors-table-body');
        if (data.debtors.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" style="text-align: center; color: #27ae60;">Нет должников 🎉</td></tr>';
            return;
        }
        
        tbody.innerHTML = data.debtors.map(d => {
            return `
                <tr>
                    <td><strong>${d.student_name}</strong></td>
                    <td>${d.student_phone}</td>
                    <td>${d.tariff_name}</td>
                    <td><span style="background: #fff3cd; padding: 4px 8px; border-radius: 4px;">${d.month_label}</span></td>
                    <td>${d.amount_paid.toLocaleString('ru-RU')} сум</td>
                    <td><span class="debt-badge">${d.amount_due.toLocaleString('ru-RU')} сум</span></td>
                </tr>
            `;
        }).join('');
    } catch (error) {
        console.error('Ошибка загрузки должников:', error);
    }
}

// Загрузка расходов
async function loadExpenses() {
    try {
        const response = await fetch('/api/finances/expenses');
        const data = await response.json();
        
        // Статистика
        document.getElementById('expense-today').textContent = data.today.toLocaleString('ru-RU') + ' сум';
        document.getElementById('expense-month').textContent = data.month.toLocaleString('ru-RU') + ' сум';
        document.getElementById('expense-total').textContent = data.total.toLocaleString('ru-RU') + ' сум';
        
        // Таблица
        const tbody = document.getElementById('expense-table-body');
        if (data.expenses.length === 0) {
            tbody.innerHTML = '<tr><td colspan="4" style="text-align: center; color: #95a5a6;">Нет расходов</td></tr>';
            return;
        }
        
        tbody.innerHTML = data.expenses.map(e => {
            const date = new Date(e.expense_date).toLocaleDateString('ru-RU');
            return `
                <tr>
                    <td>${date}</td>
                    <td><span style="color: #e74c3c;">${e.category}</span></td>
                    <td><strong>${e.amount.toLocaleString('ru-RU')} сум</strong></td>
                    <td>${e.description || '-'}</td>
                </tr>
            `;
        }).join('');
    } catch (error) {
        console.error('Ошибка загрузки расходов:', error);
    }
}

// Загрузка аналитики
async function loadAnalytics() {
    try {
        const response = await fetch('/api/finances/analytics');
        const data = await response.json();
        
        // Таблица
        const tbody = document.getElementById('analytics-table-body');
        if (data.months.length === 0) {
            tbody.innerHTML = '<tr><td colspan="4" style="text-align: center; color: #95a5a6;">Нет данных</td></tr>';
            return;
        }
        
        tbody.innerHTML = data.months.map(m => {
            const balance = m.income - m.expense;
            const balanceColor = balance >= 0 ? '#27ae60' : '#e74c3c';
            
            return `
                <tr>
                    <td><strong>${m.month_name}</strong></td>
                    <td style="color: #27ae60;">${m.income.toLocaleString('ru-RU')} сум</td>
                    <td style="color: #e74c3c;">${m.expense.toLocaleString('ru-RU')} сум</td>
                    <td style="color: ${balanceColor}; font-weight: bold;">
                        ${balance >= 0 ? '+' : ''}${balance.toLocaleString('ru-RU')} сум
                    </td>
                </tr>
            `;
        }).join('');
        
        // График (простая визуализация без Chart.js)
        drawSimpleChart(data.months);
    } catch (error) {
        console.error('Ошибка загрузки аналитики:', error);
    }
}

// Простой график на Canvas
function drawSimpleChart(months) {
    const canvas = document.getElementById('financeChart');
    const ctx = canvas.getContext('2d');
    
    canvas.width = canvas.offsetWidth;
    canvas.height = 300;
    
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    
    if (months.length === 0) {
        ctx.fillStyle = '#95a5a6';
        ctx.font = '16px Arial';
        ctx.textAlign = 'center';
        ctx.fillText('Нет данных для отображения', canvas.width / 2, canvas.height / 2);
        return;
    }
    
    const padding = 40;
    const chartWidth = canvas.width - padding * 2;
    const chartHeight = canvas.height - padding * 2;
    
    const maxValue = Math.max(...months.map(m => Math.max(m.income, m.expense)));
    const barWidth = chartWidth / (months.length * 2 + 1);
    
    months.forEach((m, i) => {
        const x = padding + i * barWidth * 2 + barWidth / 2;
        
        // Приход (зелёный)
        const incomeHeight = (m.income / maxValue) * chartHeight;
        ctx.fillStyle = '#27ae60';
        ctx.fillRect(x, padding + chartHeight - incomeHeight, barWidth * 0.8, incomeHeight);
        
        // Расход (красный)
        const expenseHeight = (m.expense / maxValue) * chartHeight;
        ctx.fillStyle = '#e74c3c';
        ctx.fillRect(x + barWidth, padding + chartHeight - expenseHeight, barWidth * 0.8, expenseHeight);
        
        // Подпись месяца
        ctx.fillStyle = '#2c3e50';
        ctx.font = '12px Arial';
        ctx.textAlign = 'center';
        ctx.fillText(m.month_name, x + barWidth, canvas.height - 10);
    });
    
    // Легенда
    ctx.fillStyle = '#27ae60';
    ctx.fillRect(padding, 10, 20, 15);
    ctx.fillStyle = '#2c3e50';
    ctx.font = '14px Arial';
    ctx.textAlign = 'left';
    ctx.fillText('Приход', padding + 25, 22);
    
    ctx.fillStyle = '#e74c3c';
    ctx.fillRect(padding + 100, 10, 20, 15);
    ctx.fillText('Расход', padding + 125, 22);
}

// Загрузить все данные при открытии страницы
loadIncome();
loadDebtors();
loadExpenses();
loadAnalytics();
