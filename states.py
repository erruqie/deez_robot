from aiogram.dispatcher.filters.state import State, StatesGroup


class UploadState(StatesGroup):
    sending_upc = State()
    sending_isrc = State()
