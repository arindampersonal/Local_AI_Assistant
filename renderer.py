import base64
import hashlib
import html
import io
import re

try:
    import markdown
except Exception:
    markdown = None

try:
    from pygments import highlight
    from pygments.formatters import HtmlFormatter
    from pygments.lexers import TextLexer, get_lexer_by_name
except Exception:
    highlight = None
    HtmlFormatter = None
    TextLexer = None
    get_lexer_by_name = None

try:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
except Exception:
    plt = None


FENCED_CODE_RE = re.compile(r"```([A-Za-z0-9_+\-.#]*)[ \t]*\n(.*?)```", re.DOTALL)
DISPLAY_MATH_RE = re.compile(r"\$\$(.+?)\$\$|\\\[(.+?)\\\]", re.DOTALL)
INLINE_MATH_RE = re.compile(r"(?<!\\)\$(?!\s|\$)(.+?)(?<!\s|\\)\$|\\\((.+?)\\\)", re.DOTALL)
PLACEHOLDER_PREFIX = "CHAT_RENDERER_PLACEHOLDER"


class ChatRenderer:
    def __init__(self):
        self.messages = []
        self._ai_index = None
        self.equation_cache = {}

    def add_user(self, text):
        self.messages.append({
            "role": "user",
            "content": text,
        })

    def start_ai(self):
        self.messages.append({
            "role": "assistant",
            "content": "",
            "elapsed": None,
            "done": False,
        })
        self._ai_index = len(self.messages) - 1

    def append_ai(self, text):
        if self._ai_index is None:
            self.start_ai()
        self.messages[self._ai_index]["content"] += text

    def finish_ai(self, elapsed):
        if self._ai_index is None:
            return
        self.messages[self._ai_index]["elapsed"] = elapsed
        self.messages[self._ai_index]["done"] = True
        self._ai_index = None

    def get_html(self, font_size=16):
        font_size = self._safe_font_size(font_size)
        body = "\n".join(
            self._render_message(message, font_size)
            for message in self.messages
        )

        return f"""<!doctype html>
<html>
<head>
<meta charset="utf-8">
<style>
    html, body {{
        margin: 0;
        min-height: 100%;
        background: #111111;
    }}
    body {{
        padding: 18px;
        color: #f2f2f2;
        font-family: "Segoe UI", Arial, sans-serif;
        font-size: {font_size}px;
        line-height: 1.58;
    }}
    .message {{
        box-sizing: border-box;
        width: 100%;
        margin: 0 0 14px;
        padding: 14px 16px;
        border: 1px solid #2f2f2f;
        border-radius: 8px;
        background: #1a1a1a;
    }}
    .message.user {{
        border-color: #2e6ca7;
        background: #142436;
    }}
    .message.assistant {{
        border-color: #3b3b3b;
        background: #1b1b1b;
    }}
    .role {{
        margin-bottom: 8px;
        color: #9ecbff;
        font-size: 0.78em;
        font-weight: 700;
        letter-spacing: 0;
        text-transform: uppercase;
    }}
    .content > :first-child {{
        margin-top: 0;
    }}
    .content > :last-child {{
        margin-bottom: 0;
    }}
    p {{
        margin: 0 0 0.75em;
    }}
    h1, h2, h3, h4, h5, h6 {{
        margin: 1em 0 0.45em;
        color: #ffffff;
        line-height: 1.25;
    }}
    h1 {{ font-size: 1.65em; }}
    h2 {{ font-size: 1.42em; }}
    h3 {{ font-size: 1.24em; }}
    h4, h5, h6 {{ font-size: 1.08em; }}
    strong {{
        font-weight: 700;
        color: #ffffff;
    }}
    em {{
        color: #e8e8e8;
    }}
    ul, ol {{
        margin: 0 0 0.85em 1.35em;
        padding: 0;
    }}
    li {{
        margin: 0.2em 0;
    }}
    blockquote {{
        margin: 0.8em 0;
        padding: 0.15em 0 0.15em 1em;
        border-left: 3px solid #4d86bf;
        color: #d0d0d0;
    }}
    table {{
        border-collapse: collapse;
        margin: 0.85em 0;
        width: 100%;
        max-width: 100%;
    }}
    th, td {{
        border: 1px solid #3f3f3f;
        padding: 0.45em 0.6em;
        text-align: left;
    }}
    th {{
        background: #242424;
    }}
    code {{
        padding: 0.12em 0.32em;
        border: 1px solid #3d3d3d;
        border-radius: 4px;
        background: #242424;
        color: #f5d67b;
        font-family: Consolas, "Cascadia Mono", monospace;
        font-size: 0.92em;
    }}
    pre {{
        margin: 0;
        white-space: pre-wrap;
    }}
    pre code {{
        padding: 0;
        border: 0;
        background: transparent;
        color: inherit;
        font-size: 1em;
    }}
    .code-block {{
        box-sizing: border-box;
        width: 100%;
        margin: 0.9em 0;
        overflow: hidden;
        border: 1px solid #444444;
        border-radius: 8px;
        background: #171717;
    }}
    .code-title {{
        padding: 0.45em 0.7em;
        background: #232323;
        color: #dcdcdc;
        font-size: 0.82em;
        font-weight: 700;
    }}
    .code-body {{
        padding: 0.7em;
        overflow: auto;
    }}
    .math-inline {{
        display: inline-block;
        max-width: 100%;
        vertical-align: -0.22em;
    }}
    .math-block {{
        display: block;
        max-width: 100%;
        margin: 0.85em auto;
    }}
    .math-error {{
        color: #ffb4a9;
    }}
    .meta {{
        margin-top: 0.85em;
        color: #9a9a9a;
        font-size: 0.78em;
    }}
</style>
</head>
<body>
{body}
</body>
</html>"""

    def _render_message(self, message, font_size):
        role = message.get("role", "assistant")
        content = self.render_markdown(message.get("content", ""), font_size)
        meta = ""

        elapsed = message.get("elapsed")
        if elapsed is not None:
            meta = f'<div class="meta">Finished in {elapsed:.1f}s</div>'

        return f"""
<div class="message {html.escape(role)}">
    <div class="role">{html.escape(role)}</div>
    <div class="content">{content}</div>
    {meta}
</div>"""

    def render_markdown(self, text, font_size=16):
        if not text:
            return ""

        placeholders = {}
        protected = self._extract_code_blocks(text, placeholders)
        protected = self._extract_display_math(protected, placeholders, font_size)
        protected = self._extract_inline_math(protected, placeholders, font_size)

        if markdown is None:
            rendered = self._fallback_markdown(protected)
        else:
            rendered = markdown.markdown(
                protected,
                extensions=[
                    "extra",
                    "sane_lists",
                    "smarty",
                    "nl2br",
                ],
                output_format="html5",
            )

        return self._restore_placeholders(rendered, placeholders)

    def _extract_code_blocks(self, text, placeholders):
        def replace(match):
            lang = (match.group(1) or "text").strip() or "text"
            code = match.group(2)
            token = self._add_placeholder(placeholders, self.render_code(lang, code))
            return f"\n\n{token}\n\n"

        return FENCED_CODE_RE.sub(replace, text)

    def _extract_display_math(self, text, placeholders, font_size):
        def replace(match):
            equation = match.group(1) or match.group(2)
            token = self._add_placeholder(
                placeholders,
                self.render_equation(equation, display=True, font_size=font_size),
            )
            return f"\n\n{token}\n\n"

        return DISPLAY_MATH_RE.sub(replace, text)

    def _extract_inline_math(self, text, placeholders, font_size):
        def replace(match):
            equation = match.group(1) or match.group(2)
            token = self._add_placeholder(
                placeholders,
                self.render_equation(equation, display=False, font_size=font_size),
            )
            return token

        return INLINE_MATH_RE.sub(replace, text)

    def _add_placeholder(self, placeholders, value):
        digest = hashlib.sha1(value.encode("utf-8")).hexdigest()[:12]
        token = f"{PLACEHOLDER_PREFIX}_{len(placeholders)}_{digest}"
        placeholders[token] = value
        return token

    def _restore_placeholders(self, rendered, placeholders):
        for token, value in placeholders.items():
            rendered = rendered.replace(f"<p>{token}</p>", value)
            rendered = rendered.replace(token, value)
        return rendered

    def _fallback_markdown(self, text):
        escaped = html.escape(text)

        escaped = re.sub(r"^###### (.+)$", r"<h6>\1</h6>", escaped, flags=re.MULTILINE)
        escaped = re.sub(r"^##### (.+)$", r"<h5>\1</h5>", escaped, flags=re.MULTILINE)
        escaped = re.sub(r"^#### (.+)$", r"<h4>\1</h4>", escaped, flags=re.MULTILINE)
        escaped = re.sub(r"^### (.+)$", r"<h3>\1</h3>", escaped, flags=re.MULTILINE)
        escaped = re.sub(r"^## (.+)$", r"<h2>\1</h2>", escaped, flags=re.MULTILINE)
        escaped = re.sub(r"^# (.+)$", r"<h1>\1</h1>", escaped, flags=re.MULTILINE)
        escaped = re.sub(r"`([^`]+)`", r"<code>\1</code>", escaped)
        escaped = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", escaped)
        escaped = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", escaped)

        paragraphs = []
        for block in escaped.split("\n\n"):
            block = block.strip()
            if not block:
                continue
            if block.startswith("<h"):
                paragraphs.append(block)
            else:
                paragraphs.append(f"<p>{block.replace(chr(10), '<br>')}</p>")
        return "".join(paragraphs)

    def render_code(self, lang, code):
        if highlight is None:
            highlighted = f"<pre><code>{html.escape(code)}</code></pre>"
        else:
            try:
                lexer = get_lexer_by_name(lang)
            except Exception:
                lexer = TextLexer()

            formatter = HtmlFormatter(noclasses=True, style="monokai")
            highlighted = highlight(code, lexer, formatter)

        return f"""
<div class="code-block">
    <div class="code-title">{html.escape(lang)}</div>
    <div class="code-body">{highlighted}</div>
</div>"""

    def render_equation(self, equation, display, font_size):
        equation = equation.strip()
        if not equation:
            return ""

        cache_key = (equation, display, self._safe_font_size(font_size))
        if cache_key not in self.equation_cache:
            self.equation_cache[cache_key] = self._render_equation_png(
                equation,
                display,
                font_size,
            )

        class_name = "math-block" if display else "math-inline"
        alt = html.escape(equation, quote=True)
        uri = self.equation_cache[cache_key]

        if uri is None:
            return f'<code class="math-error">{alt}</code>'

        return f'<img class="{class_name}" src="{uri}" alt="{alt}">'

    def _render_equation_png(self, equation, display, font_size):
        if plt is None:
            return None

        dpi = 180
        size = max(10, self._safe_font_size(font_size))
        if display:
            size += 4

        expression = equation
        if not (expression.startswith("$") and expression.endswith("$")):
            expression = f"${expression}$"

        try:
            fig = plt.figure(figsize=(0.01, 0.01), dpi=dpi)
            fig.patch.set_alpha(0)
            text = fig.text(
                0,
                0,
                expression,
                fontsize=size,
                color="#f2f2f2",
            )
            fig.canvas.draw()
            bbox = text.get_window_extent()
            width = max(1, bbox.width / dpi)
            height = max(1, bbox.height / dpi)
            fig.set_size_inches(width, height)
            text.set_position((0, 0))

            buffer = io.BytesIO()
            fig.savefig(
                buffer,
                format="png",
                dpi=dpi,
                transparent=True,
                bbox_inches="tight",
                pad_inches=0.03,
            )
            plt.close(fig)
        except Exception:
            plt.close("all")
            return None

        encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
        return f"data:image/png;base64,{encoded}"

    def _safe_font_size(self, font_size):
        try:
            value = int(font_size)
        except (TypeError, ValueError):
            value = 16
        return min(32, max(12, value))
