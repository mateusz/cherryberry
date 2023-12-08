from llama_cpp import Llama, LlamaCache, LlamaDiskCache, llama_log_set
from jinja2 import Environment, PackageLoader
import orjson
import re
import time
from textual.app import App
from queue import Queue
from events import BufferUpdated, GenerateUpdated, GenerateCleared
import logging

import ctypes


def mute_llama(level, message, user_data):
    pass


log_callback = ctypes.CFUNCTYPE(None, ctypes.c_int, ctypes.c_char_p, ctypes.c_void_p)(
    mute_llama
)
llama_log_set(log_callback, ctypes.c_void_p())


class Model:
    queue: Queue
    debug: bool

    def __init__(self, queue, debug=False):
        self.queue = queue
        self.tmpl = Environment(loader=PackageLoader("language_model", "prompts"))
        self.debug = debug
        self.llm = Llama(
            model_path="../models/LLaMA2-13B-Psyfighter2.Q4_K_M.gguf",
            n_ctx=4096,
            n_batch=512,
            rope_freq_scale=1,
            rope_freq_base=10000,
            n_gpu_layers=1,
            n_threads=4,
            seed=int(time.time()),
        )
        # self.llm.set_cache(LlamaDiskCache('cache'))

    def printb(self, message="", end="\n", flush=False):
        self.queue.put(BufferUpdated(message + end), block=False)

    def printg(self, message="", end="\n", flush=False):
        self.queue.put(GenerateUpdated(message + end), block=False)

    def clearg(self):
        self.queue.put(GenerateCleared(), block=False)

    def generate_location(self, setting, history, requirements):
        self.printb("[grey46][Generating location...][/]")

        if len(history) == 0:
            hist = ["* EMPTY"]
        else:
            hist = []
            for i in history:
                hist += [f"* {i}"]
        hist = "\n".join(hist[-20:])

        prompt = self.tmpl.get_template("00_generate_location.txt").render(
            {
                "setting": setting,
                "history": hist,
                "requirements": requirements,
            }
        )
        if self.debug:
            logging.debug(prompt)
        stream = self.llm.create_completion(
            prompt=prompt,
            max_tokens=2048,
            temperature=1.2,
            repeat_penalty=1.1,
            top_p=0.95,
            top_k=40,
            stop=["\n\n"],
            stream=True,
        )
        out = ""
        for output in stream:
            out += output["choices"][0]["text"]
            self.printb(output["choices"][0]["text"], end="", flush=True)
        self.printb()

        out = out.strip()
        if self.debug:
            logging.debug(out)
        return out

    def generate_location_from_exit(
        self, setting, history, previous, exit_name, exit_description
    ):
        self.printb("[grey46][Generating location from exit...][/]")

        if len(history) == 0:
            hist = ["* EMPTY"]
        else:
            hist = []
            for i in history:
                hist += [f"* {i}"]
        hist = "\n".join(hist[-20:])

        prompt = self.tmpl.get_template("05_generate_location_from_exit.txt").render(
            {
                "setting": setting,
                "history": hist,
                "previous": previous,
                "exit_name": exit_name,
                "exit_description": exit_description,
            }
        )
        if self.debug:
            logging.debug(prompt)
        stream = self.llm.create_completion(
            prompt=prompt,
            max_tokens=2048,
            temperature=1.2,
            repeat_penalty=1.1,
            top_p=0.95,
            top_k=40,
            stop=["\n\n"],
            stream=True,
        )
        out = ""
        for output in stream:
            out += output["choices"][0]["text"]
            self.printb(output["choices"][0]["text"], end="", flush=True)

        self.printb()
        out = out.strip()
        if self.debug:
            logging.debug(out)
        return out

    def action_items(self, description, inventory, action):
        self.printb("[grey46][Generating action items...][/]")

        if len(inventory) == 0:
            inv = ["* EMPTY"]
        else:
            inv = []
            for i in inventory:
                inv += [f"* {i}"]
        inv = "\n".join(inv)

        prompt = self.tmpl.get_template("20_action_items.txt").render(
            {
                "description": description,
                "inventory": inv,
                "action": action,
            }
        )
        if self.debug:
            logging.debug(prompt)
        stream = self.llm.create_completion(
            prompt=prompt,
            max_tokens=2048,
            temperature=0.4,
            repeat_penalty=1.1,
            top_p=0.95,
            top_k=40,
            stop=["\n\n"],
            stream=True,
        )
        out = "* "
        for output in stream:
            out += output["choices"][0]["text"]
            self.printg(output["choices"][0]["text"], end="", flush=True)
        self.clearg()

        out = out.strip()
        if self.debug:
            logging.debug(out)

        items = []
        lines = re.split(r"[\n\*]", out)
        for l in lines:
            if l.strip() == "":
                continue
            if not re.search(r":\s*$", l):
                l = re.sub(r"^(\s*[\*\+\-])*", "", l)
                l = re.sub(r"\([^)]*\)", "", l)
                l = re.sub(r"\w+[0-9]\w*", "", l)
                l = re.sub(r"\w*[0-9]\w+", "", l)
                l = re.sub(r"\s\s", " ", l)

                items += [l.strip().lower()]

        if self.debug:
            logging.debug(items)
        return items

    def consequences(self, history, description, inventory, action):
        self.printb("[grey46][Generating consequences...][/]")

        if len(history) == 0:
            hist = ["* EMPTY"]
        else:
            hist = []
            for i in history:
                hist += [f"* {i}"]
        hist = "\n".join(hist[-20:])

        if len(inventory) == 0:
            inv = ["* EMPTY"]
        else:
            inv = []
            for i in inventory:
                inv += [f"* {i}"]
        inv = "\n".join(inv)

        prompt = self.tmpl.get_template("30_consequences.txt").render(
            {
                "history": hist,
                "description": description,
                "inventory": inv,
                "action": action,
            }
        )
        if self.debug:
            logging.debug(prompt)
        stream = self.llm.create_completion(
            prompt=prompt,
            max_tokens=2048,
            temperature=1.2,
            repeat_penalty=1.1,
            top_p=0.95,
            top_k=40,
            stop=["\n\n"],
            stream=True,
        )
        out = ""
        for output in stream:
            out += output["choices"][0]["text"]
            self.printb(output["choices"][0]["text"], end="", flush=True)
        self.printb()

        out = out.strip()
        if self.debug:
            logging.debug(out)
        return out

    def update_description(self, description, action, consequences):
        self.printb("[grey46][Generating update description...][/]")

        prompt = self.tmpl.get_template("40_update_description.txt").render(
            {
                "description": description,
                "action": action,
                "consequences": consequences,
            }
        )
        if self.debug:
            logging.debug(prompt)
        stream = self.llm.create_completion(
            prompt=prompt,
            max_tokens=2048,
            temperature=1.2,
            repeat_penalty=1.1,
            top_p=0.95,
            top_k=40,
            stop=[],
            stream=True,
        )

        out = ""
        for output in stream:
            out += output["choices"][0]["text"]
            self.printb(output["choices"][0]["text"], end="", flush=True)
        self.printb()

        out = out.strip()
        if self.debug:
            logging.debug(out)
        return out

    def update_inventory(self, inventory, description, action, consequences):
        self.printb("[grey46][Generating inventory updates][/]")

        if len(inventory) == 0:
            inv = ["* EMPTY"]
        else:
            inv = []
            for i in inventory:
                inv += [f"* {i}"]
        inv = "\n".join(inv)

        prompt = self.tmpl.get_template("50_inventory_updates.txt").render(
            {
                "inventory": inv,
                "description": description,
                "action": action,
                "consequences": consequences,
            }
        )
        if self.debug:
            logging.debug(prompt)
        stream = self.llm.create_completion(
            prompt=prompt,
            max_tokens=2048,
            temperature=0.6,
            repeat_penalty=1.1,
            top_p=0.95,
            top_k=40,
            stop=[],
            stream=True,
        )
        out = "1. "
        for output in stream:
            out += output["choices"][0]["text"]
            self.printg(output["choices"][0]["text"], end="", flush=True)
        self.printg()
        out = out.strip()
        if self.debug:
            logging.debug(out)

        updates = out

        self.printb("[grey46][Generating update inventory][/]")
        prompt = self.tmpl.get_template("55_update_inventory.txt").render(
            {
                "inventory": inv,
                "description": description,
                "action": action,
                "consequences": consequences,
                "updates": updates,
            }
        )
        if self.debug:
            logging.debug(prompt)
        stream = self.llm.create_completion(
            prompt=prompt,
            max_tokens=2048,
            temperature=0.4,
            repeat_penalty=1.1,
            top_p=0.95,
            top_k=40,
            stop=["\n\n"],
            stream=True,
        )
        out = "* "
        self.printg(out, end="")
        for output in stream:
            out += output["choices"][0]["text"]
            self.printg(output["choices"][0]["text"], end="", flush=True)
        self.clearg()

        out = out.strip()
        if self.debug:
            logging.debug(out)

        items = []
        lines = re.split(r"[\n\*]", out)
        for l in lines:
            if l.strip() == "":
                continue
            if not re.search(r":\s*$", l):
                # if re.search(r"^\s*[\*\+\-] ", l):
                l = re.sub(r"^(\s*[\*\+\-])*", "", l)
                l = re.sub(r"\([^)]*\)", "", l)
                l = re.sub(r"\w+[0-9]\w*", "", l)
                l = re.sub(r"\w*[0-9]\w+", "", l)
                l = re.sub(r"\s\s", " ", l)

                items += [l.strip().lower()]

        if self.debug:
            logging.debug(items)
        return items

    def find_exits(self, location_description):
        self.printb("[grey46][Generating find exits...][/]")

        prompt = self.tmpl.get_template("10_find_exits.txt").render(
            {"description": location_description}
        )
        if self.debug:
            logging.debug(prompt)

        stream = self.llm.create_completion(
            prompt=prompt,
            max_tokens=512,
            temperature=0.8,
            repeat_penalty=1.1,
            top_p=0.95,
            top_k=40,
            stop=["`"],
            stream=True,
        )

        out = '{\n    "'
        self.printg(out, end="")
        for output in stream:
            out += output["choices"][0]["text"]
            self.printg(output["choices"][0]["text"], end="", flush=True)
        self.printg()

        out = out.strip()
        if self.debug:
            logging.debug(out)

        out = re.sub("`.*", "", out, re.M)
        try:
            obj = orjson.loads(out)
            self.clearg()
            return obj
        except:
            pass

        try:
            obj = orjson.loads(out + "}")
            self.clearg()
            return obj
        except:
            pass

        try:
            obj = orjson.loads(out + "} }")
            self.clearg()
            return obj
        except:
            pass

        self.printg("[Attempting to fix JSON...]")
        out = self.json_fixer(out)

        out = re.sub("`.*", "", out, re.M)
        try:
            obj = orjson.loads(out)
            self.clearg()
            return obj
        except Exception as exc:
            self.clearg()
            raise Exception(f"Unable to parse: {out}") from exc

    def json_fixer(self, json_str):
        prompt = self.tmpl.get_template("99_json_fixer.txt").render(
            {
                "json": json_str,
            }
        )
        if self.debug:
            logging.debug(prompt)

        stream = self.llm.create_completion(
            prompt=prompt,
            max_tokens=2048,
            temperature=0.4,
            repeat_penalty=1.1,
            top_p=0.95,
            top_k=40,
            stop=["`"],
            stream=True,
        )
        out = ""
        for output in stream:
            out += output["choices"][0]["text"]
            self.printg(output["choices"][0]["text"], end="", flush=True)
        self.printg()

        out = out.strip()
        if self.debug:
            logging.debug(out)
        return out
