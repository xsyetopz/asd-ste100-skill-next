"""Document structure for ste-lint.

The scanner turns Markdown into prose blocks with true line and column
positions. It blanks markup and never removes it, so each column stays true.
A block is a list of (line, column, text) pieces that belong to one paragraph,
one heading, one list item, or one table cell. The scanner also records each
list item that ends with "and" or "or".
"""
import re

from ste_fences import closes, ends_with_quote, open_fence, strip_quotes
from ste_html import html_step, track_containers
from ste_tables import is_separator, read_table, split_row
from ste_text import KEEP, LINE_BREAK, TAB_WIDTH, indent_of, mask, prefix_length, view
from ste_words import ALERT_WORDS, LIST_CONJUNCTIONS

FRONT_MATTER = "---"
COMMENT_OPEN = "<!--"
COMMENT_CLOSE = "-->"
HTML_OPEN = "<"
QUOTE_MARK = ">"
FENCE_ROOM = 3      # a fence may start up to 3 spaces inside its own block
CODE_INDENT = 4     # 4 spaces of indentation make a code block
TOP_QUOTE = 1       # a GitHub alert marker works in a quote of depth 1 only
BLANK = " "
MIN_THEMATIC_MARKS = 3   # CommonMark: a thematic break needs 3 marks
MAX_LIST_DIGITS = 9      # CommonMark: an ordered list number has 1 to 9 digits
MAX_MARKER_INDENT = 3    # CommonMark: a marker may sit up to 3 spaces in
HEADING_LEVELS = 6       # CommonMark: ATX headings run from # to ######

REFDEF = re.compile(r"^ {0,%d}\[" % MAX_MARKER_INDENT + r"(?!\^)[^\]]+\]:\s")
COMMENT = re.compile(COMMENT_OPEN + r".*?" + COMMENT_CLOSE)
LIST_ITEM = re.compile(r"^( *)([-*+]|[0-9]{1,%d}[.)])(?:[ \t]+|$)" % MAX_LIST_DIGITS)
THEMATIC = re.compile(r"^ {0,%d}(?:[-*_=] *){%d,}$" % (MAX_MARKER_INDENT, MIN_THEMATIC_MARKS))
HEADING = re.compile(r"^ {0,%d}#{1,%d}(?: |$)" % (MAX_MARKER_INDENT, HEADING_LEVELS))
ALERT = re.compile(r"\[!(?:" + "|".join(ALERT_WORDS) + r")\]", re.I)
CONJUNCTION = re.compile(r"\b(" + "|".join(LIST_CONJUNCTIONS) + r")\s*$", re.I)
# After the quote prefix, these end a paragraph and are no paragraph line: an ATX
# heading, and a thematic break of one repeated character.
NO_PARAGRAPH = re.compile(r" {0,3}(?:#{1,6}(?:\s|$)|(?:-[ \t]*){3,}$|(?:\*[ \t]*){3,}$"
                          r"|(?:_[ \t]*){3,}$)")
# A setext underline ends a paragraph only at the quote depth of that paragraph.
SETEXT_UNDERLINE = re.compile(r" {0,3}(?:=+|-+)[ \t]*$")


