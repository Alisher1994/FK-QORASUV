const DAY_LABELS = { 1: 'Пн', 2: 'Вт', 3: 'Ср', 4: 'Чт', 5: 'Пт', 6: 'Сб', 7: 'Вс' };
let clubSettings = {
    working_days: [1, 2, 3, 4, 5],
    work_start_time: '09:00',
    work_end_time: '21:00',
    max_groups_per_slot: 4
};

function describeDays(days) {
    if (!days || days.length === 0) return '-';
    return days.map(day => DAY_LABELS[day] || day).join(', ');
}

function setWeekdaySelection(target, days) {
    const boxes = document.querySelectorAll(`.weekday-checkbox[data-target="${target}"]`);
    boxes.forEach(box => {
        box.checked = days.includes(parseInt(box.value));
    });
}

function getSelectedDays(target) {
    const boxes = document.querySelectorAll(`.weekday-checkbox[data-target="${target}"]`);
    return Array.from(boxes)
        .filter(box => box.checked)
        .map(box => parseInt(box.value));
}

function updateWorkingHoursHint() {
    const hint = document.getElementById('workingHoursHint');
    if (hint) {
        hint.textContent = `Рабочее время клуба: ${clubSettings.work_start_time} – ${clubSettings.work_end_time}. Максимум ${clubSettings.max_groups_per_slot} групп.`;
    }
}

async function loadClubSettings() {
    try {
        const response = await fetch('/api/club-settings');
        const data = await response.json();
        clubSettings = data;
        updateWorkingHoursHint();
        setWeekdaySelection('settings', clubSettings.working_days);
        document.getElementById('workStartTime').value = clubSettings.work_start_time;
        document.getElementById('workEndTime').value = clubSettings.work_end_time;
        document.getElementById('maxGroupsPerSlot').value = clubSettings.max_groups_per_slot;
    } catch (error) {
        console.error('Ошибка загрузки настроек клуба:', error);
    }
}

async function loadGroups() {
    try {
        const response = await fetch('/api/groups');
        const groups = await response.json();
        
        const tbody = document.getElementById('groupsTableBody');
        
        if (!groups.length) {
            tbody.innerHTML = '<tr><td colspan="7">Нет групп</td></tr>';
            return;
        }
        
        tbody.innerHTML = groups.map(group => {
            let studentsDisplay = group.active_student_count || group.student_count || 0;
            if (group.max_students) {
                const isFull = group.is_full;
                const color = isFull ? '#e74c3c' : (group.active_student_count / group.max_students > 0.8 ? '#f39c12' : '#27ae60');
                studentsDisplay = `<span style="color: ${color}; font-weight: bold;">${group.active_student_count}/${group.max_students}</span>`;
            }
            
            return `
            <tr>
                <td><strong>${group.name}</strong></td>
                <td>${group.schedule_days_label || describeDays(group.schedule_days)}</td>
                <td>${group.schedule_time}</td>
                <td>${group.late_threshold}</td>
                <td>${studentsDisplay}</td>
                <td>${group.notes || '-'}</td>
                <td>
                    <button class="btn-small btn-info" onclick="editGroup(${group.id})">✏️ Изменить</button>
                </td>
            </tr>
        `}).join('');
    } catch (error) {
        console.error('Ошибка загрузки групп:', error);
    }
}

function showAddGroupModal() {
    setWeekdaySelection('add', clubSettings.working_days || []);
    document.getElementById('scheduleTime').value = clubSettings.work_start_time || '';
    document.getElementById('slotValidationMessage').style.display = 'none';
    document.getElementById('addGroupModal').style.display = 'block';
}

function closeAddGroupModal() {
    document.getElementById('addGroupModal').style.display = 'none';
    document.getElementById('addGroupForm').reset();
    setWeekdaySelection('add', []);
    document.getElementById('slotValidationMessage').style.display = 'none';
}

document.getElementById('addGroupForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const alertBox = document.getElementById('slotValidationMessage');
    alertBox.style.display = 'none';
    const data = {
        name: document.getElementById('groupName').value,
        schedule_time: document.getElementById('scheduleTime').value,
        late_threshold: document.getElementById('lateThreshold').value,
        max_students: document.getElementById('maxStudents').value || null,
        notes: document.getElementById('notes').value,
        schedule_days: getSelectedDays('add')
    };
    if (!data.schedule_days.length) {
        alertBox.textContent = 'Выберите хотя бы один день недели';
        alertBox.style.display = 'block';
        return;
    }
    try {
        const response = await fetch('/api/groups/add', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        const result = await response.json();
        if (result.success) {
            alert('✓ Группа добавлена!');
            closeAddGroupModal();
            loadGroups();
        } else {
            alertBox.textContent = result.message;
            alertBox.style.display = 'block';
        }
    } catch (error) {
        console.error('Ошибка:', error);
        alertBox.textContent = 'Ошибка при добавлении группы';
        alertBox.style.display = 'block';
    }
});

