# Created 2026-11-21. Last updated 2026-11-21.
import json
import os
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FONT_FILE = ROOT / "scripts" / "fonts" / "barlow-condensed.b64"
API = "https://api.github.com"
IGNORED = {"Jupyter Notebook"}
MAX_LANGUAGES = 8

WIDTH = 840
BAR_HEIGHT = 10
BAR_GAP = 2
LIST_TOP = 34
COLUMN_GAP = 48
ROW_HEIGHT = 38
SWATCH = 10

THEMES = {
    "light": {
        "text": "#0b1f3a",
        "percent": "#5b6b85",
        "hairline": "#d0d7de",
        "scale": ["#0b1f3a", "#1f3d6b", "#33598f", "#5577ab", "#7d97c2", "#a9bcda", "#d3deee"],
    },
    "dark": {
        "text": "#ffffff",
        "percent": "#8b98b0",
        "hairline": "#30363d",
        "scale": ["#ffffff", "#9fb7dd", "#5d7fb8", "#3d5f99", "#2b4675", "#223657", "#1a2840"],
    },
}


def get(path, token):
    request = urllib.request.Request(API + path, headers={
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
    })
    try:
        with urllib.request.urlopen(request) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:
        # status only, the URL would expose repo names in the Actions log
        raise SystemExit(f"GitHub API error {error.code}") from None


def language_bytes(token):
    totals = {}
    page = 1
    while True:
        repos = get(f"/user/repos?affiliation=owner&per_page=100&page={page}", token)
        for repo in repos:
            if repo["fork"] or repo["archived"]:
                continue
            for language, size in get(f"/repos/{repo['full_name']}/languages", token).items():
                if language not in IGNORED:
                    totals[language] = totals.get(language, 0) + size
        if len(repos) < 100:
            return totals
        page += 1


def shares(totals):
    total = sum(totals.values())
    ranked = sorted(totals.items(), key=lambda item: item[1], reverse=True)
    rows = [(name, 100 * size / total) for name, size in ranked[:MAX_LANGUAGES]]
    other = sum(size for _, size in ranked[MAX_LANGUAGES:])
    if other:
        rows.append(("Other", 100 * other / total))
    return rows


def scale_colors(scale, count):
    if count <= len(scale):
        return scale[:count]
    rgb = [tuple(int(hex_color[i:i + 2], 16) for i in (1, 3, 5)) for hex_color in scale]
    colors = []
    for index in range(count):
        position = index * (len(scale) - 1) / (count - 1)
        low = min(int(position), len(scale) - 2)
        fraction = position - low
        mixed = (round(a + (b - a) * fraction) for a, b in zip(rgb[low], rgb[low + 1]))
        colors.append("#" + "".join(f"{channel:02x}" for channel in mixed))
    return colors


def font_faces():
    faces = []
    for line in FONT_FILE.read_text().split("\n"):
        if line:
            weight, data = line.split(" ", 1)
            faces.append(
                "@font-face{font-family:'Barlow Condensed';font-weight:%s;"
                "src:url(data:font/woff2;base64,%s) format('woff2')}" % (weight, data)
            )
    return "".join(faces)


def render(rows, theme):
    colors = scale_colors(theme["scale"], len(rows))
    usable = WIDTH - BAR_GAP * (len(rows) - 1)
    parts = []

    x = 0.0
    for (_, percent), color in zip(rows, colors):
        width = usable * percent / 100
        parts.append(f'<rect x="{x:.2f}" y="0" width="{width:.2f}" height="{BAR_HEIGHT}" fill="{color}"/>')
        x += width + BAR_GAP

    left_count = (len(rows) + 1) // 2
    column_width = (WIDTH - COLUMN_GAP) / 2
    for index, ((name, percent), color) in enumerate(zip(rows, colors)):
        column, row = divmod(index, left_count)
        left = column * (column_width + COLUMN_GAP)
        top = LIST_TOP + row * ROW_HEIGHT
        middle = top + ROW_HEIGHT / 2
        parts.append(
            f'<rect x="{left:.2f}" y="{top}" width="{column_width:.2f}" height="1" fill="{theme["hairline"]}"/>'
            f'<rect x="{left:.2f}" y="{middle - SWATCH / 2:.2f}" width="{SWATCH}" height="{SWATCH}" fill="{color}"/>'
            f'<text class="name" x="{left + SWATCH + 14:.2f}" y="{middle:.2f}">{name.upper()}</text>'
            f'<text class="percent" x="{left + column_width:.2f}" y="{middle:.2f}">{percent:.2f}%</text>'
        )

    height = LIST_TOP + left_count * ROW_HEIGHT
    style = (
        font_faces()
        + "text{font-family:'Barlow Condensed','Arial Narrow',sans-serif;font-size:15px;dominant-baseline:central}"
        + f".name{{font-weight:700;letter-spacing:0.14em;fill:{theme['text']}}}"
        + f".percent{{font-weight:500;letter-spacing:0.04em;text-anchor:end;fill:{theme['percent']}}}"
    )
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{height}" '
        f'viewBox="0 0 {WIDTH} {height}" role="img" aria-label="Language stats">'
        f"<style>{style}</style>{''.join(parts)}</svg>\n"
    )


def main():
    rows = shares(language_bytes(os.environ["STATS_TOKEN"]))
    output_dir = ROOT / "profile"
    output_dir.mkdir(exist_ok=True)
    for name, theme in THEMES.items():
        (output_dir / f"stats-{name}.svg").write_text(render(rows, theme))


if __name__ == "__main__":
    main()
