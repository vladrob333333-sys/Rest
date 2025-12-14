from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, abort
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.exceptions import HTTPException
from datetime import datetime, date, timedelta
import json
import os
from sqlalchemy import desc, func, or_, and_
from models import *
from database import db

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'restaurant-management-secret-key-2024')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///restaurant.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Инициализация базы данных
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Middleware для отслеживания просмотров страниц
@app.before_request
def track_page_view():
    if current_user.is_authenticated and request.endpoint not in ['static']:
        try:
            view = PageView(
                user_id=current_user.id,
                page_url=request.path,
                viewed_at=datetime.utcnow(),
                ip_address=request.remote_addr
            )
            db.session.add(view)
            db.session.commit()
        except:
            db.session.rollback()

# Вспомогательная функция для перевода статусов
@app.context_processor
def utility_processor():
    def get_status_text(status):
        status_map = {
            'pending': 'Ожидает обработки',
            'preparing': 'Готовится',
            'ready': 'Готов к выдаче',
            'delivered': 'Доставлен',
            'cancelled': 'Отменен'
        }
        return status_map.get(status, status)
    return dict(get_status_text=get_status_text)

# Обработчики ошибок
@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404

@app.errorhandler(400)
def bad_request_error(error):
    return render_template('errors/400.html'), 400

@app.errorhandler(403)
def forbidden_error(error):
    return render_template('errors/403.html'), 403

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('errors/500.html'), 500

# Главная страница
@app.route('/')
def index():
    # Пример данных для слайдера
    slider_items = [
        {'image': 'slide1.jpg', 'title': 'Добро пожаловать', 'description': 'Лучшие блюда от шеф-повара'},
        {'image': 'slide2.jpg', 'title': 'Специальное предложение', 'description': 'Скидка 20% на все заказы от 50 BYN'},
        {'image': 'slide3.jpg', 'title': 'Новое меню', 'description': 'Попробуйте наши сезонные блюда'}
    ]
    
    # Информационные блоки
    info_blocks = [
        {'icon': 'clock', 'title': 'Часы работы', 'text': 'Пн-Вс: 10:00 - 23:00'},
        {'icon': 'phone', 'title': 'Доставка', 'text': 'Быстрая доставка за 60 минут'},
        {'icon': 'star', 'title': 'Качество', 'text': 'Свежие продукты ежедневно'},
        {'icon': 'users', 'title': 'Банкеты', 'text': 'Организация мероприятий'}
    ]
    
    return render_template('index.html', 
                         slider_items=slider_items,
                         info_blocks=info_blocks)

# Страница меню
@app.route('/menu')
def menu():
    categories = Category.query.all()
    menu_items = MenuItem.query.filter_by(is_available=True).all()
    return render_template('menu.html', categories=categories, menu_items=menu_items)

