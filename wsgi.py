from app import app, db
from werkzeug.security import generate_password_hash
from models import User, Category, MenuItem
import os

# Создание базы данных и тестовых данных
with app.app_context():
    # Создаем все таблицы
    db.create_all()
    print("База данных создана/проверена")
    
    # Создаем тестового администратора, если его нет
    if not User.query.filter_by(username='admin').first():
        admin = User(
            username='admin',
            email='admin@gurman.by',
            password=generate_password_hash('admin123'),
            role='admin'
        )
        db.session.add(admin)
        print("Тестовый администратор создан: login: admin, password: admin123")
    
    # Создаем тестового пользователя, если его нет
    if not User.query.filter_by(username='user').first():
        user = User(
            username='user',
            email='user@gurman.by',
            password=generate_password_hash('user123'),
            role='customer'
        )
        db.session.add(user)
        print("Тестовый пользователь создан: login: user, password: user123")
    
    # Создаем категории, если их нет
    if not Category.query.first():
        categories = [
            Category(name='Закуски', description='Легкие закуски к столу'),
            Category(name='Основные блюда', description='Горячие блюда'),
            Category(name='Напитки', description='Холодные и горячие напитки'),
            Category(name='Десерты', description='Сладкие блюда')
        ]
        
        for category in categories:
            db.session.add(category)
        
        db.session.flush()
        
        # Создаем тестовые блюда
        menu_items = [
            MenuItem(name='Брускетта', description='С помидорами и базиликом', price=12.5, category_id=1, is_available=True),
            MenuItem(name='Стейк', description='Говяжий стейк с овощами', price=42.5, category_id=2, is_available=True),
            MenuItem(name='Салат Цезарь', description='С курицей и соусом', price=16.0, category_id=1, is_available=True),
            MenuItem(name='Кофе', description='Арабика 200мл', price=7.0, category_id=3, is_available=True),
            MenuItem(name='Тирамису', description='Итальянский десерт', price=14.0, category_id=4, is_available=True),
            MenuItem(name='Суп Том Ям', description='Тайский острый суп с креветками', price=19.5, category_id=2, is_available=True),
            MenuItem(name='Паста Карбонара', description='С беконом и сливочным соусом', price=17.0, category_id=2, is_available=True),
            MenuItem(name='Чизкейк', description='Классический чизкейк', price=12.5, category_id=4, is_available=True)
        ]
        
        for item in menu_items:
            db.session.add(item)
        
        print("Тестовые категории и блюда созданы")
    
    # Сохраняем изменения
    db.session.commit()
    print("База данных готова к работе")

if __name__ == "__main__":
    app.run()
