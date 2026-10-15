"""Download candidate photos of Indian cars from Wikimedia Commons.

Saves a few freely licensed photos per model into evals/candidates/<model>/,
plus credits.csv with the source page, author and licence of every image.

You still pick and label the eval cars yourself: open the candidates, choose
the realistic street photos, and copy them into evals/images/car_XXX/.

Run from the evals folder:
    uv run python fetch_wikimedia.py
"""

import csv
import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

API = "https://commons.wikimedia.org/w/api.php"
# Wikimedia asks every script to identify itself with a descriptive User-Agent.
USER_AGENT = "ListPilotEvalFetcher/1.0 (https://github.com/farhanxansari/listpilot)"
OUT = Path(__file__).parent / "candidates"
PER_MODEL = 4  # candidates to keep per model
THUMB_WIDTH = 1280  # downscaled copy, plenty for a vision model

MODELS = [
    "Maruti Suzuki Swift",
    "Maruti Suzuki Baleno",
    "Maruti Suzuki Dzire",
    "Maruti Suzuki Wagon R",
    "Maruti Suzuki Alto",
    "Maruti Suzuki Ertiga",
    "Maruti Suzuki Brezza",
    "Hyundai Creta",
    "Hyundai i20",
    "Hyundai Venue",
    "Hyundai Grand i10",
    "Tata Nexon",
    "Tata Punch",
    "Tata Tiago",
    "Mahindra Scorpio",
    "Mahindra XUV700",
    "Mahindra Thar",
    "Mahindra Bolero",
    "Kia Seltos",
    "Kia Sonet",
    "Toyota Innova",
    "Toyota Fortuner",
    "Honda City",
    "Honda Amaze",
]

# Only keep licences that allow reuse.
ALLOWED_LICENCE = re.compile(r"(cc[- ]?by|cc0|public domain|pd)", re.IGNORECASE)
# Skip obvious non-photos and interiors.
SKIP_WORDS = re.compile(
    r"(logo|interior|dashboard|engine|badge|emblem|seat|wheel|"
    r"brochure|diagram|toy|model car|\.svg)",
    re.IGNORECASE,
)


def api_get(params: dict) -> dict:
    url = f"{API}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text or "").strip()


def search_images(model: str) -> list[dict]:
    data = api_get(
        {
            "action": "query",
            "format": "json",
            "generator": "search",
            "gsrsearch": f'"{model}" filetype:bitmap',
            "gsrnamespace": 6,
            "gsrlimit": 30,
            "prop": "imageinfo",
            "iiprop": "url|size|mime|extmetadata",
            "iiurlwidth": THUMB_WIDTH,
        }
    )
    pages = data.get("query", {}).get("pages", {}).values()
    results = []
    for page in pages:
        title = page.get("title", "")
        info = (page.get("imageinfo") or [{}])[0]
        meta = info.get("extmetadata", {})
        licence = strip_html(meta.get("LicenseShortName", {}).get("value", ""))
        if info.get("mime") != "image/jpeg":
            continue
        if SKIP_WORDS.search(title):
            continue
        if info.get("width", 0) < 800:
            continue
        if not ALLOWED_LICENCE.search(licence):
            continue
        results.append(
            {
                "title": title,
                "url": info.get("thumburl") or info.get("url"),
                "page": info.get("descriptionurl", ""),
                "author": strip_html(meta.get("Artist", {}).get("value", ""))[:120],
                "licence": licence,
            }
        )
    return results


def download(url: str, dest: Path) -> None:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=60) as resp:
        dest.write_bytes(resp.read())


def main() -> None:
    OUT.mkdir(exist_ok=True)
    credits_path = OUT / "credits.csv"
    with credits_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["model", "file", "commons_page", "author", "licence"])
        for model in MODELS:
            folder = OUT / model.lower().replace(" ", "_")
            folder.mkdir(exist_ok=True)
            try:
                found = search_images(model)
            except Exception as e:  # noqa: BLE001 - one failed search shouldn't stop the run
                print(f"  ! {model}: search failed ({e})")
                continue
            saved = 0
            for item in found:
                if saved >= PER_MODEL:
                    break
                name = f"{saved + 1}.jpg"
                try:
                    download(item["url"], folder / name)
                except Exception as e:  # noqa: BLE001
                    print(f"  ! {model}: download failed ({e})")
                    continue
                writer.writerow(
                    [
                        model,
                        f"{folder.name}/{name}",
                        item["page"],
                        item["author"],
                        item["licence"],
                    ]
                )
                saved += 1
                time.sleep(0.5)  # be polite to Wikimedia's servers
            print(f"{model}: {saved} image(s)")
            time.sleep(1)
    print(f"\nDone. Review the photos in {OUT} and credits in {credits_path}")


if __name__ == "__main__":
    main()
