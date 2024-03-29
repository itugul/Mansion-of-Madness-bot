import logging
import time
import json
import random
from telegram import Update
from telegram.ext import filters, MessageHandler, ApplicationBuilder, CommandHandler, ContextTypes, Application

class bcolors:
    PURP = '\033[95m'  # Purple color
    BLUE = '\033[94m'  # Blue color
    GREEN = '\033[92m'  # Green color
    YELL = '\033[93m'  # Yellow color
    RED = '\033[91m'  # Red color
    BOLD = '\033[1m'  # Bold
    ULINE = '\033[4m'  # Underline
    ENDC = '\033[0m'  # End of color line

logging.basicConfig(
    format=f"{bcolors.GREEN}%(asctime)s - %(name)s - %(levelname)s - %(message)s{bcolors.ENDC}",
    level=logging.INFO
)

token = ""
adm_chat_id = -4006484999
statistics_db = {}
start_timer = 0
duration_game = 21600
completed_puzzles = []
players = []
game_on = False
puzzle_text = []
start_text = []
end_text = []


#Служебные функции
def remove_job_if_exists(name: str, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Remove job with given name. Returns whether job was removed."""
    current_jobs = context.job_queue.get_jobs_by_name(name)
    if not current_jobs:
        return False
    for job in current_jobs:
        job.schedule_removal()
    return True

async def alarm(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send the alarm message."""
    global game_on

    job = context.job
    if completed_puzzles.count(0) < 1:
        await context.bot.send_message(job.chat_id, text=end_text[0])
    else:
        await context.bot.send_message(job.chat_id, text=end_text[1])
    game_on = False
    await save()

async def game_off_alert(update, context):
    await context.bot.send_message(
        chat_id=update.effective_chat.id ,
        text="Игра не запущена или окончена!"
    )

def start_load():
        global statistics_db
        global start_timer
        global duration_game
        global completed_puzzles
        global players
        global game_on
        global puzzle_text
        global start_text
        global end_text

        with open("data.json", "r", encoding="utf-8") as read_file:
            data = json.load(read_file)
        start_timer = data['start_timer']
        duration_game = data['duration_game']
        completed_puzzles = data['completed_puzzles']
        players = data['players']
        game_on = data['game_on']
        puzzle_text = data['puzzle_text']
        start_text = data['start_text']
        end_text = data['end_text']
        print(f"{bcolors.YELL}Стартовая загрузка из резервной копии завершена.{bcolors.ENDC}")

async def check_fin(num, update, context):
    if completed_puzzles[num - 1] != 0:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Задание №" + str(num) + " уже решено. Финальный ответ прислал " + completed_puzzles[num - 1] + ". Узнай результаты у него."
        )
        return True
    else:
        return False
    
async def completing_puzzle(num, update, context):
    global completed_puzzles

    completed_puzzles[num - 1] = "@" + update.effective_user.username
    players_id = players.copy()
    players_id.append(adm_chat_id)
    count = 0
    for i in completed_puzzles:
        if i != 0:
            count += 1
    all_puzzle_fin = ""
    if count == len(completed_puzzles):
        all_puzzle_fin = "\n\nВсе печати сняты! Осталось лишь дождаться правильного расположения звёзд, и вы получите по заслугам!"
    for id in players_id:
        await context.bot.send_message(
            chat_id=id,
            text="Задание №" + str(num) + " пройдено! " + completed_puzzles[num - 1] + " прислал финальный ответ." + all_puzzle_fin
        )


async def save():
    data = {
        'statistics_db': statistics_db,
        'start_timer': start_timer,
        'duration_game': duration_game,
        'completed_puzzles': completed_puzzles,
        'players': players,
        'game_on': game_on,
        'puzzle_text': puzzle_text,
        'start_text': start_text,
        'end_text': end_text
    }
    with open('data.json', 'w', encoding="utf-8") as save_file:
        json.dump(data, save_file, indent=4)
    print(f"{bcolors.YELL}Файл резервной копии перезаписан.{bcolors.ENDC}")

def how_time_left():
    time_left = duration_game - (time.time() - start_timer)
    hours_left = time_left // 3600
    minutes_left = (time_left % 3600) // 60
    seconds_left = ((time_left % 3600) % 60) // 1
    res = "Окончание игры через: " + str(int(hours_left)) + ":" + str(int(minutes_left)) + ":" + str(int(seconds_left))

    return res

