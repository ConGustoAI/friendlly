# AUTOGENERATED! DO NOT EDIT! File to edit: ../../nbs/03_utils.capture_io.ipynb.

# %% auto 0
__all__ = ['TeeIO']

# %% ../../nbs/03_utils.capture_io.ipynb 2
from io import StringIO

# %% ../../nbs/03_utils.capture_io.ipynb 3
class TeeIO:
    """
    OutStream that and also passes it to the original stream.
    """
    def __init__(self, stream):
        self._io = StringIO()
        self._stream = stream
        self._call_log = []

    def write(self, s):
        self._io.write(s)
        return self._stream.write(s)

    def getvalue(self):
        return self._io.getvalue()

    # ipykernel's OutStream class defined some other things, pass them to the parent.
    def __getattr__(self, name):
        if name in ['_stream', '_io', '_call_log']:
            # This will call object.__getattr__ on self, returning the real self.value
            return super().__getattr__(name)
        self._call_log.append(("getattr", name))
        return getattr(self._stream, name)

    def __setattr__(self, name, value):
        if name in ['_stream', '_io', '_call_log']:
            super().__setattr__(name, value)
        else:
            self._call_log.append(("setattr", name, value))
            setattr(self._stdout, name, value)
