from __future__ import annotations
import os
import logging
import io
import sys
import argparse

from game import Game
from textual import work, events
from textual.app import App, ComposeResult
from textual.containers import VerticalScroll
from textual.widgets import Input, Markdown, Log, MarkdownViewer, RichLog
from textual.logging import TextualHandler
import queue
from textual.message import Message
from textwrap import wrap
from events import BufferUpdated, GenerateUpdated, GenerateCleared, Stopped, SaveState
import os.path

logging.basicConfig(
    level="DEBUG",
    handlers=[TextualHandler()],
)


class Cherryberry(App):
    CSS_PATH = "cherryberry.tcss"

    game: Game
    buffer: str
    generte: str
    line_limit = 4096

    def __init__(self, args):
        self.args = args
        super().__init__()

    def compose(self) -> ComposeResult:
        self.dark = False
        self.executor = None
        self.listener = None
        self.queue_to_game = queue.Queue()
        self.queue_from_game = queue.Queue()

        # with VerticalScroll(id="buffer-container"):
        yield RichLog(id="buffer_panel", auto_scroll=True, wrap=True, markup=True)
        yield RichLog(id="generation_panel", auto_scroll=True, wrap=True, markup=True)
        yield Input(placeholder="Your command, e.g. help")

    def on_mount(self) -> None:
        self.buffer = "\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\n\t\t\t\t[b u]Welcome to CHERRYBERRY, your friendly AI text adventure![/]\n\n"
        self.buffer += (
            "[i]This game is an experiment in using LLMs for text-mode gameplay. "
        )
        self.buffer += "It's able to generate locations as you go, as well as process player actions and manage inventory (somewhat). "
        self.buffer += "The gameplay is limited, so treat it as a demo. "
        self.buffer += "\n\nThe game is saved frequently into JSON (hence the sluggishness), but it's safe to exit with CTRL-C anytime. "
        self.buffer += (
            "If anything goes wrong, CTRL-C, and edit the files in the save directory. "
        )
        self.buffer += "\n\nHappy experimenting 😊[/i]\n\n\n"

        self.generate = ""
        self.query_one(Input).focus()
        self.executor = self.run_worker(self.execute, thread=True)
        self.listener = self.run_worker(self.listen, thread=True)

        panel = self.query_one("#generation_panel", RichLog).clear()
        panel.display = False
        panel.border_title = "LLM"

    def on_unmount(self) -> None:
        self.queue_to_game.put("<<<stop>>>", block=False)
        self.queue_from_game.put("<<<stop>>>", block=False)

    async def on_input_submitted(self, message: Input.Submitted) -> None:
        self.query_one("Input", Input).clear()
        if message.value == "dark":
            self.dark = True
        elif message.value == "light":
            self.dark = False
        else:
            self.queue_to_game.put(message.value, block=True)

    async def on_buffer_updated(self, message: BufferUpdated) -> None:
        self.buffer += message.message

        lines = self.buffer.split("\n")
        if len(lines) > self.line_limit:
            lines = lines[len(lines) - self.line_limit :]
            self.buffer = "\n".join(lines)

        panel = self.query_one("#buffer_panel", RichLog)
        panel.clear()
        panel.write(self.buffer + "\n", scroll_end=True)

    async def on_generate_updated(self, message: GenerateUpdated) -> None:
        panel = self.query_one("#generation_panel", RichLog).clear()
        panel.display = True

        # Unsure why this gets wiped when we do panel.display = True
        buf = self.query_one("#buffer_panel", RichLog).clear()
        buf.write(self.buffer + "\n", scroll_end=True)

        self.generate += message.message

        panel = self.query_one("#generation_panel", RichLog)
        panel.clear()
        panel.write(self.generate + "\n", scroll_end=True)

    async def on_generate_cleared(self, message: GenerateCleared) -> None:
        panel = self.query_one("#generation_panel", RichLog).clear()
        panel.display = False
        panel.clear()
        self.generate = ""

    def listen(self):
        while True:
            event = self.queue_from_game.get(block=True)
            if event == "<<<stop>>>":
                print("Listener stopping...")
                break
            else:
                self.post_message(event)

    def execute(self):
        if os.path.exists("save/game_loop.json"):
            game = Game(
                self.queue_from_game,
                args=self.args,
                from_save="save",
            )
        else:
            game = Game(self.queue_from_game, args=self.args)

        while True:
            line = self.queue_to_game.get(block=True)
            if line == "<<<stop>>>":
                print("Executor stopping...")
                break
            else:
                game.execute(line)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="Cherryberry",
    )
    parser.add_argument("-m", "--model", type=str)
    parser.add_argument("-ngl", "--gpu-layers", type=int)
    parser.add_argument("-c", "--n_ctx", type=int)
    parser.add_argument("-b", "--n_batch", type=int)
    parser.add_argument("-t", "--threads", type=int)
    parser.add_argument("--mlock", action="store_true")
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()

    if not os.path.isfile(args.model):
        print("Pass model path as the first parameter")

    app = Cherryberry(args)
    app.run()
