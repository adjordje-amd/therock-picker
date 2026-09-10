"""Reusable Yes/No confirmation modal for destructive actions."""

from __future__ import annotations

from textual import on
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Label


class ConfirmScreen(ModalScreen[bool]):
    """Modal dialog asking the user to confirm or cancel an action."""

    CSS = """
    ConfirmScreen {
        align: center middle;
    }
    #confirm_dialog {
        width: auto;
        height: auto;
        padding: 1 2;
        border: thick $background 80%;
        background: $surface;
    }
    #confirm_message {
        width: 100%;
        margin-bottom: 1;
        content-align: center middle;
    }
    #confirm_buttons {
        width: auto;
        align: center middle;
    }
    #confirm_buttons Button {
        margin: 0 1;
    }
    """

    def __init__(self, message: str) -> None:
        super().__init__()
        self._message = message

    def compose(self) -> ComposeResult:
        with Vertical(id="confirm_dialog"):
            yield Label(self._message, id="confirm_message")
            with Horizontal(id="confirm_buttons"):
                yield Button("Delete", id="confirm_yes", variant="error")
                yield Button("Cancel", id="confirm_no")

    @on(Button.Pressed, "#confirm_yes")
    def _handle_yes(self) -> None:
        self.dismiss(True)

    @on(Button.Pressed, "#confirm_no")
    def _handle_no(self) -> None:
        self.dismiss(False)
