#!/usr/bin/env python3
"""Add the 4 October-batch Prime games missed at launch to data/games.json.

Verified 2026-11-17: Luna claims detail pages (primary) + appgamer / beebom /
2ndshift / metacritic / steamdeckhq trackers (second source). Deadlines:
Trash Goblin Dec 2, Time Travel Nov 25, Caravan SandWitch Dec 16,
WarBreeds Jan 8 2027. claim_from dates are the October batch start dates
per metacritic's dated list.
"""
import json
import pathlib

ROOT = pathlib.Path("/home/hatch/workspace/free-game-hot")
P = ROOT / "data" / "games.json"
d = json.loads(P.read_text(encoding="utf-8"))

NEW = [
    {
        "category": "prime",
        "claim_by": "2026-12-02",
        "claim_by_label": "2026-12-02",
        "claim_from": "2026-10-29",
        "en_summary": "A cozy shop game about cleaning up odd trinkets, upcycling them, and selling them on.",
        "id": "trash-goblin-prime",
        "link": "https://luna.amazon.com/claims",
        "source": "Prime Gaming / Amazon Luna",
        "status": "claimable",
        "title": "Trash Goblin",
        "zh_summary": "温馨小店经营：收拾各种古怪小玩意儿，翻新改造后再卖出去。",
    },
    {
        "category": "prime",
        "claim_by": "2026-11-25",
        "claim_by_label": "2026-11-25",
        "claim_from": "2026-10-22",
        "en_summary": "Escape-room puzzles and hidden objects built around a broken time machine.",
        "id": "time-travel-escape-room-prime",
        "link": "https://luna.amazon.com/claims",
        "source": "Prime Gaming / Amazon Luna",
        "status": "claimable",
        "title": "Time Travel: Escape Room Game",
        "zh_summary": "围绕一台坏掉的时间机器解谜、找隐藏物品的密室逃脱。",
    },
    {
        "category": "prime",
        "claim_by": "2026-12-16",
        "claim_by_label": "2026-12-16",
        "claim_from": "2026-10-15",
        "en_summary": "A laid-back road trip in a van across a sci-fi world inspired by Provence.",
        "id": "caravan-sandwitch-prime",
        "link": "https://luna.amazon.com/claims",
        "source": "Prime Gaming / Amazon Luna",
        "status": "claimable",
        "title": "Caravan SandWitch",
        "zh_summary": "开着房车在普罗旺斯风情的科幻世界里悠闲探索。",
    },
    {
        "category": "prime",
        "claim_by": "2027-01-08",
        "claim_by_label": "2027-01-08",
        "claim_from": "2026-10-08",
        "en_summary": "A sci-fi real-time strategy game where four clans fight over a fallen empire.",
        "id": "warbreeds-prime",
        "link": "https://luna.amazon.com/claims",
        "source": "Prime Gaming / Amazon Luna",
        "status": "claimable",
        "title": "WarBreeds",
        "zh_summary": "科幻即时战略，四个氏族为一个陨落的帝国开战。",
    },
]

ids = {g["id"] for g in d["games"]}
for g in NEW:
    assert g["id"] not in ids, f"duplicate {g['id']}"
    d["games"].append(g)

d["updated"] = "2026-11-17T17:10:00Z"
d["updated_beijing"] = "2026-11-18 01:10"
d["note"] = (
    "All summaries are written in our own words. No store description text is copied. "
    "Claim-by dates verified 2026-11-17 from Epic and Prime/Luna listings via independent trackers; "
    "the four October-batch Prime games (Trash Goblin, Time Travel: Escape Room Game, "
    "Caravan SandWitch, WarBreeds) were added 2026-11-17 after their deadlines were read on the "
    "Luna claims detail pages and cross-checked on trackers; "
    "TBC means Amazon had not published an end date when checked."
)
P.write_text(json.dumps(d, ensure_ascii=False, sort_keys=True, separators=(",", ":")), encoding="utf-8")
print(f"games: {len(d['games'])} (was 13), claimable: {sum(1 for g in d['games'] if g['status']=='claimable')}")
