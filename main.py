from config import BOT_TOKEN
from typing import Dict, List

from aiogram import Bot, Dispatcher, types, executor
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from keyboards import *

NAME_STATE = "name"
LOGGED_STATE = "logged"
NEW_GAME_NAME_STATE = "new_game_name"
NEW_GAME_NAME_CANCELLATION_STATE = "new_game_name_cancellation"
NEW_GAME_NAME_CONFIRMATION_STATE = "new_game_name_confirmation"
NEW_GAME_SIZE_STATE = "new_game_size_state"
NEW_GAME_SIZE_CANCELLATION_STATE = "new_game_size_cancellation"
GAME_DELETION_STATE = "game_deletion"
GAME_DELETION_CONFIRMATION_STATE = "game_deletion_confirmation"
JOIN_STATE = "join"
JOIN_CANCELLATION_STATE = "join_cancellation"
# new states
GAME_STATE = "game"
GAME_CLOSE_STATE = "game_close"
GAME_MOVE_STATE = "game_move"
GAME_MOVE_CANCEL_STATE = "game_move_cancel"
GAME_CHAT_STATE = "game_chat"
GAME_CHAT_CANCEL_STATE = "game_chat_cancel"
GAME_RESIGN_STATE = "game_resign"


class Game:
    def __init__(self, creator, creator_id, name, size):
        self.creator = creator
        self.creator_id = creator_id
        self.name = name
        self.size = size

    def __str__(self):
        return f"{self.creator}: {self.name}\n    size: {self.size}x{self.size}"


class Chat:
    def __init__(self):
        self.messages = []

    def add(self, message: str, sender: str):
        self.messages.append(f"{sender}: {message}")

    def display(self):
        return "\n".join(self.messages)


class LiveGame:
    def __init__(self, game, opponent, opponent_id):
        self.game = game
        self.opponent = opponent
        self.opponent_id = opponent_id
        self.board = None
        self.chat = Chat()

    def __str__(self):
        return f"{self.game.name}: {self.game.creator} vs {self.opponent} \n" \
               f"    {self.game.size}x{self.game.size}"

    def other_player(self, player_id):
        if player_id == self.opponent_id:
            return self.game.creator_id
        else:
            return self.opponent_id


class GameBuilder:
    def __init__(self):
        self._creator = ''
        self._creator_id = -1
        self._name = 'Friendly game'
        self._size = 19

    def build(self):
        return Game(self._creator, self._creator_id, self._name, self._size)

    def creator(self, creator):
        self._creator = creator
        return self

    def creator_id(self, creator_id):
        self._creator_id = creator_id
        return self

    def name(self, name):
        self._name = name
        return self

    def size(self, size):
        self._size = size
        return self


