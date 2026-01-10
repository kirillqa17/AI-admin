"""
Telegram Inline Keyboards for slot selection and other interactions
"""

from typing import List, Dict, Any
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def create_time_slots_keyboard(
    slots: List[Dict[str, Any]],
    date: str,
    service_id: str
) -> InlineKeyboardMarkup:
    """
    Создает клавиатуру с доступными слотами времени

    Args:
        slots: Список слотов с полями time, employee_id, employee_name
        date: Дата в формате YYYY-MM-DD
        service_id: ID услуги

    Returns:
        InlineKeyboardMarkup с кнопками слотов
    """
    builder = InlineKeyboardBuilder()

    for slot in slots:
        time = slot.get("time", slot.get("start_time", ""))
        employee_id = slot.get("employee_id", "")
        employee_name = slot.get("employee_name", "")

        # Формат кнопки: "14:00 (Мастер)"
        button_text = f"{time}"
        if employee_name:
            button_text += f" ({employee_name})"

        # Callback data: slot:{date}:{time}:{employee_id}:{service_id}
        callback_data = f"slot:{date}:{time}:{employee_id}:{service_id}"

        builder.button(
            text=button_text,
            callback_data=callback_data[:64]  # Max callback_data length
        )

    # 3 buttons per row
    builder.adjust(3)

    # Add cancel button
    builder.row(
        InlineKeyboardButton(
            text="❌ Отмена",
            callback_data="cancel_booking"
        )
    )

    return builder.as_markup()


def create_dates_keyboard(
    dates: List[str],
    service_id: str
) -> InlineKeyboardMarkup:
    """
    Создает клавиатуру с доступными датами

    Args:
        dates: Список дат в формате YYYY-MM-DD
        service_id: ID услуги

    Returns:
        InlineKeyboardMarkup с кнопками дат
    """
    builder = InlineKeyboardBuilder()

    # Словарь дней недели
    weekdays = {
        0: "Пн", 1: "Вт", 2: "Ср",
        3: "Чт", 4: "Пт", 5: "Сб", 6: "Вс"
    }

    for date_str in dates:
        from datetime import datetime
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        weekday = weekdays[dt.weekday()]

        # Формат: "15 янв (Пн)"
        button_text = f"{dt.day} {_month_name(dt.month)} ({weekday})"
        callback_data = f"date:{date_str}:{service_id}"

        builder.button(
            text=button_text,
            callback_data=callback_data[:64]
        )

    # 2 buttons per row
    builder.adjust(2)

    # Cancel button
    builder.row(
        InlineKeyboardButton(
            text="❌ Отмена",
            callback_data="cancel_booking"
        )
    )

    return builder.as_markup()


def create_services_keyboard(
    services: List[Dict[str, Any]]
) -> InlineKeyboardMarkup:
    """
    Создает клавиатуру с доступными услугами

    Args:
        services: Список услуг с полями id, title, price, duration

    Returns:
        InlineKeyboardMarkup с кнопками услуг
    """
    builder = InlineKeyboardBuilder()

    for service in services:
        service_id = service.get("id", "")
        title = service.get("title", "Услуга")
        price = service.get("price")
        duration = service.get("duration")

        # Формат: "Стрижка - 1500₽ (30 мин)"
        button_text = title
        if price:
            button_text += f" - {price}₽"
        if duration:
            button_text += f" ({duration} мин)"

        callback_data = f"service:{service_id}"

        builder.button(
            text=button_text,
            callback_data=callback_data[:64]
        )

    # 1 button per row (services are long)
    builder.adjust(1)

    # Cancel button
    builder.row(
        InlineKeyboardButton(
            text="❌ Отмена",
            callback_data="cancel_booking"
        )
    )

    return builder.as_markup()


def create_employees_keyboard(
    employees: List[Dict[str, Any]],
    service_id: str
) -> InlineKeyboardMarkup:
    """
    Создает клавиатуру с выбором мастера

    Args:
        employees: Список сотрудников
        service_id: ID услуги

    Returns:
        InlineKeyboardMarkup
    """
    builder = InlineKeyboardBuilder()

    # Опция "Любой мастер"
    builder.button(
        text="👤 Любой свободный мастер",
        callback_data=f"employee:any:{service_id}"
    )

    for emp in employees:
        emp_id = emp.get("id", "")
        name = emp.get("name", "Мастер")
        rating = emp.get("rating")

        button_text = f"👤 {name}"
        if rating:
            button_text += f" ⭐{rating}"

        callback_data = f"employee:{emp_id}:{service_id}"

        builder.button(
            text=button_text,
            callback_data=callback_data[:64]
        )

    builder.adjust(1)

    builder.row(
        InlineKeyboardButton(
            text="❌ Отмена",
            callback_data="cancel_booking"
        )
    )

    return builder.as_markup()


def create_confirmation_keyboard(
    appointment_data: Dict[str, Any]
) -> InlineKeyboardMarkup:
    """
    Создает клавиатуру подтверждения записи

    Args:
        appointment_data: Данные записи

    Returns:
        InlineKeyboardMarkup
    """
    builder = InlineKeyboardBuilder()

    # Encode appointment data into callback
    # Simplified: just use confirm/cancel with stored context
    builder.button(
        text="✅ Подтвердить запись",
        callback_data="confirm_booking"
    )

    builder.button(
        text="❌ Отменить",
        callback_data="cancel_booking"
    )

    builder.adjust(1)

    return builder.as_markup()


def create_cancel_appointment_keyboard(
    appointment_id: str
) -> InlineKeyboardMarkup:
    """
    Создает клавиатуру отмены записи

    Args:
        appointment_id: ID записи

    Returns:
        InlineKeyboardMarkup
    """
    builder = InlineKeyboardBuilder()

    builder.button(
        text="❌ Отменить запись",
        callback_data=f"cancel_appt:{appointment_id}"
    )

    builder.button(
        text="⬅️ Назад",
        callback_data="back_to_menu"
    )

    builder.adjust(1)

    return builder.as_markup()


def _month_name(month: int) -> str:
    """Возвращает короткое название месяца на русском"""
    months = {
        1: "янв", 2: "фев", 3: "мар",
        4: "апр", 5: "май", 6: "июн",
        7: "июл", 8: "авг", 9: "сен",
        10: "окт", 11: "ноя", 12: "дек"
    }
    return months.get(month, "")