def how_puzzles_completed():
    count = 0
    for i in completed_puzzles:
        if i != 0:
            count += 1
    return str(count) + " из 5ти загадок решено"

def statistics():
    statistics_str = "Статистика по всем ключам:\n"
    for i in statistics_db.items():
        statistics_str += str(i) + "\n"
    if completed_puzzles.count(0) < 1:
        statistics_str += "🔥🔥🔥🔥🔥🔥🔥🔥ФИНАЛ🔥🔥🔥🔥🔥🔥🔥🔥"
    return statistics_str

async def registration(context, update, puzzle_num, rep):
    global statistics_db
    global players

    name = "@" + str(update.effective_user.username)
    if name not in statistics_db[update.effective_message.text.lower()]:
        statistics_db[update.effective_message.text].append(name)
        if rep:
            for id in players:
                if id != update.effective_chat.id:
                    await context.bot.send_message(
                        chat_id=id,
                        text= name + " продвинулся в задании №" + str(puzzle_num) + ". Свяжись с ним, если хочешь узнать падробности!"
                    )

    if update.effective_chat.id not in players:
        players.append(update.effective_chat.id)
        """Add a job to the queue."""
        time_left = duration_game - (time.time() - start_timer)
        context.job_queue.run_once(alarm, time_left, chat_id=update.effective_chat.id, name=str(update.effective_chat.id), data=duration_game)

    await save()

async def user_msg_footer(context, update, puzzle_num= 0, rep= True):
    if update.effective_chat.id != adm_chat_id:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text = how_puzzles_completed() + "\n\n" + how_time_left()
        )

        await registration(context, update, puzzle_num, rep)
        await report(context, update)

async def send_msg(update, context, puzzle_num, stage_num, clue = "", clue_target = "", fin = False):
    to_send = "О, кажется это касается задания №" + str(puzzle_num) + "\nДавайте я напомню что там за задание:" + "\n" + puzzle_text[puzzle_num-1][0] 
    if len(puzzle_text[puzzle_num-1][stage_num]) > 2:
        to_send += "\n\nА вот что я знаю о твоей находке:\n" + puzzle_text[puzzle_num-1][stage_num][2]
    if update.effective_chat.id != adm_chat_id:
        if not await check_fin(puzzle_num, update, context):
            if fin:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text= puzzle_text[puzzle_num-1][stage_num][2]
                )
                await completing_puzzle(puzzle_num, update, context)
            else:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text= to_send
                )
                if clue_target != "" and len(statistics_db[clue_target]) > 1:
                    await context.bot.send_message(
                        chat_id=update.effective_chat.id ,
                        text= "Вообще то, следующий код уже нашёл " + str(statistics_db[clue_target][random.randint(1, len(statistics_db[clue_target]) - 1)]) + " . Можешь спросить у него!"
                    )
            await user_msg_footer(context, update, puzzle_num)
    else:
        await context.bot.send_message(
            chat_id=adm_chat_id,
            text= to_send
        )


#Административные функции
async def load_timer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    players_id = players.copy()
    players_id.append(adm_chat_id)
    time_left = duration_game - (time.time() - start_timer)
    for id in players_id:
        """Add a job to the queue."""
        remove_job_if_exists(str(id), context)
        context.job_queue.run_once(alarm, time_left, chat_id=id, name=str(id), data=duration_game)
    await context.bot.send_message(
            chat_id=adm_chat_id,
            text = "Таймеры возобновлены"
        )
    print(f"{bcolors.YELL}Таймеры перенастроены.{bcolors.ENDC}")
    

async def add_duration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id == adm_chat_id:
        global duration_game

        duration_game += int(context.args[0]) * 60
        await context.bot.send_message(
            chat_id=adm_chat_id,
            text = how_time_left()
        )
        print(f"{bcolors.YELL}Таймер изменён на {bcolors.ENDC}", int(context.args[0]), f"{bcolors.YELL}минут{bcolors.ENDC}")
        await load_timer(update, context)
        await save()


