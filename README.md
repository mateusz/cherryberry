# Cherryberry

Welcome to CHERRYBERRY, your friendly AI text adventure!

This game is an experiment in using LLMs for text-mode gameplay. It's able to
generate locations as you go, as well as process player actions and manage
inventory (somewhat). The gameplay is limited, so treat it as a demo.

The game is saved frequently into JSON (hence the sluggishness), but it's safe
to exit with CTRL-C anytime.  If anything goes wrong, CTRL-C, and edit the files
in the save directory. 

Happy experimenting 😊

## Running

Download an LLM to your local machine. Recommended model is [LLaMA2-13B-Psyfighter2-GGUF](https://huggingface.co/KoboldAI/LLaMA2-13B-Psyfighter2-GGUF), the Q4_K_M variant. Why is it recommended you may ask? Because this is the model I've made the game with 😂

[Install micromamba](https://mamba.readthedocs.io/en/latest/installation/micromamba-installation.html), then:

```bash
micromamba create -n cherryberry -f environment.yml
poetry install
```

You might however want to add flags, to get the proper version of LlamaCpp (see [original instructions](https://github.com/ggerganov/llama.cpp)):

```bash
CMAKE_ARGS="-DLLAMA_METAL=on" poetry install
```

Then to run the game (settings given here are appropriate for Psyfighter):

```bash
python3 -m cherryberry \
	--model ../models/LLaMA2-13B-Psyfighter2.Q4_K_M.gguf \
	--n_ctx 4096 \
	--n_batch 512 \
	--rope_freq_scale 1 \
	--rope_freq_base 10000 \
	-ngl 1 \
	--threads 4
```

To run the game in the debug mode:

```bash
# In one terminal window:
textual console
# In another
textual run --dev cherryberry.py --debug --model ...
```