# ─────────────────────────────────────────
# ENCODING - MUST BE FIRST
# ─────────────────────────────────────────
import sys
import os
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')
os.environ["PYTHONIOENCODING"] = "utf-8"

# ─────────────────────────────────────────
# STANDARD IMPORTS
# ─────────────────────────────────────────
import json
import time
import urllib.request
from html.parser import HTMLParser
from datetime import datetime, date

# ─────────────────────────────────────────
# GOOGLE GEMINI - AI CLIENT
# ─────────────────────────────────────────
from google import genai
from google.genai import types

API_KEY = ""  # ← PASTE YOUR GOOGLE AI STUDIO KEY HERE
client  = genai.Client(api_key=API_KEY)

# ─────────────────────────────────────────
# MODELS - DUAL STRATEGY
# ─────────────────────────────────────────
MODEL_FAST  = "gemini-2.0-flash"
MODEL_SMART = "gemini-2.5-pro"

_smart_calls_today = 0
_smart_calls_date  = date.today()
_MAX_SMART_CALLS   = 100


def choose_model(user_message: str) -> str:
    global _smart_calls_today, _smart_calls_date
    if date.today() != _smart_calls_date:
        _smart_calls_today = 0
        _smart_calls_date  = date.today()
    msg = user_message.lower()
    simple  = ["open","click","type","screenshot","save","read","scroll",
               "wait","close","show","list","go to","navigate","press"]
    complex_ = ["analyz","compare","strategy","plan","summarize","summary",
                "report","optimize","explain","create","design","budget",
                "calculate","step by step","excel","spreadsheet","html",
                "table","chart","graph","following","perform"]
    is_simple  = any(k in msg for k in simple)
    is_complex = any(k in msg for k in complex_) or len(user_message) > 200
    if is_complex and _smart_calls_today < _MAX_SMART_CALLS:
        _smart_calls_today += 1; return MODEL_SMART
    if is_simple and not is_complex:
        return MODEL_FAST
    if _smart_calls_today < _MAX_SMART_CALLS:
        _smart_calls_today += 1; return MODEL_SMART
    return MODEL_FAST


# ─────────────────────────────────────────
# PLAYWRIGHT
# ─────────────────────────────────────────
try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    print("[⚠️  Playwright not available. Run: pip install playwright && playwright install chromium]")

# ─────────────────────────────────────────
# OPENPYXL
# ─────────────────────────────────────────
try:
    import openpyxl
    from openpyxl import Workbook, load_workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.chart import BarChart, LineChart, PieChart, Reference
    EXCEL_AVAILABLE = True
except ImportError:
    EXCEL_AVAILABLE = False
    print("[⚠️  openpyxl not available. Run: pip install openpyxl]")

# ─────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────
DESKTOP = os.path.join(os.path.expanduser("~"), "Desktop")
_playwright = _browser = _page = None


def fix_path(p: str) -> str:
    return p.replace("~/Desktop", DESKTOP).replace("/desktop", DESKTOP).replace("~/desktop", DESKTOP)


# ─────────────────────────────────────────
# BROWSER HELPERS
# ─────────────────────────────────────────
def get_page():
    global _playwright, _browser, _page
    if _page is None:
        _playwright = sync_playwright().start()
        _browser    = _playwright.chromium.launch(headless=False, slow_mo=100)
        _page       = _browser.new_page()
        _page.set_viewport_size({"width": 1280, "height": 800})
    return _page


def close_browser():
    global _playwright, _browser, _page
    for obj, method in [(_browser, "close"), (_playwright, "stop")]:
        if obj:
            try: getattr(obj, method)()
            except: pass
    _page = _browser = _playwright = None


# ─────────────────────────────────────────
# TOOL IMPLEMENTATIONS
# ─────────────────────────────────────────

def _read_file(path):
    path = fix_path(path)
    try:
        with open(path, "r", encoding="utf-8") as f: c = f.read()
        return (c[:10000] + "\n[truncated]") if len(c) > 10000 else c
    except UnicodeDecodeError:
        try:
            with open(path, "r", encoding="cp1250") as f: return f.read()[:10000]
        except Exception as e: return f"Read error: {e}"
    except Exception as e: return f"Read error: {e}"

