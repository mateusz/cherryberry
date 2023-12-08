from llama_cpp import Llama, LlamaCache, LlamaDiskCache, llama_log_set
from jinja2 import Environment, PackageLoader
import json
import re
import time
from textual.app import App
from queue import Queue
from events import BufferUpdated, GenerateUpdated, GenerateCleared

import ctypes


def mute_llama(level, message, user_data):
    pass


log_callback = ctypes.CFUNCTYPE(None, ctypes.c_int, ctypes.c_char_p, ctypes.c_void_p)(
    mute_llama
)
llama_log_set(log_callback, ctypes.c_void_p())


class Model:
    queue: Queue

    def __init__(self, queue):
        self.queue = queue
        self.tmpl = Environment(loader=PackageLoader("language_model", "prompts"))
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

    def generate_location(self, setting, requirements):
        self.printb("[grey46][Generating location...][/]")

        prompt = self.tmpl.get_template("00_generate_location.txt").render(
            {"setting": setting, "requirements": requirements}
        )
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

        return out.strip()

    def generate_location_from_exit(
        self, setting, previous, exit_name, exit_description
    ):
        self.printb("[grey46][Generating location from exit...][/]")

        prompt = self.tmpl.get_template("05_generate_location_from_exit.txt").render(
            {
                "setting": setting,
                "previous": previous,
                "exit_name": exit_name,
                "exit_description": exit_description,
            }
        )
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
        return out.strip()

    def action_items(self, description, inventory, action):
        self.printb("[grey46][Generating action items...][/]")

        if len(inventory) == 0:
            i = "* EMPTY\n"
        else:
            i = ""
            for k in inventory:
                i += f"* {k}\n"

        prompt = self.tmpl.get_template("20_action_items.txt").render(
            {
                "description": description,
                "inventory": i,
                "action": action,
            }
        )
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
        out = ""
        for output in stream:
            out += output["choices"][0]["text"]
            self.printg(output["choices"][0]["text"], end="", flush=True)
        self.clearg()

        items = []
        lines = re.split(r"[\n\*]", out.strip())
        for l in lines:
            if l.strip() == "":
                continue
            if not re.search(r":\s*$", l):
                # if re.search(r"^\s*[\*\+\-] ", l):
                l = re.sub(r"^\s*[\*\+\-] ", "", l)
                l = re.sub(r"\([^)]*\)", "", l)
                l = re.sub(r"\w+[0-9]\w*", "", l)
                l = re.sub(r"\w*[0-9]\w+", "", l)
                l = re.sub(r"\s\s", " ", l)

                items += [l.strip().lower()]

        return items

    def consequences(self, description, inventory, action):
        self.printb("[grey46][Generating consequences...][/]")

        if len(inventory) == 0:
            i = "* EMPTY\n"
        else:
            i = ""
            for k in inventory:
                i += f"* {k}\n"

        prompt = self.tmpl.get_template("30_consequences.txt").render(
            {
                "description": description,
                "inventory": i,
                "action": action,
            }
        )
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
        return out.strip()

    def update_description(self, description, action, consequences):
        self.printb("[grey46][Generating update description...][/]")

        prompt = self.tmpl.get_template("40_update_description.txt").render(
            {
                "description": description,
                "action": action,
                "consequences": consequences,
            }
        )
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
        return out.strip()

    def update_inventory(self, inventory, description, action, consequences):
        self.printb("[grey46][Generating inventory updates][/]")

        if len(inventory) == 0:
            i = "* EMPTY\n"
        else:
            i = ""
            for k in inventory:
                i += f"* {k}\n"

        prompt = self.tmpl.get_template("50_inventory_updates.txt").render(
            {
                "inventory": i,
                "description": description,
                "action": action,
                "consequences": consequences,
            }
        )
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
        out = ""
        for output in stream:
            out += output["choices"][0]["text"]
            self.printg(output["choices"][0]["text"], end="", flush=True)
        self.printg()
        updates = out

        self.printb("[grey46][Generating update inventory][/]")
        prompt = self.tmpl.get_template("55_update_inventory.txt").render(
            {
                "inventory": i,
                "description": description,
                "action": action,
                "consequences": consequences,
                "updates": updates,
            }
        )
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

        items = []
        lines = re.split(r"[\n\*]", out.strip())
        for l in lines:
            if l.strip() == "":
                continue
            if not re.search(r":\s*$", l):
                # if re.search(r"^\s*[\*\+\-] ", l):
                l = re.sub(r"^\s*[\*\+\-] ", "", l)
                l = re.sub(r"\([^)]*\)", "", l)
                l = re.sub(r"\w+[0-9]\w*", "", l)
                l = re.sub(r"\w*[0-9]\w+", "", l)
                l = re.sub(r"\s\s", " ", l)

                items += [l.strip().lower()]

        return items

    def find_exits(self, location_description):
        self.printb("[grey46][Generating find exits...][/]")

        prompt = self.tmpl.get_template("10_find_exits.txt").render(
            {"description": location_description}
        )
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

        out = re.sub("`.*", "", out, re.M)
        try:
            obj = json.loads(out)
            self.clearg()
            return obj
        except:
            pass

        try:
            obj = json.loads(out + "}")
            self.clearg()
            return obj
        except:
            pass

        try:
            obj = json.loads(out + "} }")
            self.clearg()
            return obj
        except:
            pass

        self.printg("[Attempting to fix JSON...]")
        out = self.json_fixer(out)

        out = re.sub("`.*", "", out, re.M)
        try:
            obj = json.loads(out)
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
        return out.strip()
