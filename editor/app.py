#!/usr/bin/env python3
"""
QSTEAP Lab website editor.

A small local web app for editing the website content without touching code.
Run it with the launcher (start-editor.command on Mac, start-editor.bat on
Windows) or:  python3 editor/app.py   then open http://localhost:5055
"""
import os
import re
import shutil
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path

import yaml
from flask import Flask, jsonify, request, send_from_directory, abort
from werkzeug.utils import secure_filename

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "_site"
UPLOADS = ROOT / "images" / "uploads"
PORT = int(os.environ.get("QSTEAP_EDITOR_PORT", "5055"))

DATA_FILES = {
    "lab": ROOT / "_lab.yml",
    "team": ROOT / "data" / "team.yml",
    "publications": ROOT / "data" / "publications.yml",
    "news": ROOT / "data" / "news.yml",
    "research": ROOT / "data" / "research.yml",
}
PAGES = {
    "home": ROOT / "index.qmd",
    "research": ROOT / "research.qmd",
    "join": ROOT / "join.qmd",
    "contact": ROOT / "contact.qmd",
}

app = Flask(__name__, static_folder=None)
app.json.sort_keys = False  # keep field order in the YAML files


# ---------- helpers ----------
class _Dumper(yaml.SafeDumper):
    pass


def _str_presenter(dumper, data):
    style = "|" if "\n" in data else None
    return dumper.represent_scalar("tag:yaml.org,2002:str", data, style=style)


_Dumper.add_representer(str, _str_presenter)


class _Loader(yaml.SafeLoader):
    pass


# keep dates as plain "YYYY-MM-DD" strings (so they round-trip unchanged)
_Loader.add_constructor("tag:yaml.org,2002:timestamp", lambda loader, node: loader.construct_scalar(node))


def load_yaml(path):
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        return yaml.load(f, Loader=_Loader)


def save_yaml(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        yaml.dump(data, f, Dumper=_Dumper, sort_keys=False, allow_unicode=True, width=10000)
    os.replace(tmp, path)


def split_qmd(text):
    m = re.match(r"^---\n(.*?)\n---\n?(.*)$", text, re.S)
    if not m:
        return "", text
    return m.group(1), m.group(2)


def run(cmd, timeout=600):
    try:
        p = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=timeout)
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except FileNotFoundError:
        return 127, f"Command not found: {cmd[0]}"
    except subprocess.TimeoutExpired:
        return 124, "Timed out."


# ---------- BibTeX import (e.g. exported from Google Scholar) ----------
def _bib_fields(body):
    fields, i, n = {}, 0, len(body)
    while i < n:
        m = re.compile(r"\s*,?\s*([A-Za-z_\-]+)\s*=\s*").match(body, i)
        if not m:
            break
        key, i = m.group(1).lower(), m.end()
        if i < n and body[i] == "{":
            depth, j = 0, i
            while j < n:
                if body[j] == "{":
                    depth += 1
                elif body[j] == "}":
                    depth -= 1
                    if depth == 0:
                        break
                j += 1
            val, i = body[i + 1:j], j + 1
        elif i < n and body[i] == '"':
            j = body.find('"', i + 1)
            val, i = body[i + 1:j], j + 1
        else:
            m2 = re.compile(r"[^,}]+").match(body, i)
            val, i = (m2.group(0), m2.end()) if m2 else ("", i + 1)
        fields[key] = re.sub(r"\s+", " ", val.replace("{", "").replace("}", "")).strip()
    return fields


def _short_author(name):
    name = name.strip()
    if "," in name:
        last, first = [x.strip() for x in name.split(",", 1)]
    else:
        parts = name.split()
        last, first = parts[-1], " ".join(parts[:-1])
    initials = " ".join(p[0] + "." for p in re.split(r"[\s]+", first) if p)
    return (initials + " " + last).strip()


def parse_bibtex(text):
    out = []
    for m in re.finditer(r"@(\w+)\s*\{\s*[^,]*,", text):
        kind = m.group(1).lower()
        start, depth, j = m.end(), 1, m.end()
        while j < len(text) and depth:
            if text[j] == "{":
                depth += 1
            elif text[j] == "}":
                depth -= 1
            j += 1
        f = _bib_fields(text[start:j - 1])
        if not f.get("title"):
            continue
        authors = ", ".join(_short_author(a) for a in re.split(r"\s+and\s+", f.get("author", "")) if a.strip())
        venue = f.get("journal") or f.get("booktitle") or f.get("publisher") or ""
        bits = [venue]
        if f.get("volume"):
            bits.append(f["volume"] + (f", {f['pages']}" if f.get("pages") else ""))
        year = f.get("year", "")
        venue_str = " ".join(b for b in bits if b) + (f" ({year})" if year else "")
        arxiv = ""
        am = re.search(r"(\d{4}\.\d{4,5})", " ".join([venue, f.get("eprint", ""), f.get("url", "")]))
        if am and ("arxiv" in venue.lower() or f.get("eprint") or "arxiv" in f.get("url", "")):
            arxiv = am.group(1)
        out.append({
            "title": f["title"],
            "authors": authors,
            "venue": venue_str,
            "year": int(year) if year.isdigit() else year,
            "type": "preprint" if ("arxiv" in venue.lower() and not f.get("volume")) else ("conference" if kind == "inproceedings" else "journal"),
            "doi": f.get("doi", ""),
            "arxiv": arxiv,
            "highlight": False,
        })
    return out


