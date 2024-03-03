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

import ollama

def mute_llama(level, message, user_data):
    pass


log_callback = ctypes.CFUNCTYPE(None, ctypes.c_int, ctypes.c_char_p, ctypes.c_void_p)(
    mute_llama
)
llama_log_set(log_callback, ctypes.c_void_p())

class OllamaClient:
    def __init__(self, host=None, model=None):
        self.client = ollama.Client(host=host)
        self.model = model

    def create_completion(self, prompt=None, max_tokens=None, temperature=None, repeat_penalty=None, top_p=None, top_k=None, stop=None, stream=None):
        options = {
                'num_predict': max_tokens,
                'temperature': temperature,
                'repeat_penalty': repeat_penalty,
                'top_p': top_p,
                'top_k': top_k,
                'stop': stop
                }
        for chunk in self.client.generate(model=self.model, prompt=prompt, stream=stream, options=options):
            text = chunk['response']
            text_dict = {
                    'text': text
                    }
            choices_list = [text_dict]
            choices_dict = {
                    'choices': choices_list
                    }
            yield choices_dict


class Model:
    queue: Queue
    debug: bool

    def __init__(self, queue, args):
        self.queue = queue
        self.debug = args.debug

        self.tmpl = Environment(loader=PackageLoader("language_model", "prompts"))

        if args.ollama_host is not None and args.ollama_model is not None:
            self.llm = OllamaClient(host=args.ollama_host, model=args.ollama_model)
        else:
            self.llm = Llama(
                model_path=args.model,
                n_ctx=args.n_ctx,
                n_batch=args.n_batch,
                n_gpu_layers=args.gpu_layers,
                n_threads=args.threads,
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

        htext = ""
        if len(history) != 0:
            hist = []
            for i in history[-10:]:
                hist += [f"* {i}"]
            htext = "The story so far, for context only:\n\n" + "\n".join(hist)

        prompt = self.tmpl.get_template("00_generate_location.txt").render(
            {
                "setting": setting,
                "history": htext,
                "requirements": requirements,
            }
        )
        if self.debug:
            logging.debug(prompt)
        stream = self.llm.create_completion(
            prompt=prompt,
            max_tokens=2048,
            temperature=1.6,
            repeat_penalty=1.1,
            top_p=0.99,
            top_k=200,
            stop=["\n\n", "#"],
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

        htext = ""
        if len(history) != 0:
            hist = []
            for i in history[-10:]:
                hist += [f"* {i}"]
            htext = "The story so far, for context only:\n\n" + "\n".join(hist)

        prompt = self.tmpl.get_template("05_generate_location_from_exit.txt").render(
            {
                "setting": setting,
                "history": htext,
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
            temperature=1.6,
            repeat_penalty=1.1,
            top_p=0.99,
            top_k=200,
            stop=["\n\n", "#"],
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
            stop=["\n\n", "#"],
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

    def consequences(self, setting, history, description, inventory, action):
        self.printb("[grey46][Generating consequences...][/]")

        htext = ""
        if len(history) != 0:
            hist = []
            for i in history[-10:]:
                hist += [f"* {i}"]
            htext = "The story so far, for context only:\n\n" + "\n".join(hist)

        if len(inventory) == 0:
            inv = ["* EMPTY"]
        else:
            inv = []
            for i in inventory:
                inv += [f"* {i}"]
        inv = "\n".join(inv)

        prompt = self.tmpl.get_template("30_consequences.txt").render(
            {
                "setting": setting,
                "history": htext,
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
            temperature=1.6,
            repeat_penalty=1.1,
            top_p=0.99,
            top_k=200,
            stop=["\n\n", "#"],
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

    def update_description(self, setting, description, action, consequences):
        self.printb("[grey46][Generating update description...][/]")

        prompt = self.tmpl.get_template("40_update_description.txt").render(
            {
                "setting": setting,
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
            stop=["#"],
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
            stop=["#"],
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
            stop=["\n\n", "#"],
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

    def find_exits(self, setting, location_description):
        self.printb("[grey46][Generating find exits...][/]")

        prompt = self.tmpl.get_template("10_find_exits.txt").render(
            {"setting": setting, "description": location_description}
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
            stop=["`", "#"],
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
            stop=["`", "#"],
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