# Страница заказа
@app.route('/order', methods=['GET', 'POST'])
@login_required
def order():
    if request.method == 'POST':
        try:
            # Получаем данные из формы
            cart_items = request.json.get('items', [])
            delivery_address = request.json.get('delivery_address', '')
            phone = request.json.get('phone', '')
            notes = request.json.get('notes', '')
            order_type = request.json.get('order_type', 'delivery')
            guests_count = request.json.get('guests_count', 0)
            reservation_time = request.json.get('reservation_time', '')
            
            if not cart_items:
                return jsonify({'error': 'Корзина пуста'}), 400
            
            # Для бронирования столика проверяем данные
            if order_type == 'reservation':
                if not guests_count or guests_count <= 0:
                    return jsonify({'error': 'Укажите количество гостей'}), 400
                if not reservation_time:
                    return jsonify({'error': 'Укажите время бронирования'}), 400
            
            # Считаем общую сумму
            total_amount = 0
            order_items_data = []
            
            for item in cart_items:
                menu_item = MenuItem.query.get(item['id'])
                if not menu_item:
                    continue
                    
                item_total = menu_item.price * item['quantity']
                total_amount += item_total
                
                order_items_data.append({
                    'menu_item': menu_item,
                    'quantity': item['quantity'],
                    'price_at_time': menu_item.price
                })
            
            # Проверяем, что есть действительные товары
            if len(order_items_data) == 0:
                return jsonify({'error': 'Нет действительных товаров в заказе'}), 400
            
            # Создаем заказ с общей суммой
            order = Order(
                user_id=current_user.id,
                delivery_address=delivery_address,
                phone=phone,
                notes=notes,
                status='pending',
                total_amount=total_amount,
                order_type=order_type
            )
            
            db.session.add(order)
            db.session.flush()  # Получаем ID заказа
            
            # Добавляем позиции заказа
            for item_data in order_items_data:
                order_item = OrderItem(
                    order_id=order.id,
                    menu_item_id=item_data['menu_item'].id,
                    quantity=item_data['quantity'],
                    price_at_time=item_data['price_at_time']
                )
                db.session.add(order_item)
            
            # Если это бронирование, создаем запись
            if order_type == 'reservation':
                try:
                    reservation_datetime = datetime.strptime(reservation_time, '%Y-%m-%dT%H:%M')
                except ValueError:
                    reservation_datetime = datetime.strptime(reservation_time, '%Y-%m-%d %H:%M')
                
                reservation = Reservation(
                    order_id=order.id,
                    user_id=current_user.id,
                    table_id=None,  # Пока без столика, администратор назначит
                    reservation_time=reservation_datetime,
                    guests_count=guests_count,
                    status='pending'
                )
                db.session.add(reservation)
            
            db.session.commit()
            
            return jsonify({
                'success': True, 
                'order_id': order.id,
                'total_amount': total_amount,
                'order_type': order_type
            })
            
        except Exception as e:
            db.session.rollback()
            print(f"Ошибка при создании заказа: {str(e)}")
            return jsonify({'error': f'Ошибка сервера: {str(e)}'}), 500
    
    # GET запрос - отображаем форму заказа
    menu_items = MenuItem.query.filter_by(is_available=True).all()
    
    # Получаем статистику по столикам
    total_tables = 10
    total_seats = total_tables * 4
    reserved_tables = Table.query.filter_by(is_reserved=True).count()
    reserved_seats = db.session.query(func.sum(Table.seats)).filter_by(is_reserved=True).scalar() or 0
    
    available_tables = total_tables - reserved_tables
    available_seats = total_seats - reserved_seats
    
    return render_template('order.html', 
                          menu_items=menu_items,
                          total_tables=total_tables,
                          total_seats=total_seats,
                          reserved_tables=reserved_tables,
                          reserved_seats=reserved_seats,
                          available_tables=available_tables,
                          available_seats=available_seats)

# История заказов
@app.route('/profile/orders')
@login_required
def user_orders():
    orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.created_at.desc()).all()
    return render_template('profile.html', orders=orders)

# Регистрация
@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        # Валидация
        errors = []
        if not username or len(username) < 3:
            errors.append('Имя пользователя должно содержать минимум 3 символа')
        if not email or '@' not in email:
            errors.append('Введите корректный email')
        if not password or len(password) < 6:
            errors.append('Пароль должен содержать минимум 6 символов')
        if password != confirm_password:
            errors.append('Пароли не совпадают')
        
        # Проверка уникальности
        if User.query.filter_by(username=username).first():
            errors.append('Пользователь с таким именем уже существует')
        if User.query.filter_by(email=email).first():
            errors.append('Пользователь с таким email уже существует')
        
        if errors:
            for error in errors:
                flash(error, 'danger')
        else:
            # Создание пользователя
            user = User(
                username=username,
                email=email,
                password=generate_password_hash(password),
                role='customer'
            )
            db.session.add(user)
            db.session.commit()
            
            flash('Регистрация прошла успешно! Теперь вы можете войти.', 'success')
            return redirect(url_for('login'))
    
    return render_template('register.html')

