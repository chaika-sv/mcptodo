# setup_database.py
import sqlite3


def setup_database():
    with sqlite3.connect('tasks.db') as conn:
        cursor = conn.cursor()

        # Включаем поддержку внешних ключей
        cursor.execute('PRAGMA foreign_keys = ON')

        # ===== СПРАВОЧНИКИ =====

        # Справочник приоритетов
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS priorities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                sort_order INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Справочник категорий
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                description TEXT,
                color TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Справочник статусов
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS statuses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                is_completed BOOLEAN DEFAULT FALSE,
                sort_order INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # ===== ОСНОВНАЯ ТАБЛИЦА ЗАДАЧ =====
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT,
                due_date TIMESTAMP,
                priority_id INTEGER DEFAULT 2 REFERENCES priorities(id),
                category_id INTEGER DEFAULT 1 REFERENCES categories(id),
                status_id INTEGER DEFAULT 1 REFERENCES statuses(id),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                started_at TIMESTAMP,
                completed_at TIMESTAMP,
                FOREIGN KEY (priority_id) REFERENCES priorities(id),
                FOREIGN KEY (category_id) REFERENCES categories(id),
                FOREIGN KEY (status_id) REFERENCES statuses(id)
            )
        ''')

        # ===== ЗАПОЛНЯЕМ СПРАВОЧНИКИ БАЗОВЫМИ ДАННЫМИ =====

        # Приоритеты (sort_order для сортировки по важности)
        priorities_data = [
            ('low', 1),
            ('normal', 2),
            ('high', 3)
        ]
        cursor.executemany('''
            INSERT OR IGNORE INTO priorities (name, sort_order) VALUES (?, ?)
        ''', priorities_data)

        # Категории
        categories_data = [
            ('general', 'Общие задачи', '#6B7280'),
            ('work', 'Рабочие задачи', '#3B82F6'),
            ('personal', 'Личные дела', '#10B981'),
            ('study', 'Обучение', '#F59E0B')
        ]
        cursor.executemany('''
            INSERT OR IGNORE INTO categories (name, description, color) VALUES (?, ?, ?)
        ''', categories_data)

        # Статусы
        statuses_data = [
            ('todo', False, 1),
            ('in_progress', False, 2),
            ('done', True, 3),
            ('blocked', False, 4)
        ]
        cursor.executemany('''
            INSERT OR IGNORE INTO statuses (name, is_completed, sort_order) VALUES (?, ?, ?)
        ''', statuses_data)

        conn.commit()
        print("Database with reference tables created successfully!")

        # Показываем статистику
        cursor.execute("SELECT COUNT(*) FROM priorities")
        priorities_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM categories")
        categories_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM statuses")
        statuses_count = cursor.fetchone()[0]

        print(f"Справочники:")
        print(f"   • Приоритеты: {priorities_count}")
        print(f"   • Категории: {categories_count}")
        print(f"   • Статусы: {statuses_count}")

        return True


def show_reference_data():
    """Показывает данные из справочников"""
    with sqlite3.connect('tasks.db') as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        print("\n🎯 ПРИОРИТЕТЫ:")
        cursor.execute("SELECT * FROM priorities ORDER BY sort_order")
        for row in cursor.fetchall():
            print(f"   {row['id']}: {row['name']} (порядок: {row['sort_order']})")

        print("\n📁 КАТЕГОРИИ:")
        cursor.execute("SELECT * FROM categories ORDER BY name")
        for row in cursor.fetchall():
            print(f"   {row['id']}: {row['name']} - {row['description']} ({row['color']})")

        print("\n📋 СТАТУСЫ:")
        cursor.execute("SELECT * FROM statuses ORDER BY sort_order")
        for row in cursor.fetchall():
            completed = "✅" if row['is_completed'] else "⏳"
            print(f"   {row['id']}: {row['name']} {completed}")


if __name__ == "__main__":
    if setup_database():
        show_reference_data()