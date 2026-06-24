from aiohttp import web
import os
import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.exceptions import TelegramBadRequest

# --- НАСТРОЙКИ ---
# Токен вашего бота (получить у @BotFather)
BOT_TOKEN = "8868862012:AAEdg_2eC1QUo32cp9kgmiS2mEmoWDkHPmA"
# ID администратора или ID чата, куда будут приходить анкеты
ADMIN_CHAT_ID = -5532275291
# ------------------

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())


# Состояния для опроса
class Form(StatesGroup):
    role = State()
    current_question = State()


# Данные, требования и вопросы
DATA = {
    "streamer": {
        "title": "🎥 Стример",
        "requirements": (
            "📋 **Требования для Стримеров:**\n"
            "• Возраст 12+\n"
            "• Адекватность и вежливость\n"
            "• Хорошее качество стрима (без сильных лагов)\n"
            "• Название сервера в названии стрима\n"
            "• Голос желательно\n"
            "• Стримить только с нашего сервера\n"
            "• Минимум 1 час стрима"
        ),
        "questions": [
            "1. Никнейм в Minecraft:",
            "2. Возраст:",
            "3. Платформа для стримов (YouTube / Twitch / TikTok):",
            "4. Ссылка на канал:",
            "5. Есть ли микрофон? (Да / Нет):",
            "6. Сколько часов обычно можете стримить?:",
            "7. Согласны стримить только наш сервер? (Да / Нет):",
            "9. Сколько примерно зрителей у вас обычно на стримах?:"
        ]
    },
    "moderator": {
        "title": "🛡️ Модератор",
        "requirements": (
            "📋 **Требования для Модераторов:**\n"
            "• Возраст 13+\n"
            "• Наиграно на сервере минимум 10 часов\n"
            "• Наличие OBS Studio (Steam) для записи нарушений\n"
            "• Адекватность и вежливость\n"
            "• Грамотная речь\n"
            "• Активность на сервере\n"
            "• Хорошее знание правил\n"
            "• Умение решать конфликты\n"
            "• Ответственность и умение работать в команде\n"
            "• Готовность уделять время модерации"
        ),
        "questions": [
            "1. Ваш никнейм:",
            "2. Ваш возраст:",
            "3. Сколько часов у вас наиграно на сервере?:",
            "4. Сколько времени в день вы обычно проводите на сервере?:",
            "5. В какие часы вы чаще всего играете?:",
            "6. Почему хотите стать модератором?:",
            "7. Есть ли у вас опыт модерации? Если да, где?:",
            "8. Хорошо ли вы знаете правила сервера?:",
            "9. Что вы сделаете, если игрок нарушит правила?:",
            "10. Как поступите, если ваш друг нарушит правила?:",
            "11. Как вы реагируете на оскорбления или провокации?:",
            "12. Готовы ли вы помогать новичкам?:",
            "13. Есть ли у вас рабочий Discord и микрофон?:",
            "14. Были ли у вас наказания на нашем сервере? Если да, какие?:",
            "15. Почему именно вас мы должны выбрать модератором?:",
            "16. Готовы ли вы соблюдать правила модерации и выполнять указания администрации?:",
            "17. Есть ли у вас установленный OBS Studio (Steam) и готовы ли вы записывать нарушения?:"
        ]
    },
    "tiktoker": {
        "title": "📝 Тиктокер",
        "requirements": (
            "📋 **Требования для Тиктокеров:**\n"
            "• Возраст 12+\n"
            "• Адекватность и вежливость\n"
            "• Активность на сервере\n"
            "• Умение снимать качественные видео\n"
            "• Без накрутки просмотров, лайков и подписчиков\n"
            "• В каждом видео должно быть название или IP сервера\n"
            "• Минимум 2 видео в неделю"
        ),
        "questions": [
            "1. Никнейм в Minecraft:",
            "2. Возраст:",
            "3. Ссылка на TikTok:",
            "4. Сколько видео в неделю планируешь делать?:",
            "5. Есть ли опыт в монтаже видео? (Да / Нет):",
            "6. Используешь ли ты микрофон для озвучки? (Да / Нет):",
            "7. Среднее количество просмотров на видео (если есть):"
        ]
    }
}


# --- КЛАВИАТУРЫ ---

