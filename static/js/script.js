// Основной JavaScript файл

document.addEventListener('DOMContentLoaded', function() {
    // Валидация форм
    initFormValidation();
    
    // Инициализация корзины
    initCart();
    
    // Инициализация меню
    initMenu();
});

// Валидация форм
function initFormValidation() {
    const forms = document.querySelectorAll('form[data-validate]');
    
    forms.forEach(form => {
        form.addEventListener('submit', function(event) {
            if (!validateForm(this)) {
                event.preventDefault();
            }
        });
    });
}

function validateForm(form) {
    let isValid = true;
    const inputs = form.querySelectorAll('input[required], select[required], textarea[required]');
    
    inputs.forEach(input => {
        const errorElement = input.nextElementSibling?.classList.contains('form-error') 
            ? input.nextElementSibling 
            : input.parentNode.querySelector('.form-error');
        
        if (!input.value.trim()) {
            showError(input, 'Это поле обязательно для заполнения', errorElement);
            isValid = false;
        } else if (input.type === 'email' && !isValidEmail(input.value)) {
            showError(input, 'Введите корректный email', errorElement);
            isValid = false;
        } else if (input.type === 'password' && input.hasAttribute('data-min-length')) {
            const minLength = parseInt(input.getAttribute('data-min-length'));
            if (input.value.length < minLength) {
                showError(input, `Пароль должен содержать минимум ${minLength} символов`, errorElement);
                isValid = false;
            }
        } else if (input.hasAttribute('data-match')) {
            const matchField = form.querySelector(`[name="${input.getAttribute('data-match')}"]`);
            if (matchField && input.value !== matchField.value) {
                showError(input, 'Пароли не совпадают', errorElement);
                isValid = false;
            }
        } else {
            clearError(input, errorElement);
        }
    });
    
    return isValid;
}

function isValidEmail(email) {
    const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return re.test(email);
}

function showError(input, message, errorElement) {
    input.style.borderColor = '#e74c3c';
    if (errorElement) {
        errorElement.textContent = message;
        errorElement.style.display = 'block';
    }
}

function clearError(input, errorElement) {
    input.style.borderColor = '';
    if (errorElement) {
        errorElement.style.display = 'none';
    }
}

// Корзина
let cart = JSON.parse(localStorage.getItem('restaurant_cart')) || [];

function initCart() {
    // Сохранение корзины в localStorage
    window.saveCart = function() {
        localStorage.setItem('restaurant_cart', JSON.stringify(cart));
        updateCartCount();
    }
    
    // Обновление счетчика корзины
    window.updateCartCount = function() {
        const countElement = document.getElementById('cart-count');
        if (countElement) {
            const totalItems = cart.reduce((sum, item) => sum + item.quantity, 0);
            countElement.textContent = totalItems;
        }
    }
    
    // Добавление в корзину
    window.addToCart = function(itemId, itemName, itemPrice, itemImage) {
        const existingItem = cart.find(item => item.id === itemId);
        
        if (existingItem) {
            existingItem.quantity += 1;
        } else {
            cart.push({
                id: itemId,
                name: itemName,
                price: itemPrice,
                image: itemImage,
                quantity: 1
            });
        }
        
        saveCart();
        showNotification('Товар добавлен в корзину', 'success');
    }
    
    // Удаление из корзины
    window.removeFromCart = function(itemId) {
        cart = cart.filter(item => item.id !== itemId);
        saveCart();
        renderCart();
    }
    
    // Изменение количества
    window.updateQuantity = function(itemId, change) {
        const item = cart.find(item => item.id === itemId);
        if (item) {
            item.quantity += change;
            if (item.quantity <= 0) {
                removeFromCart(itemId);
            } else {
                saveCart();
                renderCart();
            }
        }
    }
    
    // Отрисовка корзины
    window.renderCart = function() {
        const cartContainer = document.getElementById('cart-items-container');
        const totalElement = document.getElementById('cart-total');
        
        if (cartContainer && totalElement) {
            if (cart.length === 0) {
                cartContainer.innerHTML = '<p class="empty-cart">Корзина пуста</p>';
                totalElement.textContent = '0';
                return;
            }
            
            let html = '';
            let total = 0;
            
            cart.forEach(item => {
                const itemTotal = item.price * item.quantity;
                total += itemTotal;
                
                html += `
                    <div class="cart-item">
                        <div class="item-info">
                            <h4>${item.name}</h4>
                            <p class="item-price">${item.price}₽ × ${item.quantity}</p>
                        </div>
                        <div class="item-quantity">
                            <button class="quantity-btn" onclick="updateQuantity(${item.id}, -1)">-</button>
                            <span>${item.quantity}</span>
                            <button class="quantity-btn" onclick="updateQuantity(${item.id}, 1)">+</button>
                        </div>
                        <div class="item-total">${itemTotal}₽</div>
                        <button class="btn btn-small btn-outline" onclick="removeFromCart(${item.id})">Удалить</button>
                    </div>
                `;
            });
            
            cartContainer.innerHTML = html;
            totalElement.textContent = total.toFixed(2);
        }
    }
    
    // Очистка корзины
    window.clearCart = function() {
        cart = [];
        saveCart();
        renderCart();
    }
    
    // Получение данных корзины для отправки
    window.getCartData = function() {
        return cart;
    }
    
    // Инициализация
    updateCartCount();
    if (document.getElementById('cart-items-container')) {
        renderCart();
    }
}

