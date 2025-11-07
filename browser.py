import re
import tkinter as tk
from tkinter import ttk
from tkinterweb import HtmlFrame
import requests
from io import BytesIO
from PIL import Image, ImageTk

# ==============================
# Konfiguracja
# ==============================
BASE_URL = "https://www.radiosuwalki.pl/www/"

# ==============================
# Pobranie pliku PML z serwera
# ==============================
def get_pml_from_web(filename):
    url = BASE_URL + filename
    resp = requests.get(url)
    resp.raise_for_status()
    return resp.text

# ==============================
# Dynamiczne mapowanie stron
# ==============================
def get_site_mapping():
    url = BASE_URL + "pns-sites.txt"
    mapping = {}
    try:
        resp = requests.get(url, timeout=5)
        resp.raise_for_status()
        for line in resp.text.splitlines():
            if "=" in line and "-" in line:
                key_part, rest = line.split("=", 1)
                if "-" in rest:
                    pml_file, pol_file = rest.split("-", 1)
                    key = key_part.strip()
                    mapping[key] = {
                        "pml": pml_file.strip(),
                        "pol": pol_file.strip()
                    }
        if not mapping:
            raise ValueError("Plik pusty lub błędny format.")
    except Exception as e:
        print(f"[!] Nie udało się pobrać mapy stron: {e}")
        mapping = {
            "pse": {"pml": "pse.pml", "pol": "pse.pol"},
            "pns": {"pml": "pnssite.pml", "pol": "pns.pol"},
            "pwh": {"pml": "pwh.pml", "pol": "pwh.pol"},
            "pln900": {"pml": "pln900.pml", "pol": "pln900.pol"},
            "radiosuwalki": {"pml": "radiosuwalki.pml", "pol": "radiosuwalki.pol"},
        }
    return mapping

