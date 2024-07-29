# AUTOGENERATED! DO NOT EDIT! File to edit: ../nbs/05_notebook.ipynb.

# %% auto 0
__all__ = ['update_code_self', 'update_code_next', 'detect_environment', 'vscode_extract_path', 'vscode_get_cells',
           'nbclassic_patch_kernel', 'nbclassic_add_cell', 'nbclassic_update_cell', 'nbclassic_execute_cell',
           'nbclassic_render_cell', 'nbclassic_delete_cell', 'nbclassic_get_cells']

# %% ../nbs/05_notebook.ipynb 2
from IPython import get_ipython
from IPython.display import display, clear_output, Markdown, Javascript
import json
import os
import time
import psutil
from urllib.parse import urlparse
import warnings
from .utils import nict

# %% ../nbs/05_notebook.ipynb 4
def update_code_self(source:str):
    """
    Updates the current cell with the contents of the cell passed as argument.

    The update will take place after the cell has finished executing.
    Works with all front-ennds.
    """

    payload = dict(
        source="set_next_input",
        text=source,
        replace=True,
        clear_output=False
    )
    # We have to call payload_manager directly because ip.set_next_input does not have a clear_output parameter
    get_ipython().payload_manager.write_payload(payload, single=False)


# %% ../nbs/05_notebook.ipynb 5
def update_code_next(source:str):
    """
    Updates the next cell with the code passed as argument.

    The update will take place after the cell has finished executing.
    Works with all front-ennds.
    """
    payload = dict(
        source="set_next_input",
        text=source,
        replace=False,
        clear_output=False
    )
    # We have to call payload_manager directly because ip.set_next_input does not have a clear_output parameter
    get_ipython().payload_manager.write_payload(payload, single=False)

# %% ../nbs/05_notebook.ipynb 6
def detect_environment():
    """
    Detects if we are running in vscode, Jupyter nbclassic, or Jupyter notebook 7 / Jupyter lab.
    """

    parent_cmdline = psutil.Process(os.getppid()).cmdline()

    for l in parent_cmdline:
        # Vscode might have a different name (e,g, cursor), but it should have "vscode" somewhere in the command line.
        if "vscode" in l.lower():
            return "vscode"

        # jupyter-nbclassic is the modern name of the "old" Jupyter notebook, as it was in Jupyter 6.
        if "jupyter-nbclassic" in l:
            return "nbclassic"

        # jupyter-notebook is probably Jupyter notebook 7, which is a re-skin of Jupyter lab
        if "jupyter-lab" in l or "jupyter-notebook" in l:
            return "jupyterlab"

    warnings.warn("Could not detect environment. Functionality might be limited.")
    return "unknown"

# %% ../nbs/05_notebook.ipynb 7
def inject_js(js:str):
    """Inject javascript into the notebook

    Args:
        js (str): The javascript code to be injected.

    After the injection, it will be overwrittent with an empty string to avoid running it again on notebook load.
    """

    display_handle = display(Javascript(js), display_id=True)
    display_handle.update(Javascript(""))

# %% ../nbs/05_notebook.ipynb 9
def vscode_extract_path():
    """
    Extracts the filename from the parent_header of the current notebook.
    """
    cellid = get_ipython().parent_header.get("metadata", {}).get("cellId", '')
    url = urlparse(cellid)
    return url.path

def vscode_get_cells(num_cells):
    path = vscode_extract_path()

    def get_last_modified(path):
        try: return os.path.getmtime(path)
        except BaseException as e:
            warnings.warn(f"{e}: Could not get mtime for {path}")
            return 0

    if path:
        exec_cnt = get_ipython().execution_count
        ts = time.time()

        display(Javascript("")) # Empty js to kick off autosave.
        last_modified = get_last_modified(path)

        # Wait for the file to be saved.
        for i in range(50):
            last_modified = get_last_modified(path)
            if last_modified > ts:
                break
            time.sleep(0.1)
        else:
            warnings.warn("Make sure autosave is set to afterDelay in vscode settings, and the delay is less than a second!")

        for i in range(50):
            try: # In case the file is being written to and is not parseable.
                with open(path) as f:
                    data = json.load(f)
                    cells = data.get("cells", [])
                    for idx, cell in enumerate(cells):
                        if cell.get("execution_count") == exec_cnt:
                            cells = [ nict(c) for c in cells[(max(0, idx-num_cells)):idx] ]
                            # source is saved as an array of strings in ipynb.
                            for c in cells: c.source = "\n".join(c.source)
                            return idx, cells
            except: pass
            time.sleep(0.1)

        warnings.warn(f"Could not find the cell data in {path} . The assistant won't be able to see previous cells.")
    else:
        warnings.warn("VSCode did not send a cellId in the parent_header. The assistant won't be able to see previous cells.")

    return None, []

