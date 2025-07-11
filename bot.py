import logging
import asyncio
from aiogram import Bot, Dispatcher, types, Router, F
from aiogram.filters import Command
import aiohttp
from aiogram.exceptions import TelegramBadRequest
import aiosqlite
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from aiogram.utils.keyboard import InlineKeyboardBuilder
from datetime import datetime
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from dotenv import load_dotenv
import os

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
YANDEX_API_KEY = os.getenv("YANDEX_API_KEY")
FOLDER_ID = os.getenv("FOLDER_ID")



bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()

logging.basicConfig(level=logging.INFO)
db_path = "ege_bot_db.db"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IMAGES_DIR = os.path.join(BASE_DIR, "assets", "images")
FILES_DIR = os.path.join(BASE_DIR, "assets", "files")
router = Router()
class AdminStates(StatesGroup):
    waiting_for_task_text = State()
    waiting_for_image_confirm = State()
    waiting_for_image = State()
    waiting_for_file_confirm = State()
    waiting_for_file = State()
    browsing_tasks = State()
class TestStates(StatesGroup):
    testing = State()
    questions = State()
    current = State()
    answers = State()
# Кнопка для старта
def get_keyboard():
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔍 Задача от ИИ", callback_data="get_task")],
            [InlineKeyboardButton(text="🎁 Подарок", callback_data="gift")],
            [InlineKeyboardButton(text="📌 Тренировка одного номера", callback_data="select_task")],
            [InlineKeyboardButton(text="📋 Тренировочный вариант", callback_data="train_variant")],
            [InlineKeyboardButton(text="📈 Мои результаты", callback_data="results")]
            # [InlineKeyboardButton(text="🛍 Товары", callback_data="tovars")]
        ]
    )
    return keyboard
def get_admin_keyboard():
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➕Добавить задачу", callback_data="add_task")],
            [InlineKeyboardButton(text="❌Удалить задачу", callback_data="delete_task")],
            [InlineKeyboardButton(text="🔙 Назад в меню", callback_data="go_back")]

        ]
    )
    return keyboard
def yes_no_keyboard(callback_prefix):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Да", callback_data=f"{callback_prefix}_yes"),
                InlineKeyboardButton(text="❌ Нет", callback_data=f"{callback_prefix}_no")
            ]
        ]
    )
def back_or_add_more_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_back")],
            [InlineKeyboardButton(text="➕ Добавить ещё", callback_data="add_task")]
        ]
    )

# Кнопка "Назад"
def get_back_keyboard():
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data="go_back")]
        ]
    )
    return keyboard
def get_retry_keyboard():
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Новая задача", callback_data="get_task")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="go_back")]
        ]
    )
    return keyboard

async def is_user_subscribed(bot, channel_id: str, user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id=channel_id, user_id=user_id)
        return member.status in ['member', 'administrator', 'creator']
    except TelegramBadRequest:
        return False