async function editGroup(groupId) {
    try {
        const response = await fetch('/api/groups');
        const groups = await response.json();
        const group = groups.find(g => g.id === groupId);
        if (!group) return;
        document.getElementById('editGroupId').value = group.id;
        document.getElementById('editGroupName').value = group.name;
        document.getElementById('editScheduleTime').value = group.schedule_time;
        document.getElementById('editLateThreshold').value = group.late_threshold;
        document.getElementById('editMaxStudents').value = group.max_students || '';
        document.getElementById('editNotes').value = group.notes || '';
        setWeekdaySelection('edit', group.schedule_days || []);
        document.getElementById('editSlotValidationMessage').style.display = 'none';
        document.getElementById('editGroupModal').style.display = 'block';
    } catch (error) {
        console.error('Ошибка:', error);
    }
}

function closeEditGroupModal() {
    document.getElementById('editGroupModal').style.display = 'none';
    document.getElementById('editGroupForm').reset();
    setWeekdaySelection('edit', []);
    document.getElementById('editSlotValidationMessage').style.display = 'none';
}

document.getElementById('editGroupForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const alertBox = document.getElementById('editSlotValidationMessage');
    alertBox.style.display = 'none';
    const groupId = document.getElementById('editGroupId').value;
    const data = {
        name: document.getElementById('editGroupName').value,
        schedule_time: document.getElementById('editScheduleTime').value,
        late_threshold: document.getElementById('editLateThreshold').value,
        max_students: document.getElementById('editMaxStudents').value || null,
        notes: document.getElementById('editNotes').value,
        schedule_days: getSelectedDays('edit')
    };
    if (!data.schedule_days.length) {
        alertBox.textContent = 'Выберите хотя бы один день недели';
        alertBox.style.display = 'block';
        return;
    }
    try {
        const response = await fetch(`/api/groups/${groupId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        const result = await response.json();
        if (result.success) {
            alert('✓ Группа обновлена!');
            closeEditGroupModal();
            loadGroups();
        } else {
            alertBox.textContent = result.message;
            alertBox.style.display = 'block';
        }
    } catch (error) {
        console.error('Ошибка:', error);
        alertBox.textContent = 'Ошибка при обновлении группы';
        alertBox.style.display = 'block';
    }
});

window.onclick = function(event) {
    const addModal = document.getElementById('addGroupModal');
    const editModal = document.getElementById('editGroupModal');
    const settingsModal = document.getElementById('clubSettingsModal');
    if (event.target === addModal) {
        closeAddGroupModal();
    }
    if (event.target === editModal) {
        closeEditGroupModal();
    }
    if (event.target === settingsModal) {
        closeSettingsModal();
    }
};

function showSettingsModal() {
    setWeekdaySelection('settings', clubSettings.working_days || []);
    document.getElementById('settingsStatus').style.display = 'none';
    document.getElementById('clubSettingsModal').style.display = 'block';
}

function closeSettingsModal() {
    document.getElementById('clubSettingsModal').style.display = 'none';
}

document.getElementById('clubSettingsForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const statusBox = document.getElementById('settingsStatus');
    statusBox.style.display = 'none';
    const payload = {
        working_days: getSelectedDays('settings'),
        work_start_time: document.getElementById('workStartTime').value,
        work_end_time: document.getElementById('workEndTime').value,
        max_groups_per_slot: document.getElementById('maxGroupsPerSlot').value
    };
    if (!payload.working_days.length) {
        statusBox.textContent = 'Выберите рабочие дни';
        statusBox.style.display = 'block';
        return;
    }
    try {
        const response = await fetch('/api/club-settings', {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const result = await response.json();
        if (result.success) {
            alert('Настройки сохранены');
            closeSettingsModal();
            await loadClubSettings();
        } else {
            statusBox.textContent = result.message;
            statusBox.style.display = 'block';
        }
    } catch (error) {
        console.error('Ошибка сохранения настроек:', error);
        statusBox.textContent = 'Ошибка при сохранении настроек';
        statusBox.style.display = 'block';
    }
});

loadClubSettings().then(loadGroups);
