from aiogram.fsm.state import State, StatesGroup

class BookingStates(StatesGroup):
    choosing_service = State()
    choosing_date = State()
    choosing_time = State()
    entering_phone = State()
    entering_secret = State()
    entering_description = State()
    confirming = State()

class ReviewStates(StatesGroup):
    rating = State()
    text = State()

class AdminStates(StatesGroup):
    mailing_text = State()
    mailing_confirm = State()