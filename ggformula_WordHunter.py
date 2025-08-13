# suffix_search_full_ui_height_up.py
import os
import textwrap
import tkinter as tk
from tkinter import ttk, filedialog, simpledialog, messagebox
import pandas as pd

# optional libs
try:
    from nltk.corpus import wordnet
    import nltk
except Exception as e:
    raise RuntimeError("Please install nltk (pip install nltk) and ensure it's available.") from e

try:
    from deep_translator import GoogleTranslator
except Exception:
    GoogleTranslator = None  # translation will be skipped if unavailable

# ---------- Config ----------
WORDLIST_PATH = r"E:\SuffixSearchAp\largest_possible_aspell_wordlist.txt"  # change if needed
WRAP_EN = 80   # wrap width for English defs when inserting into table (visual)
WRAP_TA = 100  # wrap width for Tamil defs before inserting into table
POS_MAP = {'n': 'Noun', 'v': 'Verb', 'a': 'Adjective', 's': 'Adjective Satellite', 'r': 'Adverb'}

# ensure wordnet downloaded
try:
    nltk.data.find("corpora/wordnet")
except Exception:
    nltk.download("wordnet")
    nltk.download("omw-1.4")

# ---------- Helpers ----------
def load_wordlist(path):
    if not os.path.exists(path):
        messagebox.showerror("Missing file", f"Word list not found at: {path}")
        return []
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        words = [w.strip() for w in f.read().split() if w.strip()]
    # unique, case-preserve but sort short->long then lexicographically
    words = sorted(set(words), key=lambda x: (len(x), x.lower()))
    return words

def append_word_to_file(path, word):
    with open(path, "a", encoding="utf-8") as f:
        f.write("\n" + word.strip())

def get_wordnet_meanings_for_table(word):
    syns = wordnet.synsets(word)
    rows = []
    if not syns:
        return rows
    for i, syn in enumerate(syns, start=1):
        pos_full = POS_MAP.get(syn.pos(), syn.pos())
        eng = syn.definition()
        ta = ""
        if GoogleTranslator:
            try:
                ta = GoogleTranslator(source='auto', target='ta').translate(eng)
            except Exception:
                ta = ""
        rows.append((str(i), pos_full, eng, ta))
    return rows

def export_tree_to_excel(tree, initialfile="meanings_export.xlsx"):
    items = tree.get_children()
    if not items:
        messagebox.showinfo("No data", "No rows to export.")
        return
    data = []
    for iid in items:
        vals = tree.item(iid)['values']
        # expected: No, POS, English, Tamil
        if len(vals) >= 4:
            no, pos, eng, ta = vals[0], vals[1], vals[2], vals[3]
        else:
            # fallback
            no = vals[0] if len(vals)>0 else ""
            pos = vals[1] if len(vals)>1 else ""
            eng = vals[2] if len(vals)>2 else ""
            ta = vals[3] if len(vals)>3 else ""
        data.append({"No": no, "POS": pos, "English Definition": eng, "Tamil Translation": ta})
    df = pd.DataFrame(data)
    fp = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel files","*.xlsx")], initialfile=initialfile)
    if not fp:
        return
    try:
        with pd.ExcelWriter(fp, engine="xlsxwriter") as writer:
            df.to_excel(writer, sheet_name="Meanings", index=False)
            workbook = writer.book
            worksheet = writer.sheets["Meanings"]
            header_fmt = workbook.add_format({"bold": True, "bg_color": "#FFD700"})
            wrap_fmt = workbook.add_format({"text_wrap": True})
            for cnum, col in enumerate(df.columns):
                worksheet.write(0, cnum, col, header_fmt)
                # set wide columns for English and Tamil
                if col == "English Definition":
                    worksheet.set_column(cnum, cnum, 80, wrap_fmt)
                elif col == "Tamil Translation":
                    worksheet.set_column(cnum, cnum, 120, wrap_fmt)
                else:
                    worksheet.set_column(cnum, cnum, 20, wrap_fmt)
        messagebox.showinfo("Exported", f"Exported to {fp}")
    except Exception as e:
        messagebox.showerror("Export failed", str(e))

