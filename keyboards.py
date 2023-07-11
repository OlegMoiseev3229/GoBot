from aiogram.types import KeyboardButton, ReplyKeyboardMarkup,\
    ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup

logged_keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
new_game_button = KeyboardButton("/new_game")
delete_game_button = KeyboardButton("/delete_game")
list_button = KeyboardButton("/list")
list_my_button = KeyboardButton("/list_my")
list_my_live_button = KeyboardButton("/list_my_live")
join_button = KeyboardButton("/join")
play_button = KeyboardButton("/play")
logged_keyboard = logged_keyboard.insert(new_game_button).insert(delete_game_button)\
    .add(list_button).insert(list_my_button).insert(list_my_live_button)\
    .add(join_button).insert(play_button)

y_n_keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
y_button = KeyboardButton("Y")
n_button = KeyboardButton("N")
y_n_keyboard = y_n_keyboard.insert(y_button).insert(n_button)

game_size_keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
small_button = KeyboardButton("9")
medium_button = KeyboardButton("13")
big_button = KeyboardButton("19")
game_size_keyboard = game_size_keyboard.insert(small_button).insert(medium_button).insert(big_button)

game_keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
make_move_button = KeyboardButton("/make_move")
board_button = KeyboardButton("/board")
chat_button = KeyboardButton("/chat")
pass_button = KeyboardButton("/pass")
resign_button = KeyboardButton("/resign")
close_game_button = KeyboardButton("/close_game")
game_keyboard = game_keyboard.add(make_move_button).insert(board_button)\
    .add(chat_button).insert(pass_button).insert(resign_button)\
    .add(close_game_button)

chat_keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
close_chat_button = KeyboardButton("/close_chat")
history_button = KeyboardButton("/history")
gl_button = KeyboardButton("gl")
hf_button = KeyboardButton("hf")
hi_button = KeyboardButton("hi")
gg_button = KeyboardButton("gg")
chat_keyboard = chat_keyboard.add(gl_button).insert(hf_button).insert(hi_button).insert(gg_button).\
    add(close_chat_button).insert(history_button)

make_move_keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
cancel_move_button = KeyboardButton("/cancel_move")
make_move_keyboard = make_move_keyboard.add(board_button)\
    .add(cancel_move_button)
