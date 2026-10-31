"""Code fences for ste-lint, with the blockquote depth of each fence.

A fence opens on 3 or more backticks or tildes, also inside a blockquote. Only
a run of the same character, at least as long, with no text after it, closes
it. A fence in a blockquote ends when its quote ends (CommonMark 4.5).
"""
import re
from collections import namedtuple

from ste_text import TAB_WIDTH

BACKTICK = "`"
QUOTE_LEVEL = re.compile(r" {0,3}> ?")  # one level: up to 3 spaces, ">", one space
RUN = re.compile(r"`{3,}|~{3,}")
INDENT_CHARS = " \t"

Fence = namedtuple("Fence", "run depth")


def strip_quotes(line, depth=None):
    """Return (levels, rest) for the quote levels that start a tab-expanded line.

    With `depth`, remove at most that many levels: a deeper ">" is content.
    """
    levels, pos = 0, 0
    while depth is None or levels < depth:
        level = QUOTE_LEVEL.match(line, pos)
        if not level:
            break
        levels, pos = levels + 1, level.end()
    return levels, line[pos:]


def _indent(text):
    return len(text) - len(text.lstrip(INDENT_CHARS))


def open_fence(line, room):
    """Return the Fence that a line opens, or None. `room` is the deepest indent."""
    depth, rest = strip_quotes(line.expandtabs(TAB_WIDTH))
    content = rest.lstrip(INDENT_CHARS)
    run = RUN.match(content)
    if not run or _indent(rest) > room:
        return None
    if run.group()[0] == BACKTICK and BACKTICK in content[run.end():]:
        return None
    return Fence(run.group(), depth)


def ends_with_quote(fence, line):
    """True when a line has fewer quote levels than the open fence."""
    return strip_quotes(line.expandtabs(TAB_WIDTH), fence.depth)[0] < fence.depth


def closes(fence, line, room):
    """True when a line inside the fence closes it."""
    rest = strip_quotes(line.expandtabs(TAB_WIDTH), fence.depth)[1]
    content = rest.lstrip(INDENT_CHARS)
    run = RUN.match(content)
    return bool(run and run.group()[0] == fence.run[0] and len(run.group()) >= len(fence.run)
                and _indent(rest) <= room and not content[run.end():].strip(INDENT_CHARS))