# ==============================
# Konwersja PML → HTML
# ==============================
def pml_to_html(pml_text):
    title_match = re.search(r"<title>(.*?)</title>", pml_text, re.DOTALL)
    title = title_match.group(1).strip() if title_match else "Nowa karta"

    html = re.sub(r"<text size=['\"]1['\"]>(.*?)</text>", r"<h1>\1</h1>", pml_text)
    html = re.sub(r"<text size=['\"]2['\"]>(.*?)</text>", r"<h2>\1</h2>", html)
    html = re.sub(r"<text>(.*?)</text>", r"<p>\1</p>", html)
    html = html.replace("<line>", "<br>")

    html = re.sub(r"<image src=['\"](.*?)['\"]>",
                  lambda m: f"<img src='{BASE_URL + m.group(1)}' style='max-width:100%;border:2px solid gray;'>", html)

    html = re.sub(r"<link href=['\"](.*?)['\"]>(.*?)</link>",
                  lambda m: f"<a href='{BASE_URL + m.group(1)}' target='_blank'>{m.group(2)}</a>", html)

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset='utf-8'>
      <title>{title}</title>
      <style>
        body {{
          font-family: 'Segoe UI', sans-serif;
          background-color: #f3f4f6;
          color: #111;
          margin-top: 70px;
        }}
        h1 {{
          color: #2563eb;
          font-weight: 600;
          margin-bottom: 20px;
        }}
        a {{
          color: #2563eb;
          text-decoration: none;
        }}
        a:hover {{
          text-decoration: underline;
        }}
        img {{
          margin: 10px 0;
        }}
      </style>
    </head>
    <body>{html}</body>
    </html>
    """
    return html, title

# ==============================
# Wyszukiwarka PSE (ładna, mniejsza, wycentrowana)
# ==============================
def handle_search_widget(container, browser):
    for w in container.winfo_children():
        w.destroy()

    frame = tk.Frame(container, bg="#f3f4f6")
    frame.pack(expand=True, fill="both")

    tk.Label(frame, text="Polish Search Engine", font=("Segoe UI", 22, "bold"),
             fg="#2563eb", bg="#f3f4f6").pack(pady=(120, 15))

    entry = tk.Entry(frame, width=45, font=("Segoe UI", 13), relief="flat",
                     highlightthickness=2, highlightbackground="#2563eb", highlightcolor="#2563eb")
    entry.pack(pady=10)

    results_frame = tk.Frame(frame, bg="#f3f4f6")
    results_frame.pack(fill="both", expand=True, pady=10)

    def search():
        for w in results_frame.winfo_children():
            w.destroy()
        query = entry.get().strip().lower()
        if not query:
            tk.Label(results_frame, text="Wpisz zapytanie...", bg="#f3f4f6", fg="#444").pack()
            return
        try:
            resp = requests.get(BASE_URL + "pse-cat.log")
            resp.raise_for_status()
            lines = [ln.strip() for ln in resp.text.splitlines() if ln.strip()]
        except:
            tk.Label(results_frame, text="Brak pliku pse-cat.log", bg="#f3f4f6").pack()
            return
        matches = []
        for line in lines:
            if " - " not in line:
                continue
            fname, desc = line.split(" - ", 1)
            if query in fname.lower() or query in desc.lower():
                matches.append((fname.strip(), desc.strip()))
        if not matches:
            tk.Label(results_frame, text=f"Brak wyników dla: {query}", bg="#f3f4f6").pack()
            return
        for fname, desc in matches:
            link = f"pns://{fname.replace('.pml', '.pol')}"
            btn = tk.Button(results_frame, text=f"{desc} - {fname}",
                            bg="#2563eb", fg="white", font=("Segoe UI", 10),
                            relief="flat", cursor="hand2",
                            command=lambda l=link: open_result(l, browser))
            btn.pack(pady=3, ipadx=10, ipady=4)

    tk.Button(frame, text="Szukaj", bg="#2563eb", fg="white",
              font=("Segoe UI", 11, "bold"), relief="flat",
              cursor="hand2", command=search).pack(pady=5)

def open_result(link, browser):
    browser.address_bar.delete(0, "end")
    browser.address_bar.insert(0, link)
    browser.go_to_url()

# ==============================
# Menu kontekstowe
# ==============================
def create_context_menu(label, browser):
    menu = tk.Menu(label, tearoff=0, bg="#f9fafb", relief="flat")
    menu.add_command(label="Zbadaj element", command=lambda: inspect_element_in_panel(label, browser))
    menu.add_command(label="Logi", command=lambda: show_logs_in_panel(browser))
    menu.add_command(label="Odśwież", command=browser.refresh_page)

    def on_right_click(event):
        menu.tk_popup(event.x_root, event.y_root)
    label.bind("<Button-3>", on_right_click)

def inspect_element_in_panel(label, browser):
    browser.bottom_panel.pack(fill="x", side="bottom")
    for w in browser.bottom_panel.winfo_children():
        w.destroy()
    txt = tk.Text(browser.bottom_panel, wrap="word", height=10, bg="#f9fafb", relief="flat")
    txt.insert("1.0", getattr(label, "html", "<br>Brak danych"))
    txt.pack(fill="both", expand=True)

def show_logs_in_panel(browser):
    browser.bottom_panel.pack(fill="x", side="bottom")
    for w in browser.bottom_panel.winfo_children():
        w.destroy()
    for url in browser.history:
        tk.Label(browser.bottom_panel, text=url, anchor="w", bg="#f9fafb").pack(fill="x")
    tk.Button(browser.bottom_panel, text="Wyczyść logi", bg="#2563eb", fg="white", relief="flat",
              command=lambda: browser.history.clear()).pack(pady=5)

# ==============================
# Klasa przeglądarki
# ==============================
class PMLBrowser:
    def __init__(self, root):
        self.root = root
        self.root.title("PNS Browser v1.1")
        self.root.configure(bg="#f3f4f6")
        self.root.geometry("950x650")
        self.history = []

        toolbar = tk.Frame(root, bg="#f3f4f6")
        toolbar.pack(fill="x", side="top", pady=5)

        btn_style = {"bg": "#2563eb", "fg": "white", "relief": "flat",
                     "font": ("Segoe UI", 9), "cursor": "hand2"}

        tk.Button(toolbar, text="◀ Wstecz", **btn_style, command=self.go_back).pack(side="left", padx=5)
        tk.Button(toolbar, text="🔄 Odśwież", **btn_style, command=self.refresh_page).pack(side="left", padx=5)
        tk.Button(toolbar, text="➕ Nowa karta", **btn_style, command=self.new_tab).pack(side="left", padx=5)

        self.address_bar = tk.Entry(toolbar, width=60, font=("Segoe UI", 10), relief="flat", bd=2)
        self.address_bar.pack(side="left", padx=(8, 4))
        tk.Button(toolbar, text="➡ Idź", **btn_style, command=self.go_to_url).pack(side="left", padx=6)

        self.tab_control = ttk.Notebook(root)
        self.tab_control.pack(fill="both", expand=True)
        self.tabs = {}

        self.bottom_panel = tk.Frame(root, height=150, bg="#f9fafb")
        self.bottom_panel.pack_forget()

        self.new_tab()
        self.address_bar.insert(0, "pns://pse.pol")
        self.go_to_url()

    def new_tab(self):
        frame = tk.Frame(self.tab_control, bg="#f3f4f6")
        self.tab_control.add(frame, text="Nowa karta")
        self.tab_control.select(frame)
        html = HtmlFrame(frame)
        html.load_html("<center><h3>Witaj w PNS Browser v1.1</h3></center>")
        html.pack(fill="both", expand=True)
        self.tabs[frame] = {"widget": html, "url": ""}
        create_context_menu(html, self)

    def current_frame(self):
        sel = self.tab_control.select()
        return self.tab_control.nametowidget(sel)

    def go_to_url(self):
        url = self.address_bar.get().strip()
        if not url.startswith("pns://"):
            url = f"pns://{url}"  # automatyczne dodanie protokołu
            self.address_bar.delete(0, "end")
            self.address_bar.insert(0, url)
        short = url.replace("pns://", "").replace(".pol", "")
        mapping = get_site_mapping()
        page = mapping.get(short, {}).get("pml", short + ".pml")
        frame = self.current_frame()
        for w in frame.winfo_children():
            w.destroy()
        try:
            pml_code = get_pml_from_web(page)
        except Exception as e:
            err = HtmlFrame(frame)
            err.load_html(f"<h1>Błąd</h1><p>{e}</p>")
            err.pack(fill="both", expand=True)
            return
        html_content, title = pml_to_html(pml_code)
        if "<search>" in pml_code:
            handle_search_widget(frame, self)
        else:
            label = HtmlFrame(frame)
            label.load_html(html_content)
            label.pack(fill="both", expand=True)
            label.html = html_content
            create_context_menu(label, self)
        self.tab_control.tab(frame, text=title)
        self.history.append(url)

    def refresh_page(self):
        if self.history:
            self.go_to_url()

    def go_back(self):
        if len(self.history) > 1:
            self.history.pop()
            prev = self.history.pop()
            self.address_bar.delete(0, "end")
            self.address_bar.insert(0, prev)
            self.go_to_url()

# ==============================
# Start programu
# ==============================
if __name__ == "__main__":
    root = tk.Tk()
    try:
        icon_url = BASE_URL + "pnsbrowser.png"
        resp = requests.get(icon_url)
        resp.raise_for_status()
        img = Image.open(BytesIO(resp.content))
        icon = ImageTk.PhotoImage(img)
        root.iconphoto(False, icon)
    except Exception as e:
        print("[!] Nie udało się pobrać ikony:", e)

    app = PMLBrowser(root)
    root.mainloop()