def _norm(t):
    return re.sub(r"[^a-z0-9]", "", str(t).lower())


# ---------- routes ----------
@app.get("/")
def home():
    return send_from_directory(Path(__file__).parent, "index.html")


@app.get("/api/data/<name>")
def get_data(name):
    if name not in DATA_FILES:
        abort(404)
    data = load_yaml(DATA_FILES[name])
    if name == "lab":
        data = (data or {}).get("lab", {})
    return jsonify(data if data is not None else [])


@app.post("/api/data/<name>")
def set_data(name):
    if name not in DATA_FILES:
        abort(404)
    data = request.get_json()
    if name == "lab":
        data = {"lab": data}
    save_yaml(DATA_FILES[name], data)
    return jsonify(ok=True)


@app.get("/api/page/<name>")
def get_page(name):
    if name not in PAGES:
        abort(404)
    fm, body = split_qmd(PAGES[name].read_text(encoding="utf-8"))
    return jsonify(body=body)


@app.post("/api/page/<name>")
def set_page(name):
    if name not in PAGES:
        abort(404)
    path = PAGES[name]
    fm, _ = split_qmd(path.read_text(encoding="utf-8"))
    body = request.get_json().get("body", "")
    path.write_text(f"---\n{fm}\n---\n{body}", encoding="utf-8")
    return jsonify(ok=True)


@app.post("/api/upload")
def upload():
    f = request.files.get("file")
    if not f or not f.filename:
        return jsonify(ok=False, error="No file"), 400
    UPLOADS.mkdir(parents=True, exist_ok=True)
    name = secure_filename(f.filename) or "image"
    stem, ext = os.path.splitext(name)
    dest, k = UPLOADS / name, 1
    while dest.exists():
        dest = UPLOADS / f"{stem}-{k}{ext}"
        k += 1
    f.save(dest)
    return jsonify(ok=True, path=str(dest.relative_to(ROOT)).replace("\\", "/"))


@app.post("/api/bibtex")
def bibtex():
    text = request.get_json().get("text", "")
    new = parse_bibtex(text)
    pubs = load_yaml(DATA_FILES["publications"]) or []
    have = {_norm(p.get("title")) for p in pubs}
    added = [p for p in new if _norm(p["title"]) not in have]
    save_yaml(DATA_FILES["publications"], pubs + added)
    return jsonify(ok=True, found=len(new), added=len(added))


@app.get("/api/status")
def status():
    q = shutil.which("quarto")
    g = shutil.which("git")
    info = {"quarto": bool(q), "git": bool(g), "repo": (ROOT / ".git").exists(), "changes": "", "remote": ""}
    if g and info["repo"]:
        info["changes"] = run(["git", "status", "--short"])[1]
        info["remote"] = run(["git", "remote", "get-url", "origin"])[1].strip()
    return jsonify(info)


@app.post("/api/render")
def render():
    code, out = run(["quarto", "render"])
    return jsonify(ok=code == 0, log=out[-6000:])


@app.post("/api/publish")
def publish():
    msg = (request.get_json() or {}).get("message") or "Update website content"
    logs = []
    for cmd in (["git", "add", "-A"], ["git", "commit", "-m", msg], ["git", "push"]):
        code, out = run(cmd, timeout=180)
        logs.append(f"$ {' '.join(cmd)}\n{out}")
        if code != 0 and not (cmd[1] == "commit" and "nothing to commit" in out):
            return jsonify(ok=False, log="\n".join(logs))
    return jsonify(ok=True, log="\n".join(logs))


# preview of the rendered site
@app.get("/preview/")
@app.get("/preview/<path:p>")
def preview(p="index.html"):
    target = SITE / p
    if target.is_dir():
        p = p.rstrip("/") + "/index.html"
    return send_from_directory(SITE, p)


# images used in the editor thumbnails
@app.get("/files/<path:p>")
def files(p):
    return send_from_directory(ROOT, p)


if __name__ == "__main__":
    url = f"http://localhost:{PORT}"
    print(f"\n  QSTEAP Lab editor running at {url}\n  (close this window to stop it)\n")
    if "--no-browser" not in sys.argv:
        threading.Thread(target=lambda: (time.sleep(1.2), webbrowser.open(url)), daemon=True).start()
    app.run(host="127.0.0.1", port=PORT, debug=False)