# Вход
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = request.form.get('remember')
        
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password, password):
            login_user(user, remember=bool(remember))
            flash('Вход выполнен успешно!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Неверное имя пользователя или пароль', 'danger')
    
    return render_template('login.html')

# Выход
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Вы вышли из системы', 'info')
    return redirect(url_for('index'))

# API для получения меню
@app.route('/api/menu')
def api_menu():
    categories = Category.query.all()
    menu_items = MenuItem.query.filter_by(is_available=True).all()
    
    result = []
    for category in categories:
        category_data = {
            'id': category.id,
            'name': category.name,
            'description': category.description,
            'items': []
        }
        
        for item in menu_items:
            if item.category_id == category.id:
                category_data['items'].append({
                    'id': item.id,
                    'name': item.name,
                    'description': item.description,
                    'price': item.price,
                    'image': item.image
                })
        
        if category_data['items']:
            result.append(category_data)
    
    return jsonify(result)

# API для получения обновленных данных меню
@app.route('/api/menu/update')
def api_menu_update():
    categories = Category.query.all()
    menu_items = MenuItem.query.filter_by(is_available=True).all()
    
    result = []
    for category in categories:
        category_data = {
            'id': category.id,
            'name': category.name,
            'items': []
        }
        
        for item in menu_items:
            if item.category_id == category.id:
                category_data['items'].append({
                    'id': item.id,
                    'name': item.name,
                    'description': item.description,
                    'price': item.price,
                    'image': item.image,
                    'is_available': item.is_available
                })
        
        if category_data['items']:
            result.append(category_data)
    
    return jsonify(result)

# API для получения обновленных заказов пользователя
@app.route('/api/user/orders/update')
@login_required
def api_user_orders_update():
    orders = Order.query.filter_by(user_id=current_user.id)\
                       .order_by(desc(Order.created_at))\
                       .limit(20)\
                       .all()
    
    result = []
    for order in orders:
        order_data = {
            'id': order.id,
            'total_amount': order.total_amount,
            'status': order.status,
            'created_at': order.created_at.strftime('%d.%m.%Y %H:%M'),
            'delivery_address': order.delivery_address,
            'phone': order.phone,
            'order_type': order.order_type,
            'items_count': len(order.items),
            'items': []
        }
        
        for item in order.items[:5]:  # Берем только первые 5 позиций
            order_data['items'].append({
                'name': item.menu_item.name,
                'quantity': item.quantity,
                'price': item.price_at_time
            })
        
        result.append(order_data)
    
    return jsonify(result)

# API для получения информации о свободных местах
@app.route('/api/tables/status')
def api_tables_status():
    total_tables = 10
    total_seats = total_tables * 4
    reserved_tables = Table.query.filter_by(is_reserved=True).count()
    reserved_seats = db.session.query(func.sum(Table.seats)).filter_by(is_reserved=True).scalar() or 0
    
    available_tables = total_tables - reserved_tables
    available_seats = total_seats - reserved_seats
    
    # Получаем ближайшие бронирования
    now = datetime.now()
    upcoming_reservations = Reservation.query.filter(
        Reservation.reservation_time > now,
        Reservation.status.in_(['active', 'pending'])
    ).order_by(Reservation.reservation_time).limit(10).all()
    
    upcoming = []
    for res in upcoming_reservations:
        upcoming.append({
            'time': res.reservation_time.strftime('%d.%m.%Y %H:%M'),
            'guests': res.guests_count,
            'table': res.table.table_number if res.table else 'Не назначен'
        })
    
    return jsonify({
        'total_tables': total_tables,
        'total_seats': total_seats,
        'reserved_tables': reserved_tables,
        'reserved_seats': reserved_seats,
        'available_tables': available_tables,
        'available_seats': available_seats,
        'upcoming_reservations': upcoming
    })

