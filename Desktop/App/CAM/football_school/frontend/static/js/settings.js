document.addEventListener('DOMContentLoaded', initSettings);

async function initSettings() {
    attachWorkingDayToggles();
    await loadSettings();
    await loadAdminCredentials();
    
    const form = document.getElementById('settingsForm');
    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        await saveSettings();
    });
    
    const adminForm = document.getElementById('adminCredentialsForm');
    if (adminForm) {
        adminForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            await saveAdminCredentials();
        });
    }
}

function attachWorkingDayToggles() {
    const container = document.getElementById('working-days');
    if (!container) return;
    container.addEventListener('click', (e) => {
        const btn = e.target.closest('.day-toggle');
        if (!btn) return;
        btn.classList.toggle('active');
    });
}

function collectWorkingDays() {
    return Array.from(document.querySelectorAll('.day-toggle.active'))
        .map(btn => parseInt(btn.dataset.day, 10));
}

function setWorkingDays(days) {
    const set = new Set(days || []);
    document.querySelectorAll('.day-toggle').forEach(btn => {
        const day = parseInt(btn.dataset.day, 10);
        if (set.has(day)) {
            btn.classList.add('active');
        } else {
            btn.classList.remove('active');
        }
    });
}

async function loadSettings() {
    try {
        const resp = await fetch('/api/club-settings');
        const data = await resp.json();
        document.getElementById('system_name').value = data.system_name || '';
        setWorkingDays(data.working_days || []);
        document.getElementById('work_start_time').value = data.work_start_time || '09:00';
        document.getElementById('work_end_time').value = data.work_end_time || '21:00';
        document.getElementById('max_groups_per_slot').value = data.max_groups_per_slot || 1;
        document.getElementById('block_future_payments').checked = !!data.block_future_payments;
        document.getElementById('rewards_reset_period_months').value = data.rewards_reset_period_months || 1;
        // Убедимся, что значение кратно 5 и в диапазоне 5-50
        const podiumValue = data.podium_display_count || 20;
        const normalizedPodiumValue = Math.max(5, Math.min(50, Math.round(podiumValue / 5) * 5));
        document.getElementById('podium_display_count').value = normalizedPodiumValue;
    } catch (error) {
        console.error('Ошибка загрузки настроек:', error);
        alert('Не удалось загрузить настройки');
    }
}

async function saveSettings() {
    const system_name = document.getElementById('system_name').value.trim();
    const working_days = collectWorkingDays();
    const work_start_time = document.getElementById('work_start_time').value;
    const work_end_time = document.getElementById('work_end_time').value;
    const max_groups_per_slot = parseInt(document.getElementById('max_groups_per_slot').value, 10);
    const block_future_payments = document.getElementById('block_future_payments').checked;
    const rewards_reset_period_months = parseInt(document.getElementById('rewards_reset_period_months').value, 10);
    const podium_display_count = parseInt(document.getElementById('podium_display_count').value, 10);

    if (!system_name) {
        alert('Введите название системы');
        return;
    }

    if (rewards_reset_period_months < 1 || rewards_reset_period_months > 12) {
        alert('Период сброса вознаграждений должен быть от 1 до 12 месяцев');
        return;
    }

    if (podium_display_count < 5 || podium_display_count > 50 || podium_display_count % 5 !== 0) {
        alert('Отображение пьедестала должно быть от 5 до 50 учеников с шагом 5');
        return;
    }

    try {
        const resp = await fetch('/api/club-settings', {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                system_name,
                working_days,
                work_start_time,
                work_end_time,
                max_groups_per_slot,
                block_future_payments,
                rewards_reset_period_months,
                podium_display_count
            })
        });
        const data = await resp.json();
        if (data.success) {
            alert('Настройки сохранены');
        } else {
            alert('Ошибка: ' + (data.message || 'не удалось сохранить'));
        }
    } catch (error) {
        console.error('Ошибка сохранения настроек:', error);
        alert('Не удалось сохранить настройки');
    }
}

async function loadAdminCredentials() {
    try {
        const resp = await fetch('/api/admin-credentials');
        const data = await resp.json();
        if (data.success) {
            document.getElementById('current_username').value = data.username || '';
        } else {
            console.error('Ошибка загрузки учетных данных:', data.message);
            // Скрыть форму, если нет доступа
            const adminForm = document.getElementById('adminCredentialsForm');
            if (adminForm) {
                adminForm.closest('.card').style.display = 'none';
            }
        }
    } catch (error) {
        console.error('Ошибка загрузки учетных данных:', error);
        // Скрыть форму при ошибке
        const adminForm = document.getElementById('adminCredentialsForm');
        if (adminForm) {
            adminForm.closest('.card').style.display = 'none';
        }
    }
}

async function saveAdminCredentials() {
    const newUsername = document.getElementById('new_username').value.trim();
    const newPassword = document.getElementById('new_password').value;
    const confirmPassword = document.getElementById('confirm_password').value;
    
    // Валидация
    if (newUsername && newUsername.length < 3) {
        alert('Логин должен содержать минимум 3 символа');
        return;
    }
    
    if (newPassword && newPassword.length < 6) {
        alert('Пароль должен содержать минимум 6 символов');
        return;
    }
    
    if (newPassword && newPassword !== confirmPassword) {
        alert('Пароли не совпадают');
        return;
    }
    
    if (!newUsername && !newPassword) {
        alert('Введите новый логин и/или пароль');
        return;
    }
    
    try {
        const resp = await fetch('/api/admin-credentials', {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                username: newUsername,
                password: newPassword,
                confirm_password: confirmPassword
            })
        });
        
        const data = await resp.json();
        if (data.success) {
            alert('Учетные данные успешно обновлены!');
            // Очистить поля
            document.getElementById('new_username').value = '';
            document.getElementById('new_password').value = '';
            document.getElementById('confirm_password').value = '';
            // Обновить текущий логин
            await loadAdminCredentials();
        } else {
            alert('Ошибка: ' + (data.message || 'не удалось сохранить'));
        }
    } catch (error) {
        console.error('Ошибка сохранения учетных данных:', error);
        alert('Не удалось сохранить учетные данные');
    }
}