def _write_file(path, content):
    path = fix_path(path)
    try:
        d = os.path.dirname(path)
        if d: os.makedirs(d, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f: f.write(content)
        return f"Saved: {path} ({len(content)} chars)"
    except Exception as e: return f"Write error: {e}"

def _list_files(directory="."):
    directory = fix_path(directory)
    try:
        result = []
        for e in sorted(os.listdir(directory)):
            full = os.path.join(directory, e)
            if os.path.isdir(full):
                result.append(f"📁 {e}/")
            else:
                s = os.path.getsize(full)
                sz = f"{s} B" if s < 1024 else (f"{s/1024:.1f} KB" if s < 1024**2 else f"{s/1024/1024:.1f} MB")
                result.append(f"📄 {e} ({sz})")
        return "\n".join(result) or "Empty."
    except Exception as e: return f"List error: {e}"

def _open_file(path):
    path = fix_path(path)
    try: os.startfile(path); return f"Opened: {path}"
    except Exception as e: return f"Open error: {e}"

def _delete_file(path):
    path = fix_path(path)
    try:
        if os.path.isfile(path): os.remove(path); return f"Deleted: {path}"
        elif os.path.isdir(path):
            import shutil; shutil.rmtree(path); return f"Deleted folder: {path}"
        return f"Not found: {path}"
    except Exception as e: return f"Delete error: {e}"

def _copy_file(src, dst):
    src, dst = fix_path(src), fix_path(dst)
    try:
        import shutil
        d = os.path.dirname(dst)
        if d: os.makedirs(d, exist_ok=True)
        shutil.copy2(src, dst); return f"Copied: {src} -> {dst}"
    except Exception as e: return f"Copy error: {e}"

def _move_file(src, dst):
    src, dst = fix_path(src), fix_path(dst)
    try:
        import shutil
        d = os.path.dirname(dst)
        if d: os.makedirs(d, exist_ok=True)
        shutil.move(src, dst); return f"Moved: {src} -> {dst}"
    except Exception as e: return f"Move error: {e}"

def _create_directory(path):
    path = fix_path(path)
    try: os.makedirs(path, exist_ok=True); return f"Created: {path}"
    except Exception as e: return f"mkdir error: {e}"

def _browser_goto(url):
    if not PLAYWRIGHT_AVAILABLE: return "Playwright not available."
    try:
        if not url.startswith("http"): url = "https://" + url
        page = get_page()
        page.goto(url, wait_until="domcontentloaded", timeout=20000)
        return f"Opened: {url} | Title: {page.title()}"
    except Exception as e: return f"Navigation error: {e}"

def _browser_click(selector):
    if not PLAYWRIGHT_AVAILABLE: return "Playwright not available."
    try:
        page = get_page(); clicked = False
        for s in [
            lambda: page.get_by_text(selector, exact=False).first.click(timeout=3000),
            lambda: page.get_by_role("button", name=selector).first.click(timeout=3000),
            lambda: page.get_by_role("link",   name=selector).first.click(timeout=3000),
            lambda: page.click(selector, timeout=3000),
        ]:
            try: s(); clicked = True; break
            except: pass
        if not clicked: return f"Element not found: {selector}"
        page.wait_for_load_state("domcontentloaded")
        return f"Clicked: {selector}"
    except Exception as e: return f"Click error: {e}"

def _browser_type(selector, text):
    if not PLAYWRIGHT_AVAILABLE: return "Playwright not available."
    try:
        page = get_page(); filled = False
        for s in [
            lambda: page.get_by_placeholder(selector).first.fill(text, timeout=3000),
            lambda: page.get_by_label(selector).first.fill(text, timeout=3000),
            lambda: page.get_by_role("textbox",   name=selector).first.fill(text, timeout=3000),
            lambda: page.get_by_role("searchbox").first.fill(text, timeout=3000),
            lambda: page.fill(selector, text, timeout=3000),
        ]:
            try: s(); filled = True; break
            except: pass
        if not filled: return f"Field not found: {selector}"
        return f"Typed '{text}' into: {selector}"
    except Exception as e: return f"Type error: {e}"

def _browser_get_text():
    if not PLAYWRIGHT_AVAILABLE: return "Playwright not available."
    try:
        text = get_page().inner_text("body")
        return (text[:6000] + "\n[truncated]") if len(text) > 6000 else text
    except Exception as e: return f"Get text error: {e}"

def _browser_screenshot(path):
    if not PLAYWRIGHT_AVAILABLE: return "Playwright not available."
    path = fix_path(path)
    if not path.endswith(".png"): path += ".png"
    try:
        d = os.path.dirname(path)
        if d: os.makedirs(d, exist_ok=True)
        get_page().screenshot(path=path, full_page=True)
        return f"Screenshot saved: {path}"
    except Exception as e: return f"Screenshot error: {e}"

def _browser_get_links():
    if not PLAYWRIGHT_AVAILABLE: return "Playwright not available."
    try:
        links = get_page().eval_on_selector_all(
            "a[href]", "els=>els.map(e=>({text:e.innerText.trim(),href:e.href})).filter(l=>l.text&&l.href)")
        return "\n".join(f"{l['text'][:60]} -> {l['href']}" for l in links[:40]) or "No links."
    except Exception as e: return f"Get links error: {e}"

def _browser_scroll(direction):
    if not PLAYWRIGHT_AVAILABLE: return "Playwright not available."
    try:
        get_page().keyboard.press({"down":"PageDown","up":"PageUp","top":"Home","bottom":"End"}.get(direction,"PageDown"))
        time.sleep(0.3); return f"Scrolled: {direction}"
    except Exception as e: return f"Scroll error: {e}"

def _browser_press_key(key):
    if not PLAYWRIGHT_AVAILABLE: return "Playwright not available."
    try:
        get_page().keyboard.press(key); time.sleep(0.5); return f"Pressed: {key}"
    except Exception as e: return f"Key error: {e}"

def _browser_select_option(selector, value):
    if not PLAYWRIGHT_AVAILABLE: return "Playwright not available."
    try:
        page = get_page()
        try: page.select_option(selector, label=value, timeout=5000)
        except: page.select_option(selector, value=value, timeout=5000)
        return f"Selected '{value}' in: {selector}"
    except Exception as e: return f"Select error: {e}"

def _browser_wait(seconds):
    try: time.sleep(min(float(seconds), 30)); return f"Waited {seconds}s"
    except Exception as e: return f"Wait error: {e}"

def _browser_current_url():
    if not PLAYWRIGHT_AVAILABLE: return "Playwright not available."
    try: p = get_page(); return f"URL: {p.url} | Title: {p.title()}"
    except Exception as e: return f"URL error: {e}"

def _browser_go_back():
    if not PLAYWRIGHT_AVAILABLE: return "Playwright not available."
    try:
        get_page().go_back(wait_until="domcontentloaded", timeout=10000)
        return f"Went back. URL: {get_page().url}"
    except Exception as e: return f"Go back error: {e}"

def _browser_eval_js(script):
    if not PLAYWRIGHT_AVAILABLE: return "Playwright not available."
    try:
        r = get_page().evaluate(script)
        return str(r)[:3000] if r else "OK (no result)"
    except Exception as e: return f"JS error: {e}"

class TextExtractor(HTMLParser):
    def __init__(self): super().__init__(); self.text = []; self.skip = False
    def handle_starttag(self, tag, attrs):
        if tag in ("script","style","nav","footer","head","noscript"): self.skip = True
    def handle_endtag(self, tag):
        if tag in ("script","style","nav","footer","head","noscript"): self.skip = False
    def handle_data(self, data):
        if not self.skip:
            s = data.strip()
            if s: self.text.append(s)

def _read_webpage(url):
    try:
        if not url.startswith("http"): url = "https://" + url
        req = urllib.request.Request(url, headers={"User-Agent":"Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as r:
            html = r.read().decode("utf-8", errors="ignore")
        p = TextExtractor(); p.feed(html); text = "\n".join(p.text)
        return (text[:8000] + "\n[truncated]") if len(text) > 8000 else text or "No content."
    except Exception as e: return f"Fetch error: {e}"

def _thin_border():
    t = Side(style="thin")
    return Border(left=t, right=t, top=t, bottom=t)

def _create_excel(path, sheets_data):
    if not EXCEL_AVAILABLE: return "openpyxl not available."
    path = fix_path(path)
    if not path.endswith(".xlsx"): path += ".xlsx"
    try:
        wb = Workbook(); wb.remove(wb.active)
        for sd in sheets_data:
            ws = wb.create_sheet(title=sd.get("name","Sheet1"))
            headers = sd.get("headers",[]); rows = sd.get("rows",[])
            if headers:
                ws.append(headers)
                for cell in ws[1]:
                    cell.font = Font(bold=True, color="FFFFFF", size=11)
                    cell.fill = PatternFill("solid", fgColor="4472C4")
                    cell.alignment = Alignment(horizontal="center", vertical="center")
                    cell.border = _thin_border()
            for row in rows:
                ws.append(row)
                for cell in ws[ws.max_row]:
                    cell.border = _thin_border()
                    cell.alignment = Alignment(vertical="center")
            cw = sd.get("col_widths",[])
            if cw:
                for i, w in enumerate(cw):
                    ws.column_dimensions[openpyxl.utils.get_column_letter(i+1)].width = w
            else:
                for col in ws.columns:
                    mx = max((len(str(c.value)) for c in col if c.value), default=10)
                    ws.column_dimensions[col[0].column_letter].width = min(mx+4, 50)
        d = os.path.dirname(path)
        if d: os.makedirs(d, exist_ok=True)
        wb.save(path); return f"Excel '{path}' created ({len(sheets_data)} sheet(s))."
    except Exception as e: return f"Excel create error: {e}"

def _read_excel(path):
    if not EXCEL_AVAILABLE: return "openpyxl not available."
    path = fix_path(path)
    try:
        wb = load_workbook(path, data_only=True); result = []
        for sn in wb.sheetnames:
            ws = wb[sn]; result.append(f"=== Sheet: {sn} ({ws.max_row}r x {ws.max_column}c) ===")
            n = 0
            for row in ws.iter_rows(values_only=True):
                if any(c is not None for c in row):
                    result.append("\t".join(str(c) if c is not None else "" for c in row))
                    n += 1
                    if n > 100: result.append("[truncated]"); break
        return "\n".join(result) or "Empty."
    except Exception as e: return f"Excel read error: {e}"

def _edit_excel_cell(path, sheet_name, cell, value):
    if not EXCEL_AVAILABLE: return "openpyxl not available."
    path = fix_path(path)
    try:
        wb = load_workbook(path); ws = wb[sheet_name] if sheet_name in wb.sheetnames else wb.active
        try:
            v = float(value); value = int(v) if v == int(v) else v
        except: pass
        ws[cell] = value; wb.save(path); return f"Cell {sheet_name}!{cell} = {value}"
    except Exception as e: return f"Cell edit error: {e}"

def _add_excel_formula(path, sheet_name, cell, formula):
    if not EXCEL_AVAILABLE: return "openpyxl not available."
    path = fix_path(path)
    try:
        wb = load_workbook(path); ws = wb[sheet_name] if sheet_name in wb.sheetnames else wb.active
        ws[cell] = formula; wb.save(path); return f"Formula '{formula}' set in {sheet_name}!{cell}"
    except Exception as e: return f"Formula error: {e}"

def _add_excel_chart(path, sheet_name, chart_type, data_range, title, position):
    if not EXCEL_AVAILABLE: return "openpyxl not available."
    path = fix_path(path)
    try:
        wb = load_workbook(path); ws = wb[sheet_name] if sheet_name in wb.sheetnames else wb.active
        ref = Reference(ws, range_string=f"{sheet_name}!{data_range}")
        chart = {"bar": BarChart, "line": LineChart, "pie": PieChart}.get(chart_type, BarChart)()
        chart.title = title; chart.style = 10; chart.width = 18; chart.height = 12
        chart.add_data(ref, titles_from_data=True); ws.add_chart(chart, position)
        wb.save(path); return f"Chart '{chart_type}' added at {position}."
    except Exception as e: return f"Chart error: {e}"

def _add_excel_sheet(path, sheet_name):
    if not EXCEL_AVAILABLE: return "openpyxl not available."
    path = fix_path(path)
    try:
        wb = load_workbook(path)
        if sheet_name not in wb.sheetnames: wb.create_sheet(sheet_name)
        wb.save(path); return f"Sheet '{sheet_name}' added."
    except Exception as e: return f"Add sheet error: {e}"

def _excel_add_rows(path, sheet_name, rows):
    if not EXCEL_AVAILABLE: return "openpyxl not available."
    path = fix_path(path)
    try:
        wb = load_workbook(path); ws = wb[sheet_name] if sheet_name in wb.sheetnames else wb.active
        for row in rows:
            ws.append(row)
            for cell in ws[ws.max_row]: cell.border = _thin_border()
        wb.save(path); return f"Added {len(rows)} row(s) to '{sheet_name}'."
    except Exception as e: return f"Add rows error: {e}"

def _excel_style_range(path, sheet_name, cell_range, bold=False, bg_color=None, font_size=None):
    if not EXCEL_AVAILABLE: return "openpyxl not available."
    path = fix_path(path)
    try:
        wb = load_workbook(path); ws = wb[sheet_name] if sheet_name in wb.sheetnames else wb.active
        for row in ws[cell_range]:
            if not isinstance(row, tuple): row = (row,)
            for cell in row:
                if bold or font_size: cell.font = Font(bold=bold, size=font_size or cell.font.size)
                if bg_color: cell.fill = PatternFill("solid", fgColor=bg_color)
        wb.save(path); return f"Style applied to {cell_range}."
    except Exception as e: return f"Style error: {e}"

def _run_command(command):
    try:
        import subprocess
        r = subprocess.run(command, shell=True, capture_output=True, text=True,
                           timeout=30, encoding="utf-8", errors="ignore")
        out = r.stdout + r.stderr
        return (out[:5000] + "\n[truncated]") if len(out) > 5000 else out or "Done (no output)."
    except subprocess.TimeoutExpired: return "Timeout."
    except Exception as e: return f"Command error: {e}"


# ─────────────────────────────────────────
# TOOL DISPATCHER
# ─────────────────────────────────────────
TOOL_MAP = {
    "read_file":             lambda a: _read_file(a["path"]),
    "write_file":            lambda a: _write_file(a["path"], a["content"]),
    "list_files":            lambda a: _list_files(a.get("directory",".")),
    "open_file":             lambda a: _open_file(a["path"]),
    "delete_file":           lambda a: _delete_file(a["path"]),
    "copy_file":             lambda a: _copy_file(a["src"], a["dst"]),
    "move_file":             lambda a: _move_file(a["src"], a["dst"]),
    "create_directory":      lambda a: _create_directory(a["path"]),
    "browser_goto":          lambda a: _browser_goto(a["url"]),
    "browser_click":         lambda a: _browser_click(a["selector"]),
    "browser_type":          lambda a: _browser_type(a["selector"], a["text"]),
    "browser_get_text":      lambda a: _browser_get_text(),
    "browser_screenshot":    lambda a: _browser_screenshot(a["path"]),
    "browser_get_links":     lambda a: _browser_get_links(),
    "browser_scroll":        lambda a: _browser_scroll(a["direction"]),
    "browser_press_key":     lambda a: _browser_press_key(a["key"]),
    "browser_select_option": lambda a: _browser_select_option(a["selector"], a["value"]),
    "browser_wait":          lambda a: _browser_wait(a["seconds"]),
    "browser_current_url":   lambda a: _browser_current_url(),
    "browser_go_back":       lambda a: _browser_go_back(),
    "browser_eval_js":       lambda a: _browser_eval_js(a["script"]),
    "read_webpage":          lambda a: _read_webpage(a["url"]),
    "create_excel":          lambda a: _create_excel(a["path"], a["sheets_data"]),
    "read_excel":            lambda a: _read_excel(a["path"]),
    "edit_excel_cell":       lambda a: _edit_excel_cell(a["path"], a["sheet_name"], a["cell"], a["value"]),
    "add_excel_formula":     lambda a: _add_excel_formula(a["path"], a["sheet_name"], a["cell"], a["formula"]),
    "add_excel_chart":       lambda a: _add_excel_chart(a["path"], a["sheet_name"], a["chart_type"],
                                                         a["data_range"], a["title"], a["position"]),
    "add_excel_sheet":       lambda a: _add_excel_sheet(a["path"], a["sheet_name"]),
    "excel_add_rows":        lambda a: _excel_add_rows(a["path"], a["sheet_name"], a["rows"]),
    "excel_style_range":     lambda a: _excel_style_range(a["path"], a["sheet_name"], a["cell_range"],
                                                           a.get("bold", False), a.get("bg_color"),
                                                           a.get("font_size")),
    "run_command":           lambda a: _run_command(a["command"]),
}


def handle_tool_call(name: str, args: dict) -> str:
    preview = ", ".join(f"{k}={repr(v)[:50]}" for k, v in args.items())
    print(f"  [🔧 {name}({preview})]")
    handler = TOOL_MAP.get(name)
    return str(handler(args)) if handler else f"Unknown tool: {name}"


# ─────────────────────────────────────────
# GEMINI TOOL DECLARATIONS
# ALL tools as explicit FunctionDeclaration.
# google-genai types.Tool only accepts
# FunctionDeclaration objects — NOT raw Python functions.
# ─────────────────────────────────────────
T  = types.Type
S  = types.Schema
FD = types.FunctionDeclaration

def _s(t, desc="", **kw): return S(type=t, description=desc, **kw)

TOOL_DECLARATIONS = [
    # ── FILES ────────────────────────────────────────────────────────────
    FD(name="read_file", description="Read the contents of a text file.",
       parameters=S(type=T.OBJECT, properties={"path": _s(T.STRING,"Path to the file")}, required=["path"])),

    FD(name="write_file", description="Write text to a file. Creates parent directories if needed.",
       parameters=S(type=T.OBJECT, properties={
           "path":    _s(T.STRING, "Destination path"),
           "content": _s(T.STRING, "Text content to write"),
       }, required=["path","content"])),

    FD(name="list_files", description="List files and folders in a directory with sizes.",
       parameters=S(type=T.OBJECT, properties={
           "directory": _s(T.STRING, "Path to directory (default: current)"),
       })),

    FD(name="open_file", description="Open a file in its default Windows application.",
       parameters=S(type=T.OBJECT, properties={"path": _s(T.STRING)}, required=["path"])),

    FD(name="delete_file", description="Delete a file or folder.",
       parameters=S(type=T.OBJECT, properties={"path": _s(T.STRING)}, required=["path"])),

    FD(name="copy_file", description="Copy a file to a new location.",
       parameters=S(type=T.OBJECT, properties={
           "src": _s(T.STRING,"Source path"), "dst": _s(T.STRING,"Destination path"),
       }, required=["src","dst"])),

    FD(name="move_file", description="Move or rename a file.",
       parameters=S(type=T.OBJECT, properties={
           "src": _s(T.STRING), "dst": _s(T.STRING),
       }, required=["src","dst"])),

    FD(name="create_directory", description="Create a folder recursively.",
       parameters=S(type=T.OBJECT, properties={"path": _s(T.STRING)}, required=["path"])),

    # ── BROWSER ──────────────────────────────────────────────────────────
    FD(name="browser_goto", description="Navigate to a URL in the Chromium browser.",
       parameters=S(type=T.OBJECT, properties={"url": _s(T.STRING)}, required=["url"])),

    FD(name="browser_click", description="Click an element by visible text or CSS selector.",
       parameters=S(type=T.OBJECT, properties={"selector": _s(T.STRING)}, required=["selector"])),

    FD(name="browser_type", description="Type text into a form field (placeholder, label, or CSS selector).",
       parameters=S(type=T.OBJECT, properties={
           "selector": _s(T.STRING,"Field identifier"),
           "text":     _s(T.STRING,"Text to type"),
       }, required=["selector","text"])),

    FD(name="browser_get_text", description="Get all visible text from the current page (max 6000 chars).",
       parameters=S(type=T.OBJECT, properties={})),

    FD(name="browser_screenshot", description="Take a full-page screenshot and save as PNG.",
       parameters=S(type=T.OBJECT, properties={"path": _s(T.STRING,"Output file path")}, required=["path"])),

    FD(name="browser_get_links", description="Return up to 40 links from the current page.",
       parameters=S(type=T.OBJECT, properties={})),

    FD(name="browser_scroll", description="Scroll the page: up, down, top, or bottom.",
       parameters=S(type=T.OBJECT, properties={
           "direction": S(type=T.STRING, enum=["up","down","top","bottom"]),
       }, required=["direction"])),

    FD(name="browser_press_key", description="Press a keyboard key: Enter, Tab, Escape, ArrowDown, etc.",
       parameters=S(type=T.OBJECT, properties={"key": _s(T.STRING)}, required=["key"])),

    FD(name="browser_select_option", description="Select an option from a dropdown.",
       parameters=S(type=T.OBJECT, properties={
           "selector": _s(T.STRING), "value": _s(T.STRING),
       }, required=["selector","value"])),

    FD(name="browser_wait", description="Wait N seconds (max 30).",
       parameters=S(type=T.OBJECT, properties={"seconds": _s(T.NUMBER)}, required=["seconds"])),

    FD(name="browser_current_url", description="Return the current URL and page title.",
       parameters=S(type=T.OBJECT, properties={})),

    FD(name="browser_go_back", description="Go back to the previous page.",
       parameters=S(type=T.OBJECT, properties={})),

    FD(name="browser_eval_js", description="Execute JavaScript on the page and return the result.",
       parameters=S(type=T.OBJECT, properties={"script": _s(T.STRING)}, required=["script"])),

    # ── WEB ──────────────────────────────────────────────────────────────
    FD(name="read_webpage", description="Fast HTTP text fetch without a browser (max 8000 chars).",
       parameters=S(type=T.OBJECT, properties={"url": _s(T.STRING)}, required=["url"])),

    # ── EXCEL ─────────────────────────────────────────────────────────────
    FD(name="create_excel",
       description="Create a new Excel .xlsx file with sheets, headers, data rows, and auto-formatting.",
       parameters=S(type=T.OBJECT,
           properties={
               "path": _s(T.STRING, "Full path to the .xlsx file"),
               "sheets_data": S(type=T.ARRAY,
                   description="List of sheets to create",
                   items=S(type=T.OBJECT,
                       properties={
                           "name":    _s(T.STRING, "Sheet name"),
                           "headers": S(type=T.ARRAY, description="Column headers",
                                        items=_s(T.STRING)),
                           "rows":    S(type=T.ARRAY, description="Data rows (list of lists)",
                                        items=S(type=T.ARRAY, items=_s(T.STRING))),
                           "col_widths": S(type=T.ARRAY, description="Optional column widths",
                                           items=_s(T.NUMBER)),
                       },
                   ),
               ),
           },
           required=["path","sheets_data"],
       )),

    FD(name="read_excel", description="Read an Excel file contents (max 100 rows per sheet).",
       parameters=S(type=T.OBJECT, properties={"path": _s(T.STRING)}, required=["path"])),

    FD(name="edit_excel_cell", description="Edit a single cell value in an Excel file.",
       parameters=S(type=T.OBJECT, properties={
           "path":       _s(T.STRING),
           "sheet_name": _s(T.STRING),
           "cell":       _s(T.STRING, "Cell address e.g. A1"),
           "value":      _s(T.STRING, "New value"),
       }, required=["path","sheet_name","cell","value"])),

    FD(name="add_excel_formula",
       description="Insert an Excel formula: =SUM(), =VLOOKUP(), =COUNTIF(), =IF(), =AVERAGE(), =MAX(), =MIN().",
       parameters=S(type=T.OBJECT, properties={
           "path":       _s(T.STRING),
           "sheet_name": _s(T.STRING),
           "cell":       _s(T.STRING, "Target cell e.g. B12"),
           "formula":    _s(T.STRING, "Excel formula e.g. =SUM(B2:B11)"),
       }, required=["path","sheet_name","cell","formula"])),

    FD(name="add_excel_chart",
       description="Add a bar, line, or pie chart to an Excel sheet.",
       parameters=S(type=T.OBJECT, properties={
           "path":       _s(T.STRING),
           "sheet_name": _s(T.STRING),
           "chart_type": S(type=T.STRING, enum=["bar","line","pie"]),
           "data_range": _s(T.STRING, "Data range e.g. A1:B10"),
           "title":      _s(T.STRING),
           "position":   _s(T.STRING, "Anchor cell e.g. D2"),
       }, required=["path","sheet_name","chart_type","data_range","title","position"])),

    FD(name="add_excel_sheet", description="Add a new sheet to an existing Excel file.",
       parameters=S(type=T.OBJECT, properties={
           "path":       _s(T.STRING),
           "sheet_name": _s(T.STRING),
       }, required=["path","sheet_name"])),

    FD(name="excel_add_rows", description="Append rows to the end of an Excel sheet.",
       parameters=S(type=T.OBJECT,
           properties={
               "path":       _s(T.STRING),
               "sheet_name": _s(T.STRING),
               "rows": S(type=T.ARRAY,
                   description="Rows to append; each row is a list of cell values",
                   items=S(type=T.ARRAY, items=_s(T.STRING)),
               ),
           },
           required=["path","sheet_name","rows"],
       )),

    FD(name="excel_style_range", description="Style a cell range: bold, background color, font size.",
       parameters=S(type=T.OBJECT, properties={
           "path":       _s(T.STRING),
           "sheet_name": _s(T.STRING),
           "cell_range": _s(T.STRING, "Range e.g. A1:D1"),
           "bold":       _s(T.BOOLEAN, "Make text bold"),
           "bg_color":   _s(T.STRING,  "Hex fill color without # e.g. FF0000"),
           "font_size":  _s(T.INTEGER, "Font size in pt"),
       }, required=["path","sheet_name","cell_range"])),

    # ── SYSTEM ───────────────────────────────────────────────────────────
    FD(name="run_command", description="Run a CMD / PowerShell command and return the output.",
       parameters=S(type=T.OBJECT, properties={"command": _s(T.STRING)}, required=["command"])),
]

GEMINI_TOOLS = types.Tool(function_declarations=TOOL_DECLARATIONS)


# ─────────────────────────────────────────
# SYSTEM PROMPT
# ─────────────────────────────────────────
SYSTEM_PROMPT = f"""You are an advanced AI assistant with full access to a Windows 11 computer.

AVAILABLE TOOLS (ALWAYS USE THEM when the task requires it):
📁 FILES: read_file, write_file, list_files, open_file, delete_file, copy_file, move_file, create_directory
🌐 BROWSER: browser_goto, browser_click, browser_type, browser_get_text, browser_screenshot, browser_get_links, browser_scroll, browser_press_key, browser_wait, browser_current_url, browser_go_back, browser_eval_js
🔗 WEB: read_webpage
📊 EXCEL: create_excel, read_excel, edit_excel_cell, add_excel_formula, add_excel_chart, add_excel_sheet, excel_add_rows, excel_style_range
⚙️ SYSTEM: run_command

CRITICAL RULES:
1. ALWAYS use tools — never say "I can't" or "unavailable".
2. Execute multi-step tasks autonomously.
3. Use full Windows paths: {DESKTOP}
4. If something fails, try an alternative approach.
5. Google: browser_goto("google.com") → browser_type("q","query") → browser_press_key("Enter")
6. Do NOT ask the user for data you can find with tools.

User desktop: {DESKTOP}"""


# ─────────────────────────────────────────
# CONVERSATION HISTORY + API LOOP
# ─────────────────────────────────────────
MAX_TURNS = 50
history: list[types.Content] = []


def trim_history():
    global history
    if len(history) > MAX_TURNS * 2:
        history = history[-(MAX_TURNS * 2):]


def call_gemini(user_text: str, retries: int = 3) -> str:
    global history
    model = choose_model(user_text)
    history.append(types.Content(role="user", parts=[types.Part(text=user_text)]))
    trim_history()

    config = types.GenerateContentConfig(
        system_instruction=SYSTEM_PROMPT,
        tools=[GEMINI_TOOLS],
        temperature=0.2,
        max_output_tokens=4096,
    )

    for attempt in range(retries):
        try:
            print(f"  [🤖 {model}]", end="", flush=True)
            MAX_ITER = 25
            for _ in range(MAX_ITER):
                response      = client.models.generate_content(model=model, contents=history, config=config)
                model_content = response.candidates[0].content
                history.append(model_content)
                print(" ✓")

                tool_parts = [p for p in model_content.parts if p.function_call]
                text_parts = [p for p in model_content.parts if p.text]

                if not tool_parts:
                    return " ".join(p.text for p in text_parts if p.text).strip()

                # Execute tools
                result_parts = []
                for part in tool_parts:
                    fc   = part.function_call
                    args = dict(fc.args) if fc.args else {}
                    result_parts.append(types.Part(
                        function_response=types.FunctionResponse(
                            name=fc.name,
                            response={"result": handle_tool_call(fc.name, args)},
                        )
                    ))
                history.append(types.Content(role="user", parts=result_parts))
                print(f"  [🤖 {model}]", end="", flush=True)

            return "⚠️ Reached iteration limit."

        except Exception as e:
            err = str(e).lower()
            print(f"\n  [⚠️  Attempt {attempt+1}/{retries}: {str(e)[:120]}]")
            if "quota" in err or "429" in err or "resource_exhausted" in err:
                if model == MODEL_SMART:
                    print(f"  [↩️  Switching to {MODEL_FAST}]"); model = MODEL_FAST; continue
                wait = min(2**attempt * 5, 60)
                print(f"  [⏳ Waiting {wait}s...]"); time.sleep(wait); continue
            if "not found" in err or "unavailable" in err:
                if model == MODEL_SMART:
                    print(f"  [↩️  Falling back to {MODEL_FAST}]"); model = MODEL_FAST; continue
            if attempt < retries - 1:
                time.sleep(3); continue
            raise


# ─────────────────────────────────────────
# STARTUP BANNER
# ─────────────────────────────────────────
print()
print("╔══════════════════════════════════════════════════════╗")
print("║      🤖  GeminiAgent  (Dual Model Strategy)         ║")
print("╠══════════════════════════════════════════════════════╣")
print(f"║  Smart : {MODEL_SMART:<42} ║")
print(f"║  Fast  : {MODEL_FAST:<42} ║")
print("╚══════════════════════════════════════════════════════╝")
print()
print(f"  📁 Desktop    : {DESKTOP}")
print(f"  🌐 Playwright : {'✅ OK' if PLAYWRIGHT_AVAILABLE else '❌  →  pip install playwright && playwright install chromium'}")
print(f"  📊 Excel      : {'✅ OK' if EXCEL_AVAILABLE     else '❌  →  pip install openpyxl'}")
print()
print("  Commands: 'exit' | 'reset' | 'status'")
print()

# ─────────────────────────────────────────
# MAIN LOOP
# ─────────────────────────────────────────
while True:
    try:
        user_input = input("👤 You: ").strip()
    except (KeyboardInterrupt, EOFError):
        print("\n👋 Goodbye!"); close_browser(); break

    if user_input.lower() in ("exit","quit"):
        print("👋 Goodbye!"); close_browser(); break

    if user_input.lower() in ("reset","clear"):
        history = []; print("🔄 History cleared.\n"); continue

    if user_input.lower() in ("status","stats"):
        print(f"\n📊 Smart calls: {_smart_calls_today}/{_MAX_SMART_CALLS} | "
              f"History: {len(history)//2} turns | "
              f"Browser: {'open' if _page else 'closed'}\n"); continue

    if not user_input: continue

    try:
        reply = call_gemini(user_input)
        if reply: print(f"\n🤖 Agent: {reply}\n")
    except Exception as e:
        print(f"\n❌ Error: {e}\n")
        if history and history[-1].role == "user": history.pop()