# Панель администратора (просмотр заказов)
@app.route('/admin/orders')
@login_required
def admin_orders():
    if current_user.role != 'admin':
        abort(403)
    
    orders = Order.query.order_by(desc(Order.created_at)).all()
    return render_template('admin/orders.html', orders=orders)

# Детали заказа для администратора
@app.route('/admin/order/<int:order_id>')
@login_required
def admin_order_details(order_id):
    if current_user.role != 'admin':
        abort(403)
    
    order = Order.query.get_or_404(order_id)
    return render_template('admin/order_details.html', order=order)

# Админ панель - управление меню
@app.route('/admin/menu')
@login_required
def admin_menu():
    if current_user.role != 'admin':
        abort(403)
    
    categories = Category.query.all()
    menu_items = MenuItem.query.all()
    return render_template('admin/menu.html', categories=categories, menu_items=menu_items)

# Админ панель - управление столиками
@app.route('/admin/tables')
@login_required
def admin_tables():
    if current_user.role != 'admin':
        abort(403)
    
    tables = Table.query.all()
    reservations = Reservation.query.order_by(desc(Reservation.reservation_time)).all()
    
    # Инициализируем столики, если их нет
    if not tables:
        for i in range(1, 11):
            table = Table(table_number=i, seats=4, is_reserved=False)
            db.session.add(table)
        db.session.commit()
        tables = Table.query.all()
    
    return render_template('admin/tables.html', tables=tables, reservations=reservations)

# API для администратора - получение обновленных заказов
@app.route('/api/admin/orders/update')
@login_required
def api_admin_orders_update():
    if current_user.role != 'admin':
        abort(403)
    
    # Получение параметров фильтрации
    status_filter = request.args.get('status', 'all')
    date_filter = request.args.get('date', None)
    
    query = Order.query
    
    if status_filter != 'all':
        query = query.filter_by(status=status_filter)
    
    if date_filter:
        try:
            filter_date = datetime.strptime(date_filter, '%Y-%m-%d').date()
            query = query.filter(func.date(Order.created_at) == filter_date)
        except ValueError:
            pass
    
    orders = query.order_by(desc(Order.created_at)).limit(50).all()
    
    result = []
    for order in orders:
        # Обрезаем длинный адрес
        address = order.delivery_address
        if address and len(address) > 50:
            address = address[:50] + '...'
            
        result.append({
            'id': order.id,
            'username': order.user.username,
            'total_amount': order.total_amount,
            'status': order.status,
            'created_at': order.created_at.strftime('%d.%m.%Y %H:%M'),
            'delivery_address': address,
            'phone': order.phone,
            'order_type': order.order_type
        })
    
    return jsonify(result)

# API для получения статистики (для администратора)
@app.route('/api/admin/stats')
@login_required
def api_admin_stats():
    if current_user.role != 'admin':
        abort(403)
    
    # Считаем общую выручку БЕЗ учета отмененных заказов
    total_orders = Order.query.filter(Order.status != 'cancelled').count()
    pending_orders = Order.query.filter_by(status='pending').count()
    today_orders = Order.query.filter(func.date(Order.created_at) == date.today()).filter(Order.status != 'cancelled').count()
    
    # Выручка считается БЕЗ отмененных заказов
    total_revenue_result = db.session.query(func.sum(Order.total_amount)).filter(Order.status != 'cancelled').scalar()
    total_revenue = float(total_revenue_result) if total_revenue_result else 0.0
    
    # Статистика по бронированиям
    active_reservations = Reservation.query.filter(Reservation.status.in_(['active', 'pending'])).count()
    today_reservations = Reservation.query.filter(func.date(Reservation.reservation_time) == date.today()).count()
    
    # Статистика по столикам
    total_tables = Table.query.count()
    reserved_tables = Table.query.filter_by(is_reserved=True).count()
    
    return jsonify({
        'total_orders': total_orders,
        'pending_orders': pending_orders,
        'today_orders': today_orders,
        'total_revenue': total_revenue,
        'active_reservations': active_reservations,
        'today_reservations': today_reservations,
        'total_tables': total_tables,
        'reserved_tables': reserved_tables
    })

