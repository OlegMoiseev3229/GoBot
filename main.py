from config import BOT_TOKEN
from typing import Dict, List

from aiogram import Bot, Dispatcher, types, executor
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from keyboards import *

import numpy as np
import string

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
GAME_CHOICE_STATE = "game_choice"
GAME_STATE = "game"
GAME_MOVE_STATE = "game_move"
GAME_CHAT_STATE = "game_chat"
GAME_RESIGN_STATE = "game_resign"
# new states
TAKE_OFF_STATE = "take_off"
TAKE_OFF_CONFIRM_STATE = "take_off_confirm"


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
        text = "\n".join(self.messages)
        if text == "":
            text = "Chat history si empty"
        return text


class LiveGame:
    def __init__(self, game, opponent, opponent_id):
        self.game = game
        self.opponent = opponent
        self.opponent_id = opponent_id
        self.board = Board(self.game.size)
        self.chat = Chat()

    def __str__(self):
        return f"{self.game.name}: {self.game.creator} vs {self.opponent} \n" \
               f"    {self.game.size}x{self.game.size}. {self.current_player()}'s move"

    def other_player(self, player_id):
        if player_id == self.opponent_id:
            return self.game.creator_id
        else:
            return self.opponent_id

    def is_creator(self, uid):
        return uid == self.game.creator_id

    def current_player(self):
        if self.board.current_move == self.board.BLACK:
            return self.game.creator
        else:
            return self.opponent


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


class Board:
    WHITE_CIRCLE = '⚪️'
    BLACK_CIRCLE = '⚫️'
    BROWN_CIRCLE = '🟠'
    EMPTY = ' '

    BLACK = 1
    WHITE = 2

    FINE = 100
    INVALID_POSITION = 200
    PLACE_TAKEN = 201
    ILLEGAL_SUICIDE = 202
    ILLEGAL_KO = 203
    INVALID_NOTATION = 204
    GAME_END = 300

    def __init__(self, size):
        self.board_array = np.zeros((size, size))
        self.groups_array = np.zeros((size, size))
        self.group_dict = dict()
        self.size = size
        self.current_move = Board.BLACK
        self.black_score = 0
        self.white_score = 0
        self.passes = 0
        self.end = False

    def make_move(self, move: str):
        if len(move) not in (2, 3):
            return self.INVALID_NOTATION

        letter = move[0]
        digit = move[1:]
        if letter not in string.ascii_lowercase:
            return self.INVALID_NOTATION
        if not digit.isdigit():
            return self.INVALID_NOTATION
        move = string.ascii_lowercase.find(letter), int(digit)
        if move[0] >= self.size:
            return self.INVALID_POSITION
        if move[1] >= self.size:
            return self.INVALID_POSITION
        if self.board_array[move] != 0:
            return self.PLACE_TAKEN

        # here be game logic

        self.board_array[move] = self.current_move
        self.update_groups()
        self.take_dead_stones()

        if self.current_move == self.BLACK:
            self.current_move = self.WHITE
        else:
            self.current_move = self.BLACK

        self.passes = 0

        return self.FINE

    def display(self):
        result_array = []
        for i, row in enumerate(self.board_array):
            text_array = []
            for cell in row:
                if cell == 0:
                    text_array.append(self.BROWN_CIRCLE)
                if cell == self.BLACK:
                    text_array.append(self.BLACK_CIRCLE)
                if cell == self.WHITE:
                    text_array.append(self.WHITE_CIRCLE)
            text_array.append(string.ascii_uppercase[i])
            result_array.append("".join(text_array))
        separator = "\n"
        numbers = []
        for i in range(self.size):
            num = str(i)
            numbers.append(num)
            if i < 10:
                numbers.append("  ")
            numbers.append(" "*(3 - len(num)))

        result_array.insert(0, "".join(numbers))
        return separator.join(result_array)

    def update_groups(self):
        self.groups_array = np.zeros((self.size, self.size))
        self.group_dict = dict()
        group_n = 0
        for i in range(self.size):
            for j in range(self.size):
                if self.groups_array[i][j] != 0:
                    continue
                group_n += 1
                stone = (i, j)
                color = self.board_array[stone]
                self.group_dict[group_n] = Group(group_n, color)
                self.fill_group(stone, color, group_n)

    def fill_group(self, stone, color, group_n):
        try:
            group = self.group_dict[group_n]
            if self.groups_array[stone] == group_n:
                return
            if self.board_array[stone] == color:
                self.groups_array[stone] = group_n
                group.add_stone(stone)
                for s in self.stone_neighbours(stone):
                    self.fill_group(s, color, group_n)
            else:
                neigh_group = self.group_dict.get(self.groups_array[stone], None)
                if neigh_group is None:
                    return
                group.add_neighbour(neigh_group)
                neigh_group.add_neighbour(group)
        except IndexError:
            print("Index error occurred")

    def stone_neighbours(self, stone):
        stones = [(stone[0]-1, stone[1]),
                  (stone[0], stone[1]-1),
                  (stone[0]+1, stone[1]),
                  (stone[0], stone[1]+1)]
        for s in stones:
            if s[0] >= self.size or s[0] < 0:
                stones.remove(s)
            elif s[1] >= self.size or s[1] < 0:
                stones.remove(s)
        return stones

    def take_dead_stones(self):
        for group in self.group_dict.values():
            if group.color == 0:
                continue
            if group.is_dead():
                for stone in group.stones:
                    color = self.board_array[stone]
                    if color == self.BLACK:
                        self.black_score += 1
                    elif color == self.WHITE:
                        self.white_score += 1
                    self.board_array[stone] = 0

    def passing(self):
        self.passes += 1
        if self.passes == 2:
            self.end = True
            return self.GAME_END
        if self.current_move == self.BLACK:
            self.current_move = self.WHITE
        else:
            self.current_move = self.BLACK
        return self.FINE


