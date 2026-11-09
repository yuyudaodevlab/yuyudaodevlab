#!/usr/bin/env python3
"""Refresh the profile's daily GitHub snapshot (Python standard library only)."""

from __future__ import annotations

import argparse
from datetime import date, datetime, timezone
from html import escape
import json
import os
from pathlib import Path
import re
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "assets" / "daily.svg"
API = "https://api.github.com"
USERNAME_RE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?$")


class UpdateError(RuntimeError):
    pass


def valid_username(username: str) -> str:
    if not USERNAME_RE.fullmatch(username):
        raise UpdateError("GitHub username is invalid")
    return username


def get_json(url: str) -> object:
    headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "profile-readme-daily"}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = Request(url, headers=headers)
    try:
        with urlopen(request, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, OSError, ValueError) as exc:
        raise UpdateError(f"GitHub API request failed ({type(exc).__name__})") from None


def fetch_stats(username: str) -> dict[str, int]:
    encoded = quote(valid_username(username), safe="")
    profile = get_json(f"{API}/users/{encoded}")
    if (not isinstance(profile, dict) or not isinstance(profile.get("followers"), int)
            or isinstance(profile.get("followers"), bool) or profile["followers"] < 0):
        raise UpdateError("GitHub API returned an invalid profile response")
    repo_count = 0
    stars = 0
    page = 1
    while True:
        repos = get_json(f"{API}/users/{encoded}/repos?type=owner&per_page=100&page={page}")
        if not isinstance(repos, list) or any(not isinstance(repo, dict) for repo in repos):
            raise UpdateError("GitHub API returned an invalid repository response")
        for repo in repos:
            star_count = repo.get("stargazers_count")
            fork = repo.get("fork")
            if not isinstance(star_count, int) or isinstance(star_count, bool) or star_count < 0 or not isinstance(fork, bool):
                raise UpdateError("GitHub API returned invalid repository statistics")
            if not isinstance(repo.get("private", False), bool):
                raise UpdateError("GitHub API returned invalid repository visibility")
            if not repo.get("private", False):
                repo_count += 1
                if not fork:
                    stars += star_count
        if len(repos) < 100:
            break
        page += 1
    return {"followers": profile["followers"], "repos": repo_count, "stars": stars}