// Меню
function initMenu() {
    const menuContainer = document.getElementById('menu-container');
    
    if (menuContainer) {
        fetch('/api/menu')
            .then(response => response.json())
            .then(data => {
                renderMenu(data);
            })
            .catch(error => {
                console.error('Ошибка загрузки меню:', error);
                menuContainer.innerHTML = '<p class="error">Не удалось загрузить меню. Попробуйте позже.</p>';
            });
    }
}

function renderMenu(categories) {
    const menuContainer = document.getElementById('menu-container');
    let html = '';
    
    categories.forEach(category => {
        html += `
            <div class="menu-category">
                <h3>${category.name}</h3>
                ${category.description ? `<p class="category-description">${category.description}</p>` : ''}
                <div class="menu-items">
        `;
        
        category.items.forEach(item => {
            html += `
                <div class="menu-item">
                    <div class="item-image" style="background-image: url('${item.image || '/static/images/default-dish.jpg'}')"></div>
                    <div class="item-info">
                        <h4>${item.name}</h4>
                        <p class="item-description">${item.description}</p>
                        <div class="item-footer">
                            <span class="item-price">${item.price}₽</span>
                            <button class="btn btn-small" onclick="addToCart(${item.id}, '${item.name.replace(/'/g, "\\'")}', ${item.price}, '${item.image || ''}')">
                                В корзину
                            </button>
                        </div>
                    </div>
                </div>
            `;
        });
        
        html += `
                </div>
            </div>
        `;
    });
    
    menuContainer.innerHTML = html;
}

// Уведомления
function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.textContent = message;
    
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 15px 20px;
        background-color: ${getNotificationColor(type)};
        color: white;
        border-radius: 5px;
        z-index: 10000;
        animation: slideIn 0.3s ease-out;
    `;
    
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease-out forwards';
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

function getNotificationColor(type) {
    const colors = {
        success: '#27ae60',
        error: '#e74c3c',
        warning: '#f39c12',
        info: '#3498db'
    };
    return colors[type] || colors.info;
}

// Стили для анимаций
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from { transform: translateX(100%); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
    }
    
    @keyframes slideOut {
        from { transform: translateX(0); opacity: 1; }
        to { transform: translateX(100%); opacity: 0; }
    }
`;
document.head.appendChild(style);

// Обработка заказа
window.processOrder = async function() {
    const cart = getCartData();
    if (cart.length === 0) {
        showNotification('Корзина пуста', 'error');
        return;
    }
    
    const deliveryAddress = document.getElementById('delivery_address')?.value;
    const phone = document.getElementById('phone')?.value;
    const notes = document.getElementById('notes')?.value;
    
    // Валидация
    if (!deliveryAddress || !phone) {
        showNotification('Заполните обязательные поля', 'error');
        return;
    }
    
    // Проверка формата телефона
    const phoneRegex = /^[\+]\d{1,3}\s?\(?\d{1,4}\)?[\s.-]?\d{1,4}[\s.-]?\d{1,4}[\s.-]?\d{1,9}$/;
    if (!phoneRegex.test(phone)) {
        showNotification('Введите корректный номер телефона', 'error');
        return;
    }
    
    try {
        const response = await fetch('/order', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                items: cart,
                delivery_address: deliveryAddress,
                phone: phone,
                notes: notes
            })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            clearCart();
            showNotification('Заказ успешно создан! Номер заказа: ' + data.order_id, 'success');
            setTimeout(() => {
                window.location.href = '/profile/orders';
            }, 2000);
        } else {
            showNotification(data.error || 'Ошибка при создании заказа', 'error');
        }
    } catch (error) {
        showNotification('Ошибка сети. Проверьте подключение к интернету.', 'error');
    }
}

// Инициализация при загрузке страницы
updateCartCount();