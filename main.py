import asyncio
import logging

from aiogram import Bot, Dispatcher, types
from aiogram.filters.command import Command
from aiogram import F
from aiogram import types
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

import nest_asyncio
import aiosqlite
import yaml


import db_actions as db
import helper
from quiz_data import quiz_data

nest_asyncio.apply()

# Включаем логирование, чтобы не пропустить важные сообщения
logging.basicConfig(level=logging.INFO)



# Подгрузка параметров конфига
config = {}
with open('config.yaml', 'r',  encoding='utf-8') as configfile:
    config = yaml.safe_load(configfile)
db.set_config(config)
helper.set_config(config)

API_TOKEN = config['Bot_API']
START_BUT = config['Start_But']
STATS_BUT = config['Stats_But']
STOP_BUT = config['Stop_But']
ANSWER_ACTION = config['Answer_action']


# Объект бота
bot = Bot(token=API_TOKEN)
# Диспетчер
dp = Dispatcher()



# Хэндлер на команду /start
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    bord = helper.build_reply_keyboard([START_BUT,STATS_BUT])
    await message.answer("Это бот! Это квиз! Хотите начать игру? (Да хотите). Есть еще вот: посмотеть статистику игроков", reply_markup=bord)

# Хэндлер на старт новой игры
@dp.message(F.text==START_BUT)
@dp.message(Command("quiz"))
async def cmd_quiz(message: types.Message):
    await new_quiz(message)
    
# Хэндлер на показ статистики
@dp.message(F.text==STATS_BUT)
@dp.message(Command("stats"))
async def cmd_stats(message: types.Message):
    await show_stats(message)
    
    
# Хэндлер на остановку игры и сохранение результатов
@dp.message(F.text==STOP_BUT)
@dp.message(Command("stop"))
async def cmd_stop(message: types.Message):
    # Остановка игры
    await stop_quiz(message)



async def new_quiz(message):
    bord = helper.build_reply_keyboard([STOP_BUT])
    await message.answer("Не ну раз вы так сильно хотите играть - тогда вопросы: ", reply_markup=bord)
    
    user_id = message.from_user.id
    first_name = message.from_user.first_name
    
    await db.create_quiz_index(user_id, first_name)  # Создание/Сброс статистики
    await send_question(message, user_id)

async def stop_quiz(message, send_reply = True):
    if send_reply:
        bord = helper.build_reply_keyboard([START_BUT,STATS_BUT])
        await message.answer("Вы больше не играете в игру. Вы всегда можете начать сначала если не справляетесь с такой легкой игрой или посмотерть насколько остальные игроки сильно лучше вас", reply_markup=bord)
    
    user_id = message.from_user.id
    stats_data = await db.select_quiz_user(user_id)
    
    print("***")
    print(stats_data)
    print("***")
    await db.save_stats(stats_data)
    

async def show_stats(message):
    result = await db.get_all_stats()
    
    total_stats = ""
    for row in result:
        user_id= row[0]
        first_name = row[1]
        game_time = int(row[2])
        correct_answers = row[3]
        wrong_answers = row[4]
        
        user_link = f"tg://user?id={user_id}"
        
        total_stats += f'''
[{first_name}]({user_link}) : {game_time} секунд : {correct_answers} правильных : {wrong_answers} неправильных'''
        
    await message.answer(total_stats, parse_mode="Markdown")




async def send_question(message, user_id):
    # Получаем вопрос, генерим кнопки
    user_session = await db.select_quiz_session(user_id)
    current_question_index = user_session[0]
    opts = quiz_data[current_question_index]['options']
    kb = helper.generate_options_keyboard(opts)
    
    await message.answer(f"{quiz_data[current_question_index]['question']}", reply_markup=kb)

# Обработка ответов
@dp.callback_query()
async def answer_handler(callback):
    # Получаем данные из callback
    callback_data = callback.data
    
    # Разбираем callback_data (например, разделитель ":")
    action, *args = callback_data.split(":")
    
    if action == ANSWER_ACTION:
        user_id = callback.from_user.id
        user_session = await db.select_quiz_session(user_id)
        
        current_question_index = user_session[0]
        current_correct_answers = user_session[1]
        current_wrong_answers = user_session[2]
        
        answer_n = int(args[0])
        
        quiz_question_data = quiz_data[current_question_index]
        quiz_question = quiz_question_data["question"]
        answer_text = quiz_question_data["options"][answer_n]
        is_correct = quiz_question_data["correct_option"] == answer_n
        
        # редактируем текущее сообщение
        await callback.bot.edit_message_text(
            chat_id=callback.from_user.id,
            message_id=callback.message.message_id,
            text = f"{quiz_question}\n - {answer_text}",
            reply_markup=None
        )

        if is_correct:
            current_correct_answers += 1
            # Отправляем в чат сообщение, что ответ верный
            await callback.message.answer("Верно!")    
        else:
            current_wrong_answers += 1
            correct_option = quiz_data[current_question_index]['correct_option']
            # Отправляем в чат сообщение об ошибке с указанием верного ответа
            await callback.message.answer(f"Неправильно. Правильный ответ: [{quiz_data[current_question_index]['options'][correct_option]}]")
    
        # Обновление номера текущего вопроса в базе данных
        current_question_index += 1
        await db.update_quiz_session(callback.from_user.id, current_question_index, current_correct_answers, current_wrong_answers)
        
        # Проверяем достигнут ли конец квиза
        if current_question_index < len(quiz_data):
            # Следующий вопрос
            await send_question(callback.message, callback.from_user.id)
        else:
            # Уведомление об окончании квиза
            bord = helper.build_reply_keyboard([START_BUT,STATS_BUT])
            await callback.message.answer("Это был последний вопрос. Квиз завершен!", reply_markup=bord)
            await stop_quiz(callback, False)




# Запуск процесса поллинга новых апдейтов
async def main():    
    # Запускаем создание таблицы базы данных
    await db.create_tables()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())