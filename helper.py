from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from aiogram import types


def set_config(cfg):
    global config, ANSWER_ACTION
    
    config = cfg
    ANSWER_ACTION = config['Answer_action']




def build_reply_keyboard(options):
    builder = ReplyKeyboardBuilder()
    for opt in options:
        builder.add(types.KeyboardButton(text=opt))
    return builder.as_markup(resize_keyboard=True)


def generate_options_keyboard(answer_options):
    builder = InlineKeyboardBuilder()
    
    i = 0
    for option in answer_options:
        builder.add(types.InlineKeyboardButton(
            text=option,
            callback_data=f"{ANSWER_ACTION}:{i}")
        )
        i+=1
    # Выводим по одной кнопке в столбик
    builder.adjust(1)
    return builder.as_markup()