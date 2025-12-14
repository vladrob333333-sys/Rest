from database import db
from flask_login import UserMixin
from datetime import datetime

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), default='customer')  # customer, admin
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    orders = db.relationship('Order', backref='user', lazy=True)
    views = db.relationship('PageView', backref='user', lazy=True)
    table_reservations = db.relationship('TableReservation', backref='user', lazy=True)

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    items = db.relationship('MenuItem', backref='category', lazy=True)

class MenuItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Float, nullable=False)
    image = db.Column(db.String(200))
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=False)
    is_available = db.Column(db.Boolean, default=True)
    
    order_items = db.relationship('OrderItem', backref='menu_item', lazy=True)

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    total_amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, preparing, ready, delivered, cancelled
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    delivery_address = db.Column(db.Text)
    phone = db.Column(db.String(20))
    notes = db.Column(db.Text)
    order_type = db.Column(db.String(20), default='delivery')  # delivery, pickup, dine_in
    reservation_id = db.Column(db.Integer, db.ForeignKey('table_reservation.id'), nullable=True)
    
    items = db.relationship('OrderItem', backref='order', lazy=True, cascade='all, delete-orphan')
    reservation = db.relationship('TableReservation', backref='order', uselist=False)

class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    menu_item_id = db.Column(db.Integer, db.ForeignKey('menu_item.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    price_at_time = db.Column(db.Float, nullable=False)

class PageView(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    page_url = db.Column(db.String(200), nullable=False)
    viewed_at = db.Column(db.DateTime, default=datetime.utcnow)
    ip_address = db.Column(db.String(45))

class RestaurantTable(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    table_number = db.Column(db.Integer, unique=True, nullable=False)
    seats = db.Column(db.Integer, nullable=False, default=4)
    is_available = db.Column(db.Boolean, default=True)
    
    reservations = db.relationship('TableReservation', backref='table', lazy=True)

class TableReservation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    table_id = db.Column(db.Integer, db.ForeignKey('restaurant_table.id'), nullable=False)
    reservation_time = db.Column(db.DateTime, nullable=False)
    duration_hours = db.Column(db.Integer, default=2)  # Продолжительность бронирования в часах
    guests_count = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), default='reserved')  # reserved, cancelled, completed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    notes = db.Column(db.Text)
