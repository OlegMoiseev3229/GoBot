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

    def result(self):
        return f"The game {self.game.name} has ended. \n" \
               f"{self.game.creator}: {self.board.black_score} vs {self.opponent}: {self.board.white_score} \n" \
               f"{'White' if self.board.white_score >= self.board.black_score else 'Black'} won"


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
        self.take_off_list = TakeOffList()

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

    def mark_dead_stone(self, move, color):
        if len(move) not in (2, 3):
            return self.INVALID_NOTATION

        letter = move[0]
        digit = move[1:]

        if not self.end:
            raise RuntimeError("Trying to take off stones before the end of the game")
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
            if color == self.BLACK:
                self.take_off_list.black_add(move)
            if color == self.WHITE:
                self.take_off_list.white_add(move)
            return self.PLACE_TAKEN
        return self.FINE

    def end_game(self):
        dead_groups = set()
        for stone in self.take_off_list.black:
            dead_groups.add(self.group_dict[self.groups_array[stone]])
        for stone in self.take_off_list.white:
            dead_groups.add(self.group_dict[self.groups_array[stone]])

        for group in dead_groups:
            for stone in group.stones:
                color = self.board_array[stone]
                if color == self.BLACK:
                    self.white_score += 1
                elif color == self.WHITE:
                    self.black_score += 1
                self.board_array[stone] = 0

        self.update_groups()

        for group in self.group_dict.values():
            if group.color != 0:
                continue
            neigh_colors = set()
            for neighbour in group.neighbours:
                neigh_colors.add(neighbour.color)
            if len(neigh_colors) == 1:
                color = neigh_colors.pop()
                if color == self.BLACK:
                    self.black_score += len(group.stones)
                elif color == self.WHITE:
                    self.white_score += len(group.stones)


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


class TakeOffList:
    def __init__(self):
        self.black = []
        self.white = []
        self.black_agree = False
        self.white_agree = False
        self.black_ready = False
        self.white_ready = False

    def black_add(self, stone):
        self.black.append(stone)

    def white_add(self, stone):
        self.white.append(stone)


