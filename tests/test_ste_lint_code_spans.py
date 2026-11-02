"""Indented code, code spans that wrap lines, and modal perfects across lines.

Each case comes from the upstream selftest of #47, #48, and #49, so the fork and
upstream agree. A case gives the text and the lines that hold a semicolon finding.
"""
import unittest

from ste_lint_fixture import rules


def semicolon_lines(text):
    return [f["line"] for f in rules(text, "semicolon")]


def perfect_lines(text):
    return [f["line"] for f in rules(text, "present-perfect")]


class IndentedCodeTests(unittest.TestCase):
    def test_an_indented_code_block_is_code(self):
        for text in ("Intro text.\n\n    x = 1; y = 2\n\tz; w",
                     "> Intro.\n>\n>     x = 1; y = 2",
                     "- Item.\n\n      x = 1; y = 2",
                     "- Item.\n\nText.\n\n    x; y",
                     "Steps:\n- Open the file.\n\n      x = 1; y = 2\n"):
            self.assertEqual(semicolon_lines(text), [], text)

    def test_an_item_indent_and_a_continuation_are_prose(self):
        for text, lines in (("Intro text\n    goes on; here.", [2]),
                            ("- Item.\n\n    More; text.", [3]),
                            ("1. Item.\n\n   - Sub.\n\n     More; text.", [5]),
                            ("Steps to follow:\n- Open the file.\n\n    Then save it; close it.\n",
                             [4]),
                            ("- Open the file.\n  - Pick a row.\n\n      Then save it; close it.\n",
                             [4]),
                            ("- Item\ncontinued\n\n    More; text.", [4])):
            self.assertEqual(semicolon_lines(text), lines, text)


class WrappedSpanTests(unittest.TestCase):
    def test_a_code_span_wraps_across_lines_of_one_paragraph(self):
        for text, lines in (("Run `a;\nb; c` now; then", [2]),
                            ("Run ``a`;\nb;`` now.", []),
                            ("Run `a;\nb` now.\n", []),
                            ("- Run `a;\n  b` now.\n", []),
                            ("> Run `a;\n> b` now.\n", []),
                            ("Run ``a`;\nb;`` now.\n- Next `x;` y.", [])):
            self.assertEqual(semicolon_lines(text), lines, text)

    def test_a_run_that_nothing_closes_is_text(self):
        self.assertEqual(semicolon_lines("A ` mark; here.\n\nAnd ` there; too."), [1, 3])

    def test_a_code_span_stops_at_a_block_boundary(self):
        for text, lines in (("- Press the ` key; it opens.\n- Run `x` now.\n", [1]),
                            ("Press the ` key; it opens.\n# Run `x` now\n", [1]),
                            ("Type ` to start; then stop.\n```\ncode\n```\nThe ` mark ends it.\n",
                             [1]),
                            ("> A ` mark; here.\n>\n> And ` there; too.\n", [1, 3]),
                            ("# Title ` x\nText; with ` more\n", [2]),
                            ("A ` mark; here.\n---\nAnd ` there; too.", [1, 3]),
                            ("> A ` mark; here.\n> > And ` there; too.", [1, 2])):
            self.assertEqual(semicolon_lines(text), lines, text)

    def test_many_open_runs_stay_linear(self):
        text = "A ` b.\n\n" * 20000
        self.assertEqual(semicolon_lines(text), [])


class ModalPerfectTests(unittest.TestCase):
    def test_more_modal_perfects_are_hedges(self):
        text = ("It cannot have run. It won't have finished. It can't have stopped. "
                "It may well have failed. It may very well have failed. "
                "It shan't have left.")
        self.assertEqual(perfect_lines(text), [])

    def test_a_modal_at_the_end_of_the_line_before_is_a_hedge(self):
        for text in ("The request may\nhave failed.", "It may\nhave failed.",
                     "> It may\n> have failed.", "> > It may\n> > have failed.",
                     "- It may\n  have run.", "> - It may\n>   have run."):
            self.assertEqual(perfect_lines(text), [], text)

    def test_a_modal_in_another_paragraph_is_no_hedge(self):
        self.assertEqual(perfect_lines("It may\n\nhave failed."), [3])
        self.assertEqual(perfect_lines("> It may\n>\n> have failed."), [3])


if __name__ == "__main__":
    unittest.main()
