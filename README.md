# Cherryberry

Welcome to CHERRYBERRY, your friendly AI text adventure!

This game is an experiment in using LLMs for text-mode gameplay. It's able to
generate locations as you go, as well as process player actions and manage
inventory (somewhat). The gameplay is limited, so treat it as a demo.

The game is saved frequently into JSON (hence the sluggishness), but it's safe
to exit with CTRL-C anytime.  If anything goes wrong, CTRL-C, and edit the files
in the save directory. 

Happy experimenting 😊

## Demo

This demo has been recorded on an M1 Mac with 32 GB RAM. The demo is in real time (not sped up). You can see the model is a bit weak at times, and needs some corrections, but it's consistent enough for lightweight gameplay.

![Demo](demo.gif)

(41MB download, might take a tick ⌛)

## Running

Download an LLM to your local machine. Recommended model is [LLaMA2-13B-Psyfighter2-GGUF](https://huggingface.co/KoboldAI/LLaMA2-13B-Psyfighter2-GGUF), the Q4_K_M variant. Why is it recommended you may ask? Because this is the model I've made the game with 😂

The following instructions are for Metal on Mac and CUDA on Linux.

My preferred installation option is via micromamba. [Install micromamba](https://mamba.readthedocs.io/en/latest/installation/micromamba-installation.html), then:

```bash
# For Mac:
micromamba create -n cherryberry -f environment.yml
# For Linux/CUDA:
micromamba create -n cherryberry -f environment-cuda.yml

micromamba activate cherryberry
```

If your system has python (and CUDA dependencies on Nvidia) already installed (for Nvidia, try to run `nvcc`), then you should be able to skip the above step.

Install dependencies:

```bash
# For CPU:
poetry install
# For Mac M*:
CMAKE_ARGS="-DLLAMA_METAL=on" poetry install
# For Linux/CUDA:
CMAKE_ARGS="-DLLAMA_CUBLAS=on" poetry install 
```

If you don't like poetry, you can also install the dependencies manually using `pip` - have a look at the list in `pyproject.toml`.

If you are running into problems with compiling LlamaCpp for your target, go to [llama-cpp-python](https://github.com/abetlen/llama-cpp-python) and [LlamaCpp instructions](https://github.com/ggerganov/llama.cpp)). In particular, I'm not sure how to install this in Windows.

Warning: poetry will compile LlamaCpp only on the first install, if you change the compile time flags (`LLAMA_METAL`, `LLAMA_CUBLAS` etc) you can force recompilation with:

```bash
poetry remove llama-cpp-python
CMAKE_ARGS="-DLLAMA_CUBLAS=on" poetry add llama-cpp-python
# Note the messes around with pyproject.toml and poetry.lock
```

Finally to run the game (settings given here are appropriate for Psyfighter):

```bash
# For Mac:
python3 -m cherryberry \
	--model ../models/LLaMA2-13B-Psyfighter2.Q4_K_M.gguf \
	--n_ctx 4096 \
	--n_batch 512 \
	-ngl 1 \
	--threads 4
```

Change `ngl` and `threads` to suit. `ngl` should be 1 on Mac, and actual number of layers to offload on Linux/CUDA.

## Debug mode

To run the game in the debug mode:

```bash
# In one terminal window:
textual console
# In another
textual run --dev cherryberry.py --debug --model ...
```