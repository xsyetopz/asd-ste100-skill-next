"""CommonMark block edges of ste-lint: quoted fences, HTML blocks, and paragraph ends.

Each case comes from the upstream selftest, so the fork and upstream agree.
A case gives the text and the lines that hold a semicolon finding.
"""
import unittest

from ste_lint_fixture import BODY26, has, rules


def semicolon_lines(text):
    return [f["line"] for f in rules(text, "semicolon")]


class QuotedFenceTests(unittest.TestCase):
    def test_a_quoted_fence_ends_with_its_quote(self):
        for text, lines in (("> ```\n> code\n\nProse; here.", [4]),
                            ("```\n> ```\nx; y\n```\n\nProse; here.", [6]),
                            (">  > ```\n>  > x; y\n>  > ```\n\nProse; here.", [5]),
                            ("> ```\n>     ```\n> x; y\n> ```\n\nProse; here.", [6]),
                            ("```foo`bar\nProse; here.", [2]),
                            ("```\nx; y\n```` \t\n\nProse; here.", [5]),
                            ("> ```\n> x\nProse; here.", [3]),
                            ("> > ```\n> x; y", [2])):
            self.assertEqual(semicolon_lines(text), lines, text)

    def test_a_tab_counts_from_its_real_column(self):
        for text, line in (("\t```\n\tx = 1\n\t```\n\nProse; here.", 5),
                           ("```\nx\n\t```\ny; z\n```\n\nProse; here.", 7),
                           ("> ```\n> x\n>\t```\n> Use a; b.", 4),
                           ("> ```\n> x\n>  \t```\n> Use a; b.", 4),
                           (">\t> ```\n>\t> x; y\n>\t> ```\n\nProse; here.", 5),
                           ("- Item\n  ```\n\t```\n\nProse; here.", 5)):
            self.assertEqual(semicolon_lines(text), [line], text)

    def test_a_closing_fence_may_sit_three_columns_deeper(self):
        self.assertEqual(semicolon_lines("```\nx; y\n   ```\n\nProse; here."), [5])

    def test_a_tilde_fence_takes_a_backtick_in_its_info(self):
        self.assertEqual(semicolon_lines("~~~ a`b\nx; y\n~~~\n\nProse; here."), [5])


class HtmlBlockTests(unittest.TestCase):
    def test_a_quote_line_in_an_html_block_is_text(self):
        for text, lines in (("<div>\n> ```\n> Prose; here.\n> ```\n</div>", [3]),
                            ("<custom>\n> ```\n> Prose; here.\n> ```\n</custom>", [3]),
                            # comment text is never linted, and no fence opens in it
                            ("<!--\n> ```\n> a; b\n-->\n\nProse; here.", [6]),
                            ("<pre>\n> ```\n> Prose; here.\n> ```\n</pre>", [3]),
                            ("<?php\n> ```\n> Prose; here.\n> ```\n?>", [3]),
                            ("<![CDATA[\n> ```\n> Prose; here.\n> ```\n]]>", [3]),
                            ("<DIV class=x>text\n> ```\n> Prose; here.\n> ```", [3])):
            self.assertEqual(semicolon_lines(text), lines, text)

    def test_a_blank_line_ends_a_tag_block(self):
        for text, lines in (("<div>\n\n> ```\n> x; y\n> ```\n\nProse; here.", [7]),
                            ("<details>\n\n> ```\n> a; b\n> ```\n\n</details>\n\nProse; here.",
                             [9])):
            self.assertEqual(semicolon_lines(text), lines, text)

    def test_inline_html_starts_no_block(self):
        for text in ("<span>Label</span>\n> ```\n> a; b\n> ```",
                     "<kbd>Enter</kbd> starts the job.\n> ```\n> a; b\n> ```",
                     "Text.\n<custom>\n> ```\n> a; b\n> ```",
                     "<custom a=>\n> ```\n> a; b\n> ```"):
            self.assertEqual(semicolon_lines(text), [], text)

    def test_a_type_7_tag_after_a_heading_or_a_fence_starts_a_block(self):
        for text in ("# Title\n<custom>\n> ```\n> Prose; here.\n> ```\n</custom>",
                     "```\nx\n```\n<img src=\"a.png\">\n> ```\n> Prose; here.\n> ```",
                     '<span title="a > b">\n> ```\n> Prose; here.\n> ```'):
            self.assertEqual(len(semicolon_lines(text)), 1, text)

    def test_a_type_1_name_is_no_type_7_tag(self):
        for text in ("<pre/>\n> ```\n> a; b\n> ```", "</pre>\n> ```\n> a; b\n> ```"):
            self.assertEqual(semicolon_lines(text), [], text)
        self.assertEqual(semicolon_lines("<pre-x>\n> ```\n> Prose; here.\n> ```"), [3])

    def test_no_fence_opens_in_an_html_block(self):
        self.assertEqual(semicolon_lines(
            "<pre>\n```\nsample\n</pre>\n\nThe paragraph is here; it must be checked."), [6])
        self.assertEqual(semicolon_lines("<div>\n```\n\nProse; here."), [4])

    def test_the_line_that_ends_a_quoted_fence_can_start_a_block(self):
        self.assertEqual(semicolon_lines("> ```\n> x\n<custom>\n> ```\n> Prose; here."), [5])


