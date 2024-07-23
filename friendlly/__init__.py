__version__ = "0.1.0"

from .magic_cell import fr_cell
from .magic_line import fr_line
from .utils.nbclassic import patch_kernel
from IPython.display import clear_output

def load_ipython_extension(ipython):
    patch_kernel()
    clear_output()

    ipython.register_magic_function(fr_cell, "cell", magic_name="fr")
    ipython.register_magic_function(fr_line, "line", magic_name="fr")

def unload_ipython_extension(ipython):
    pass
