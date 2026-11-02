"""Code spans that wrap across the lines of one paragraph (CommonMark 6.1).

A span ends at the next backtick run of the same length. A run that no later
run in the same paragraph closes is literal text. A paragraph ends at a blank
or quote-only line, a list item, a heading, a thematic break, an HTML line, a
fence, or a change of quote depth, so a stray backtick never pairs across them.
"""
import re

from ste_fences import open_fence, strip_quotes
from ste_text import TAB_WIDTH

BACKTICK_RUN = re.compile(r"`+")
LIST_START = re.compile(r"\s*(?:[-*+]|[0-9]+[.)])(?:\s|$)")
LEAF_LINE = re.compile(r" {0,3}(?:#|<|(?:[-*_=] *){3,}$)")
FENCE_ROOM = 3


def _split(line):
    return strip_quotes(line.expandtabs(TAB_WIDTH))


def _is_leaf(line):
    """True for a line that no paragraph text continues: a heading, a break, HTML, a fence."""
    return bool(LEAF_LINE.match(_split(line)[1]) or open_fence(line, FENCE_ROOM))


def breaks(prev, line):
    """True when `line` cannot continue the paragraph of `prev`."""
    depth, rest = _split(line)
    return (not rest.strip() or bool(LIST_START.match(rest))
            or depth != _split(prev)[0] or _is_leaf(prev) or _is_leaf(line))


def _closes_later(run, lines, start, prev):
    """True when a run of length `run` is in lines[start:] before the paragraph ends."""
    for index in range(start, len(lines)):
        line = lines[index]
        if breaks(prev, line):
            return False
        if any(len(found.group()) == run for found in BACKTICK_RUN.finditer(line)):
            return True
        prev = line
    return False


def code_spans(line, open_run, lines, next_index):
    """Return ((start, end) ranges of code in `line`, open run after it).

    `open_run` is the run length of a span still open from an earlier line, or 0.
    lines[next_index:] are the lines after `line`. The list is never copied, so a
    long file stays linear.
    """
    ranges, start = [], 0 if open_run else None
    runs = list(BACKTICK_RUN.finditer(line))
    for i, run in enumerate(runs):
        size = len(run.group())
        if start is not None:
            if size == open_run:
                ranges.append((start, run.end()))
                start, open_run = None, 0
            continue
        if (any(len(later.group()) == size for later in runs[i + 1:])
                or _closes_later(size, lines, next_index, line)):
            start, open_run = run.start(), size
    if start is not None:
        ranges.append((start, len(line)))
    return ranges, open_run


def blank(text, ranges, fill=" "):
    """Fill each range of `text` with `fill`, so columns stay true."""
    for start, end in ranges:
        text = text[:start] + fill * (end - start) + text[end:]
    return text