class ParagraphEndTests(unittest.TestCase):
    def test_lines_that_end_a_paragraph(self):
        for text in ("Title\n=====\n<custom>\n> ```\n> Prose; here.\n> ```\n</custom>",
                     "> Quote.\n>\n<custom>\n> ```\n> Prose; here.\n> ```\n</custom>",
                     "Title\n-\n<custom>\n> ```\n> Prose; here.\n> ```\n</custom>",
                     "> Quote.\n> >\n<custom>\n> ```\n> Prose; here.\n> ```\n</custom>",
                     "> Note\n> ***\n<custom>\n> ```\n> Prose; here.\n> ```\n</custom>"):
            self.assertEqual(semicolon_lines(text), [5], text)

    def test_lines_that_keep_a_paragraph_open(self):
        for text in ("-*-\n<custom>\n> ```\n> a; b\n> ```",
                     "Intro.\n\n==\n<custom>\n> ```\n> a; b\n> ```",
                     "> Title\n===\n<custom>\n> ```\n> a; b\n> ```",
                     "> > Title\n> lazy\n> ===\n<custom>\n> ```\n> a; b\n> ```",
                     "> # Note\n> ===\n<custom>\n> ```\n> a; b\n> ```"):
            self.assertEqual(semicolon_lines(text), [], text)


class ContainerTests(unittest.TestCase):
    def dangling(self, text):
        return [f["line"] for f in rules(text, "dangling-conjunction")]

    def test_a_fence_at_column_0_ends_a_list_item(self):
        self.assertEqual(self.dangling("- Do this and\n```\nx\n```\n  done"), [1])

    def test_a_quoted_fence_does_not_join_a_list_item(self):
        self.assertEqual(self.dangling("- Item\n  > ```\n  > code\nProse and"), [])
        self.assertEqual(self.dangling("- Do this and\n\n> ```\n> code\n> ```\n  done"), [1])

    def test_an_alert_after_a_fence_is_text(self):
        found = rules(f"> ```\n> x\n> ```\n> [!NOTE]\n> {BODY26}", "long-sentence")
        self.assertEqual(len(found), 1)

    def test_an_alert_after_a_fence_outside_the_quote_is_an_alert(self):
        self.assertFalse(has(f"> Text.\n~~~\ncode\n~~~\n> [!NOTE]\n> {BODY26}", "long-sentence"))

    def test_an_alert_after_a_lazy_line_is_text(self):
        self.assertTrue(has(f"> Intro.\ncontinuation.\n> [!NOTE]\n> {BODY26}", "long-sentence"))

    def test_an_alert_in_an_html_container_is_text(self):
        for opening, closing in (("<details>", "</details>"),
                                 ('<DIV class="note">', "</DIV>"),
                                 ("<section><details>", "</details></section>")):
            text = f"{opening}\n\n> [!NOTE]\n> {BODY26}\n\n{closing}"
            self.assertEqual([f["match"] for f in rules(text, "long-sentence")], ["26 words"])
            self.assertFalse(has(f"{opening}\n{closing}\n\n> [!NOTE]\n> {BODY26}",
                                 "long-sentence"), opening)

    def test_an_inner_close_does_not_close_the_container(self):
        for content in ("<details>\n<div>\n</div>", "<details>\n\n~~~\n</details>\n~~~"):
            text = f"{content}\n\n> [!NOTE]\n> {BODY26}\n\n</details>"
            self.assertEqual([f["match"] for f in rules(text, "long-sentence")], ["26 words"])
        self.assertFalse(has(f"<details>\n~~~\n</details>\n~~~\n\n> [!NOTE]\n> {BODY26}\n\n"
                             "</details>", "long-sentence"))

    def test_tags_that_open_no_container(self):
        for content in ("```html\n<details>\n```", "<!-- <details> -->", "<span>Text.</span>",
                        "<hr>", "<div />", "<details></details>", "</details>"):
            self.assertFalse(has(f"{content}\n\n> [!NOTE]\n> {BODY26}", "long-sentence"),
                             content)


if __name__ == "__main__":
    unittest.main()