class Group:
    def __init__(self, group_id, color):
        self.group_id = group_id
        self.color = color
        self.stones = set()
        self.neighbours = set()

    def add_stone(self, stone):
        self.stones.add(stone)

    def add_neighbour(self, neighbour):
        self.neighbours.add(neighbour)

    def is_dead(self):
        dead = True
        for n in self.neighbours:
            if n.color == 0:
                dead = False
                break
        return dead


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
        await message.answer(f"The game name is set to '{game_name}', are you OK with it? \nY/N?",
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
        text = "\n".join([f"{i + 1}) {str(game)}" for i, game in enumerate(new_games.values())])
        if len(new_games) == 0:
            text = "There is no games yet"
        await message.answer(text, reply_markup=logged_keyboard)

    @dp.message_handler(commands=['list_my'], state=LOGGED_STATE)
    async def list_my(message: types.Message, state: FSMContext):
        name = (await state.get_data())["name"]
        my_games = filter(lambda game: True if game.creator == name else False, new_games.values())
        text = "\n".join((f"{i + 1}) {str(game)}" for i, game in enumerate(my_games)))
        if len(text) == 0:
            text = "There is no your games yet"
        await message.answer(text, reply_markup=logged_keyboard)

    @dp.message_handler(commands=['list_my_live'], state=LOGGED_STATE)
    async def list_my_live(message: types.Message, state: FSMContext):
        name = (await state.get_data())["name"]
        my_games = await live_games_by_name(name)
        text = "\n".join((f"{i + 1}) {str(game)}" for i, game in enumerate(my_games)))
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

    @dp.message_handler(commands=['cancel_join'], state=JOIN_STATE)
    async def join_cancel(message: types.Message, state: FSMContext):
        await message.answer("Are you sure? \n Y/N", reply_markup=y_n_keyboard)
        await state.set_state(JOIN_CANCELLATION_STATE)

    @dp.message_handler(state=JOIN_STATE)
    async def join_game_name(message: types.Message, state: FSMContext):
        game_name = message.text
        name = (await state.get_data())['name']
        if game_name not in new_games.keys():
            await message.answer("Such game does not exist. Enter /cancel_join to cancel joining")
            return
        game = new_games.pop(game_name)
        live_games[game_name] = LiveGame(game, name, message.chat.id)
        await message.answer("You connected to the game. Enter /play to start playing it",
                             reply_markup=logged_keyboard)
        await bot.send_message(game.creator_id, f"Player {name} connected to your game {game_name}",
                               reply_markup=logged_keyboard)
        await state.set_state(LOGGED_STATE)

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

    @dp.message_handler(commands=['play'], state=LOGGED_STATE)
    async def play_handler(message: types.Message, state: FSMContext):
        await state.set_state(GAME_CHOICE_STATE)
        await message.answer("Enter the name of the game you want to play."
                             " Enter /cancel_play to cancel", reply_markup=ReplyKeyboardRemove())

    @dp.message_handler(commands=['cancel_play'], state=GAME_CHOICE_STATE)
    async def cancel_play(message: types.Message, state: FSMContext):
        await state.set_state(LOGGED_STATE)
        await message.answer("Game selection cancelled", reply_markup=logged_keyboard)

    @dp.message_handler(state=GAME_CHOICE_STATE)
    async def game_choice(message: types.Message, state: FSMContext):
        game_name = message.text
        name = (await state.get_data())['name']
        the_game = await live_game_by_name(game_name, name)
        if the_game is None:
            await message.answer("You didn't join game with such name. Enter /cancel_play to cancel")
            return
        await state.update_data({"current_game": game_name})
        await state.set_state(GAME_STATE)
        await message.answer("/make_move - make move \n"
                             "/board - look at the board\n"
                             "/chat - open game chat \n"
                             "/pass - pass\n"
                             "/resign - resign \n"
                             "/close_game - stop playing game (You will be able to play it later)",
                             reply_markup=game_keyboard)

    @dp.message_handler(commands=['close_game'], state=GAME_STATE)
    async def close_game(message: types.Message, state: FSMContext):
        await state.set_state(LOGGED_STATE)
        await message.answer("You closed the game", reply_markup=logged_keyboard)

    @dp.message_handler(commands=['chat'], state=GAME_STATE)
    async def chat_handler(message: types.Message, state: FSMContext):
        await state.set_state(GAME_CHAT_STATE)
        await message.answer("You entered chat. Enter /history to view chat history. Enter /close_chat to close chat",
                             reply_markup=chat_keyboard)

    @dp.message_handler(commands=['history'], state=GAME_CHAT_STATE)
    async def history_handler(message: types.Message, state: FSMContext):
        player_data = await state.get_data()
        game_name = player_data['current_game']
        name = player_data['name']
        the_game = await live_game_by_name(game_name, name)
        chat = the_game.chat
        await message.answer(chat.display(),
                             reply_markup=chat_keyboard)

    @dp.message_handler(commands=['close_chat'], state=GAME_CHAT_STATE)
    async def close_chat(message: types.Message, state: FSMContext):
        await state.set_state(GAME_STATE)
        await message.answer("You closed the chat", reply_markup=game_keyboard)

    @dp.message_handler(state=GAME_CHAT_STATE)
    async def chatting_handler(message: types.Message, state: FSMContext):
        player_data = await state.get_data()
        text = message.text
        uid = message.chat.id
        game_name = player_data['current_game']
        name = player_data['name']
        the_game = await live_game_by_name(game_name, name)
        opponent_id = the_game.other_player(uid)
        chat = the_game.chat
        chat.add(text, name)
        await bot.send_message(opponent_id, f"{name}: {text}")

    @dp.message_handler(commands=['board'], state=GAME_STATE)
    async def display_board(message: types.Message, state: FSMContext):
        player_data = await state.get_data()
        game_name = player_data['current_game']
        name = player_data['name']
        the_game = await live_game_by_name(game_name, name)
        await message.answer(the_game.board.display())

    @dp.message_handler(commands=['make_move'], state=GAME_STATE)
    async def move_handler(message: types.Message, state: FSMContext):
        await message.answer("Now make a move. Enter the letter, then the number. i.e. a0, f10, e3"
                             "Enter /cancel_move to cancel.", reply_markup=make_move_keyboard)
        await state.set_state(GAME_MOVE_STATE)

    @dp.message_handler(commands=['cancel_move'], state=GAME_MOVE_STATE)
    async def cancel_move(message: types.Message, state: FSMContext):
        await message.answer("Cancelled the move", reply_markup=game_keyboard)
        await state.set_state(GAME_STATE)

    @dp.message_handler(commands=['board'], state=GAME_MOVE_STATE)
    async def display_board(message: types.Message, state: FSMContext):
        player_data = await state.get_data()
        game_name = player_data['current_game']
        name = player_data['name']
        the_game = await live_game_by_name(game_name, name)
        await message.answer(the_game.board.display())

    @dp.message_handler(state=GAME_MOVE_STATE)
    async def make_move(message: types.Message, state: FSMContext):
        move = message.text
        player_data = await state.get_data()
        uid = message.chat.id
        game_name = player_data['current_game']
        name = player_data['name']
        the_game = await live_game_by_name(game_name, name)
        opponent_id = the_game.other_player(uid)
        board = the_game.board
        if board.end:
            await message.answer("The game is in taking off stage. Enter /take_off",
                                 reply_markup=game_keyboard)
            await state.set_state(GAME_STATE)
        color = board.WHITE
        if the_game.is_creator(uid):
            color = board.BLACK
        if the_game.opponent_id == the_game.game.creator_id:
            color = board.current_move
        if color != board.current_move:
            await message.answer("It's not your turn",
                                 reply_markup=make_move_keyboard)
            return
        result = board.make_move(move)
        if result == board.INVALID_NOTATION:
            await message.answer("Move should be letter and a number without a space i.e a0, f10 or e3",
                                 reply_markup=make_move_keyboard)
        elif result == board.INVALID_POSITION:
            await message.answer("You are trying to place a stone outside of the board",
                                 reply_markup=make_move_keyboard)
        elif result == board.PLACE_TAKEN:
            await message.answer("There is already a stone there",
                                 reply_markup=make_move_keyboard)
        elif result == board.ILLEGAL_SUICIDE:
            await message.answer("This move kills your stones, it's illegal",
                                 reply_markup=make_move_keyboard)
        elif result == board.ILLEGAL_KO:
            await message.answer("This move repeats positions, first make a move somewhere else",
                                 reply_markup=make_move_keyboard)
        elif result == board.FINE:
            await bot.send_message(opponent_id, f"{name} made a move in the game {game_name}",
                                   reply_markup=make_move_keyboard)
            await bot.send_message(opponent_id, board.display())
        else:
            raise NotImplementedError(f"Unexpected board return code: {result}")

    @dp.message_handler(commands=['resign'], state=GAME_STATE)
    async def resign_handler(message: types.Message, state: FSMContext):
        await state.set_state(GAME_RESIGN_STATE)
        await message.answer("Are you sure? Y/N", reply_markup=y_n_keyboard)

    @dp.message_handler(state=GAME_RESIGN_STATE)
    async def resign(message: types.Message, state: FSMContext):
        text = message.text.lower()
        if text == "y":
            uid = message.chat.id
            player_data = await state.get_data()
            game_name = player_data['current_game']
            name = player_data['name']
            the_game = await live_game_by_name(game_name, name)
            opponent_id = the_game.other_player(uid)
            await bot.send_message(opponent_id, f"{name} has resigned in game '{game_name}', you won!")
            live_games.pop(game_name)
        if text == "n":
            await state.set_state(GAME_STATE)
            await message.answer("Resignation cancelled",
                                 reply_markup=game_keyboard)
        else:
            await message.answer("Y/N", reply_markup=y_n_keyboard)

    @dp.message_handler(commands=['pass'], state=GAME_STATE)
    async def pass_handler(message: types.Message, state: FSMContext):
        uid = message.chat.id
        player_data = await state.get_data()
        game_name = player_data['current_game']
        name = player_data['name']
        the_game = await live_game_by_name(game_name, name)
        board = the_game.board
        opponent_id = the_game.other_player(uid)
        color = board.WHITE
        if the_game.is_creator(uid):
            color = board.BLACK
        if the_game.opponent_id == the_game.game.creator_id:
            color = board.current_move
        if color != board.current_move:
            await message.answer("It's not your turn",
                                 reply_markup=make_move_keyboard)
            return
        result = board.passing()
        if result == board.FINE:
            await bot.send_message(opponent_id, f"{name} has passed in game '{game_name}'")
        elif result == board.GAME_END:
            await bot.send_message(opponent_id, f"{name} has also passed in game '{game_name}', take off dead stones."
                                                f"Enter /take_off")
            await message.answer("Take off the dead stones. Enter /take_off")

    async def live_game_by_name(game_name, name):
        my_games = await live_games_by_name(name)
        the_game = None
        for game in my_games:
            if game.game.name == game_name:
                the_game = game
                break
        return the_game

    executor.start_polling(dp, skip_updates=True)


if __name__ == '__main__':
    main()
