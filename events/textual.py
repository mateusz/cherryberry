from textual.message import Message


class BufferUpdated(Message):
    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__()


class GenerateUpdated(Message):
    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__()


class GenerateCleared(Message):
    def __init__(self) -> None:
        super().__init__()


class Stopped(Message):
    def __init__(self) -> None:
        super().__init__()


class SaveState(Message):
    def __init__(
        self,
        all_modules,
        current_module,
        inventory,
        history,
    ) -> None:
        self.all_modules = (all_modules,)
        self.current_module = (current_module,)
        self.inventory = (inventory,)
        self.history = (history,)
        super().__init__()
