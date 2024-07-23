__version__ = "0.0.3"

from .magic_cell import fr_cell
from .magic_line import fr_line
from .utils.nbclassic import patch_kernel

def load_ipython_extension(ipython):
    patch_kernel()
    ipython.register_magic_function(fr_cell, "cell", magic_name="fr")
    ipython.register_magic_function(fr_line, "line", magic_name="fr")

def unload_ipython_extension(ipython):
    pass