async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id == adm_chat_id:
        global statistics_db
        global start_timer
        global duration_game
        global completed_puzzles
        global players
        global game_on
        global puzzle_text
        global start_text
        global end_text

        with open("default_data.json", "r", encoding='utf-8') as read_file:
            data = json.load(read_file)
        start_timer = data['start_timer']
        duration_game = data['duration_game']
        puzzle_text = data['puzzle_text']
        start_text = data['start_text']
        end_text = data['end_text']

        completed_puzzles = [0 for vl in puzzle_text]

        statistics_db.clear()
        statistics_db['/start'] = ['start', ]
        puzzle_num = 1
        while puzzle_num <= len(puzzle_text):
            stage_num = 1
            while stage_num < len(puzzle_text[puzzle_num-1]):
                label = "quest " + str(puzzle_num)
                if puzzle_text[puzzle_num-1][stage_num][0]!="fin":
                    label += "." + str(stage_num)
                else:
                    label += " fin"
                statistics_db[puzzle_text[puzzle_num-1][stage_num][1]] = [label, ]
                stage_num += 1
            puzzle_num += 1

        players_id = players.copy()
        players_id.append(adm_chat_id)
        for id in players_id:
            """Remove a job to the queue."""
            remove_job_if_exists(str(id), context)
        players = data['players']

        game_on = data['game_on']
        await context.bot.send_message(
            chat_id=adm_chat_id,
            text = "Игра сброшена!"
        )
        print(f"{bcolors.YELL}Настройки игры сброшены до дефолтных.{bcolors.ENDC}")

async def load(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id == adm_chat_id:
        global statistics_db
        global start_timer
        global duration_game
        global completed_puzzles
        global players
        global game_on
        global puzzle_text
        global start_text
        global end_text

        with open("data.json", "r", encoding="utf-8") as read_file:
            data = json.load(read_file)
        statistics_db = data['statistics_db']
        start_timer = data['start_timer']
        duration_game = data['duration_game']
        completed_puzzles = data['completed_puzzles']
        players = data['players']
        game_on = data['game_on']
        puzzle_text = data['puzzle_text']
        start_text = data['start_text']
        end_text = data['end_text']
        await context.bot.send_message(
            chat_id=adm_chat_id,
            text = "Данные загружены!"
        )
        print(f"{bcolors.YELL}Загрузка из резервной копии завершена.{bcolors.ENDC}")

async def start_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global game_on
    
    if update.effective_chat.id == adm_chat_id and not game_on:
        global start_timer

        start_timer = time.time()
        dgh = duration_game / 3600
        game_on = True
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Начало игры: " + time.ctime(start_timer) + "\nДлительность игры: " + str(int(dgh)) + "часов\n" + how_time_left()
        )
        """Add a job to the queue."""
        time_left = duration_game - (time.time() - start_timer)
        context.job_queue.run_once(alarm, time_left, chat_id=adm_chat_id, name=str(adm_chat_id), data=duration_game)
        await save()
        print(f"{bcolors.YELL}Игра запущена.{bcolors.ENDC}")

async def cid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=update.effective_chat.id
    )

async def report(context, update):
    await context.bot.send_message(
        chat_id=adm_chat_id,
        text="Пользователь @" + str(update.effective_user.username) + " прислал код: " + update.effective_message.text + "\n" + str(statistics())
    )

async def info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id == adm_chat_id:
        await context.bot.send_message(
            chat_id=adm_chat_id,
            text = how_puzzles_completed() + "\n\n" + how_time_left()
        )
        await context.bot.send_message(
            chat_id=adm_chat_id,
            text = statistics()
        )