# %% ../nbs/05_notebook.ipynb 13
def nbclassic_patch_kernel():
    """
    Overrides Codecell.execute to add cell_index cell_id,
    and possibly cells_above to the extras passed to the kernel.

    The execute() is based on the one in Jupyter nbclassic with the features added.
    """

    payload = """
        console.log("patching nbclassic execute function...")
        Jupyter.CodeCell.prototype.execute = function (stop_on_error) {
            if (!this.kernel) {
                console.log(i18n.msg._("Can't execute cell since kernel is not set."));
                return;
            }

            if (stop_on_error === undefined) {
                if (this.metadata !== undefined &&
                        this.metadata.tags !== undefined) {
                    if (this.metadata.tags.indexOf('raises-exception') !== -1) {
                        stop_on_error = false;
                    } else {
                        stop_on_error = true;
                    }
                } else {
                stop_on_error = true;
                }
            }

            this.clear_output(false, true);
            var old_msg_id = this.last_msg_id;
            if (old_msg_id) {
                this.kernel.clear_callbacks_for_msg(old_msg_id);
                delete Jupyter.CodeCell.msg_cells[old_msg_id];
                this.last_msg_id = null;
            }
            if (this.get_text().trim().length === 0) {
                // nothing to do
                this.set_input_prompt(null);
                return;
            }
            this.set_input_prompt('*');
            this.element.addClass("running");
            var callbacks = this.get_callbacks();


            const cell_index = Jupyter.notebook.find_cell_index(this)

            let extras = {
                cell_index : cell_index,
                cell_id: this.id
            }
            let text = this.get_text().trim()
            let firstLine = text.split('\\n')[0];

            // Parse the magic command
            if (firstLine.startsWith("%%fr")) {
                // Separate args by spaces or tabs
                let parts = firstLine.split(/\\s+|\\t+/);
                let magic = parts[0];
                if (parts.length > 1) {
                    let magic_args = parts.slice(1);
                    let plusNArg = magic_args.find(arg => arg.startsWith('+') && !isNaN(parseInt(arg.slice(1))));
                    if (plusNArg) {
                        let n = parseInt(plusNArg.slice(1));
                        let start_pos = Math.max(0, cell_index - n);
                        cells = Jupyter.notebook.get_cells().slice(start_pos, cell_index);

                        extras = {
                            cells_above: cells,
                            ...extras
                        }
                    }
                }
            }

            this.last_msg_id = this.kernel.execute(
                this.get_text(),
                callbacks,
                {silent: false, store_history: true, stop_on_error : stop_on_error, ...extras });
            Jupyter.CodeCell.msg_cells[this.last_msg_id] = this;
            this.render();
            this.events.trigger('execute.CodeCell', {cell: this});
            var that = this;
            function handleFinished(evt, data) {
                if (that.kernel.id === data.kernel.id && that.last_msg_id === data.msg_id) {
                        that.events.trigger('finished_execute.CodeCell', {cell: that});
                    that.events.off('finished_iopub.Kernel', handleFinished);
                }
            }
            this.events.on('finished_iopub.Kernel', handleFinished);
        };
        Jupyter.notebook.events.trigger('set_dirty.Notebook', {value: true});
        Jupyter.notebook._fully_patched = true;
        console.log("Done.")
    """
    inject_js(payload)