def get_main_keyboard():
    buttons = [
        [InlineKeyboardButton(text="🎥 Подать на Стримера", callback_data="apply_streamer")],
        [InlineKeyboardButton(text="🛡️ Подать на Модератора", callback_data="apply_moderator")],
        [InlineKeyboardButton(text="📝 Подать на Тиктокера", callback_data="apply_tiktoker")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_admin_keyboard(user_id: int):
    # Кнопки для админ-чата, передающие ID кандидата
    buttons = [
        [
            InlineKeyboardButton(text="✅ Одобрить", callback_data=f"adm_accept_{user_id}"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"adm_decline_{user_id}")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# --- ХЕНДЛЕРЫ КЛИЕНТСКОЙ ЧАСТИ ---

@dp.message(F.text == "/start")
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "👋 **Привет!** Это бот для подачи заявок в команду нашего сервера.\n\n"
        "Выбери роль, на которую хочешь подать анкету 👇",
        reply_markup=get_main_keyboard(),
        parse_mode="Markdown"
    )


@dp.callback_query(F.data.startswith("apply_"))
async def process_apply(callback: CallbackQuery, state: FSMContext):
    role = callback.data.split("_")[1]

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Я подхожу, начать", callback_data=f"start_survey_{role}")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")]
    ])

    await callback.message.edit_text(
        f"{DATA[role]['requirements']}\n\n"
        "✨ *Пожалуйста, внимательно ознакомься с требованиями. Если ты подходишь — нажимай кнопку ниже!*",
        reply_markup=kb,
        parse_mode="Markdown"
    )
    await callback.answer()


@dp.callback_query(F.data == "cancel")
async def process_cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("✨ Подача анкеты отменена. Ты можешь начать заново в любое время: /start")
    await callback.answer()


@dp.callback_query(F.data.startswith("start_survey_"))
async def start_survey(callback: CallbackQuery, state: FSMContext):
    role = callback.data.split("_")[2]
    await state.update_data(role=role, answers=[], current_q_index=0)

    first_question = DATA[role]['questions'][0]
    await callback.message.edit_text(
        f"📝 **Вопрос 1 из {len(DATA[role]['questions'])}**\n\n*{first_question}*",
        parse_mode="Markdown"
    )
    await state.set_state(Form.current_question)
    await callback.answer()


@dp.message(Form.current_question)
async def process_question(message: Message, state: FSMContext):
    # Ограничение: защита от отправки медиафайлов вместо текста
    if not message.text:
        await message.answer("⚠️ Пожалуйста, введи ответ текстом (без картинок, стикеров и файлов).")
        return

    # Ограничение: защита от спама слишком длинными сообщениями (макс. 400 символов)
    if len(message.text) > 400:
        await message.answer("⚠️ Твой ответ слишком длинный (максимум 400 символов). Пожалуйста, напиши короче.")
        return

    user_data = await state.get_data()
    role = user_data['role']
    q_index = user_data['current_q_index']
    answers = user_data['answers']

    # --- ПРОВЕРКА ВОЗРАСТА (Второй вопрос во всех анкетах, индекс = 1) ---
    if q_index == 1:
        age_text = message.text.strip()

        # Проверка, что введены исключительно цифры
        if not age_text.isdigit():
            await message.answer(
                "⚠️ Ошибка! В поле 'Возраст' нужно ввести **только цифры** (например: 14). Попробуй еще раз:")
            return

        age = int(age_text)
        min_age = 13 if role == "moderator" else 12  # Для модераторов 13+, для остальных 12+

        # Жесткий отсев по возрасту без отправки анкеты админам
        if age < min_age:
            await message.answer(
                f"❌ **Подача заявки отклонена.**\n"
                f"К сожалению, вы слишком малы для этой должности. Минимальный возраст для роли {DATA[role]['title']} — **{min_age}+**.\n"
                f"Будем рады видеть вашу заявку позже! 😉"
            )
            await state.clear()
            return
    # ---------------------------------------------------------------------

    current_question_text = DATA[role]['questions'][q_index]
    # Экранируем спецсимволы Markdown, чтобы ответы пользователей не ломали верстку в админке
    clean_text = message.text.replace("_", "\\_").replace("*", "\\*").replace("`", "\\`")
    answers.append((current_question_text, clean_text))

    next_q_index = q_index + 1

    if next_q_index < len(DATA[role]['questions']):
        await state.update_data(answers=answers, current_q_index=next_q_index)
        next_question_text = DATA[role]['questions'][next_q_index]
        await message.answer(
            f"📝 **Вопрос {next_q_index + 1} из {len(DATA[role]['questions'])}**\n\n*{next_question_text}*",
            parse_mode="Markdown"
        )
    else:
        # Анкета успешно заполнена
        username = f"@{message.from_user.username}" if message.from_user.username else "Нет юзернейма"
        user_id = message.from_user.id
        full_name = message.from_user.full_name.replace("_", "\\_").replace("*", "\\*")

        # Красивый уютный шаблон для админ-группы
        summary = f"⚡️ **НОВАЯ ЗАЯВКА НА РАССМОТРЕНИЕ!**\n"
        summary += f"━━━━━━━━━━━━━━━━━━━━\n"
        summary += f"• **Должность:** {DATA[role]['title']}\n"
        summary += f"• **Кандидат:** {full_name} ({username})\n"
        summary += f"• **ID:** `{user_id}`\n"
        summary += f"━━━━━━━━━━━━━━━━━━━━\n"
        summary += "📋 **ОТВЕТЫ КАНДИДАТА:**\n"

        for q, a in answers:
            summary += f"\n❓ *{q}*\n💬 {a}\n"

        try:
            # Отправляем в чат администрации с интерактивными кнопками вердикта
            await bot.send_message(
                chat_id=ADMIN_CHAT_ID,
                text=summary,
                parse_mode="Markdown",
                reply_markup=get_admin_keyboard(user_id)
            )
            await message.answer(
                "🎉 **Ваша анкета успешно отправлена администрации!**\n"
                "Она будет рассмотрена в ближайшее время. В случае одобрения бот напишет вам сюда. Удачи! ✨"
            )
        except Exception as e:
            await message.answer(
                "❌ Произошла ошибка при отправке анкеты админу. Пожалуйста, обратитесь к создателю бота.")
            print(f"Ошибка отправки заявки: {e}")

        await state.clear()


