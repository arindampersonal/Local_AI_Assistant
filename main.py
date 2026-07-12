
"""
main.py
Entry point for Local Infrastructure AI Assistant.

Works with:
    renderer.py

Requirements:
    pip install -r requirements.txt
"""

import json
import threading
import time
from pathlib import Path

import customtkinter as ctk
import ollama
from tkinterweb import HtmlFrame

from renderer import ChatRenderer

HISTORY_FILE = Path("chat_history.json")
TEXT_SIZE_OPTIONS = ["14", "16", "18", "20", "22", "24", "28", "32"]


class ModernAIApp(ctk.CTk):

    def __init__(self):
        super().__init__()

        self.title("Local Infrastructure AI Assistant")
        self.geometry("1000x700")

        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")

        self.renderer = ChatRenderer()

        self.stop_requested = False
        self.last_prompt = ""

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        toolbar = ctk.CTkFrame(self)
        toolbar.grid(row=0, column=0, sticky="ew", padx=10, pady=10)

        self.model_box = ctk.CTkComboBox(toolbar, values=self.get_models(), width=250)
        self.model_box.pack(side="left", padx=5)

        self.no_think_var = ctk.BooleanVar(value=True)
        self.no_think_switch = ctk.CTkSwitch(
            toolbar,
            text="No Think",
            variable=self.no_think_var
        )
        self.no_think_switch.pack(side="left", padx=10)

        self.text_size_var = ctk.StringVar(value="18")
        self.text_size_box = ctk.CTkComboBox(
            toolbar,
            values=TEXT_SIZE_OPTIONS,
            variable=self.text_size_var,
            width=80,
            command=self.change_text_size
        )
        self.text_size_box.pack(side="left", padx=5)

        self.clear_btn = ctk.CTkButton(toolbar, text="Clear", command=self.clear_chat)
        self.clear_btn.pack(side="left", padx=5)

        self.regen_btn = ctk.CTkButton(toolbar, text="Regenerate", command=self.regenerate)
        self.regen_btn.pack(side="left", padx=5)

        self.viewer = HtmlFrame(self, messages_enabled=False)
        self.viewer.grid(row=1, column=0, sticky="nsew", padx=10)

        bottom = ctk.CTkFrame(self)
        bottom.grid(row=2, column=0, sticky="ew", padx=10, pady=10)
        bottom.grid_columnconfigure(0, weight=1)

        self.entry = ctk.CTkTextbox(bottom, height=90, font=("Segoe UI", 18))
        self.entry.grid(row=0, column=0, sticky="ew", padx=(0, 10))

        self.run_btn = ctk.CTkButton(bottom, text="Run", command=self.send)
        self.run_btn.grid(row=0, column=1, padx=5)

        self.stop_btn = ctk.CTkButton(bottom, text="Stop", command=self.stop)
        self.stop_btn.grid(row=0, column=2)

        self.load_history()
        self.refresh()

    def get_models(self):
        try:
            resp = ollama.list()
            if hasattr(resp, "models"):
                vals = [getattr(m, "model", getattr(m, "name", "")) for m in resp.models]
            else:
                vals = [(m.get("model") or m.get("name","")) for m in resp.get("models",[])]
            vals = [v for v in vals if v]
            return vals or ["gemma4:12b", "gemma3:12b"]
        except Exception:
            return ["gemma4:12b", "gemma3:12b"]

    def refresh(self):
        self.viewer.load_html(self.renderer.get_html(self.get_text_size()))

    def get_text_size(self):
        try:
            return int(self.text_size_var.get())
        except (TypeError, ValueError):
            return 18

    def change_text_size(self, _choice=None):
        font_size = self.get_text_size()
        self.entry.configure(font=("Segoe UI", font_size))
        self.refresh()

    def save_history(self):
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(self.renderer.messages, f, indent=2)

    def load_history(self):
        if HISTORY_FILE.exists():
            try:
                with open(HISTORY_FILE, encoding="utf-8") as f:
                    self.renderer.messages = json.load(f)
            except Exception:
                self.renderer.messages = []

    def clear_chat(self):
        self.renderer.messages.clear()
        if HISTORY_FILE.exists():
            HISTORY_FILE.unlink()
        self.refresh()

    def regenerate(self):
        if self.last_prompt:
            self.start_generation(self.last_prompt)

    def stop(self):
        self.stop_requested = True

    def send(self):
        prompt = self.entry.get("1.0", "end").strip()
        if not prompt:
            return
        self.entry.delete("1.0", "end")
        self.start_generation(prompt)

    def start_generation(self, prompt):
        self.last_prompt = prompt
        self.stop_requested = False
        model = self.model_box.get()
        no_think = self.no_think_var.get()

        self.renderer.add_user(prompt)
        self.renderer.start_ai()
        self.refresh()

        threading.Thread(
            target=self.generate,
            args=(prompt, model, no_think),
            daemon=True
        ).start()

    def generate(self, prompt, model, no_think):
        start = time.time()

        try:
            stream = self.open_stream(model, prompt, no_think)

            last = time.time()

            for chunk in stream:

                if self.stop_requested:
                    break

                self.renderer.append_ai(self.get_chunk_content(chunk))

                if time.time() - last > 0.08:
                    last = time.time()
                    self.after(0, self.refresh)

            self.renderer.finish_ai(time.time()-start)
            self.after(0, self.refresh)
            self.after(0, self.save_history)

        except Exception as ex:
            self.renderer.append_ai("\n\nError: "+str(ex))
            self.renderer.finish_ai(0)
            self.after(0, self.refresh)

    def open_stream(self, model, prompt, no_think):
        messages = [{
            "role": "user",
            "content": prompt
        }]

        kwargs = {
            "model": model,
            "messages": messages,
            "stream": True,
            "keep_alive": "10m"
        }

        if no_think:
            kwargs["think"] = False

        try:
            return ollama.chat(**kwargs)
        except TypeError:
            if no_think:
                messages[0]["content"] = "/no_think\n\n" + prompt
            kwargs.pop("think", None)
            return ollama.chat(**kwargs)

    def get_chunk_content(self, chunk):
        if isinstance(chunk, dict):
            return chunk.get("message", {}).get("content", "")

        message = getattr(chunk, "message", None)
        if message is None:
            return ""

        if isinstance(message, dict):
            return message.get("content", "")

        return getattr(message, "content", "")


if __name__ == "__main__":
    app = ModernAIApp()
    app.mainloop()
