from app import app, init_db

# Инициализация базы данных при запуске
if __name__ == "__main__":
    with app.app_context():
        init_db()
    
