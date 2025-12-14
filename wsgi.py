from app import app, init_db

# Инициализация базы данных
with app.app_context():
    init_db()

if __name__ == '__main__':
    app.run()