class Scanner:
    """One pass over the lines of a document."""

    def __init__(self, text):
        self.lines = LINE_BREAK.split(text)
        self.blocks = []
        self.current = []
        self.dangling = []
        self.fence = None
        self.html = None
        self.containers = []
        self.in_paragraph = False
        self.paragraph_depth = 0
        self.after_boundary = True
        self.comment = False
        self.list_open = False
        self.prev_text = False
        self.prev_quote = False
        self.item = None
        self.index = 0

    def _cut(self):
        if self.current:
            self.blocks.append(self.current)
            self.current = []

    def _close_item(self):
        """End the open list item and record a conjunction at its end."""
        if self.item and self.item["last"]:
            lineno, tail = self.item["last"]
            found = CONJUNCTION.search(tail)
            if found:
                col = (self.item["col"] if lineno == self.item["line"]
                       else found.start(1) + 1)
                self.dangling.append((lineno, col, found.group(1)))
        self.item = None

    def _open_item(self, lineno, marker):
        self._cut()
        self.list_open = True
        self.item = {"line": lineno, "col": marker.start(2) + 1, "last": None,
                     "indent": max(marker.end(), marker.end(2) + 1)}

    def _room(self):
        # Inside a list item a fence sits at the content column of the item.
        return FENCE_ROOM + (self.item["indent"] if self.item else 0)

    def _fence_step(self, raw):
        """Handle a fence line or a line inside a fence. True when consumed."""
        if self.fence:
            if closes(self.fence, raw, self._room()):
                self.fence = None
                self._cut()
                self.after_boundary = self._top_level(raw)
            return True
        found = open_fence(raw, self._room())
        if not found:
            return False
        depth, rest = strip_quotes(raw.expandtabs(TAB_WIDTH))
        if self.item and (depth or indent_of(rest) < self.item["indent"]):
            self._close_item()  # a line outside the item ends it, also a fence
        if not depth and not indent_of(rest):
            self.list_open = False
        self.fence = found
        self._cut()
        self.after_boundary = self._top_level(raw)
        return True

    @staticmethod
    def _top_level(raw):
        """A fence in a quote does not start the quote, so an alert after it is text."""
        return strip_quotes(raw.expandtabs(TAB_WIDTH))[0] == 0

    def _paragraph_step(self, raw, in_html, consumed):
        """Track the open paragraph, which a type 7 HTML tag cannot interrupt."""
        depth, content = strip_quotes(raw.expandtabs(TAB_WIDTH))
        underline = (self.in_paragraph and depth == self.paragraph_depth
                     and SETEXT_UNDERLINE.match(content))
        was_open = self.in_paragraph
        self.in_paragraph = bool(content.strip() and not in_html and not consumed
                                 and not NO_PARAGRAPH.match(content) and not underline)
        if not self.in_paragraph:
            self.paragraph_depth = 0
        elif not was_open or depth > self.paragraph_depth:
            self.paragraph_depth = depth  # a lazy line keeps the depth of its paragraph

    def _comment_step(self, raw):
        """Handle a line inside an HTML comment. True when consumed."""
        if not self.comment:
            return False
        self._cut()
        self.comment = COMMENT_CLOSE not in raw
        return True

    def _blank_comment(self, raw):
        """Blank each closed comment, and the tail of a comment that stays open."""
        line = COMMENT.sub(lambda m: BLANK * len(m.group()), raw)
        start = line.find(COMMENT_OPEN)
        if start >= 0:
            self.comment = True
            line = line[:start] + BLANK * (len(line) - start)
        return line

    def _skip_front_matter(self):
        if self.lines and self.lines[0].strip() == FRONT_MATTER:
            for number, line in enumerate(self.lines[1:], start=1):
                if line.strip() == FRONT_MATTER:
                    self.index = number + 1
                    return

    def _table_step(self, text_line, pre):
        """Read a whole table and give each cell its own block. True when read."""
        if self.index >= len(self.lines):
            return False
        header = split_row(text_line, pre)
        if not header:
            return False
        separator = split_row(self.lines[self.index], prefix_length(self.lines[self.index]))
        if not is_separator(separator, len(header)):
            return False
        self._cut()
        rows, self.index = read_table(self.lines, self.index, header)
        for lineno, row in rows:
            for cell, col in row:
                if cell:
                    self.blocks.append([(lineno, col, cell)])
        self.prev_text = False
        return True

    def run(self):
        self._skip_front_matter()
        while self.index < len(self.lines):
            raw = self.lines[self.index]
            lineno = self.index + 1
            self.index += 1
            self._line(raw, lineno)
        self._cut()
        self._close_item()
        return self.blocks, self.dangling

    def _line(self, raw, lineno):
        if self.fence and ends_with_quote(self.fence, raw):
            self.fence = None  # the quote of the fence ended: judge the line as any other
            self._cut()
        in_html = False
        if not self.fence:
            in_html, self.html = html_step(self.html, raw, self.in_paragraph)
        # An HTML block holds literal text, so no fence opens in it.
        consumed = self._comment_step(raw) or (
            not in_html and not self.comment and self._fence_step(raw))
        self._paragraph_step(raw, in_html, consumed or bool(self.fence))
        if consumed:
            return
        self._text_line(raw, lineno)
        self.after_boundary = not raw.strip()

    def _text_line(self, raw, lineno):
        if not raw.strip():
            self._cut()
            self.prev_text = self.prev_quote = False
            return
        if REFDEF.match(raw):
            self._cut()
            self.prev_text = False
            return
        line = self._blank_comment(raw)
        track_containers(self.containers, line)
        text_line, pre = view(line)
        quoted = pre > 0
        body = line[pre:]
        indent = indent_of(body)
        marker = LIST_ITEM.match(body)
        starts_item = bool(marker) and not THEMATIC.match(body)
        if self.item and (starts_item or quoted or indent < self.item["indent"]):
            self._close_item()
        if not starts_item and not quoted and indent == 0:
            self.list_open = False
        was_quote, self.prev_quote = self.prev_quote, quoted
        if quoted != was_quote:
            self._cut()
        if raw[pre:].lstrip().startswith(HTML_OPEN) or (
                indent >= CODE_INDENT and not self.list_open
                and not self.prev_text and not quoted):
            self._cut()
            self.prev_text = False
            return
        # A GitHub alert marker is markup only on the first line of an unindented
        # top quote, after a blank line, a fence, or the start of the text, and
        # outside an HTML container. Elsewhere GitHub shows it as text.
        if (raw.startswith(QUOTE_MARK) and self.after_boundary and not self.containers
                and line[:pre].count(QUOTE_MARK) == TOP_QUOTE
                and ALERT.fullmatch(body.strip())):
            return
        heading = HEADING.match(body)
        if THEMATIC.match(body) or heading:
            self._cut()
            self.prev_text = False
            if heading:
                end = pre + heading.end()
                self.current.append((lineno, 0, BLANK * end + text_line[end:]))
                self._cut()
            return
        if not starts_item and self._table_step(text_line, pre):
            return
        item_text = mask(line, KEEP)
        if starts_item:
            end = pre + marker.end()
            text_line = BLANK * end + text_line[end:]
            item_text = BLANK * end + item_text[end:]
            self._cut()
            self.list_open = True
            if quoted:
                self.item = None
            else:
                self._open_item(lineno, marker)
        if self.item and item_text.strip():
            self.item["last"] = (lineno, item_text)
        if text_line.strip():
            self.current.append((lineno, 0, text_line))
        self.prev_text = True


def scan(text):
    """Return (blocks, dangling) for one document."""
    return Scanner(text).run()
