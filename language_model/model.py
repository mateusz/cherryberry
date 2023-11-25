from llama_cpp import Llama, LlamaCache, LlamaDiskCache
from jinja2 import Environment, PackageLoader
import json
import re
import time

class Model:
    def __init__(self):
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
        #self.llm.set_cache(LlamaDiskCache('cache'))

    def generate_location(self, requirements):
        prompt = self.tmpl.get_template("00_generate_location.txt").render({
            "requirements": requirements
        })
        compl = self.llm.create_completion(
            prompt=prompt,
            max_tokens=1024,
            temperature=1.2,
            repeat_penalty=1.1,
            top_p=0.95,
            top_k=40,
            stop=["[INST]"],
        )
        return compl['choices'][0]['text']

    def generate_location_from_exit(self, previous, exit_name, exit_description):
        prompt = self.tmpl.get_template("05_generate_location_from_exit.txt").render({
            "previous": previous,
            "exit_name": exit_name,
            "exit_description": exit_description,
        })
        compl = self.llm.create_completion(
            prompt=prompt,
            max_tokens=1024,
            temperature=1.2,
            repeat_penalty=1.1,
            top_p=0.95,
            top_k=40,
            stop=["[INST]"],
        )
        return compl['choices'][0]['text']


    def json_fixer(self, json_str):
        prompt = self.tmpl.get_template("99_json_fixer.txt").render({
            "json": json_str,
        })
        compl = self.llm.create_completion(
            prompt=prompt,
            max_tokens=1024,
            temperature=0.4,
            repeat_penalty=1.1,
            top_p=0.95,
            top_k=40,
            stop=["[INST]"],
        )
        return compl['choices'][0]['text']

    def find_exits(self, location_description):
        prompt = self.tmpl.get_template("10_find_exits.txt").render({
            "description": location_description
        })
        compl = self.llm.create_completion(
            prompt=prompt,
            max_tokens=512,
            temperature=0.8,
            repeat_penalty=1.1,
            top_p=0.95,
            top_k=40,
            stop=["[INST]"],
        )
        out = "{\n    \"" + re.sub('`.*', '', compl['choices'][0]['text'])
        try:
            obj = json.loads(out)
            return obj
        except:
            pass
        
        try:
            obj = json.loads(out + "}")
            return obj
        except:
            pass

        try:
            obj = json.loads(out + "} }")
            return obj
        except:
            pass

        print("[Attempting to fix JSON...]")
        compl = self.json_fixer(out)
        fix = re.sub('`.*', '', compl['choices'][0]['text'])
        try:
            obj = json.loads(fix)
        except Exception as exc:
            raise Exception(f"Unable to parse: {out}") from exc