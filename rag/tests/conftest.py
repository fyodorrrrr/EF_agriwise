from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def make_pdf(tmp_path):
    def _make(name: str, pages: list[str]) -> Path:
        from reportlab.lib.pagesizes import LETTER
        from reportlab.pdfgen import canvas

        path = tmp_path / name
        pdf = canvas.Canvas(str(path), pagesize=LETTER)
        for body in pages:
            text = pdf.beginText(72, 720)
            for line in body.splitlines() or [""]:
                text.textLine(line)
            pdf.drawText(text)
            pdf.showPage()
        pdf.save()
        return path

    return _make
