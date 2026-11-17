"""The site's own scripts, one file each. They're read once here and either
joined into /app.js (app.SHARED_SCRIPTS) or put inline in a page with its
nonce - never served from this folder. Their comments are for whoever
works on them: they're left out of what a page sends (strip_comments)."""
import re
from functools import cache
from pathlib import Path

_HERE = Path(__file__).parent

# after one of these, a / starts a regular expression, not a division
_REGEX_AFTER = set("(,=:[!&|?{};+-*%~^<>")
_REGEX_WORDS = {"return", "typeof", "case", "do", "else", "in", "of", "new", "delete", "void", "throw"}


def strip_comments(source: str) -> str:
    """The script without its // and /* */ comments, and the blank lines
    and trailing spaces they leave - strings, template literals and
    regular expressions kept exactly as they are."""
    out, i, n = [], 0, len(source)
    last = ""  # the last character of code (not space), to tell / apart
    while i < n:
        ch = source[i]
        nxt = source[i + 1] if i + 1 < n else ""
        if ch in "'\"`":
            j = i + 1
            while j < n and source[j] != ch:
                j += 2 if source[j] == "\\" else 1
            out.append(source[i:j + 1])
            i, last = j + 1, ch
        elif ch == "/" and nxt == "/":
            while i < n and source[i] != "\n":
                i += 1
        elif ch == "/" and nxt == "*":
            end = source.find("*/", i + 2)
            i = n if end < 0 else end + 2
        elif ch == "/":
            word = re.search(r"([A-Za-z_$]+)\s*$", "".join(out[-3:]))
            if not last or last in _REGEX_AFTER or (word and word.group(1) in _REGEX_WORDS and last.isalpha()):
                # a regular expression: to its closing /, past escapes and [...] classes
                j, in_class = i + 1, False
                while j < n and (source[j] != "/" or in_class) and source[j] != "\n":
                    if source[j] == "\\":
                        j += 1
                    elif source[j] == "[":
                        in_class = True
                    elif source[j] == "]":
                        in_class = False
                    j += 1
                j += 1
                while j < n and source[j].isalpha():
                    j += 1
                out.append(source[i:j])
                i, last = j, "x"
            else:
                out.append(ch)
                i, last = i + 1, ch
        else:
            out.append(ch)
            if not ch.isspace():
                last = ch
            i += 1
    lines = [line.rstrip() for line in "".join(out).split("\n")]
    return "\n".join(line for line in lines if line) + "\n"


@cache
def read(name: str) -> str:
    return strip_comments((_HERE / name).read_text(encoding="utf-8"))
