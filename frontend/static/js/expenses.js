// Модалка добавления расхода
const addExpenseModal = document.getElementById('addExpenseModal');
const addExpenseBtn = document.getElementById('addExpenseBtn');
const closeBtn = document.querySelector('.close');

addExpenseBtn.addEventListener('click', () => {
    addExpenseModal.style.display = 'block';
});

closeBtn.addEventListener('click', () => {
    addExpenseModal.style.display = 'none';
});

window.addEventListener('click', (e) => {
    if (e.target === addExpenseModal) {
        addExpenseModal.style.display = 'none';
    }
});

// Добавить расход
document.getElementById('addExpenseForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const formData = new FormData(e.target);
    const data = {
        category: formData.get('category'),
        amount: formData.get('amount'),
        description: formData.get('description')
    };
    
    try {
        const response = await fetch('/api/expenses/add', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        
        const result = await response.json();
        
        if (result.success) {
            alert('Расход добавлен!');
            location.reload();
        } else {
            alert('Ошибка: ' + result.message);
        }
    } catch (error) {
        alert('Ошибка: ' + error.message);
    }
});