async def help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id == adm_chat_id:
        await context.bot.send_message(
            chat_id=adm_chat_id,
            text = "/info - текущая статистика\n\n/start_game - запустить обратный отсчёт.\n\n/add_duration ХХХ - добавить ХХХ минут к счётчику, если требуется уменьшить время, то указать -ХХХ минут.  \n\nreset - сброс статистики игры до дефолтной. P.S. всё сотрётся, останется резервная копися, но она перезапишется как только что то в текущей статистике поменяется!\n\n/load - загрузить статистику из резервной копии. Может помочь, если статистика почему то обнулилась, и новые данные в неё ещё не поступали.ОБЯЗАТЕЛЬНО ВЫПОЛНЯТЬ ПРИ ПЕРЕЗАПУСКЕ\n\n /load_timer - возобновление таймера при перезапуске бота. ОБЯЗАТЕЛЬНО ВЫПОЛНЯТЬ ПРИ ПЕРЕЗАПУСКЕ"
        )
    else:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text = "Запутался?\n\nЕсли ты нашёл какой то код, выглядящий так: 123456 - введи его в точности и отправь мне.\n\nЕсли у тебя нет идей где искать, играй в настолки - победитель получает подсказку. Кроме того, я сообщу тебе о каждом случае когда кто то присылает мне код, ты можешь связаться с ним и распросить детали!\n\nЕсли у вас всё ещё остались вопросы - обратись к Ридману(@itugul)."
        )
        await context.bot.send_message(
            chat_id=adm_chat_id,
            text = "@" + update.effective_user.username + " запросил помощи у бота."
        )


#Функции ответа пользователям
#-стартовая вводная
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if game_on:
        for message in start_text:
            if message.startswith('https'):
                await context.bot.send_photo(
                    chat_id=update.effective_chat.id,
                    photo=message
                )
            else:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=message
                )
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="*Добро пожаловать в нашу игру! Действуйте сообща, и вы обязательно выж…кхм ВЫИГРАЕТЕ. Чтобы получить от бота новую информацию, вводите в этот чат коды которые найдёте в ходе своего расследования. Например \" 123456 \" или \" ответ_на_загадку \" . Я сообщу тебе о каждом случае когда кто то присылает мне код, ты можешь связаться с ним и распросить детали! /help - если появятся вопросы.*"
        )
        await user_msg_footer(context, update, rep=False)
    else:
        await game_off_alert(update, context)

async def test(update = Update, context = ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Воу! Вот и пример найденной улики. Поздравляю! Обычно тут будет напоминание текста задания и иногда какая то доп информация."
    )

#Диспетчер ответов
async def dispatcher(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if game_on:
        message_text = update.message.text.lower()
        if message_text == "ответ_на_загадку" or message_text == "123456":
            await test(update, context)
            return
        else:
            puzzle_num = 1
            while puzzle_num <= len(puzzle_text):
                stage_num = 1
                while stage_num < len(puzzle_text[puzzle_num-1]):
                    print(message_text, ' == ', puzzle_text[puzzle_num-1][stage_num][1])
                    if message_text == puzzle_text[puzzle_num-1][stage_num][1].lower():
                        await send_msg(update, context, puzzle_num, stage_num, fin = puzzle_text[puzzle_num-1][stage_num][0]=="fin")
                        return
                    stage_num += 1
                puzzle_num += 1
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Не понимаю о чём ты.")
        await user_msg_footer(context, update, rep=False)
    else:
        await game_off_alert(update, context)

if __name__ == '__main__':
    start_load()
    with open("default_data.json", "r", encoding='utf-8') as read_file:
        data = json.load(read_file)
    adm_chat_id = data['adm_chat_id']
    token = data['token']
    application = ApplicationBuilder().token(token).build()

    #Ответы пользователям:
    start_handler = CommandHandler('start', start)
    handler_test = CommandHandler('123456', test)
    handler_answer_filter = MessageHandler(filters.TEXT & (~filters.COMMAND), dispatcher)

    #Административные
    handler_start_game = CommandHandler('start_game', start_game)
    handler_cid = CommandHandler('cid', cid)
    handler_info = CommandHandler('info', info)
    handler_help = CommandHandler('help', help)
    handler_load = CommandHandler('load', load)
    handler_reset = CommandHandler('reset', reset)
    handler_add_duration = CommandHandler('add_duration', add_duration)
    handler_load_timer = CommandHandler('load_timer', load_timer)

    application.add_handler(handler_answer_filter)
    application.add_handler(handler_load_timer)
    application.add_handler(handler_add_duration)
    application.add_handler(handler_reset)
    application.add_handler(handler_load)
    application.add_handler(handler_help)
    application.add_handler(handler_info)
    application.add_handler(handler_start_game)
    application.add_handler(handler_cid)
    application.add_handler(start_handler)
    application.add_handler(handler_test)
    application.run_polling()
