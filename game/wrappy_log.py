from textual.widgets import Log
from typing import TYPE_CHECKING
from textual._line_split import line_split
from rich.cells import cell_len
from textual.geometry import Size
from textwrap import wrap

from rich.text import Text
import logging


class WrappyLog(Log):
    def write(
        self,
        data: str,
        scroll_end: bool | None = None,
    ):
        if data:
            if not self._lines:
                self._lines.append("")
            for line, ending in line_split(data):
                self._lines[-1] += line

                ls = wrap(self._lines[-1], 120)
                if len(ls) > 1:
                    self._lines = self._lines[:-1]
                    self._lines += ls

                self._width = max(
                    self._width, cell_len(self._process_line(self._lines[-1]))
                )
                self.refresh_lines(len(self._lines) - 1)
                if ending:
                    self._lines.append("")
            self.virtual_size = Size(self._width, self.line_count)

        if self.max_lines is not None and len(self._lines) > self.max_lines:
            self._prune_max_lines()

        auto_scroll = self.auto_scroll if scroll_end is None else scroll_end
        if auto_scroll and not self.is_vertical_scrollbar_grabbed:
            self.scroll_end(animate=False)
        return self
