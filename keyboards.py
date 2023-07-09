from aiogram.types import KeyboardButton, ReplyKeyboardMarkup,\
    ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup

logged_keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
new_game_button = KeyboardButton("/new_game")
delete_game_button = KeyboardButton("/delete_game")
list_button = KeyboardButton("/list")
list_my_button = KeyboardButton("/list_my")
list_my_live_button = KeyboardButton("/list_my_live")
play_button = KeyboardButton("/play")
logged_keyboard = logged_keyboard.insert(new_game_button).insert(delete_game_button)\
    .add(list_button).insert(list_my_button).insert(list_my_live_button)\
    .add(play_button)

y_n_keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
y_button = KeyboardButton("Y")
n_button = KeyboardButton("N")
y_n_keyboard = y_n_keyboard.insert(y_button).insert(n_button)

game_size_keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
small_button = KeyboardButton("9")
medium_button = KeyboardButton("13")
big_button = KeyboardButton("19")
game_size_keyboard = game_size_keyboard.insert(small_button).insert(medium_button).insert(big_button)