# Обновление статуса заказа
@app.route('/admin/order/<int:order_id>/status', methods=['POST'])
@login_required
def update_order_status(order_id):
    if current_user.role != 'admin':
        abort(403)
    
    order = Order.query.get_or_404(order_id)
    new_status = request.json.get('status')
    
    if new_status in ['pending', 'preparing', 'ready', 'delivered', 'cancelled']:
        order.status = new_status
        
        # Если заказ отменен, освобождаем связанный столик
        if new_status == 'cancelled' and order.reservation:
            reservation = order.reservation
            if reservation.table_id:
                table = Table.query.get(reservation.table_id)
                if table:
                    table.is_reserved = False
                    db.session.add(table)
            reservation.status = 'cancelled'
            db.session.add(reservation)
        
        db.session.commit()
        return jsonify({'success': True})
    
    return jsonify({'error': 'Invalid status'}), 400

# Администратор - назначение столика для бронирования
@app.route('/admin/reservation/<int:reservation_id>/assign_table', methods=['POST'])
@login_required
def assign_table_to_reservation(reservation_id):
    if current_user.role != 'admin':
        abort(403)
    
    reservation = Reservation.query.get_or_404(reservation_id)
    table_id = request.json.get('table_id')
    
    if not table_id:
        return jsonify({'error': 'Укажите номер столика'}), 400
    
    table = Table.query.get(table_id)
    if not table:
        return jsonify({'error': 'Столик не найден'}), 404
    
    # Проверяем, свободен ли столик
    if table.is_reserved:
        return jsonify({'error': 'Столик уже занят'}), 400
    
    # Проверяем, достаточно ли мест
    if table.seats < reservation.guests_count:
        return jsonify({'error': f'Недостаточно мест за столиком {table.table_number}. Нужно {reservation.guests_count} мест, доступно {table.seats}'}), 400
    
    # Освобождаем предыдущий столик, если был
    if reservation.table_id:
        old_table = Table.query.get(reservation.table_id)
        if old_table:
            old_table.is_reserved = False
            db.session.add(old_table)
    
    # Назначаем новый столик
    reservation.table_id = table_id
    reservation.status = 'active'
    table.is_reserved = True
    db.session.add(reservation)
    db.session.add(table)
    db.session.commit()
    
    return jsonify({'success': True, 'table_number': table.table_number})

# Администратор - освобождение столика
@app.route('/admin/table/<int:table_id>/free', methods=['POST'])
@login_required
def free_table(table_id):
    if current_user.role != 'admin':
        abort(403)
    
    table = Table.query.get_or_404(table_id)
    
    if not table.is_reserved:
        return jsonify({'error': 'Столик уже свободен'}), 400
    
    # Находим активное бронирование для этого столика
    reservation = Reservation.query.filter_by(table_id=table_id, status='active').first()
    if reservation:
        reservation.status = 'completed'
        db.session.add(reservation)
    
    table.is_reserved = False
    db.session.add(table)
    db.session.commit()
    
    return jsonify({'success': True})

# Администратор - добавление новой категории
@app.route('/admin/menu/category/add', methods=['POST'])
@login_required
def admin_add_category():
    if current_user.role != 'admin':
        abort(403)
    
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        
        if not name:
            flash('Название категории обязательно', 'danger')
            return redirect(url_for('admin_menu'))
        
        # Проверяем, нет ли уже категории с таким названием
        existing_category = Category.query.filter_by(name=name).first()
        if existing_category:
            flash('Категория с таким названием уже существует', 'danger')
            return redirect(url_for('admin_menu'))
        
        # Создаем новую категорию
        category = Category(name=name, description=description)
        db.session.add(category)
        db.session.commit()
        
        flash('Категория успешно добавлена', 'success')
        return redirect(url_for('admin_menu'))