# --- ОБРАБОТКА РЕШЕНИЙ АДМИНИСТРАЦИИ ---

@dp.callback_query(F.data.startswith("adm_accept_"))
async def admin_accept(callback: CallbackQuery):
    target_user_id = int(callback.data.split("_")[2])
    admin_name = callback.from_user.full_name

    # Отправляем уведомление кандидату в ЛС
    try:
        await bot.send_message(
            chat_id=target_user_id,
            text="🎉 **Поздравляем! Твоя заявка была успешно одобрена!**\n"
                 "Совсем скоро с тобой свяжется администратор для уточнения деталей. Добро пожаловать в команду! 🚀"
        )
        user_notified = "Уведомление отправлено"
    except TelegramBadRequest:
        user_notified = "❌ Не удалось уведомить (бот заблокирован)"

    # Обновляем сообщение в группе (убираем кнопки и пишем вердикт)
    updated_text = callback.message.text + f"\n\n🟢 **РЕШЕНИЕ:** Одобрен\n• **Администратор:** {admin_name}\n• ({user_notified})"
    try:
        await callback.message.edit_text(text=updated_text, reply_markup=None)
    except Exception as e:
        print(f"Ошибка обновления сообщения: {e}")

    await callback.answer("Кандидат одобрен!")


@dp.callback_query(F.data.startswith("adm_decline_"))
async def admin_decline(callback: CallbackQuery):
    target_user_id = int(callback.data.split("_")[2])
    admin_name = callback.from_user.full_name

    # Отправляем уведомление кандидату в ЛС
    try:
        await bot.send_message(
            chat_id=target_user_id,
            text="😔 **К сожалению, твоя заявка была отклонена.**\n"
                 "Не расстраивайся! Ты можешь подтянуть свои навыки, набрать больше часов на сервере и попробовать подать заявку позже."
        )
        user_notified = "Уведомление отправлено"
    except TelegramBadRequest:
        user_notified = "❌ Не удалось уведомить (бот заблокирован)"

    # Обновляем сообщение в группе (убираем кнопки и пишем вердикт)
    updated_text = callback.message.text + f"\n\n🔴 **РЕШЕНИЕ:** Отклонен\n• **Администратор:** {admin_name}\n• ({user_notified})"
    try:
        await callback.message.edit_text(text=updated_text, reply_markup=None)
    except Exception as e:
        print(f"Ошибка обновления сообщения: {e}")

    await callback.answer("Кандидат отклонен.")


# --- ЗАПУСК БОТА ---

# --- ДОБАВЛЯЕМ ЭТИ ДВЕ ФУНКЦИИ ДЛЯ РАБОТЫ НА RENDER ---
async def handle(request):
    return web.Response(text="Бот работает!")

async def start_web_server():
    app = web.Application()
    app.router.add_get('/', handle)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()


# --- ТВОЯ ФУНКЦИЯ MAIN (ДОБАВЛЯЕМ В НЕЁ ОДНУ СТРОКУ) ---
async def main():
    # ... тут остается весь твой прежний код (создание bot, dp и т.д.) ...
    
    # Перед самым стартом поллинга вызываем запуск веб-сервера:
    await start_web_server()
    
    print("Бот успешно запущен и готов к работе!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