# %% ../nbs/05_notebook.ipynb 14
def nbclassic_add_cell(
        idx:int = None,         # Index of the cell to add. If none, add the cell under the selected one.
        cell_type:str = "code"  # Type of cell to add. Can be "code", "markdown", "raw"
    ):
    """
    Add a new notebook cell to an nbclassic notebook.
    Uses nbclassic-specific JS injection.
    """
    if not idx:
        index_payload = "let index = Jupyter.notebook.get_selected_index()+1;"
    else:
        index_payload = f"let index = {idx}"

    payload = f"""
        {index_payload}

        Jupyter.notebook.insert_cell_at_index("{cell_type}", index)
        let cell = Jupyter.notebook.get_cell(index);
        cell.events.trigger('set_dirty.Notebook', {{value: true}});
    """

    inject_js(payload)

# %% ../nbs/05_notebook.ipynb 15
def nbclassic_update_cell(
    idx:int, # Index of the cell to update. None to update the current cell
    text:str, # Text to set in the cell
    flush:bool = True # Notify Jupyter that the cell has been updated.
    ):
    """
    Update the text of a cell in an nbclassic notebook.
    Uses nbclassic-specific JS injection.
    """

    def escape_for_js(text):
        # Use json.dumps to escape the string for JavaScript
        escaped = json.dumps(text)
        # Remove the surrounding quotes added by json.dumps
        escaped = escaped[1:-1]
        # Escape backticks and ${} sequences
        return escaped.replace('`', '\\`').replace('${', '\\${')

    payload = f"""
        let cell = Jupyter.notebook.get_cell({idx})
        cell.set_text(`{escape_for_js(text)}`)
    """
    if flush:
         payload = payload + "\nJupyter.notebook.events.trigger('set_dirty.Notebook', {value: true});"
    inject_js(payload)

# %% ../nbs/05_notebook.ipynb 16
def nbclassic_execute_cell(
        idx:int # Index of the cell to execute. They start at 0
    ):
    """
    Execute a cell in an nbclassic notebook.
    Uses nbclassic-specific JS injection.
    """

    payload = f"""
        console.log("execute_cell", {idx});
        Jupyter.notebook.events.trigger('set_dirty.Notebook', {{value: true}});
        let cell = Jupyter.notebook.get_cell({idx})
        cell.execute()
    """
    # tt = display(f"About to run the cell {idx}...", display_id=True)
    inject_js(payload)

# %% ../nbs/05_notebook.ipynb 17
def nbclassic_render_cell(idx:int): # Cell to render.
    """
    Re-render a cell in an nbclassic notebook.
    Uses nbclassic-specific JS injection.
    """

    payload = f"""
        let cell = Jupyter.notebook.get_cell({idx})
        cell.unrender()
        Jupyter.notebook.events.trigger('set_dirty.Notebook', {{value: true}});

        cell.render()
    """

    inject_js(payload)

# %% ../nbs/05_notebook.ipynb 18
def nbclassic_delete_cell(idx:int): # Cell to delete.
    """
    Delete a cell in an nbclassic notebook.
    Uses nbclassic-specific JS injection.
    """

    payload = f"""
        console.log("deleting cell", {idx});
        Jupyter.notebook.delete_cell({idx});
        Jupyter.notebook.events.trigger('set_dirty.Notebook', {{value: true}});
    """

    inject_js(payload)

# %% ../nbs/05_notebook.ipynb 19
def nbclassic_get_cells(num_cells:int):
    """
    Get the cells in an nbclassic notebook.
    The notebook should have been patched with nbclassic_patch_kernel.
    """

    header = nict(get_ipython().parent_header)

    cell_index = header.get("content", {}).get("cell_index", None)
    if cell_index is None:
        warnings.warn("Jupyter did not send the cell index. Has it been patched with nbclassic_patch_kernel?")

    expected_num_cells = min(cell_index, num_cells)
    cells = header.get("content", {}).get("cells_above", [])
    if len(cells) < expected_num_cells:
        warnings.warn(f"Expected {expected_num_cells} cells, but got {len(cells)}")

    return cell_index, cells