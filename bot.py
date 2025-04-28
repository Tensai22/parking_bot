import asyncio
import random
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
from sqlalchemy.future import select
import config
from database import async_session
from models import ParkingSpot, User
from datetime import datetime, timedelta, timezone
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from typing import Optional
from sqlalchemy import func 

bot = Bot(token=config.BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Главное меню
main_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📍 Найти парковку")],
        [KeyboardButton(text="🎲 Ближайшая парковка")],
        [KeyboardButton(text="💳 Оплатить парковку")],
        [KeyboardButton(text="🚘 Мои парковки")]
    ],
    resize_keyboard=True
)


class RegistrationState(StatesGroup):
    waiting_for_car_number = State()


class PaymentState(StatesGroup):
    processing_payment = State()


@dp.message(Command("start"))
async def start(message: types.Message, state: FSMContext):
    tg_id = str(message.from_user.id)

    async with async_session() as session:
        result = await session.execute(select(User).where(User.tg_id == tg_id))
        user = result.scalars().first()

    if not user:
        user = User(tg_id=tg_id, balance=0)
        async with async_session() as session:
            session.add(user)
            await session.commit()

    if not user.car_number:
        await message.answer("🚗 Добро пожаловать! Для продолжения укажите номер вашего автомобиля:")
        await state.set_state(RegistrationState.waiting_for_car_number)
    else:
        await message.answer("🚗 Привет! Вы успешно вошли в систему.\nВыберите действие:", reply_markup=main_kb)


@dp.message(RegistrationState.waiting_for_car_number)
async def process_car_number(message: types.Message, state: FSMContext):
    car_number = message.text.strip()

    async with async_session() as session:
        result = await session.execute(select(User).where(User.tg_id == str(message.from_user.id)))
        user = result.scalars().first()

        if user:
            user.car_number = car_number
            session.add(user)
            await session.commit()

            await message.answer(f"✅ Ваш номер авто сохранён: {car_number}\nТеперь вы можете пользоваться ботом.",
                                 reply_markup=main_kb)
            await state.clear()


async def get_parking_spots():
    async with async_session() as session:
        result = await session.execute(
            select(ParkingSpot)
            .where(
                ParkingSpot.available == True,
                ParkingSpot.free_spaces > 0,
                ParkingSpot.parent_spot_id == None  # Только основные парковки
            )
        )
        return result.scalars().all()


async def get_user_id(session, tg_id: str) -> Optional[int]:
    result = await session.execute(select(User.id).where(User.tg_id == tg_id))
    return result.scalar()


async def get_or_create_user(tg_id):
    async with async_session() as session:
        user = await session.execute(select(User).where(User.tg_id == str(tg_id)))
        user = user.scalars().first()

        if not user:
            new_user = User(tg_id=str(tg_id), balance=0)
            session.add(new_user)
            await session.commit()
            return new_user, True
        return user, False


async def get_random_parking():
    parking_spots = await get_parking_spots()
    return random.choice(parking_spots) if parking_spots else None


@dp.message(F.text == "📍 Найти парковку")
async def find_parking(message: types.Message):
    await get_or_create_user(message.from_user.id)
    parking_spots = await get_parking_spots()

    if not parking_spots:
        await message.answer("🚗 Свободных парковок нет.")
        return

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"🏁 {spot.location} - {spot.price_per_hour} ₸/час ({spot.free_spaces} мест)",
                              callback_data=f"select_parking_{spot.id}")] for spot in parking_spots
    ])
    await message.answer("🔍 Выберите парковку:", reply_markup=keyboard)


@dp.message(F.text == "🎲 Ближайшая парковка")
async def nearest_parking(message: types.Message):
    await get_or_create_user(message.from_user.id)
    parking_spot = await get_random_parking()

    if not parking_spot:
        await message.answer("🚗 Свободных парковок нет.")
        return

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Выбрать", callback_data=f"select_parking_{parking_spot.id}")]
    ])

    await message.answer(
        f"🎲 Вам выпала парковка:\n🏁 {parking_spot.location}\n💰 Цена: {parking_spot.price_per_hour} ₸/час\n🚗 Свободных мест: {parking_spot.free_spaces}",
        reply_markup=keyboard
    )


