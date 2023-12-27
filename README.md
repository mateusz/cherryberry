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

Download an LLM to your local machine. Recommended model is [Big-Tiger-Gemma-27B-v1-GGUF](https://huggingface.co/TheDrummer/Big-Tiger-Gemma-27B-v1-GGUF), even the Q3_K_M is fine. 

This game was initially made with LLaMA2-13B-Psyfighter2-GGUF, but after GBNF rewrite and some testing, Gemma turned out to be way more capable.

### Mac M*

*These instructions tested on Mac M1*

My preferred installation option is via micromamba. [Install micromamba](https://mamba.readthedocs.io/en/latest/installation/micromamba-installation.html), then:

```bash
micromamba create -n cherryberry -f environment.yml
micromamba activate cherryberry
```

If your system has python already installed, then you should be able to skip the above step, or you can replace it with venv installation.

Install dependencies:

```bash
CMAKE_ARGS="-DLLAMA_METAL=on" poetry install
```

If you don't like poetry, you can also install the dependencies manually using `pip` - have a look at the list in `pyproject.toml`.


```bash
python3 -m cherryberry \
	--model ../models/Big-Tiger-Gemma-27B-v1c-Q3_K_M.gguf \
	--n_ctx 8192 \
	--n_batch 512 \
	-ngl 200 \
	--threads 4
```

### Linux/CUDA

*These instructions tested on Ubuntu 20, with 3060 which is CUDA 8*

My preferred installation option is via micromamba. [Install micromamba](https://mamba.readthedocs.io/en/latest/installation/micromamba-installation.html).

Open up `environment-cuda.yml` and adjust cudnn and cudatoolkit-dev versions to match your GPU, then:

```bash
# This will take ages and download the Nvidia world.
micromamba create -n cherryberry -f environment-cuda.yml
micromamba activate cherryberry
```

If your system has python and CUDA dependencies already installed (for Nvidia, try to run `nvcc`), then you should be able to skip the above step, or you can replace it with venv installation.

Install dependencies:

```bash
CMAKE_ARGS="-DLLAMA_CUBLAS=on" poetry install 
```

If you don't like poetry, you can also install the dependencies manually using `pip` - have a look at the list in `pyproject.toml`.

```bash
python3 -m cherryberry \
	--model ../models/Big-Tiger-Gemma-27B-v1c-Q3_K_M.gguf \
	--n_ctx 8192 \
	--n_batch 512 \
	-ngl 200 \
	--threads 4
```

Change `ngl` and `threads` to suit. `ngl` should be set to the actual number of layers to offload to GPU.


### Force LlamaCpp recompilation

If you are running into problems with compiling LlamaCpp for your target, go to [llama-cpp-python](https://github.com/abetlen/llama-cpp-python) and [LlamaCpp instructions](https://github.com/ggerganov/llama.cpp)). In particular, I'm not sure how to install this in Windows.

Warning: poetry will compile LlamaCpp only on the first install, if you change the compile time flags (`LLAMA_METAL`, `LLAMA_CUBLAS` etc) you can force recompilation with:

```bash
poetry remove llama-cpp-python
CMAKE_ARGS="-DLLAMA_CUBLAS=on" poetry add llama-cpp-python
# Note this messes around with pyproject.toml and poetry.lock
```

## Debug mode

To run the game in the debug mode:

```bash
# In one terminal window:
textual console
# In another
textual run --dev cherryberry.py --debug --model ...
```

## FAQ

**Q: Can this game support [my favourite LLM server] instead of llama.cpp?**

A: I'm afraid not. This game relies heavily on grammar-driven generation using [GBNF](https://github.com/ggerganov/llama.cpp/blob/master/grammars/README.md), and it will fall apart if that's removed. As far as I know there is currently no standard support for grammars in LLM servers.