# Администратор - редактирование категории
@app.route('/admin/menu/category/edit/<int:category_id>', methods=['GET', 'POST'])
@login_required
def admin_edit_category(category_id):
    if current_user.role != 'admin':
        abort(403)
    
    category = Category.query.get_or_404(category_id)
    
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        
        if not name:
            flash('Название категории обязательно', 'danger')
            return redirect(url_for('admin_menu'))
        
        # Проверяем, нет ли уже категории с таким названием (кроме текущей)
        existing_category = Category.query.filter(Category.name == name, Category.id != category_id).first()
        if existing_category:
            flash('Категория с таким названием уже существует', 'danger')
            return redirect(url_for('admin_menu'))
        
        # Обновляем категорию
        category.name = name
        category.description = description
        db.session.commit()
        
        flash('Категория успешно обновлена', 'success')
        return redirect(url_for('admin_menu'))
    
    return render_template('admin/edit_category.html', category=category)

# Администратор - удаление категории
@app.route('/admin/menu/category/delete/<int:category_id>', methods=['POST'])
@login_required
def admin_delete_category(category_id):
    if current_user.role != 'admin':
        abort(403)
    
    category = Category.query.get_or_404(category_id)
    
    # Проверяем, есть ли блюда в этой категории
    if category.items:
        flash('Невозможно удалить категорию, в которой есть блюда', 'danger')
        return redirect(url_for('admin_menu'))
    
    db.session.delete(category)
    db.session.commit()
    
    flash('Категория успешно удалена', 'success')
    return redirect(url_for('admin_menu'))

# Администратор - добавление нового блюда
@app.route('/admin/menu/item/add', methods=['GET', 'POST'])
@login_required
def admin_add_item():
    if current_user.role != 'admin':
        abort(403)
    
    categories = Category.query.all()
    
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        price = request.form.get('price')
        category_id = request.form.get('category_id')
        image = request.form.get('image')
        
        # Валидация
        errors = []
        if not name:
            errors.append('Название блюда обязательно')
        if not price:
            errors.append('Цена обязательна')
        else:
            try:
                price = float(price)
                if price <= 0:
                    errors.append('Цена должна быть больше 0')
            except ValueError:
                errors.append('Цена должна быть числом')
        
        if not category_id:
            errors.append('Выберите категорию')
        
        if errors:
            for error in errors:
                flash(error, 'danger')
            return render_template('admin/add_item.html', categories=categories)
        
        # Создаем новое блюдо
        menu_item = MenuItem(
            name=name,
            description=description,
            price=price,
            category_id=category_id,
            image=image,
            is_available=True
        )
        
        db.session.add(menu_item)
        db.session.commit()
        
        flash('Блюдо успешно добавлено', 'success')
        return redirect(url_for('admin_menu'))
    
    return render_template('admin/add_item.html', categories=categories)

# Администратор - редактирование блюда
@app.route('/admin/menu/item/edit/<int:item_id>', methods=['GET', 'POST'])
@login_required
def admin_edit_item(item_id):
    if current_user.role != 'admin':
        abort(403)
    
    menu_item = MenuItem.query.get_or_404(item_id)
    categories = Category.query.all()
    
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        price = request.form.get('price')
        category_id = request.form.get('category_id')
        image = request.form.get('image')
        is_available = request.form.get('is_available') == 'on'
        
        # Валидация
        errors = []
        if not name:
            errors.append('Название блюда обязательно')
        if not price:
            errors.append('Цена обязательна')
        else:
            try:
                price = float(price)
                if price <= 0:
                    errors.append('Цена должна быть больше 0')
            except ValueError:
                errors.append('Цена должна быть числом')
        
        if not category_id:
            errors.append('Выберите категорию')
        
        if errors:
            for error in errors:
                flash(error, 'danger')
            return render_template('admin/edit_item.html', menu_item=menu_item, categories=categories)
        
        # Обновляем блюдо
        menu_item.name = name
        menu_item.description = description
        menu_item.price = price
        menu_item.category_id = category_id
        menu_item.image = image
        menu_item.is_available = is_available
        
        db.session.commit()
        
        flash('Блюдо успешно обновлено', 'success')
        return redirect(url_for('admin_menu'))
    
    return render_template('admin/edit_item.html', menu_item=menu_item, categories=categories)

