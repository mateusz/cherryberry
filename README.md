# Cherryberry

Welcome to CHERRYBERRY, your friendly AI text adventure!

This game is an experiment in using LLMs for text-mode gameplay. It's able to
generate locations as you go, as well as process player actions and manage
inventory (somewhat). The gameplay is limited, so treat it as a demo.

The game is saved frequently into JSON (hence the sluggishness), but it's safe
to exit with CTRL-C anytime.  If anything goes wrong, CTRL-C, and edit the files
in the save directory. 

Happy experimenting 😊

## Installation

Download an LLM to your local machine. Recommended model is [LLaMA2-13B-Psyfighter2-GGUF](https://huggingface.co/KoboldAI/LLaMA2-13B-Psyfighter2-GGUF), the Q4_K_M variant. Why is it recommended you may ask? Because this is the model I've made the game with 😂

```bash
poetry install
python3 -m cherryberry
```