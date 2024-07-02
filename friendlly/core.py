# AUTOGENERATED! DO NOT EDIT! File to edit: ../nbs/01_core.ipynb.

# %% auto 0
__all__ = ['parse_cell', 'fr', 'load_ipython_extension', 'unload_ipython_extension']

# %% ../nbs/01_core.ipynb 3
from typing import List, Dict, Tuple
import textwrap
from claudette import Client
from IPython import get_ipython
from IPython.display import display, Markdown, clear_output
#| exporti

# %% ../nbs/01_core.ipynb 4
# A single cell can contain multiple messages.
# A message is either a user message (starts with %fr) or a bot message (starts with #).
# Both can be multiline.
def parse_cell(
    cell: str # The raw body of the cell
) -> Tuple[List[Dict[str, str]], int]:
    """
    A single cell can contain multiple messages.
    A message is either a user message (starts with %fr) or a bot message (starts with #).
    Both can be multiline.

    Returns: a list of messages (with 'role' and 'content') and the number of %fr magics in the cell
    """
    parsed_lines = []
    num_magic = 0
    for line in cell.split('\n'):
        if line.startswith('%fr'):
            message = {'role': 'user', 'content': line[3:].strip()}
            num_magic += 1
        elif line.strip().startswith('#'):
            message = {'role': 'assistant', 'content': line[1:].strip()}
        else: continue

        if not parsed_lines or parsed_lines[-1]['role'] != message['role']:
            parsed_lines.append(message)
        else:
            parsed_lines[-1]['content'] += ("\n" + message['content'])

    return parsed_lines, num_magic

# %% ../nbs/01_core.ipynb 5
models = [
    'claude-3-opus-20240229',
    'claude-3-5-sonnet-20240620',
    'claude-3-haiku-20240307',
]
chat_client = Client(model=models[1])

magic_count = 0
messages = []

# %% ../nbs/01_core.ipynb 6
def fr(line: str):
    """The magic function for the %fr magic command."""
    global magic_count, messages
    ip = get_ipython()
    raw_cell = ip.history_manager.input_hist_raw[-1]

    # The cell might have multiple %lm magics, but we only want to process the last one.
    # Presumably, the previous ones would have been processed already.
    if magic_count <= 0: messages, magic_count = parse_cell(raw_cell)

    # This is the last %lm magic invocation of the cell.
    # But we ignore cells that don't have a user message as the last message.
    if magic_count == 1 and len(messages) > 0 and messages[-1]['role'] == 'user' and messages[-1]['content'].strip():
        reply = ""
        display_id = display(Markdown("🚀..."), display_id=True)
        r = chat_client([m['content'] for m in messages], stream=True)
        for token in r:
            reply += token
            display_id.update(Markdown(reply))
        reply = textwrap.fill(text=reply, width=100, initial_indent="# ", subsequent_indent="# ")

        raw_cell += f"\n{reply}\n\n%fr"
        ip.set_next_input(raw_cell, replace=True)
        clear_output()

    magic_count -= 1

# %% ../nbs/01_core.ipynb 10
def load_ipython_extension(ipython):
    ipython.register_magic_function(fr, 'line')

def unload_ipython_extension(ipython):
    pass