# Администратор - удаление блюда
@app.route('/admin/menu/item/delete/<int:item_id>', methods=['POST'])
@login_required
def admin_delete_item(item_id):
    if current_user.role != 'admin':
        abort(403)
    
    menu_item = MenuItem.query.get_or_404(item_id)
    
    # Проверяем, есть ли заказы с этим блюдом
    if menu_item.order_items:
        # Вместо удаления делаем блюдо недоступным
        menu_item.is_available = False
        db.session.commit()
        flash('Блюдо отмечено как недоступное (есть связанные заказы)', 'warning')
    else:
        # Удаляем блюдо полностью
        db.session.delete(menu_item)
        db.session.commit()
        flash('Блюдо успешно удалено', 'success')
    
    return redirect(url_for('admin_menu'))

# Инициализация базы данных
def init_db():
    with app.app_context():
        db.create_all()
        
        # Создаем тестовые данные, если их нет
        if not Category.query.first():
            # Категории
            categories = [
                Category(name='Закуски', description='Легкие закуски к столу'),
                Category(name='Основные блюда', description='Горячие блюда'),
                Category(name='Напитки', description='Холодные и горячие напитки'),
                Category(name='Десерты', description='Сладкие блюда')
            ]
            
            for category in categories:
                db.session.add(category)
            
            db.session.flush()  # Получаем ID категорий
            
            # Пример блюд с ценами в BYN
            menu_items = [
                MenuItem(name='Брускетта', description='С помидорами и базиликом', price=12.5, category_id=1, image='bruschetta.jpg'),
                MenuItem(name='Стейк', description='Говяжий стейк с овощами', price=42.5, category_id=2, image='steak.jpg'),
                MenuItem(name='Салат Цезарь', description='С курицей и соусом', price=16.0, category_id=1, image='caesar.jpg'),
                MenuItem(name='Кофе', description='Арабика 200мл', price=7.0, category_id=3, image='coffee.jpg'),
                MenuItem(name='Тирамису', description='Итальянский десерт', price=14.0, category_id=4, image='tiramisu.jpg'),
                MenuItem(name='Суп Том Ям', description='Тайский острый суп с креветками', price=19.5, category_id=2, image='tomyam.jpg'),
                MenuItem(name='Паста Карбонара', description='С беконом и сливочным соусом', price=17.0, category_id=2, image='carbonara.jpg'),
                MenuItem(name='Чизкейк', description='Классический чизкейк', price=12.5, category_id=4, image='cheesecake.jpg')
            ]
            
            for item in menu_items:
                db.session.add(item)
            
            # Создаем столики
            if not Table.query.first():
                for i in range(1, 11):
                    table = Table(table_number=i, seats=4, is_reserved=False)
                    db.session.add(table)
            
            # Создаем тестового администратора с белорусским email
            if not User.query.filter_by(username='admin').first():
                admin = User(
                    username='admin',
                    email='admin@gurman.by',
                    password=generate_password_hash('admin123'),
                    role='admin'
                )
                db.session.add(admin)
            
            # Создаем тестового пользователя с белорусским email
            if not User.query.filter_by(username='user').first():
                user = User(
                    username='user',
                    email='user@gurman.by',
                    password=generate_password_hash('user123'),
                    role='customer'
                )
                db.session.add(user)
            
            db.session.commit()
        print("База данных инициализирована!")

# Для запуска на Render
if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
