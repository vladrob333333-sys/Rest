from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, abort
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.exceptions import HTTPException
from datetime import datetime, timedelta
import os
from functools import wraps

from config import Config
from database import db, User, MenuItem, Order, OrderItem, Reservation, Feedback

app = Flask(__name__)
app.config.from_object(Config)

# Инициализация БД
db.init_app(app)

# Инициализация Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Пожалуйста, войдите в систему'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            abort(403)
        return f(*args, **kwargs)
    return decorated_function

# Обработка ошибок
@app.errorhandler(400)
def bad_request(error):
    return render_template('error/400.html'), 400

@app.errorhandler(401)
def unauthorized(error):
    return render_template('error/401.html'), 401

@app.errorhandler(403)
def forbidden(error):
    return render_template('error/403.html'), 403

@app.errorhandler(404)
def not_found(error):
    return render_template('error/404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('error/500.html'), 500

# Главная страница
@app.route('/')
def index():
    menu_items = MenuItem.query.filter_by(is_available=True).limit(6).all()
    return render_template('index.html', menu_items=menu_items)

# Меню
@app.route('/menu')
def menu():
    category = request.args.get('category', 'all')
    if category == 'all':
        menu_items = MenuItem.query.filter_by(is_available=True).all()
    else:
        menu_items = MenuItem.query.filter_by(category=category, is_available=True).all()
    
    categories = db.session.query(MenuItem.category).distinct().all()
    return render_template('menu.html', 
                         menu_items=menu_items,
                         categories=[c[0] for c in categories],
                         selected_category=category)

# Оформление заказа
@app.route('/order', methods=['GET', 'POST'])
@login_required
def order():
    if request.method == 'POST':
        data = request.get_json()
        
        # Создание заказа
        order = Order(
            user_id=current_user.id,
            table_number=data.get('table_number'),
            total_amount=sum(item['price'] * item['quantity'] for item in data['items']),
            special_requests=data.get('special_requests', '')
        )
        db.session.add(order)
        db.session.flush()  # Получаем ID заказа
        
        # Добавление позиций заказа
        for item in data['items']:
            order_item = OrderItem(
                order_id=order.id,
                menu_item_id=item['id'],
                quantity=item['quantity'],
                price=item['price']
            )
            db.session.add(order_item)
        
        db.session.commit()
        return jsonify({'success': True, 'order_id': order.id})
    
    menu_items = MenuItem.query.filter_by(is_available=True).all()
    return render_template('order.html', menu_items=menu_items)

# Бронирование столика
@app.route('/reservation', methods=['POST'])
@login_required
def create_reservation():
    data = request.get_json()
    
    reservation = Reservation(
        user_id=current_user.id,
        table_number=data['table_number'],
        guests_count=data['guests_count'],
        reservation_date=datetime.strptime(data['date'], '%Y-%m-%d').date(),
        reservation_time=data['time']
    )
    
    db.session.add(reservation)
    db.session.commit()
    
    return jsonify({'success': True, 'reservation_id': reservation.id})

# Авторизация
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        remember = request.form.get('remember')
        
        user = User.query.filter_by(email=email).first()
        
        if user and check_password_hash(user.password, password):
            login_user(user, remember=bool(remember))
            next_page = request.args.get('next')
            return redirect(next_page or url_for('index'))
        else:
            flash('Неверный email или пароль', 'danger')
    
    return render_template('login.html')

# Регистрация
@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        phone = request.form.get('phone')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if password != confirm_password:
            flash('Пароли не совпадают', 'danger')
            return redirect(url_for('register'))
        
        if User.query.filter_by(email=email).first():
            flash('Пользователь с таким email уже существует', 'danger')
            return redirect(url_for('register'))
        
        user = User(
            username=username,
            email=email,
            phone=phone,
            password=generate_password_hash(password)
        )
        
        db.session.add(user)
        db.session.commit()
        
        flash('Регистрация успешна! Теперь вы можете войти.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

# Выход
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

# Профиль пользователя
@app.route('/profile')
@login_required
def profile():
    orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.created_at.desc()).all()
    reservations = Reservation.query.filter_by(user_id=current_user.id).order_by(Reservation.reservation_date.desc()).all()
    return render_template('profile.html', orders=orders, reservations=reservations)

# Панель администратора
@app.route('/admin')
@login_required
@admin_required
def admin_panel():
    # Статистика
    total_orders = Order.query.count()
    total_users = User.query.count()
    today_orders = Order.query.filter(
        Order.created_at >= datetime.now().date()
    ).count()
    
    # Последние заказы
    recent_orders = Order.query.order_by(Order.created_at.desc()).limit(10).all()
    
    return render_template('admin.html',
                         total_orders=total_orders,
                         total_users=total_users,
                         today_orders=today_orders,
                         orders=recent_orders)

# Управление меню (админ)
@app.route('/admin/menu', methods=['GET', 'POST', 'PUT', 'DELETE'])
@login_required
@admin_required
def manage_menu():
    if request.method == 'GET':
        items = MenuItem.query.all()
        return jsonify([{
            'id': item.id,
            'name': item.name,
            'description': item.description,
            'price': item.price,
            'category': item.category,
            'image': item.image,
            'is_available': item.is_available
        } for item in items])
    
    elif request.method == 'POST':
        data = request.get_json()
        item = MenuItem(**data)
        db.session.add(item)
        db.session.commit()
        return jsonify({'success': True, 'id': item.id})
    
    elif request.method == 'PUT':
        data = request.get_json()
        item = MenuItem.query.get(data['id'])
        if item:
            for key, value in data.items():
                if key != 'id':
                    setattr(item, key, value)
            db.session.commit()
            return jsonify({'success': True})
    
    elif request.method == 'DELETE':
        item_id = request.args.get('id')
        item = MenuItem.query.get(item_id)
        if item:
            db.session.delete(item)
            db.session.commit()
            return jsonify({'success': True})
    
    return jsonify({'success': False}), 400

# Управление заказами (админ)
@app.route('/admin/orders', methods=['GET', 'PUT'])
@login_required
@admin_required
def manage_orders():
    if request.method == 'GET':
        orders = Order.query.order_by(Order.created_at.desc()).all()
        return jsonify([{
            'id': order.id,
            'user_id': order.user_id,
            'username': order.user.username,
            'table_number': order.table_number,
            'total_amount': order.total_amount,
            'status': order.status,
            'payment_status': order.payment_status,
            'created_at': order.created_at.isoformat(),
            'items': [{
                'name': oi.menu_item.name,
                'quantity': oi.quantity,
                'price': oi.price
            } for oi in order.order_items]
        } for order in orders])
    
    elif request.method == 'PUT':
        data = request.get_json()
        order = Order.query.get(data['id'])
        if order:
            if 'status' in data:
                order.status = data['status']
            if 'payment_status' in data:
                order.payment_status = data['payment_status']
            db.session.commit()
            return jsonify({'success': True})
    
    return jsonify({'success': False}), 400

# Обратная связь
@app.route('/feedback', methods=['GET', 'POST'])
@login_required
def feedback():
    if request.method == 'POST':
        rating = request.form.get('rating')
        comment = request.form.get('comment')
        
        feedback_entry = Feedback(
            user_id=current_user.id,
            rating=int(rating),
            comment=comment
        )
        
        db.session.add(feedback_entry)
        db.session.commit()
        
        flash('Спасибо за ваш отзыв!', 'success')
        return redirect(url_for('index'))
    
    return render_template('feedback.html')

# API для получения меню
@app.route('/api/menu')
def api_menu():
    category = request.args.get('category', 'all')
    if category == 'all':
        items = MenuItem.query.filter_by(is_available=True).all()
    else:
        items = MenuItem.query.filter_by(category=category, is_available=True).all()
    
    return jsonify([{
        'id': item.id,
        'name': item.name,
        'description': item.description,
        'price': item.price,
        'category': item.category,
        'image': url_for('static', filename=f'images/{item.image}') if item.image else ''
    } for item in items])

# API для проверки доступности столиков
@app.route('/api/tables/available')
def check_table_availability():
    date = request.args.get('date')
    time = request.args.get('time')
    
    # Простая логика проверки (в реальном приложении будет сложнее)
    reservations = Reservation.query.filter_by(
        reservation_date=datetime.strptime(date, '%Y-%m-%d').date(),
        reservation_time=time,
        status='confirmed'
    ).all()
    
    booked_tables = [r.table_number for r in reservations]
    all_tables = list(range(1, 21))  # 20 столиков
    
    available_tables = [t for t in all_tables if t not in booked_tables]
    
    return jsonify({'available_tables': available_tables})

# Инициализация базы данных
def init_db():
    with app.app_context():
        db.create_all()
        
        # Создание администратора, если его нет
        if not User.query.filter_by(email='admin@restaurant.by').first():
            admin = User(
                username='admin',
                email='admin@restaurant.by',
                phone='+375 (29) 999-99-99',
                password=generate_password_hash('admin123'),
                is_admin=True
            )
            db.session.add(admin)
            
            # Добавление тестовых данных в меню
            sample_menu = [
                MenuItem(
                    name='Борщ украинский',
                    description='Традиционный украинский борщ со сметаной',
                    price=12.50,
                    category='супы',
                    image='soup1.jpg'
                ),
                MenuItem(
                    name='Стейк из говядины',
                    description='Стейк из мраморной говядины с овощами гриль',
                    price=28.90,
                    category='основные блюда',
                    image='steak.jpg'
                ),
                MenuItem(
                    name='Цезарь с курицей',
                    description='Салат Цезарь с куриной грудкой и соусом',
                    price=15.75,
                    category='закуски',
                    image='salad.jpg'
                ),
                MenuItem(
                    name='Тирамису',
                    description='Итальянский десерт с кофе и маскарпоне',
                    price=9.90,
                    category='десерты',
                    image='tiramisu.jpg'
                ),
                MenuItem(
                    name='Кола',
                    description='Газированный напиток',
                    price=3.50,
                    category='напитки',
                    image='cola.jpg'
                )
            ]
            
            for item in sample_menu:
                db.session.add(item)
            
            db.session.commit()
            print("База данных инициализирована. Создан администратор (admin@restaurant.by, пароль: admin123)")

if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5000)