def main():
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(bot, storage=MemoryStorage())
    users = set()
    names = set()
    new_games: Dict[str, Game] = dict()
    game_builders: Dict[int, GameBuilder] = dict()
    live_games: Dict[str, LiveGame] = dict()

    @dp.message_handler(commands=['guide'], state='*')
    async def guide_handler(message: types.Message, state: FSMContext):
        await message.answer("""
        Welcome to the guide on my GoBot!
        First of all, you should enter the /start command
        Then you need to enter your name
        -----------------------
        To create a new game enter /new_game:
          You will need to enter it's name and board size
          You can delete a game using the /game_del command
        ------------------------
        To look at the list of games you can join, enter /list
          /list_my will show the list of your games and /list_my_live will show the list of games you joined
        ------------------------
        To join a game you need to enter /join and then enter the name of the game
        To play the game that you've joined, you need to enter /play and then the name of the game 
        ------------------------
        After entering /play you are in the game menu:
          Enter /chat to open the chat with your opponent. There you can open chat history by entering /history
          Enter /make_move to make a move
            You will be sent to a menu, where you can enter /board to look at the boar
            Moves should be a letter, followed by a number i.e. a0, e4 or f10
          Enter /reign to resign
          Enter /pass to pass
            After both players pass, the game goes into the take off stage:
            Enter /take_off to select groups you think are dead. It's enough to enter just one stone of a group
            Enter /take_off_commit to commit to the dead stones
            Enter /take_off_confirm to look at opponent's opinion of dead stones and agree/disagree with it

        Приветствую вас в руководстве по своему GoBot
        Прежде всего, вам стоит ввести комманду /start
        Затем ввести своё имя
        ----------------------
        Чтобы создать новую игру введите /new_game:
          Вам надо будет ввести её название и размер доски
          Игру можно удалить с помощью комманды /game_del
        ----------------------
        Чтобы посмотреть на список игр, в которые можно зайти, введи /list
          /list_my покажет список всех ваших игр, а /list_my_live покажет список всех игр, в которые вы вошли
        ---------------------- 
        Чтобы зайти в игру надо ввести /join и затем ввести название игры
        Чтобы сыграть в игру, в которую вы зашли, надо ввести /play и затем название игры
        ----------------------
        После ввода комманды /play вы находитесь в меню игры:
          Введите /chat чтобы открыть чат со своим противником. В чате можно открыть историю чата, введя /history
          Ходы должны быть в формате: одна латинская буква, а затем число, например a0, e4 или f10
        Введите /resign чтобы сдатся
        Введите /pass чтобы спасовать
            После того, как оба игрока спасуют, игра переходит в стадию снятия камней:
            Введите /take_off чтобы выбрать группы камней, которые вы считаете мёртвыми. Достаточно ввести всего лишь один камень группы
            Введите /take_off_commit чтобы подтведить свой выбор мёртвых камней
            Введите /take_off_confirm чтобы посмотреть на мнение противника по мнению мёртвых камней и согласится/не согласится
        """)

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
            await state.set_state(LOGGED_STATE)
            await message.answer("You resigned the game", reply_markup=logged_keyboard)
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

    @dp.message_handler(commands=['take_off'], state=GAME_STATE)
    async def take_off_handler(message: types.Message, state: FSMContext):
        uid = message.chat.id
        player_data = await state.get_data()
        game_name = player_data['current_game']
        name = player_data['name']
        the_game = await live_game_by_name(game_name, name)
        board = the_game.board
        if not board.end:
            await message.answer("The game hasn't ended yet")
            return
        await message.answer("To take off a group enter one of the stones. To end enter /take_off_commit"
                             " Enter /board to look at the board",
                             reply_markup=ReplyKeyboardRemove())
        await state.set_state(TAKE_OFF_STATE)

    @dp.message_handler(commands=['cancel_take_off'], state=TAKE_OFF_STATE)
    async def cancel_take_off(message: types.Message, state: FSMContext):
        await message.answer("Taking off stones cancelled")
        await state.set_state(GAME_STATE)

    @dp.message_handler(commands=['take_off_commit'], state=TAKE_OFF_STATE)
    async def commit_take_off(message: types.Message, state: FSMContext):
        uid = message.chat.id
        player_data = await state.get_data()
        game_name = player_data['current_game']
        name = player_data['name']
        the_game = await live_game_by_name(game_name, name)
        board = the_game.board
        color = board.WHITE
        if the_game.is_creator(uid):
            color = board.BLACK
        if color == board.BLACK:
            board.take_off_list.black_ready = True
        if color == board.WHITE:
            board.take_off_list.white_ready = True
        if uid == the_game.other_player(uid):
            board.take_off_list.black_ready = True
            board.take_off_list.white_ready = True
        opponent_id = the_game.other_player(uid)
        await bot.send_message(opponent_id, f"{name} in game: {game_name} has marked the dead stones.")
        await message.answer("Ready", reply_markup=game_keyboard)
        await state.set_state(GAME_STATE)

    @dp.message_handler(state=TAKE_OFF_STATE)
    async def take_off_stones(message: types.Message, state: FSMContext):
        text = message.text
        uid = message.chat.id
        player_data = await state.get_data()
        game_name = player_data['current_game']
        name = player_data['name']
        the_game = await live_game_by_name(game_name, name)
        board = the_game.board
        color = board.WHITE
        if the_game.is_creator(uid):
            color = board.BLACK
        response = the_game.board.mark_dead_stone(text, color)
        if response == board.FINE:
            await message.answer("There is no stone there")
        elif response == board.INVALID_POSITION:
            await message.answer("It's outside of the board")
        elif response == board.INVALID_NOTATION:
            await message.answer("It should be a letter and a number without of space: i.e. a0, b1 or g14")

    @dp.message_handler(commands=['take_off_confirm'], state=GAME_STATE)
    async def take_off_confirmation_handler(message: types.Message, state: FSMContext):
        text = message.text
        uid = message.chat.id
        player_data = await state.get_data()
        game_name = player_data['current_game']
        name = player_data['name']
        the_game = await live_game_by_name(game_name, name)
        board = the_game.board
        color = board.WHITE
        if the_game.is_creator(uid):
            color = board.BLACK
        if color == board.BLACK:
            if board.take_off_list.black_agree:
                await message.answer("You have already agreed")
                return
            other_ready = board.take_off_list.white_ready
            if not other_ready:
                await message.answer("The other player hasn't yet took the dead stones")
                return
            await message.answer(f"Other player suggested the following removes:{', '.join(board.take_off_list.white)}"
                                 f"do you agree? Y/N?", reply_markup=y_n_keyboard)
            await state.set_state(TAKE_OFF_CONFIRM_STATE)
        else:
            if board.take_off_list.white_agree:
                await message.answer("You have already agreed")
                return
            other_ready = board.take_off_list.black_ready
            if not other_ready:
                await message.answer("The other player hasn't yet took the dead stones")
                return
            await message.answer(f"Other player suggested the following removes:{', '.join(board.take_off_list.black)}"
                                 f"do you agree? Y/N?", reply_markup=y_n_keyboard)
            await message.answer(board.display())
            await state.set_state(TAKE_OFF_CONFIRM_STATE)

    @dp.message_handler(state=TAKE_OFF_CONFIRM_STATE)
    async def take_off_confirmation(message: types.Message, state: FSMContext):
        text = message.text.lower()
        if text == 'y':
            agree = True
        elif text == 'n':
            agree = False
        else:
            await message.answer("Y/N")
            return
        uid = message.chat.id
        player_data = await state.get_data()
        game_name = player_data['current_game']
        name = player_data['name']
        the_game = await live_game_by_name(game_name, name)
        board = the_game.board
        color = board.WHITE
        if the_game.is_creator(uid):
            color = board.BLACK
        opponent_id = the_game.other_player(uid)
        if color == board.BLACK:
            other_agree = board.take_off_list.white_agree
        else:
            other_agree = board.take_off_list.black_agree
        if uid == the_game.other_player(uid):
            other_agree = True
        if not agree:
            board.take_off_list = TakeOffList()
            await bot.send_message(opponent_id, f"{name} in the game {game_name} rejected your take off of stones")
        else:
            if other_agree:
                board.end_game()
                await message.answer(the_game.result(), reply_markup=logged_keyboard)
                await bot.send_message(opponent_id, the_game.result())
                live_games.pop(game_name)
                await state.set_state(LOGGED_STATE)
            else:
                await message.answer("Now wait for the other player")
                await bot.send_message(opponent_id, f"the player {name} has agreed to your removes in the game {game_name}")
                await state.set_state(LOGGED_STATE)

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
