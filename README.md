# Local Infrastructure AI Assistant

A polished desktop chat interface for local Ollama models, built with Python, CustomTkinter, and `tkinterweb`.

This project is designed for people who want a lightweight alternative to a full Ollama GUI while still keeping the essentials: fast streaming responses, model selection, readable Markdown output, code highlighting, adjustable text size, and LaTeX equation rendering.

## Highlights

- Local-first chat UI powered by Ollama
- Streaming assistant responses
- Model picker populated from locally installed Ollama models
- `No Think` mode using Ollama's `think=False` option for supported models
- Full-width chat rendering that uses the available window space
- Adjustable chat and input text size
- Conversation actions: clear, regenerate, and stop
- Markdown rendering for headers, bold, italics, lists, tables, and blockquotes
- Inline code and fenced code blocks
- Syntax highlighting with Pygments
- LaTeX equation rendering to PNG with matplotlib mathtext
- In-memory equation caching for repeated formulas
- Local chat history saved to `chat_history.json`

## Preview

The app opens as a dark desktop chat client with:

- a toolbar for selecting the Ollama model
- a `No Think` toggle
- a text-size dropdown
- full-width rendered conversation cards
- a multiline prompt box with Run and Stop controls

## Requirements

- Python 3.10 or newer
- Ollama installed and running locally
- At least one Ollama model pulled locally

Example:

```powershell
ollama pull gemma4:12b
```

You can use any local Ollama chat model. The app automatically lists models returned by `ollama.list()`.

## Installation

Clone the repository, then install the Python dependencies:

```powershell
pip install -r requirements.txt
```

If you prefer an isolated environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Running The App

Start Ollama first if it is not already running:

```powershell
ollama serve
```

Then launch the GUI:

```powershell
python main.py
```

## Using No Think Mode

The `No Think` toggle is enabled by default. When enabled, the app sends:

```python
think=False
```

to Ollama's chat API. For models that support thinking controls, this can reduce reasoning overhead and make streaming responses feel faster.

The app also uses:

```python
keep_alive="10m"
```

so the selected model stays warm for follow-up prompts.

## Markdown Support

Assistant responses are rendered as Markdown. Supported formatting includes:

```markdown
# Heading
## Subheading

This is **bold**, *italic*, and `inline code`.

- Lists
- Tables
- Blockquotes
```

Fenced code blocks are rendered with syntax highlighting:

````markdown
```python
def hello():
    print("Hello from Ollama")
```
````

## Mathematical Equations

The renderer supports inline and display equations.

Inline math:

```markdown
Einstein's equation is $E = mc^2$.
```

Display math:

```markdown
$$
\int_0^1 x^2\,dx = \frac{1}{3}
$$
```

Alternative display syntax is also supported:

```markdown
\[
\nabla \cdot \vec{E} = \frac{\rho}{\epsilon_0}
\]
```

Equations are rendered to transparent PNG images using matplotlib mathtext and cached in memory, so repeated equations do not need to be rendered again during the session.

## Project Structure

```text
.
├── main.py           # Desktop GUI, Ollama streaming, model controls, chat actions
├── renderer.py       # Markdown, Pygments code blocks, LaTeX PNG rendering, HTML/CSS
├── requirements.txt  # Python dependencies
├── .gitignore        # Local/generated files excluded from Git
└── README.md         # Project documentation
```

## Generated Files

The app may create `chat_history.json` while running. This file stores local conversation history and is intentionally ignored by Git.

Other generated files such as `__pycache__/` are also ignored.

## Dependencies

- `customtkinter` for the desktop UI
- `tkinterweb` for rendering HTML inside the app
- `ollama` for the local model API
- `markdown` for Markdown to HTML conversion
- `pygments` for syntax highlighting
- `matplotlib` for LaTeX-style math rendering

## Notes

- The first response from a large local model may still take time while the model loads into memory.
- Follow-up responses are usually faster because the app keeps the model alive for 10 minutes.
- `think=False` only changes behavior for models and Ollama versions that support thinking controls.
- This is a local GUI wrapper. Your prompts and responses stay on your machine unless your Ollama setup points elsewhere.

## Roadmap Ideas

- Conversation sessions and named chats
- Export chat to Markdown or HTML
- Copy buttons for code blocks
- Theme selection
- Token and response timing display
- Persistent user settings

## License

No license has been added yet. Add a license file before publishing if you want others to use, modify, or redistribute the project.
