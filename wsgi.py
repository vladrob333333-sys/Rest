from app import app, init_db

# Инициализация базы данных при запуске
print("Инициализация базы данных...")
try:
    with app.app_context():
        init_db()
    print("База данных инициализирована успешно")
except Exception as e:
    print(f"Ошибка при инициализации базы данных: {e}")

if __name__ == '__main__':
    app.run()