# добавление задачи у админа
@router.callback_query(F.data == "add_task")
async def add_task_start(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Отправьте текст задачи в формате\n НОМЕР ЗАДАЧИ В КИМ@ ТЕКСТ ЗАДАЧИ @ОТВЕТ НА ЗАДАЧУ")
    await state.set_state(AdminStates.waiting_for_task_text)
    await callback.answer()
@router.message(AdminStates.waiting_for_task_text)
async def add_task_text(message: Message, state: FSMContext):
    await state.update_data(task_text=message.text)
    await message.answer(
        "Есть ли изображение для задачи?",
        reply_markup=yes_no_keyboard("image")
    )
    await state.set_state(AdminStates.waiting_for_image_confirm)
@router.callback_query(AdminStates.waiting_for_image_confirm)
async def confirm_image(callback: CallbackQuery, state: FSMContext):
    if callback.data == "image_yes":
        await callback.message.answer("Пришлите изображение (файл или фото):")
        await state.set_state(AdminStates.waiting_for_image)
    else:
        await state.update_data(image_name=None)
        await callback.message.answer(
            "Есть ли файл для задачи?",
            reply_markup=yes_no_keyboard("file")
        )
        await state.set_state(AdminStates.waiting_for_file_confirm)
    await callback.answer()
import os

@router.message(AdminStates.waiting_for_image, F.photo | F.document)
async def save_image(message: Message, state: FSMContext):
    if message.photo:
        file = message.photo[-1]
        file_id = file.file_id
        ext = ".jpg"
    elif message.document:
        file = message.document
        file_id = file.file_id
        ext = os.path.splitext(file.file_name)[-1]
    else:
        await message.answer("Это не изображение.")
        return

    filename = f"{file_id}{ext}"
    path = os.path.join(IMAGES_DIR, filename)
    # path = f"assets/images/{filename}"
    await bot.download(file, destination=path)

    await state.update_data(image_name=filename)

    await message.answer(
        "Есть ли файл для задачи?",
        reply_markup=yes_no_keyboard("file")
    )
    await state.set_state(AdminStates.waiting_for_file_confirm)
@router.callback_query(AdminStates.waiting_for_file_confirm)
async def confirm_file(callback: CallbackQuery, state: FSMContext):
    if callback.data == "file_yes":
        await callback.message.answer("Пришлите файл:")
        await state.set_state(AdminStates.waiting_for_file)
    else:
        await state.update_data(file_name=None)
        await save_task_to_db(callback.message, state)
    await callback.answer()
@router.message(AdminStates.waiting_for_file, F.document)
async def save_file(message: Message, state: FSMContext):
    doc = message.document
    filename = doc.file_name
    path = os.path.join(FILES_DIR, filename)
    # path = f"assets/files/{filename}"
    await bot.download(doc, destination=path)

    await state.update_data(file_name=filename)
    await save_task_to_db(message, state)
async def save_task_to_db(message: Message, state: FSMContext):
    data = await state.get_data()
    task_text = data["task_text"]
    image_name = data.get("image_name")
    file_name = data.get("file_name")
    task_text = task_text.split("@")
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            "INSERT INTO Tasks (num, text, image, file, answer) VALUES (?, ?, ?, ?, ?)",
            (task_text[0],task_text[1], image_name, file_name, task_text[2])
        )
        await db.commit()

    await message.answer(
        "Задача успешно добавлена!",
        reply_markup=back_or_add_more_keyboard()
    )
    await state.clear()
# удалить задачу
@router.callback_query(F.data == "delete_task")
async def delete_task_start(callback: CallbackQuery, state: FSMContext):
    kb = InlineKeyboardBuilder()
    for i in range(1, 28):
        kb.button(text=f"Задание {i}", callback_data=f"browse_{i}")
    kb.adjust(3)
    await callback.message.answer("Выберите номер задания:", reply_markup=kb.as_markup())
    await callback.answer()
@router.callback_query(F.data.startswith("browse_"))
async def browse_tasks(callback: CallbackQuery, state: FSMContext):
    num = int(callback.data.split("_")[1])

    async with aiosqlite.connect(db_path) as db:
        cursor = await db.execute(
            "SELECT id, text FROM Tasks WHERE num = ? ORDER BY id",
            (num,)
        )
        tasks = await cursor.fetchall()

    if not tasks:
        await callback.message.answer("Нет задач для этого номера.")
        return

    await state.update_data(tasks=tasks, idx=0)
    await state.set_state(AdminStates.browsing_tasks)
    await show_task(callback.message, state)
    await callback.answer()

async def show_task(message: Message, state: FSMContext):
    data = await state.get_data()
    task = data["tasks"][data["idx"]]

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="⬅️", callback_data="prev_task"),
                InlineKeyboardButton(text="➡️", callback_data="next_task")
            ],
            [
                InlineKeyboardButton(text="🗑️ Удалить", callback_data="delete_this_task"),
                InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_back")
            ]
        ]
    )
    await message.answer(f"ID: {task[0]}\nТекст: {task[1]}", reply_markup=kb)