def render_svg(username: str, day: date, stats: dict[str, int] | None) -> str:
    username_xml = escape(username, quote=True)
    date_label = day.strftime("%Y.%m.%d")
    labels = (
        ("PUBLIC REPOSITORIES", "repos"),
        ("STARS EARNED", "stars"),
        ("FOLLOWERS", "followers"),
    )
    values = [str(stats[key]) if stats is not None else "—" for _, key in labels]
    status = "PUBLIC SNAPSHOT · GITHUB API" if stats is not None else "STATS UNAVAILABLE · UPDATE WHEN ONLINE"
    provenance = "Data from the public GitHub API." if stats is not None else "Live data unavailable; statistics are marked unavailable."
    cards = []
    for index, ((label, _), value) in enumerate(zip(labels, values)):
        x = 44 + index * 304
        cards.append(f'<g transform="translate({x} 246)"><rect width="276" height="89" rx="18" fill="#30231d" stroke="#5c4030"/><text x="20" y="29" class="label">{label}</text><text x="20" y="68" class="value">{value}</text></g>')
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="390" viewBox="0 0 1000 390" role="img" aria-labelledby="title desc">
<title id="title">GitHub activity for {username_xml}</title><desc id="desc">Public repositories, stars and followers as of {date_label}. {values[0]} public repositories; {values[1]} stars; {values[2]} followers. {provenance}</desc>
<defs><radialGradient id="glow"><stop stop-color="#c89469" stop-opacity=".2"/><stop offset="1" stop-color="#1b1411" stop-opacity="0"/></radialGradient><style>
text{{font-family:ui-rounded,system-ui,-apple-system,"Segoe UI",sans-serif}}.eyebrow{{fill:#c89469;font-size:12px;font-weight:700;letter-spacing:2.3px}}.headline{{fill:#f5e7d2;font-size:31px;font-weight:700}}.body{{fill:#c9b6a3;font-size:15px}}.label{{fill:#ac9683;font-size:10px;font-weight:700;letter-spacing:1.2px}}.value{{fill:#f5e7d2;font-size:27px;font-weight:700}}.date{{fill:#e0c7ad;font-size:13px}}.bean{{fill:#a9714c}}
@keyframes steam{{0%,100%{{opacity:.25;transform:translateY(2px)}}50%{{opacity:.8;transform:translateY(-5px)}}}}@keyframes drift{{0%,100%{{transform:translateY(0) rotate(0deg)}}50%{{transform:translateY(-7px) rotate(8deg)}}}}@keyframes shimmer{{0%,100%{{opacity:.1}}50%{{opacity:.28}}}}.steam{{animation:steam 3.2s ease-in-out infinite;transform-origin:center}}.bean{{animation:drift 5s ease-in-out infinite;transform-origin:center}}.glow{{animation:shimmer 7s ease-in-out infinite}}@media(prefers-reduced-motion:reduce){{*,*::before,*::after{{animation:none!important;transition:none!important}}}}
</style></defs>
<rect width="1000" height="390" rx="28" fill="#1b1411"/><circle class="glow" cx="815" cy="140" r="250" fill="url(#glow)"/><rect x="1" y="1" width="998" height="388" rx="27" fill="none" stroke="#493329"/>
<g opacity=".8"><path d="M86 69l2 6 6 2-6 2-2 6-2-6-6-2 6-2z" fill="#e1bd93"/><path d="M899 93l1.5 4.5L905 99l-4.5 1.5L899 105l-1.5-4.5L893 99l4.5-1.5z" fill="#d5a987"/><circle cx="847" cy="195" r="2" fill="#e9cdb0"/><circle cx="105" cy="210" r="1.5" fill="#e9cdb0"/></g>
<g transform="translate(824 43)"><path d="M24 36c-9-9 9-12 0-23m17 22c-8-8 8-11 1-20" fill="none" stroke="#d6aa83" stroke-width="3" stroke-linecap="round" class="steam"/><rect x="4" y="43" width="59" height="57" rx="13" fill="#c89469"/><path d="M63 56h8a13 13 0 010 26h-8" fill="none" stroke="#c89469" stroke-width="7"/><path d="M16 57q17-11 35 0" fill="none" stroke="#f5e7d2" stroke-width="3" opacity=".75"/><circle cx="24" cy="71" r="2.3" fill="#3a271e"/><circle cx="43" cy="71" r="2.3" fill="#3a271e"/><path d="M27 80q7 7 14 0" fill="none" stroke="#3a271e" stroke-width="2.5" stroke-linecap="round"/></g>
<g class="bean"><ellipse cx="931" cy="206" rx="7" ry="4" class="bean" transform="rotate(-30 931 206)"/><path d="M926 208l10-5" stroke="#1b1411" stroke-width="1.3"/></g>
<text x="48" y="61" class="eyebrow">GITHUB</text><text x="48" y="111" class="headline">Public repositories, stars and followers.</text><text x="48" y="141" class="body">{username_xml}</text><text x="48" y="184" class="date">Updated {date_label}</text>
{''.join(cards)}<text x="48" y="366" class="eyebrow" style="font-size:9px;letter-spacing:1.2px">{status}</text><text x="952" y="366" text-anchor="end" class="date" style="font-size:10px">{date_label}</text></svg>'''


def write_update(username: str, day: date, stats: dict[str, int] | None, output: Path = OUTPUT) -> None:
    content = render_svg(username, day, stats)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    temporary.write_text(content, encoding="utf-8")
    temporary.replace(output)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--username", default=os.environ.get("GITHUB_REPOSITORY_OWNER", "yuyudaodevlab"))
    parser.add_argument("--offline", action="store_true", help="write a clearly unavailable snapshot without API access")
    parser.add_argument("--date", help="use a deterministic YYYY-MM-DD date")
    args = parser.parse_args(argv)
    try:
        username = valid_username(args.username)
        day = date.fromisoformat(args.date) if args.date else datetime.now(ZoneInfo("Asia/Tokyo")).date()
        stats = None if args.offline else fetch_stats(username)
        write_update(username, day, stats, OUTPUT)
    except (UpdateError, ValueError) as exc:
        print(f"profile update failed: {exc}", file=sys.stderr)
        return 1
    print(f"Updated {OUTPUT.name} for {username} ({day.isoformat()})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
