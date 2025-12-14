import os
from datetime import timedelta

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'restaurant-secret-key-2023'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///restaurant.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    PERMANENT_SESSION_LIFETIME = timedelta(days=1)
    
    # Цветовая схема
    PRIMARY_COLOR = '#8B0000'  # Темно-красный
    SECONDARY_COLOR = '#FFD700'  # Золотой
    BACKGROUND_COLOR = '#FFF8DC'  # Кремовый
    TEXT_COLOR = '#333333'
    
    # Контакты (белорусские)
    RESTAURANT_PHONE = '+375 (29) 123-45-67'
    RESTAURANT_ADDRESS = 'г. Минск, ул. Ленина, 10'
    RESTAURANT_EMAIL = 'info@restaurant.by'