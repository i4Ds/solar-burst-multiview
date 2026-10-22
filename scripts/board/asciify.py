#!/usr/bin/env python
"""Write the board page as pure ASCII, so it shows the same whatever encoding it is read with
(the published page showed UTF-8 characters as mojibake, e.g. "â€”" for "—").

Non-ASCII characters become \\uXXXX escapes inside <script>, CSS escapes inside <style>,
and HTML numeric entities everywhere else.

    python scripts/board/asciify.py scripts/board/index.html OUT/index.html
"""
import re
import sys


def js(s):
    return "".join(c if ord(c) < 128 else (f"\\u{ord(c):04x}" if ord(c) <= 0xFFFF
                                           else "".join(f"\\u{u:04x}" for u in c.encode("utf-16-be")[::2]))
                   for c in s)


def css(s):
    return "".join(c if ord(c) < 128 else f"\\{ord(c):06x}" for c in s)


def html(s):
    return "".join(c if ord(c) < 128 else f"&#x{ord(c):x};" for c in s)


src = open(sys.argv[1], encoding="utf-8").read()
out, pos = [], 0
for m in re.finditer(r"(<script\b[^>]*>)(.*?)(</script>)|(<style\b[^>]*>)(.*?)(</style>)", src, re.S):
    out.append(html(src[pos:m.start()]))
    if m.group(1):
        out.append(m.group(1) + js(m.group(2)) + m.group(3))
    else:
        out.append(m.group(4) + css(m.group(5)) + m.group(6))
    pos = m.end()
out.append(html(src[pos:]))
res = "".join(out)
assert all(ord(c) < 128 for c in res)
open(sys.argv[2], "w", encoding="ascii").write(res)
print(f"{sys.argv[2]}: ascii only")
