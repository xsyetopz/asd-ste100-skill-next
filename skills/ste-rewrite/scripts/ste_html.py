"""HTML blocks and HTML containers for ste-lint.

An HTML block holds literal text, so a ">" line in it is no quote and no fence
opens in it (CommonMark 4.6). A container such as <details> stays open past a
blank line, and GitHub shows an alert marker inside it as text.
"""
import re

from ste_text import mask

# CommonMark 4.6: the tag names of a type 6 block.
BLOCK_TAGS = (
    "address|article|aside|base|basefont|blockquote|body|caption|center|col|colgroup|dd|"
    "details|dialog|dir|div|dl|dt|fieldset|figcaption|figure|footer|form|frame|frameset|"
    "h[1-6]|head|header|hr|html|iframe|legend|li|link|main|menu|menuitem|nav|noframes|ol|"
    "optgroup|option|p|param|search|section|summary|table|tbody|td|tfoot|th|thead|title|"
    "tr|track|ul")
TYPE1_NAMES = "pre|script|style|textarea"
# The start of each kind of block, and the text that ends it. None: a blank line ends it.
BLOCK_KINDS = (
    (re.compile(r" {0,3}<(?:%s)(?:\s|>|$)" % TYPE1_NAMES, re.I),
     re.compile(r"</(?:%s)>" % TYPE1_NAMES, re.I)),
    (re.compile(r" {0,3}<!--"), re.compile(r"-->")),
    (re.compile(r" {0,3}<\?"), re.compile(r"\?>")),
    (re.compile(r" {0,3}<!\[CDATA\["), re.compile(r"\]\]>")),
    (re.compile(r" {0,3}<![A-Za-z]"), re.compile(r">")),
    (re.compile(r" {0,3}</?(?:%s)(?:\s|/?>|$)" % BLOCK_TAGS, re.I), None),
)
# Type 7: one complete open or closing tag alone on its line (the grammar of
# CommonMark 6.6). A type 1 name never starts one, but "pre-x" does.
ATTRIBUTE = r"\s+[A-Za-z_:][A-Za-z0-9_.:-]*(?:\s*=\s*(?:[^\s\"'=<>`]+|'[^']*'|\"[^\"]*\"))?"
NOT_TYPE1 = r"(?!(?i:%s)(?![A-Za-z0-9-]))" % TYPE1_NAMES
TYPE7 = re.compile(r" {0,3}(?:<%s[A-Za-z][A-Za-z0-9-]*(?:%s)*\s*/?>|</%s[A-Za-z][A-Za-z0-9-]*\s*>)\s*"
                   % (NOT_TYPE1, ATTRIBUTE, NOT_TYPE1))

# Block containers, not inline or void tags such as span or hr.
CONTAINER = re.compile(
    r"<(/?)(address|article|aside|blockquote|body|caption|center|dd|details|"
    r"dialog|dir|div|dl|dt|fieldset|figcaption|figure|footer|form|h[1-6]|"
    r"header|hgroup|html|iframe|legend|li|main|menu|nav|noframes|ol|"
    r"optgroup|option|p|pre|script|search|section|style|summary|table|"
    r"tbody|td|textarea|tfoot|th|thead|title|tr|ul)(?=[\s/>])[^>]*>", re.I)
SELF_CLOSING = "/>"


def html_step(block, line, in_paragraph):
    """Return (in_block, open_block) for one line.

    `block` is None, False for a block that a blank line ends, or the pattern
    that ends the open block. A type 7 tag cannot interrupt a paragraph, so
    `in_paragraph` blocks it.
    """
    if block is None:
        for start, end in BLOCK_KINDS:
            if start.match(line):
                block = False if end is None else end
                break
        else:
            if in_paragraph or not TYPE7.fullmatch(line):
                return False, None
            block = False
    if not isinstance(block, re.Pattern):
        return bool(line.strip()), (False if line.strip() else None)
    return True, (None if block.search(line) else block)


def track_containers(stack, line):
    """Push each container tag that a line opens, and pop to each one it closes."""
    if not CONTAINER.match(line.lstrip()):
        return
    for tag in CONTAINER.finditer(mask(line)):
        name = tag.group(2).lower()
        if tag.group(1):
            if name in stack:
                while stack.pop() != name:
                    pass
        elif not tag.group().endswith(SELF_CLOSING):
            stack.append(name)
