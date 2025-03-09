import aiosqlite
from datetime import datetime



def set_config(cfg):
    global config, DB_NAME
    
    config = cfg
    DB_NAME = config['DB_Name']



async def execute_query(query, *args):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(query, args)
        await db.commit()

async def select_query(query, *args):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute(query, args) as cursor:
            # Возвращаем результат
            return await cursor.fetchall()
    
    
    
    
    
    
    
# Верунть qviz индекс по user_id
async def select_quiz_session(user_id):
    results = await select_query('SELECT question_index, correct_answers, wrong_answers FROM quiz_state WHERE user_id = (?)', user_id)
    if results:
        return results[0]

# Верунть все по user_id
async def select_quiz_user(user_id):
    result = await select_query('SELECT * FROM quiz_state WHERE user_id = (?)', user_id)
    stats = False
    if result:
        result = result[0]
        stats = dict(
            user_id= result[0],
            first_name= result[1],
            question_index= result[2],
            start_time= result[3],
            correct_answers= result[4],
            wrong_answers= result[5],
        )
        
    return stats
    


# Инициализация таблиц пользователей
async def create_tables():
    await execute_query(f'''
        CREATE TABLE IF NOT EXISTS quiz_state (
            user_id INTEGER PRIMARY KEY,
            first_name TEXT,
            question_index INTEGER,
            start_time DATETIME,
            correct_answers INTEGER DEFAULT 0,
            wrong_answers INTEGER DEFAULT 0
    )''')
    await execute_query('''
        CREATE TABLE IF NOT EXISTS quiz_stats (
            user_id INTEGER PRIMARY KEY,
            first_name TEXT,
            game_time DATETIME,
            correct_answers INTEGER DEFAULT 0,
            wrong_answers INTEGER DEFAULT 0
    )''')
        
# Создание qviz индекса пользователя
async def create_quiz_index(user_id, first_name ):
    start_time = datetime.now()
    await execute_query('INSERT OR REPLACE INTO quiz_state (user_id, first_name ,question_index, start_time) VALUES (?, ?, ?, ?)', user_id, first_name, 0, start_time.strftime("%Y-%m-%d %H:%M:%S"))
    
# Сохранение qviz индекса и статистики в активной сессии
async def update_quiz_session(user_id, index, correct_answers, wrong_answers):
    await execute_query('''
        UPDATE quiz_state
        SET question_index = ?, correct_answers = ?, wrong_answers = ?
        WHERE user_id = ?
    ''', index, correct_answers, wrong_answers, user_id)
    
    
# Сохранение статистики завершенной игры
async def save_stats(stats):
    start_time = datetime.strptime(stats["start_time"], "%Y-%m-%d %H:%M:%S")
    game_time = datetime.now() - start_time
    await execute_query('INSERT OR REPLACE INTO quiz_stats (user_id, first_name ,game_time, correct_answers, wrong_answers) VALUES (?, ?, ?, ?, ?)', 
        stats['user_id'], 
        stats['first_name'], 
        game_time.total_seconds(), 
        stats['correct_answers'], 
        stats['wrong_answers']
    )
    
# Получение статистики всех пользователей
async def get_all_stats():
    result = await select_query('SELECT * FROM quiz_stats')
    return result