@router.callback_query(AdminStates.browsing_tasks, F.data == "prev_task")
async def prev_task(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    idx = max(0, data["idx"] - 1)
    await state.update_data(idx=idx)
    await show_task(callback.message, state)
    await callback.answer()

@router.callback_query(AdminStates.browsing_tasks, F.data == "next_task")
async def next_task(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    idx = min(len(data["tasks"]) - 1, data["idx"] + 1)
    await state.update_data(idx=idx)
    await show_task(callback.message, state)
    await callback.answer()

@router.callback_query(AdminStates.browsing_tasks, F.data == "delete_this_task")
async def delete_this_task(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    task = data["tasks"][data["idx"]]
    task_id = task[0]

    async with aiosqlite.connect(db_path) as db:
        await db.execute("DELETE FROM Tasks WHERE id = ?", (task_id,))
        await db.commit()

    await callback.message.answer(f"Задача ID {task_id} удалена.", reply_markup=get_admin_keyboard())
    await state.clear()
    await callback.answer()
@router.callback_query(F.data == "admin_back")
async def admin_back(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.answer(
        "Возврат в админ-панель:",
        reply_markup=get_admin_keyboard()
    )
    await callback.answer()

# Показать 27 заданий
@router.callback_query(F.data == "select_task")
async def select_task(callback: CallbackQuery):
    kb = InlineKeyboardBuilder()
    for i in range(1, 28):
        kb.button(text=f"Задание {i}", callback_data=f"task_{i}")
    kb.adjust(3)
    await callback.message.answer("Выберите задание:", reply_markup=kb.as_markup())
    await callback.answer()
# --- Начать тест ---
@router.callback_query(F.data.startswith("task_"))
async def start_task(callback: CallbackQuery, state: FSMContext):
    num = int(callback.data.split("_")[1])
    user_id = callback.from_user.id

    async with aiosqlite.connect(db_path) as db:
        cursor = await db.execute(
            "SELECT id, text, answer,  image, file FROM Tasks WHERE num = ? ORDER BY RANDOM() LIMIT 10",
            (num,)
        )
        questions = await cursor.fetchall()

    if not questions:
        await callback.message.answer("Для этого задания пока нет вопросов.",reply_markup=get_back_keyboard())
        await callback.answer()
        return

    await state.update_data(
        mode="task",
        num=num,
        questions=questions,
        current=0,
        answers=[]
    )
    await state.set_state(TestStates.testing)
    await send_next_question(callback.message, state)
    await callback.answer()


@router.callback_query(F.data == "train_variant")
async def start_train_variant(callback: CallbackQuery, state: FSMContext):
    async with aiosqlite.connect(db_path) as db:
        cursor = await db.execute("""
            SELECT id, text, answer, num, image, file 
            FROM Tasks 
            WHERE num BETWEEN 1 AND 27
            GROUP BY num
        """)
        questions = await cursor.fetchall()

    if not questions:
        await callback.message.answer("Нет вопросов для тренировочного варианта.")
        return

    await state.update_data(
        mode="train_variant",
        questions=questions,
        current=0,
        answers=[]
    )
    await state.set_state(TestStates.testing)
    await send_next_question(callback.message, state)
    await callback.answer()
# --- Отправить следующий вопрос ---
async def send_next_question(message: Message, state: FSMContext):
    data = await state.get_data()
    current = data["current"]
    questions = data["questions"]

    if current >= len(questions):
        print(state)
        await show_results(message, state)
        return

    q = questions[current]
    if data["mode"] == "train_variant":
        num = q[3]
        text = f"Задание {num}:\n{q[1]}"
    else:
        text = f"Вопрос {current + 1}:\n{q[1]}"
    await message.answer(text,reply_markup=get_back_keyboard())
    if q[3]:
        print(f"assets/images/{q[3]}")
        photo = FSInputFile(f"{IMAGES_DIR}/{q[3]}")
        await message.answer_photo(photo)
    if q[4]:
        print(f"assets/files/{q[4]}")
        file = FSInputFile(f"{FILES_DIR}/{q[4]}")
        await message.answer_document(file)

@router.message(TestStates.testing)
async def handle_answer(message: Message, state: FSMContext):
    data = await state.get_data()
    answers = data["answers"]
    answers.append(message.text.strip())
    await state.update_data(answers=answers, current=data["current"] + 1)

    await send_next_question(message, state)
# --- Показать результат ---
async def show_results(message: Message, state: FSMContext):
    data = await state.get_data()
    questions = data["questions"]
    answers = data["answers"]
    points_table = {0:0, 1: 7, 2: 14, 3: 20, 4: 27, 5: 34, 6: 40, 7: 43, 8: 46, 9: 48, 10: 51, 11: 54, 12: 56, 13: 59, 14: 62, 15: 64, 16: 67, 17: 70, 18: 72, 19: 75, 20: 78, 21: 80, 22: 83, 23: 85, 24: 88, 25: 90, 26: 93, 27: 95, 28: 98, 29: 100}
    table = "Ваш ответ | Верный ответ\n"
    correct = 0

    for idx, q in enumerate(questions):
        user_ans = answers[idx]
        true_ans = q[2]
        table += f"{user_ans} | {true_ans}\n"
        if user_ans.lower() == true_ans.lower():
            correct += 1
            print(idx)
    points = points_table[correct]

    await message.answer(f"{table}\nРезультат: {correct} из {len(questions)} баллов:{points}",reply_markup=get_back_keyboard())

    async with aiosqlite.connect(db_path) as db:
        date = datetime.now().strftime("%Y-%m-%d %H:%M")
        if data["mode"] == "train_variant":
            row = f"{date} Тренировочный вариант: {correct} из {len(questions)} баллов: {points}"
        else:
            row = f"{date} Задание {data['num']}: {correct} из {len(questions)}"

        await db.execute(
            "INSERT INTO Users (user_id, user_results) VALUES (?, ?) "
            "ON CONFLICT(user_id) DO UPDATE SET user_results = user_results || '\n' || ?",
            (message.from_user.id, row, row)
        )
        await db.commit()

    await state.clear()


@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "Привет! Выбери нужную тебе кнопку:",
        reply_markup=get_keyboard()
    )
@dp.message(F.from_user.id == ADMIN_ID, F.text.startswith("/admin"))
async def cmd_admin(message: types.Message):
    # print(F.from_user.id)
    await message.answer(
        "Привет! Это панель админа",
        reply_markup=get_admin_keyboard()
    )
@dp.callback_query(lambda c: c.data == "gift")
async def signup(callback: types.CallbackQuery, bot):
    user = callback.from_user
    CHANNEL_ID = -1002027633415
    if await is_user_subscribed(bot, CHANNEL_ID, user.id):
        msg = "🎁 Держите подарок"
        await callback.message.answer(msg)
        await callback.message.answer_document(
            types.FSInputFile("Прогнозный вариант 2025.pdf"), reply_markup=get_back_keyboard()
        )
        await callback.answer()
    else:
        msg = "Для получения подарка подпишитесь на канал.\nhttp://t.me/ege_infa_astpva"

        await callback.message.answer(msg, reply_markup=get_back_keyboard())
        await callback.answer()
    # await callback_query.message.answer(reply_markup=get_back_keyboard())

@dp.callback_query(lambda c: c.data == "results")
async def signup(callback: types.CallbackQuery, bot):
    # print(callback.from_user.id)
    async with aiosqlite.connect(db_path) as db:
        cursor = await db.execute("""
            SELECT user_id, user_results 
            FROM USERS 
            WHERE user_id = ?
        """, (callback.from_user.id,) )

        results = await cursor.fetchall()
        if results:
            results = results[0][1]
        else:
            results = "Вы еще не проходили тесты"

    await callback.message.answer(results, reply_markup=get_back_keyboard())
    await callback.answer()

def escape_md(text: str) -> str:
    # Экранируем спецсимволы MarkdownV2
    escape_chars = r"_*[]()~`>#+-={}.!"
    return ''.join(['\\' + c if c in escape_chars else c for c in text])

@dp.callback_query(lambda c: c.data == "get_task")
async def process_callback(callback: types.CallbackQuery):
    await callback.message.answer("Генерирую задачу...")

    # Генерируем запрос к ЯндексGPT
    prompt = "Сгенерируй новую базовую задачу по программированию на python и дай сразу ответ на неё."
    try:
        response = await get_gpt_response(prompt)
        response = escape_md(response)
        # print(response)
        await callback.message.answer(response, reply_markup=get_retry_keyboard(), parse_mode="MarkdownV2")
        await callback.answer()
    except:
        await callback.message.answer("Какая\\-то техническая неполадка, попробуйте еще раз", reply_markup=get_retry_keyboard(), parse_mode="MarkdownV2")
        await callback.answer()
async def get_gpt_response(prompt):
    url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"

    headers = {
        "Authorization": f"Api-Key {YANDEX_API_KEY}",
        "Content-Type": "application/json"
    }

    json_data = {
        "modelUri": f"gpt://{FOLDER_ID}/yandexgpt/latest",
        "completionOptions": {
            "stream": False,
            "temperature": 0.7,
            "maxTokens": 200
        },
        "messages": [
            {"role": "system", "text": "Ты — генератор интересных задач."},
            {"role": "user", "text": prompt}
        ]
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=json_data) as resp:
                result = await resp.json()
                answer = result["result"]["alternatives"][0]["message"]["text"].split("Ответ")[1]
                return result["result"]["alternatives"][0]["message"]["text"].split("Ответ")[0] + f"|| **Ответ {answer} ||"
    except:
        return "Какая\\-\\то техническая неполадка, попробуйте еще раз"
@dp.callback_query(lambda c: c.data == "go_back")
async def go_back(callback_query: types.CallbackQuery):
    await callback_query.answer("Возвращаюсь назад...")
    await callback_query.message.answer(
        "Меню:",
        reply_markup=get_keyboard()
    )



async def main():
    await dp.start_polling(bot)


if __name__ == '__main__':
    dp.include_router(router)
    asyncio.run(main())
