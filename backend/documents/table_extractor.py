"""Table extraction from PDF, HTML, XLSX and DOCX."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Table:
    headers: list[str] = field(default_factory=list)
    rows: list[list[str]] = field(default_factory=list)
    page_number: int | None = None
    caption: str | None = None

    @property
    def markdown(self) -> str:
        if not self.headers:
            return ""
        head = "| " + " | ".join(self.headers) + " |"
        sep = "|" + "|".join("---" for _ in self.headers) + "|"
        rows = ["| " + " | ".join(r) + " |" for r in self.rows]
        return "\n".join([head, sep] + rows)

    @property
    def csv(self) -> str:
        import csv, io
        buf = io.StringIO()
        w = csv.writer(buf)
        if self.headers:
            w.writerow(self.headers)
        w.writerows(self.rows)
        return buf.getvalue()


def from_html(raw: str) -> list[Table]:
    try:
        import pandas as pd
        from io import StringIO
        frames = pd.read_html(StringIO(raw))
        return [Table(headers=[str(c) for c in f.columns],
                      rows=[[str(v) for v in row] for row in f.values])
                for f in frames]
    except Exception:
        return []


def from_pdf(data: bytes) -> list[Table]:
    try:
        import camelot, io, tempfile
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as fh:
            fh.write(data)
            path = fh.name
        tables = camelot.read_pdf(path, flavor="lattice")
        return [Table(headers=list(df.columns),
                      rows=df.astype(str).values.tolist(),
                      page_number=page + 1)
                for page, df in enumerate(tables)]
    except Exception:
        return []


def from_xlsx(data: bytes) -> list[Table]:
    try:
        import openpyxl, io
        wb = openpyxl.load_workbook(io.BytesIO(data), read_only=True, data_only=True)
        out = []
        for ws in wb.worksheets:
            rows = [[str(v) if v is not None else "" for v in r]
                    for r in ws.iter_rows(values_only=True)]
            if rows:
                out.append(Table(headers=rows[0], rows=rows[1:], caption=ws.title))
        return out
    except Exception:
        return []


def from_docx(data: bytes) -> list[Table]:
    try:
        import io
        from docx import Document as Docx
        d = Docx(io.BytesIO(data))
        return [Table(headers=[c.text for c in t.rows[0].cells],
                      rows=[[c.text for c in row.cells] for row in t.rows[1:]])
                for t in d.tables if t.rows]
    except Exception:
        return []