def main():

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(bot, storage=MemoryStorage())
    users = set()
    names = set()
    new_games: Dict[str, Game] = dict()
    game_builders: Dict[int, GameBuilder] = dict()
    live_games: Dict[str, LiveGame] = dict()

    @dp.message_handler(commands=['start'], state="*")
    async def start_handler(message: types.Message, state: FSMContext):
        users.add(message.chat.id)
        await state.set_state(NAME_STATE)
        await message.answer("Hello", reply_markup=ReplyKeyboardRemove())
        await message.answer("Please Enter your username")

    @dp.message_handler(state=NAME_STATE)
    async def name_handler(message: types.Message, state: FSMContext):
        name = message.text
        if name in names:
            await message.answer("The name is already taken. Enter new name")
            return
        await state.update_data({"name": name})
        await message.answer(f"OK, {name} now you can play", reply_markup=logged_keyboard)
        await state.set_state(LOGGED_STATE)

    @dp.message_handler(commands=['new_game'], state=LOGGED_STATE)
    async def new_game_handler(message: types.Message, state: FSMContext):
        await state.set_state(NEW_GAME_NAME_STATE)
        uid = message.chat.id
        name = (await state.get_data())['name']
        game_builders[uid] = GameBuilder().creator(name).creator_id(uid)
        await message.answer("Enter the name of the game. Enter /cancel_new to cancel the game creation",
                             reply_markup=ReplyKeyboardRemove())

    @dp.message_handler(commands=['cancel_new'], state=NEW_GAME_NAME_STATE)
    async def cancel_new_game_handler(message: types.Message, state: FSMContext):
        await state.set_state(NEW_GAME_NAME_CANCELLATION_STATE)
        await message.answer("Are you sure? \n Y/N", reply_markup=y_n_keyboard)

    @dp.message_handler(state=NEW_GAME_NAME_CANCELLATION_STATE)
    async def cancel_new_game_at_name(message: types.Message, state: FSMContext):
        ans = message.text.lower()
        if ans == 'y':
            await state.set_state(LOGGED_STATE)
            uid = message.chat.id
            game_builders.pop(uid)
            await message.answer("New game cancelled", reply_markup=logged_keyboard)
        elif ans == 'n':
            await state.set_state(NEW_GAME_NAME_STATE)
            await message.answer("Enter the name of the game. Enter /cancel_new to cancel the game creation",
                                 reply_markup=ReplyKeyboardRemove())
        else:
            await message.answer("Y/N")

    @dp.message_handler(state=NEW_GAME_NAME_STATE)
    async def new_game_name_set(message: types.Message, state: FSMContext):
        game_name = message.text
        if game_name in new_games.keys():
            await message.answer("Game with such name already exists, Enter new name ")
            return
        if game_name in live_games.keys():
            await message.answer("Game with such name already exists, Enter new name ")
            return

        uid = message.chat.id
        game_builder: GameBuilder = game_builders[uid]
        game_builder.name(game_name)
        await message.answer(f"The game name is set to '{game_name},' are you OK with it? \nY/N?",
                             reply_markup=y_n_keyboard)
        await state.set_state(NEW_GAME_NAME_CONFIRMATION_STATE)

    @dp.message_handler(state=NEW_GAME_NAME_CONFIRMATION_STATE)
    async def new_game_name_confirm(message: types.Message, state: FSMContext):
        text = message.text.lower()
        if text == "y":
            await message.answer("OK, now enter the size of a board (9, 13 or 19)"
                                 "  Enter /cancel_new to cancel the game creation",
                                 reply_markup=game_size_keyboard)
            await state.set_state(NEW_GAME_SIZE_STATE)
        elif text == "n":
            await message.answer("Enter new name", reply_markup=ReplyKeyboardRemove())
            await state.set_state(NEW_GAME_NAME_STATE)
        else:
            await message.answer("Y/N")

    @dp.message_handler(commands=['cancel_new'], state=NEW_GAME_SIZE_STATE)
    async def cancel_new_game_handler(message: types.Message, state: FSMContext):
        await state.set_state(NEW_GAME_SIZE_CANCELLATION_STATE)
        await message.answer("Are you sure? \n Y/N", reply_markup=y_n_keyboard)

    @dp.message_handler(state=NEW_GAME_SIZE_CANCELLATION_STATE)
    async def cancel_new_game_at_size(message: types.Message, state: FSMContext):
        ans = message.text.lower()
        if ans == 'y':
            await state.set_state(LOGGED_STATE)
            uid = message.chat.id
            game_builders.pop(uid)
            await message.answer("New game cancelled", reply_markup=ReplyKeyboardRemove())
        elif ans == 'n':
            await state.set_state(NEW_GAME_NAME_STATE)
            await message.answer("OK, now enter the size of a board (9, 13 or 19)"
                                 "  Enter /cancel_new to cancel the game creation",
                                 reply_markup=game_size_keyboard)
        else:
            await message.answer("Y/N")

    @dp.message_handler(state=NEW_GAME_SIZE_STATE)
    async def new_game_size(message: types.Message, state: FSMContext):
        text = message.text
        if not text.isdigit():
            await message.answer("Enter a number")
            return
        size = int(text)
        if size not in (9, 13, 19):
            await message.answer("Size can be only 9, 13 or 19")
            return
        uid = message.chat.id
        game_builder: GameBuilder = game_builders[uid]
        game = game_builder.size(size).build()
        game_builders.pop(uid)
        new_games[game.name] = game
        await message.answer("The game has been created",
                             reply_markup=logged_keyboard)
        await state.set_state(LOGGED_STATE)

    @dp.message_handler(commands=['list'], state=LOGGED_STATE)
    async def list_handler(message: types.Message, state: FSMContext):
        text = "\n".join([f"{i+1}) {str(game)}" for i, game in enumerate(new_games.values())])
        if len(new_games) == 0:
            text = "There is no games yet"
        await message.answer(text, reply_markup=logged_keyboard)

    @dp.message_handler(commands=['list_my'], state=LOGGED_STATE)
    async def list_my(message: types.Message, state: FSMContext):
        name = (await state.get_data())["name"]
        my_games = filter(lambda game: True if game.creator == name else False, new_games.values())
        text = "\n".join((f"{i+1}) {str(game)}" for i, game in enumerate(my_games)))
        if len(text) == 0:
            text = "There is no your games yet"
        await message.answer(text, reply_markup=logged_keyboard)

    @dp.message_handler(commands=['list_my_live'], state=LOGGED_STATE)
    async def list_my_live(message: types.Message, state: FSMContext):
        name = (await state.get_data())["name"]
        my_games = await live_games_by_name(name)
        text = "\n".join((f"{i+1}) {str(game)}" for i, game in enumerate(my_games)))
        if len(text) == 0:
            text = "There is no your live games yet"
        await message.answer(text, reply_markup=logged_keyboard)

    async def live_games_by_name(name):
        return filter(lambda game: True if (game.game.creator == name or game.opponent == name) else False,
                      live_games.values())

    @dp.message_handler(commands=['delete_game'], state=LOGGED_STATE)
    async def delete_handler(message: types.Message, state: FSMContext):
        await state.set_state(GAME_DELETION_STATE)
        await message.answer("Enter the name of the game you want to delete. Enter /cancel_del to cancel the deletion",
                             reply_markup=ReplyKeyboardRemove())

    @dp.message_handler(commands=['cancel_del'], state=GAME_DELETION_STATE)
    async def cancel_deletion(message: types.Message, state: FSMContext):
        await state.set_state(LOGGED_STATE)
        await message.answer("Game deletion canceled",
                             reply_markup=logged_keyboard)

    @dp.message_handler(state=GAME_DELETION_STATE)
    async def delete_game_name(message: types.Message, state: FSMContext):
        name = message.text
        uid = message.chat.id
        game = new_games.get(name, None)
        if game is None:
            await message.answer("Such game does not exist. Enter /cancel_del to cancel the deletion")
            return
        if game.creator_id != uid:
            await message.answer("This are not your game. Enter /cancel_del to cancel the deletion")
            return
        await state.update_data({"game_to_delete": name})
        await state.set_state(GAME_DELETION_CONFIRMATION_STATE)
        await message.answer("Are you sure? \n Y/N", reply_markup=y_n_keyboard)

    @dp.message_handler(state=GAME_DELETION_CONFIRMATION_STATE)
    async def delete_game_confirm(message: types.Message, state: FSMContext):
        text = message.text.lower()
        if text == "y":
            game_name = (await state.get_data())['game_to_delete']
            new_games.pop(game_name)
            await message.answer("Game deleted", reply_markup=logged_keyboard)
            await state.set_state(LOGGED_STATE)
        elif text == "n":
            await state.set_state(LOGGED_STATE)
            await message.answer("Game deletion canceled", reply_markup=logged_keyboard)
        else:
            await message.answer("Y/N")

    @dp.message_handler(commands=['join'], state=LOGGED_STATE)
    async def join_game(message: types.Message, state: FSMContext):
        await state.set_state(JOIN_STATE)
        await message.answer("Enter the name of the game you want to join. Enter /cancel_join to cancel joining",
                             reply_markup=ReplyKeyboardRemove())

    @dp.message_handler(state=JOIN_STATE)
    async def join_game_name(message: types.Message, state: FSMContext):
        game_name = message.text
        name = (await state.get_data())['name']
        if game_name not in new_games.keys():
            await message.answer("Such game does not exist. Enter /cancel_join to cancel joining")
            return
        game = new_games.pop(game_name)
        live_games[game_name] = LiveGame(game, name, message.chat.id)
        await message.answer("You connected to the game. Enter /play to start playing it")
        await bot.send_message(game.creator_id, f"Player {name} connected to your game {game_name}",
                               reply_markup=logged_keyboard)
        await state.set_state(LOGGED_STATE)

    @dp.message_handler(commands=['cancel_join'], state=JOIN_STATE)
    async def join_cancel(message: types.Message, state: FSMContext):
        await message.answer("Are you sure? \n Y/N", reply_markup=y_n_keyboard)
        await state.set_state(JOIN_CANCELLATION_STATE)

    @dp.message_handler(state=JOIN_CANCELLATION_STATE)
    async def join_cancel_confirm(message: types.Message, state: FSMContext):
        answer = message.text.lower()
        if answer == "y":
            await message.answer("Joining game cancelled", reply_markup=logged_keyboard)
            await state.set_state(LOGGED_STATE)
        elif answer == "n":
            await message.answer("Enter the name of the game you want to join. Enter /cancel_join to cancel joining",
                                 reply_markup=ReplyKeyboardRemove())
            await state.set_state(JOIN_STATE)

        else:
            await message.answer("Y/N")

    executor.start_polling(dp, skip_updates=True)


if __name__ == '__main__':
    main()