# ---------- GUI ----------
class SuffixSearchUI:
    def __init__(self, master):
        self.master = master
        master.title("Suffix Search — Full")
        # increased vertical space to accommodate larger widgets
        master.geometry("1400x1000")

        # data
        self.words = load_wordlist(WORDLIST_PATH)

        # Top controls
        top = ttk.Frame(master, padding=8)
        top.pack(fill="x")

        ttk.Label(top, text="Suffix:", width=8).grid(row=0, column=0, sticky="w")
        self.suffix_var = tk.StringVar()
        self.suffix_entry = ttk.Entry(top, textvariable=self.suffix_var, width=20)
        self.suffix_entry.grid(row=0, column=1, padx=6)

        ttk.Label(top, text="Letters before suffix:", width=18).grid(row=0, column=2, sticky="w")
        self.before_var = tk.StringVar(value="0")
        self.before_entry = ttk.Entry(top, textvariable=self.before_var, width=6)
        self.before_entry.grid(row=0, column=3, padx=6)

        btn_search = ttk.Button(top, text="Search (with before-count)", command=self.search_with_before)
        btn_search.grid(row=0, column=4, padx=6)

        btn_show_all = ttk.Button(top, text="Show All Related Words", command=self.show_all_related)
        btn_show_all.grid(row=0, column=5, padx=6)

        btn_add = ttk.Button(top, text="Add Word", command=self.add_word_dialog)
        btn_add.grid(row=0, column=6, padx=6)

        btn_export = ttk.Button(top, text="Export Meanings to Excel", command=self.export_meanings)
        btn_export.grid(row=0, column=7, padx=6)

        # matched count label
        self.count_label = ttk.Label(top, text=f"Matched: 0    (Total words in list: {len(self.words)})")
        self.count_label.grid(row=0, column=8, padx=12)

        # Main frames
        main = ttk.Frame(master, padding=6)
        main.pack(fill="both", expand=True)

        # Left: results text (allows suffix highlight)
        left = ttk.Frame(main)
        left.pack(side="left", fill="y", padx=8, pady=8)

        ttk.Label(left, text="Matched words:").pack(anchor="w")
        # ==== HEIGHT INCREASED HERE ====
        self.results_text = tk.Text(left, width=30, height=50, wrap="none", font=("Arial", 12))
        # previous height was 40; increased to 50 as per request
        # =================================
        self.results_text.pack(side="left", fill="y")
        self.results_text.tag_configure("suffix", foreground="red", font=("Arial", 12, "bold"))
        self.results_text.bind("<Button-1>", self.on_results_click)

        # vertical scrollbar for results_text
        scr_left = ttk.Scrollbar(left, orient="vertical", command=self.results_text.yview)
        scr_left.pack(side="left", fill="y")
        self.results_text.config(yscrollcommand=scr_left.set)

        # Right: meanings table with large Tamil column and vertical scroll
        right = ttk.Frame(main)
        right.pack(side="left", fill="both", expand=True, padx=8, pady=8)

        ttk.Label(right, text="Meanings Table (click a word on left)").pack(anchor="w")

        cols = ("No", "POS", "English", "Tamil")
        # ==== TREE HEIGHT INCREASED HERE ====
        # set heights per user's request: POS=140, English=500, Tamil=900 (approx)
        self.tree = ttk.Treeview(right, columns=cols, show="headings", height=25)
        # previous tree height unspecified or small; now set to 25 rows for greater vertical space
        # =======================================
        for c in cols:
            self.tree.heading(c, text=c)
        # ====== COLUMN WIDTHS INCREASED AS REQUESTED ======
        self.tree.column("No", width=60, anchor="center")
        self.tree.column("POS", width=180, anchor="center")   # ↑ அகலம் அதிகரிப்பு
        self.tree.column("English", width=600, anchor="w")    # ↑ அகலம் அதிகரிப்பு
        self.tree.column("Tamil", width=1200, anchor="w")     # ↑ அகலம் அதிகரிப்பு
        # ===================================================
        self.tree.pack(side="left", fill="both", expand=True)

        scr_right = ttk.Scrollbar(right, orient="vertical", command=self.tree.yview)
        scr_right.pack(side="left", fill="y")
        self.tree.config(yscrollcommand=scr_right.set)

        # bottom status and instructions
        bottom = ttk.Frame(master, padding=6)
        bottom.pack(fill="x")
        ttk.Label(bottom, text="Tip: Click a word in the left panel to load meanings here.").pack(side="left")

        # internal currently displayed meanings word
        self.current_selected_word = None
        self.last_suffix = ""

    # ---------- actions ----------
    def search_with_before(self):
        suffix = self.suffix_var.get().strip().lower()
        if not suffix:
            messagebox.showwarning("Input", "Enter a suffix first.")
            return
        try:
            before = int(self.before_var.get().strip())
            if before < 0:
                before = 0
        except Exception:
            before = 0
        matched = [w for w in self.words if w.lower().endswith(suffix) and (len(w)-len(suffix)) == before]
        matched = sorted(matched, key=len)
        self.show_matched_words(matched, suffix)

    def show_all_related(self):
        suffix = self.suffix_var.get().strip().lower()
        if not suffix:
            messagebox.showwarning("Input", "Enter a suffix first.")
            return
        matched = [w for w in self.words if w.lower().endswith(suffix)]
        matched = sorted(matched, key=len)
        self.show_matched_words(matched, suffix)

    def show_matched_words(self, matched, suffix):
        # clear results_text
        self.results_text.config(state="normal")
        self.results_text.delete("1.0", tk.END)
        if not matched:
            self.results_text.insert(tk.END, "No matches found.\n")
            self.count_label.config(text=f"Matched: 0    (Total words in list: {len(self.words)})")
            self.results_text.config(state="disabled")
            return
        for w in matched:
            # insert part before suffix (normal) and suffix part (tagged)
            if suffix and w.lower().endswith(suffix):
                prefix = w[:-len(suffix)]
                sfx = w[-len(suffix):]
                self.results_text.insert(tk.END, prefix)
                # mark start index for tag
                start = self.results_text.index(tk.INSERT)
                self.results_text.insert(tk.END, sfx + "\n")
                end = self.results_text.index(tk.INSERT)
                # apply tag to suffix portion
                self.results_text.tag_add("suffix", start, end)
            else:
                self.results_text.insert(tk.END, w + "\n")
        self.results_text.config(state="disabled")
        self.count_label.config(text=f"Matched: {len(matched)}    (Total words in list: {len(self.words)})")
        # store last suffix for click-handling highlight clarity
        self.last_suffix = suffix

    def on_results_click(self, event):
        # Determine clicked line number
        idx = self.results_text.index(f"@{event.x},{event.y}")
        line = idx.split(".")[0]
        # get full line content
        line_text = self.results_text.get(f"{line}.0", f"{line}.end").strip()
        if not line_text or line_text == "No matches found.":
            return
        # line_text is the full word (prefix+suffix)
        word = line_text
        self.current_selected_word = word
        # populate tree with meanings
        self.load_meanings_into_tree(word)

    def load_meanings_into_tree(self, word):
        # clear tree
        for iid in self.tree.get_children():
            self.tree.delete(iid)
        syns = get_wordnet_meanings_for_table(word)
        if not syns:
            # insert a single row saying no meaning
            self.tree.insert("", tk.END, values=("", "No meaning found", "", ""))
            return
        for no, pos, eng, ta in syns:
            # wrap english and tamil to avoid extremely long lines (Treeview will show newlines)
            eng_wrapped = "\n".join(textwrap.wrap(eng, WRAP_EN)) if eng else ""
            ta_wrapped = "\n".join(textwrap.wrap(ta, WRAP_TA)) if ta else ""
            # Insert 4-column row: No, POS, English, Tamil
            self.tree.insert("", tk.END, values=(no, pos, eng_wrapped, ta_wrapped))

    def add_word_dialog(self):
        new = simpledialog.askstring("Add Word", "Enter single-word to add (no spaces):")
        if not new:
            return
        new = new.strip()
        if not new:
            return
        if new in self.words:
            messagebox.showinfo("Exists", f"'{new}' is already in the list.")
            return
        # append to memory and file
        self.words.append(new)
        # keep sorted by length then lexicographically
        self.words = sorted(set(self.words), key=lambda x: (len(x), x.lower()))
        try:
            append_word_to_file(WORDLIST_PATH, new)
            messagebox.showinfo("Added", f"'{new}' added to wordlist.")
            self.count_label.config(text=f"Matched: 0    (Total words in list: {len(self.words)})")
        except Exception as e:
            messagebox.showerror("Write error", f"Failed to save word: {e}")

    def export_meanings(self):
        export_tree_to_excel(self.tree, initialfile="meanings_export.xlsx")

# ---------- run ----------
if __name__ == "__main__":
    root = tk.Tk()
    app = SuffixSearchUI(root)
    root.mainloop()
