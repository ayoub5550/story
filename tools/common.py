"""Shared loaders for the Amamellen production. Pure python + PyYAML."""
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[1]
STYLE_PREFIX = ("Hand-painted 2D animated feature film, clean expressive ink linework, cel-shaded characters, "
                "painterly gouache backgrounds, warm Saharan palette (ochre, burnt sienna, sand gold, deep indigo, "
                "night ultramarine), subtle film grain, cinematic 16:9 composition, no text, no subtitles, no watermark.")
NEGATIVE = ("photorealistic, 3D render, CGI plastic, anime chibi, modern objects, guns, cars, horses, mosques, "
            "Arabic or Latin text, logos, deformed hands, visible mouth on veiled men")


def load(rel):
    return yaml.safe_load((ROOT / rel).read_text(encoding="utf-8"))


def characters():
    return {c["token"]: c for c in load("bible/characters.yaml")["characters"]}


def locations():
    return {l["token"]: l for l in load("bible/locations.yaml")["locations"]}


def parts():
    return {1: load("production/shots_part1.yaml"), 2: load("production/shots_part2.yaml")}


def iter_shots(part_doc):
    for sc in part_doc["scenes"]:
        for sh in sc.get("shots", []) or []:
            yield sc, sh


def tc(seconds):
    m, s = divmod(int(round(seconds)), 60)
    return f"{m:02d}:{s:02d}"
