"""Provide a readline wrapper to control a subprocess."""

import builtins
import ctypes
import json
import os
import signal
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

from . import compat

if compat.platform == "darwin":
    import fcntl


def rlwrap_process(args, prompt_control, use_stderr=False):
    assert len(prompt_control) == 1
    # Start process
    process = subprocess.Popen(
        args,
        bufsize=0,
        universal_newlines=True,
        stdin=subprocess.PIPE,
        **{"stderr" if use_stderr else "stdout": subprocess.PIPE},
    )
    # Readline wrapping
    return _rlwrap(process, prompt_control, use_stderr)


def _rlwrap(process, prompt_control, use_stderr=False):
    # Get source and destination
    source = process.stderr if use_stderr else process.stdout
    dest = sys.stderr if use_stderr else sys.stdout

    # Check prompt control
    assert len(prompt_control) == 1

    # Only interactive terminals send bracketed pastes
    paste = None
    if sys.stdin.isatty() and dest.isatty():
        paste = enable_bracketed_paste()

    # Run background task
    with ThreadPoolExecutor(1) as executor:
        future = executor.submit(wait_for_prompt, source, dest, prompt_control)

        # Loop over prompts
        while process.poll() is None:
            # Get prompt
            try:
                prompt = future.result()
            except KeyboardInterrupt:
                process.send_signal(signal.SIGINT)
                continue
            except EOFError:
                break
            else:
                future = executor.submit(wait_for_prompt, source, dest, prompt_control)

            # Get user input
            try:
                raw = read_input(prompt, dest, paste, use_stderr)
            except KeyboardInterrupt:
                process.send_signal(signal.SIGINT)
                continue
            except EOFError:
                break
            else:
                # Send multi-line paste as a single escaped line.
                if "\n" in raw or raw.startswith(prompt_control):
                    raw = prompt_control + json.dumps(raw)
                process.stdin.write(raw + "\n")

        # Close and wait process streams
        process.stdin.close()
        future.exception()

    # Wait process and return code
    return process.wait()


def uses_libedit(readline):
    # readline.backend is new in Python 3.13
    backend = getattr(readline, "backend", None)
    if backend is not None:
        return backend == "editline"
    return "libedit" in (readline.__doc__ or "")


def enable_bracketed_paste():
    try:
        import readline
    except ImportError:
        return None

    if uses_libedit(readline):
        # Bindings start with ESC, which stops ESC from leaving vi insert mode
        if libedit_uses_vi_mode():
            return None
        return LibeditPaste(readline)

    # GNU readline tracks pastes itself
    readline.parse_and_bind("set enable-bracketed-paste on")
    return None


class LibeditPaste:
    """Track bracketed pastes for libedit."""

    MARK = "\x01"

    def __init__(self, readline):
        self.readline = readline
        self.pasting = False

        # libedit unescapes these lines before parsing them
        bind = readline.parse_and_bind
        bind(r"bind \\e[202^A ed-insert")  # insert MARK at the cursor
        bind(r"bind \\e[203~ rl_complete")  # call self.complete
        bind(r"bind \\e[204~ ed-delete-prev-char")  # delete MARK
        # create macro for \e[200, the paste start marker
        bind(r"bind -s \\e[200~ \\e[202^A\\e[203~\\e[204~")
        # call self.complete on \e[201, the paste end marker
        bind(r"bind \\e[201~ rl_complete")
        self.completer = readline.get_completer()
        readline.set_completer(self.complete)

    def complete(self, text, state):
        if text.endswith(self.MARK):
            self.start()
        elif self.pasting:
            self.stop()
        elif self.completer:
            return self.completer(text, state)
        return None

    def start(self):
        self.pasting = True
        # Insert pasted tabs as-is
        self.readline.parse_and_bind("bind ^I ed-insert")

    def stop(self):
        self.pasting = False
        # Restore tab completion
        self.readline.parse_and_bind("bind ^I rl_complete")


def libedit_uses_vi_mode():
    # readline doesn't report the editing mode
    path = os.environ.get("EDITRC", os.path.expanduser("~/.editrc"))
    try:
        with open(path, errors="replace") as f:
            lines = f.read().splitlines()
    except OSError:
        return False

    vi_mode = False
    for line in lines:
        words = line.split()
        if not words or words[0].startswith("#"):
            continue

        command = words[0]
        if ":" in command:
            prog, command = command.split(":", 1)
            # libedit applies the rule if prog matches the program name
            if not prog or prog.lower() not in "python":
                continue

        if command != "bind":
            continue

        # The last bind -v or bind -e wins
        for option in words[1:]:
            if not option.startswith("-"):
                break
            if option[1:2] in ("v", "e"):
                vi_mode = option[1:2] == "v"
                break

    return vi_mode


def read_input(prompt, dest, paste=None, use_stderr=False):
    if paste is None:
        return input(prompt, use_stderr=use_stderr)

    # Tell terminal to wrap paste in \e[200~ and \e[201~
    dest.write("\x1b[?2004h")
    dest.flush()

    try:
        lines = [input(prompt, use_stderr=use_stderr)]
        while paste.pasting:
            lines.append(input("... ", use_stderr=use_stderr))
    finally:
        if paste.pasting:
            paste.stop()
        # Turn off wrap
        dest.write("\x1b[?2004l")
        dest.flush()

    return "\n".join(lines)


def wait_for_prompt(src, dest, prompt_control, buffersize=1):
    def read():
        value = src.read(buffersize)
        if value:
            return value
        raise EOFError

    def write(arg):
        if arg:
            dest.write(arg)
            dest.flush()

    # Prevent exception in macOS with large output (issue #42)
    if compat.platform == "darwin":
        fcntl.fcntl(dest.fileno(), fcntl.F_SETFL, 0)

    # Wait for first prompt control
    while True:
        current = read()
        if prompt_control in current:
            break
        write(current)

    preprompt, current = current.split(prompt_control, 1)
    write(preprompt)

    # Wait for second prompt control
    while prompt_control not in current:
        current += read()

    prompt, postprompt = current.split(prompt_control, 1)
    write(postprompt)

    return prompt


def input(prompt="", use_stderr=False):
    # Use readline if possible
    try:
        import readline  # noqa
    except ImportError:
        return builtins.input(prompt)
    # Use stdout
    if not use_stderr:
        return builtins.input(prompt)
    api = ctypes.pythonapi
    # Cross-platform compatibility
    if compat.platform == "darwin":
        stdin = "__stdinp"
        stderr = "__stderrp"
    else:
        stdin = "stdin"
        stderr = "stderr"
    # Get standard streams
    try:
        fin = ctypes.c_void_p.in_dll(api, stdin)
        ferr = ctypes.c_void_p.in_dll(api, stderr)
    # Cygwin fallback
    except ValueError:
        return builtins.input(prompt)
    # Call readline
    call_readline = api.PyOS_Readline
    call_readline.restype = ctypes.c_char_p
    result = call_readline(fin, ferr, prompt.encode())
    # Decode result
    if len(result) == 0:
        raise EOFError
    return result.decode().rstrip("\n")
