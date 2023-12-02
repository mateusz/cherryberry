from __future__ import annotations
import os
import logging
import asyncio

from game import Game
from textual import work, events
from textual.app import App, ComposeResult
from textual.containers import VerticalScroll
from textual.widgets import Input, Markdown, Log, MarkdownViewer
from textual.logging import TextualHandler
import queue
from textual.message import Message

logging.basicConfig(
    level="DEBUG",
    handlers=[TextualHandler()],
)


class Cherryberry(App):
    class BufferUpdated(Message):
        def __init__(self, message: str) -> None:
            self.message = message
            super().__init__()

    CSS_PATH = "cherryberry.tcss"

    game: Game
    buffer: buffer

    def __init__(self):
        super().__init__()

    def compose(self) -> ComposeResult:
        self.executor = None
        self.listener = None
        self.queue_to_game = queue.Queue()
        self.queue_from_game = queue.Queue()

        # with VerticalScroll(id="buffer-container"):
        yield Log(id="buffer_panel")
        yield Input(placeholder="Your command, e.g. help")

    def on_mount(self) -> None:
        self.buffer = ""
        self.query_one(Input).focus()
        self.executor = self.run_worker(self.execute, thread=True)
        self.listener = self.run_worker(self.listen, thread=True)

    async def on_input_submitted(self, message: Input.Submitted) -> None:
        self.query_one("Input", Input).clear()
        self.queue_to_game.put(message.value, block=True)

    async def on_cherryberry_buffer_updated(self, message: BufferUpdated) -> None:
        panel = self.query_one("#buffer_panel", Log)
        panel.write(message.message, scroll_end=True)

    def listen(self):
        while True:
            line = self.queue_from_game.get(block=True)
            if line == "<<<stop>>>":
                break
            else:
                print(line)
                self.post_message(self.BufferUpdated(line))

    def execute(self):
        if os.path.exists("save/game_loop.json"):
            game = Game(self.queue_from_game, from_save="save")
        else:
            game = Game(self.queue_from_game)

        while True:
            line = self.queue_to_game.get(block=True)
            if line == "<<<stop>>>":
                break
            else:
                game.execute(line)


if __name__ == "__main__":
    app = Cherryberry()
    app.run()
