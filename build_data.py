"""Reads the Kaggle Ultimate Pokémon Dataset, cleans it, and writes data.json for the dashboard.

Usage:
  python build_data.py                 # download via kagglehub, build data.json
  python build_data.py --csv my.csv    # use a local CSV instead
  python build_data.py --serve         # build, then open the dashboard at http://localhost:8000
Requires: pip install pandas kagglehub
"""
import argparse, glob, http.server, json, os, re, socketserver, webbrowser
import pandas as pd

DATASET = "darkmatternet/ultimate-pokmon-dataset-2025"
HERE = os.path.dirname(os.path.abspath(__file__))
ROMAN = {"i": 1, "ii": 2, "iii": 3, "iv": 4, "v": 5, "vi": 6, "vii": 7, "viii": 8, "ix": 9}

# Dataset column names differ between versions, so each field has several accepted names.
ALIAS = {
    "id": ["pokedexid", "pokedexnumber", "pokedexno", "number", "nationaldex", "dexnumber", "n", "id", "dex"],
    "name": ["name", "pokemon", "pokemonname", "englishname"],
    "genus": ["genus", "species", "classification", "category"],
    "type1": ["type1", "primarytype", "type"],
    "type2": ["type2", "secondarytype"],
    "hp": ["hp", "basehp"],
    "attack": ["attack", "atk", "baseattack"],
    "defense": ["defense", "def", "basedefense"],
    "spatk": ["spatk", "spattack", "specialattack", "basespatk", "basespecialattack"],
    "spdef": ["spdef", "spdefense", "specialdefense", "basespdef", "basespecialdefense"],
    "speed": ["speed", "spd", "basespeed"],
    "gen": ["generation", "gen"],
    "desc": ["description", "flavortext", "flavor", "pokedexentry", "pokedextext", "entry"],
    "img": ["image", "imageurl", "sprite", "spriteurl", "artwork", "officialartwork", "imagepath", "thumbnail", "img"],
}
STATS = ["hp", "attack", "defense", "spatk", "spdef", "speed"]
ART = "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/{}.png"


def find_csv():
    import kagglehub
    path = kagglehub.dataset_download(DATASET)
    files = glob.glob(os.path.join(path, "**", "*.csv"), recursive=True)
    if not files:
        raise SystemExit(f"No CSV found in {path}")
    best = max(files, key=os.path.getsize)  # the main table is normally the largest file
    print("Using", best)
    return best


def norm(s):
    return re.sub(r"[^a-z0-9]", "", str(s).lower())


def map_columns(df):
    by_norm = {norm(c): c for c in df.columns}
    mapping = {}
    for key, names in ALIAS.items():
        hit = next((by_norm[n] for n in names if n in by_norm), None)
        if hit:
            mapping[key] = hit
    print("Column mapping:")
    for key in ALIAS:
        print(f"  {key:7} <- {mapping.get(key, '(not found)')}")
    return mapping


def clean_text(v):
    return re.sub(r"\s+", " ", str(v)).strip() if pd.notna(v) else ""


def parse_gen(v):
    s = clean_text(v).lower().replace("generation", "").strip()
    m = re.search(r"\d+", s)
    return int(m.group()) if m else ROMAN.get(s)


def build(csv_path, out_path):
    df = pd.read_csv(csv_path)
    m = map_columns(df)
    col = lambda k: df[m[k]] if k in m else pd.Series([None] * len(df))

    out = pd.DataFrame()
    out["id"] = pd.to_numeric(col("id"), errors="coerce")
    out["id"] = out["id"].fillna(pd.Series(range(1, len(df) + 1)))
    out["name"] = col("name").map(clean_text)
    out["genus"] = col("genus").map(clean_text)
    out["gen"] = col("gen").map(parse_gen)
    out["desc"] = col("desc").map(clean_text)

    # Types: either two columns, or one combined column like "Grass/Poison"
    t1 = col("type1").map(clean_text)
    t2 = col("type2").map(clean_text)
    parts = t1.str.split(r"\s*[/,|]\s*", n=1, regex=True)
    t1 = parts.str[0].fillna("")
    t2 = t2.where(t2 != "", parts.str[1].fillna(""))
    out["types"] = [[x.lower() for x in (a, b) if x and x.lower() not in ("nan", "none")] for a, b in zip(t1, t2)]

    for s in STATS:
        out[s] = pd.to_numeric(col(s), errors="coerce").fillna(0).astype(int)

    out["img"] = col("img").map(clean_text) if "img" in m else ""
    out["img"] = [i if i else ART.format(int(p)) for i, p in zip(out["img"], out["id"])]

    out = out[out["name"] != ""].sort_values(["id", "name"]).reset_index(drop=True)
    records = [
        {
            "id": int(r.id), "name": r.name, "genus": r.genus, "types": r.types,
            "stats": {s: int(getattr(r, s)) for s in STATS},
            "total": int(sum(getattr(r, s) for s in STATS)),
            "gen": None if pd.isna(r.gen) else int(r.gen),
            "desc": r.desc, "img": r.img,
        }
        for r in out.itertuples()
    ]
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False)
    print(f"Wrote {len(records)} Pokémon to {out_path}")


def serve(port=8000):
    os.chdir(HERE)
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", port), http.server.SimpleHTTPRequestHandler) as httpd:
        url = f"http://localhost:{port}/index.html"
        print("Dashboard running at", url, "(Ctrl+C to stop)")
        webbrowser.open(url)
        httpd.serve_forever()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", help="path to a local CSV (skips the Kaggle download)")
    ap.add_argument("--out", default=os.path.join(HERE, "data.json"))
    ap.add_argument("--serve", action="store_true", help="start a local server after building")
    a = ap.parse_args()
    build(a.csv or find_csv(), a.out)
    if a.serve:
        serve()
