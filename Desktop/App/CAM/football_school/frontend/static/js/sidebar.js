// Управление боковым меню
document.addEventListener('DOMContentLoaded', () => {
    const sidebar = document.querySelector('.sidebar');
    const toggleBtn = document.querySelector('.sidebar-toggle');
    
    // Функция обновления иконки кнопки
    function updateToggleIcon() {
        if (toggleBtn) {
            // Если меню свернуто - показываем ☰ (чтобы развернуть)
            // Если меню развернуто - показываем ✕ (чтобы свернуть)
            toggleBtn.textContent = sidebar.classList.contains('collapsed') ? '☰' : '✕';
        }
    }
    
    // Загрузить состояние из localStorage
    const isCollapsed = localStorage.getItem('sidebarCollapsed') === 'true';
    if (isCollapsed) {
        sidebar.classList.add('collapsed');
        document.body.classList.add('sidebar-collapsed');
    }
    updateToggleIcon();
    
    // Обработчик клика на кнопку переключения
    if (toggleBtn) {
        toggleBtn.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            
            sidebar.classList.toggle('collapsed');
            document.body.classList.toggle('sidebar-collapsed');
            
            // Обновить иконку
            updateToggleIcon();
            
            // Сохранить состояние в localStorage
            localStorage.setItem('sidebarCollapsed', sidebar.classList.contains('collapsed'));
        });
    }
});