@dp.message(F.text.lower().strip() == "🚘 мои парковки")
async def my_parkings(message: types.Message):
    tg_id = str(message.from_user.id)

    async with async_session() as session:
        user_id = await get_user_id(session, tg_id)
        if not user_id:
            await message.answer("❌ Ошибка: пользователь не найден.")
            return

        now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
        result = await session.execute(
            select(ParkingSpot).where(
                ParkingSpot.user_id == user_id,
                ParkingSpot.end_time > now_utc,
                ParkingSpot.parent_spot_id.is_not(None)  # Только занятые места
            )
        )
        active_parkings = result.scalars().all()

        if not active_parkings:
            await message.answer("🚗 У вас нет активных парковок.")
            return

        response = "🅿️ **Ваши активные парковки:**\n\n"
        for parking in active_parkings:
            end_time_utc = parking.end_time
            remaining_minutes = int((end_time_utc - now_utc).total_seconds() // 60)
            response += (
                f"🏁 **Локация**: {parking.location}\n"
                f"💰 **Цена**: {parking.price_per_hour} ₸/час\n"
                f"⏳ **Окончание**: {end_time_utc.strftime('%H:%M')} UTC\n"
                f"🕒 Осталось: {remaining_minutes} мин\n\n"
            )
        await message.answer(response, parse_mode="Markdown")


@dp.callback_query(F.data.startswith("select_parking_"))
async def select_parking(callback: types.CallbackQuery, state: FSMContext):
    user, is_new = await get_or_create_user(callback.from_user.id)

    if is_new:
        await state.update_data(tg_id=str(callback.from_user.id))
        await callback.message.answer("🚗 Введите номер вашего авто для завершения регистрации:")
        await state.set_state(RegistrationState.waiting_for_car_number)
        return

    parking_id = int(callback.data.split("_")[-1])

    async with async_session() as session:
        parking_spot = await session.get(ParkingSpot, parking_id)

    if not parking_spot or not parking_spot.available or parking_spot.free_spaces <= 0:
        await callback.message.answer("🚗 Эта парковка уже занята.")
        return

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Оплатить 1 час", callback_data=f"pay_parking_{parking_id}")]
    ])

    await callback.message.answer(
        f"Вы выбрали парковку:\n🏁 {parking_spot.location}\n💰 Цена: {parking_spot.price_per_hour} ₸/час\n🚗 Свободных мест: {parking_spot.free_spaces}",
        reply_markup=keyboard
    )

    await state.set_state(PaymentState.processing_payment)
    await state.update_data(parking_id=parking_id)


@dp.callback_query(F.data.startswith("pay_parking_"))
async def pay_parking(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    parking_id = int(callback.data.split("_")[-1])

    async with async_session() as session:
        async with session.begin():
            # Получаем пользователя и парковку
            user = await session.execute(
                select(User).where(User.tg_id == str(user_id))
            )
            user = user.scalars().first()

            parking_spot = await session.execute(
                select(ParkingSpot)
                .where(ParkingSpot.id == parking_id)
                .with_for_update()
            )
            parking_spot = parking_spot.scalars().first()

            if not user or not parking_spot:
                await callback.message.answer("❌ Произошла ошибка.")
                return

            # Проверяем доступность
            if parking_spot.free_spaces <= 0:
                await callback.message.answer("❌ Это место уже занято!")
                return

            if user.balance < parking_spot.price_per_hour:
                await callback.message.answer("❌ Недостаточно средств на балансе!")
                return

            # Обновляем данные
            parking_spot.free_spaces -= 1
            if parking_spot.free_spaces <= 0:
                parking_spot.available = False

            user.balance -= parking_spot.price_per_hour
            now = datetime.now(timezone.utc).replace(tzinfo=None)
            end_time = (now + timedelta(hours=1)).replace(tzinfo=None)

            # Создаем новую запись о занятом месте
            new_parking = ParkingSpot(
                location=parking_spot.location,
                price_per_hour=parking_spot.price_per_hour,
                available=False,
                free_spaces=0,  # Конкретное занятое место
                start_time=now,
                end_time=end_time,
                user_id=user.id,
                parent_spot_id=parking_spot.id  # Связь с основной парковкой
            )
            session.add(new_parking)

    await callback.message.answer(
        f"✅ Оплата успешна! Вы запарковались на {parking_spot.location}.\n"
        f"🕒 Время окончания: {end_time.strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"Остаток на балансе: {user.balance} ₸"
    )


async def release_parking_if_not_paid(parking_id: int, timeout: int):
    await asyncio.sleep(timeout)
    async with async_session() as session:
        parking = await session.get(ParkingSpot, parking_id)
        if parking and not parking.start_time:
            parking.free_spaces += 1
            await session.commit()


async def check_parking_expiration():
    """Фоновая задача для проверки и освобождения истекших парковок"""
    while True:
        async with async_session() as session:
            async with session.begin():
                now = datetime.now(timezone.utc)

                # Находим все истекшие занятые парковочные места
                expired_spots = await session.execute(
                    select(ParkingSpot)
                    .where(
                        func.timezone('UTC', ParkingSpot.end_time) <= now,
                ParkingSpot.parent_spot_id.is_not(None)
                )
                .with_for_update()
            )   
                expired_spots = expired_spots.scalars().all()

                for spot in expired_spots:
                    # Получаем родительскую парковку
                    parent = await session.get(
                        ParkingSpot,
                        spot.parent_spot_id,
                        with_for_update=True
                    )

                    if parent:
                        # Возвращаем свободное место
                        parent.free_spaces += 1
                        if not parent.available:
                            parent.available = True
                        session.add(parent)

                    # Уведомляем пользователя
                    user = await session.get(User, spot.user_id)
                    if user:
                        await bot.send_message(
                            user.tg_id,
                            f"⌛ Время парковки истекло: {spot.location}"
                        )

                    # Удаляем запись о занятом месте
                    await session.delete(spot)

                await session.commit()

        # Проверяем каждую минуту
        await asyncio.sleep(60)


async def main():
    asyncio.create_task(check_parking_expiration())
    await bot.delete_webhook(drop_pending_updates=True)
    asyncio.create_task(check_parking_expiration())
    print("Бот запущен и слушает сообщения...")
    await dp.start_polling(bot)



if __name__ == "__main__":
    asyncio.run(main())