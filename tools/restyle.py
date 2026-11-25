#!/usr/bin/env python3
"""Rebuild free-game-hot pages in the hot-site-template layout.

Reads data/games.json + config.json and renders every page (ZH + EN) with
the template's own shell: sidebar / rail / topbar / tabbar / footer,
feed-item cards, hot rows, day sections, search overlay, theme boot.
The template CSS is copied verbatim into assets/site.css; the logo and
icons come from tools/template_assets.py (copied from the template repo's
tools/generate.py). This script is our own generator, not the template's.
"""
import html
import json
import pathlib
import re
import sys
from datetime import datetime, timezone

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from template_assets import ICONS, LOGO_SVG

ROOT = pathlib.Path(__file__).resolve().parent.parent
CFG = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
GAMES = json.loads((ROOT / "data" / "games.json").read_text(encoding="utf-8"))
DEALS = json.loads((ROOT / "data" / "deals.json").read_text(encoding="utf-8"))
SITE = CFG["site"]
BEACON = CFG.get("web_analytics_token") or SITE.get("web_analytics_token") or ""
CLARITY_ID = CFG.get("clarity_id") or SITE.get("clarity_id") or ""
# Data snapshot time; days-left is computed against it, never invented.
NOW = datetime(2026, 11, 25, 17, 15, tzinfo=timezone.utc)
UPDATED = GAMES["updated_beijing"]  # "2026-11-17 18:00"

CATS = {c["key"]: c for c in CFG["categories"] if c["key"] in ("epic", "prime", "steam_gog", "steam_deals")}
CAT_ORDER = ["epic", "prime", "steam_gog"]
DEALS_CAT = CATS["steam_deals"]
EVENTS = {e["id"]: e for e in DEALS["events"]}

# Featured picks: soonest to expire first, plus each rotation's headliner — exactly 4.
FEATURED_IDS = ["mark-of-the-deep-epic", "kiborg-prime",
                "trash-goblin-prime", "jurassic-world-evolution-2-prime"]


def esc(s):
    return html.escape(str(s), quote=True)


def L(lang, zh, en):
    return en if lang == "en" else zh


def icon(name, size=17):
    return (f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" '
            f'stroke="currentColor" stroke-width="2" stroke-linecap="round" '
            f'stroke-linejoin="round" aria-hidden="true">{ICONS[name]}</svg>')


def logo(size):
    return LOGO_SVG.replace('width="44" height="44"', f'width="{size}" height="{size}"')


def parse_deadline(g):
    """Return aware datetime for claim_by, or None for TBC."""
    cb = g.get("claim_by")
    if not cb:
        return None
    if "T" in cb:
        return datetime.fromisoformat(cb.replace("Z", "+00:00"))
    return datetime.fromisoformat(cb + "T23:59:00+00:00")


def days_left(g):
    d = parse_deadline(g)
    if d is None:
        return None
    delta = (d - NOW).total_seconds()
    if delta <= 0:
        return 0
    return int(-(-delta // 86400))  # ceil


def claim_from_label(g, lang):
    f = g.get("claim_from", "")
    if not f:
        return ""
    try:
        dt = datetime.fromisoformat(f.replace("Z", "+00:00")) if "T" in f else datetime.fromisoformat(f)
    except ValueError:
        return f
    if lang == "en":
        return dt.strftime("%b %-d") if sys.platform != "win32" else dt.strftime("%b %d")
    return f"{dt.month}月{dt.day}日"


def claim_by_text(g, lang):
    """Human deadline label, or TBC wording. Never invents a date.
    Shows the full offline time (date + time, UTC): date-only claim_by
    means 23:59 UTC, per parse_deadline."""
    d = parse_deadline(g)
    if d is None:
        return L(lang, "截止时间尚未公布", "Deadline not published yet")
    if lang == "en":
        day = d.strftime("%b %-d, %Y") if sys.platform != "win32" else d.strftime("%b %d, %Y")
        return f"Claim by {day} {d.strftime('%H:%M')} UTC"
    return f"截止 {d.strftime('%Y-%m-%d %H:%M')} UTC"


def urgency_pill(g, lang):
    """Template score-pill, repurposed for days-left (same classes/tiers)."""
    dl = days_left(g)
    if dl is None:
        return (f'<span class="score-pill t-quiet" title="{esc(L(lang, "截止时间尚未公布", "Deadline not published yet"))}">'
                f'<span class="lbl">{esc(L(lang, "截止", "Deadline"))}</span><span class="sep"></span>'
                f'<span class="num">TBC</span></span>')
    tier = "t-hot" if dl <= 2 else ("t-acc" if dl <= 7 else "t-quiet")
    return (f'<span class="score-pill {tier}" title="{esc(L(lang, "剩余", "Days left"))} {dl} '
            f'{esc(L(lang, "天", "days"))}">'
            f'<span class="lbl">{esc(L(lang, "剩余", "Left"))}</span><span class="sep"></span>'
            f'<span class="num">{dl}</span></span>')


def reason_text(g, lang):
    dl = days_left(g)
    if g["status"] == "coming_next" and dl is None:
        return L(lang, "截止时间尚未公布，领之前请以 Luna 页面为准。",
                 "The deadline has not been published yet — check the Luna page before you claim.")
    if g["status"] == "coming_next":
        return L(lang, f"领取窗口：{g.get('claim_by_label', '')}，过期作废。",
                 f"Claim window: {g.get('claim_by_label', '')}. Once it passes, it is gone.")
    return L(lang, f"还剩 {dl} 天，过期作废；领到手就是自己的。",
             f"{dl} days left — once the window passes, it is gone. Claimed is kept.")


def feed_item(g, lang, rank=None, badge=False, base=""):
    rank_html = ""
    if rank:
        cls = "r1" if rank == 1 else ("r2" if rank == 2 else ("r3" if rank == 3 else ""))
        rank_html = f'<span class="rank {cls}">{rank}</span>'
    badge_html = f'<span class="pick">{esc(L(lang, "精选", "Featured"))}</span>' if badge else ""
    new_html = (f'<span class="new-pill">{esc(L(lang, "即将", "Soon"))}</span>'
                if g["status"] == "coming_next" else "")
    cat = CATS[g["category"]]
    cat_label = cat.get("label_en") or cat["label"] if lang == "en" else cat["label"]
    summary = g["en_summary"] if lang == "en" else g["zh_summary"]
    dl_iso = ""
    if parse_deadline(g) is not None:
        dl_iso = g["claim_by"] if "T" in g["claim_by"] else g["claim_by"] + "T23:59:00Z"
    when_html = claim_by_text(g, lang)
    if dl_iso:
        when_html = (f'<span class="when" data-deadline="{esc(dl_iso)}">{esc(when_html)}</span>')
    else:
        when_html = f'<span class="when">{esc(when_html)}</span>'
    claim_word = L(lang, "去领取", "Claim")
    if g["status"] == "coming_next":
        claim_word = L(lang, "去查看", "View")
    return (
        f'<article class="feed-item" data-id="{esc(g["id"])}" data-category="{esc(g["category"])}">'
        f'<header class="fi-head"><span class="src">{esc(g["source"])}</span>'
        f'<time class="pt">· {esc(claim_from_label(g, lang))}</time>'
        f'{badge_html}{new_html}'
        f'<span class="sp">{urgency_pill(g, lang)}'
        f'<button type="button" class="star-btn" data-star="{esc(g["id"])}" aria-label="{esc(L(lang, "收藏", "Save"))}" title="{esc(L(lang, "收藏", "Save"))}">'
        f'{icon("bookmark", 16)}</button></span></header>'
        f'<h2><a href="{base}items/{esc(g["id"])}.html">{rank_html}{esc(g["title"])}</a></h2>'
        f'<p class="sum">{esc(summary)}</p>'
        f'<div class="fi-tags"><a class="tag" href="{base}topics.html#{esc(g["category"])}">#{esc(cat_label)}</a></div>'
        f'<div class="fi-foot"><button type="button" class="chip cat" data-filter="{esc(g["category"])}">{esc(cat_label)}</button>'
        f'{when_html}<a class="chip" href="{esc(g["link"])}" target="_blank" rel="noopener">{esc(claim_word)} →</a></div>'
        f'<p class="fi-reason">{esc(L(lang, "推荐理由：", "Why this: "))}{esc(reason_text(g, lang))}</p>'
        f'</article>')


def hot_row(g, rank, lang, base=""):
    dl = days_left(g)
    cls = "r1" if rank == 1 else ("r2" if rank == 2 else ("r3" if rank == 3 else ""))
    if dl is None:
        heat = (f'<span class="hot-heat"><b class="num">TBC</b> '
                f'{esc(L(lang, "待公布", "TBC"))}</span>')
    else:
        heat = (f'<span class="hot-heat"><b class="num">{dl}</b> '
                f'{esc(L(lang, "天后截止", "days left"))}</span>')
    return (f'<li><a class="hot-row" href="{base}items/{esc(g["id"])}.html">'
            f'<span class="rank {cls}">{rank}</span>'
            f'<span class="t">{esc(g["title"])}</span>{heat}</a></li>')


# ---- Steam big deals (data/deals.json; prices from the Steam store,
#      end dates per-app from SteamDB; never invent a date) ----

def deal_ends_dt(d):
    return datetime.fromisoformat(d["ends"] + "T23:59:00+00:00")


def deal_days_left(d):
    delta = (deal_ends_dt(d) - NOW).total_seconds()
    if delta <= 0:
        return 0
    return int(-(-delta // 86400))  # ceil


def deal_event_name(d, lang):
    ev = EVENTS.get(d["event"])
    if not ev:
        return ""
    return ev.get("name_en") or ev["name"] if lang == "en" else ev["name"]


def deal_claim_by_text(d, lang):
    return L(lang, f'截止 {d["ends_label"]}', f'Ends {d["ends_label"]}')


def deal_reason(d, lang):
    saved = d["original"] - d["price"]
    ev = deal_event_name(d, lang)
    if lang == "en":
        return (f'Was ${d["original"]:.2f}, now ${d["price"]:.2f} — save ${saved:.2f}. '
                f'{ev + ", " if ev else ""}ends {d["ends_label"]}.')
    return (f'原价 ${d["original"]:.2f}，现价 ${d["price"]:.2f}，省 ${saved:.2f}。'
            f'{ev + "，"}截止 {d["ends_label"]}。')


def deal_item(d, lang, base=""):
    tier = "t-hot" if d["discount"] >= 75 else ("t-acc" if d["discount"] >= 65 else "t-quiet")
    pill = (f'<span class="score-pill {tier}" title="{esc(L(lang, "折扣", "Discount"))} -{d["discount"]}%">'
            f'<span class="lbl">-{d["discount"]}%</span><span class="sep"></span>'
            f'<span class="num">${d["price"]:.2f}</span></span>')
    cat_label = DEALS_CAT.get("label_en") or DEALS_CAT["label"] if lang == "en" else DEALS_CAT["label"]
    summary = d["en_summary"] if lang == "en" else d["zh_summary"]
    src = f'Steam · {deal_event_name(d, lang)}' if deal_event_name(d, lang) else "Steam"
    dl_iso = d["ends"] + "T23:59:00Z"
    when = deal_claim_by_text(d, lang)
    return (
        f'<article class="feed-item" data-id="{esc(d["id"])}" data-category="steam_deals">'
        f'<header class="fi-head"><span class="src">{esc(src)}</span>'
        f'<span class="sp">{pill}'
        f'<button type="button" class="star-btn" data-star="{esc(d["id"])}" aria-label="{esc(L(lang, "收藏", "Save"))}" title="{esc(L(lang, "收藏", "Save"))}">'
        f'{icon("bookmark", 16)}</button></span></header>'
        f'<h2><a href="{base}items/{esc(d["id"])}.html">{esc(d["title"])}</a></h2>'
        f'<p class="sum">{esc(summary)}</p>'
        f'<div class="fi-tags"><a class="tag" href="{base}topics/steam-deals.html">#{esc(cat_label)}</a></div>'
        f'<div class="fi-foot"><button type="button" class="chip cat" data-filter="steam_deals">{esc(cat_label)}</button>'
        f'<span class="when" data-deadline="{esc(dl_iso)}">{esc(when)}</span>'
        f'<a class="chip" href="{esc(d["link"])}" target="_blank" rel="noopener">{esc(L(lang, "去 Steam 购买", "Buy on Steam"))} →</a></div>'
        f'<p class="fi-reason">{esc(L(lang, "推荐理由：", "Why this: "))}{esc(deal_reason(d, lang))}</p>'
        f'</article>')


def deals_data_json(lang):
    return json.dumps([
        {"id": d["id"], "title": d["title"],
         "summary": d["en_summary"] if lang == "en" else d["zh_summary"],
         "source": "Steam", "link": d["link"],
         "claim_by": deal_claim_by_text(d, lang), "category": "steam_deals"}
        for d in DEALS["deals"]], ensure_ascii=False)


def all_data_json(games, lang):
    """games + deals in the search/starred data shape."""
    g = json.loads(games_data_json(games, lang))
    d = json.loads(deals_data_json(lang))
    return json.dumps(g + d, ensure_ascii=False)


def deals_block(lang, base):
    n = len(DEALS["deals"])
    return (f'<h2 class="sec">{esc(L(lang, "Steam 大折扣", "Steam big deals"))}</h2>'
            f'<p>{esc(L(lang, f"本周 Steam 大折扣 {n} 款，最高 90% off：SEGA 黑五特卖至 11 月 30 日，Steam 周度特卖黑五版 11 月 23–30 日。价格以 Steam 商店为准（美元），每款的截止日逐一核实过。",
                         f"{n} Steam big deals this week, up to 90% off: SEGA Black Friday sale ends Nov 30, Steam Weeklong Sale Black Friday edition Nov 23–30. Prices are from the Steam store (USD); every deal's end date was checked."))} '
            f'<a href="{base}topics/steam-deals.html">{esc(L(lang, f"查看全部 {n} 款折扣 →", f"See all {n} deals →"))}</a></p>')


# ---- shell (mirrors the template's sidebar/rail/topbar/tabbar/footer) ----

THEME_BOOT = ("<script>(function(){try{var k='free-game-hot-theme';function sys(){return window.matchMedia"
              "&&matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light';}function apply(t){"
              "document.documentElement.setAttribute('data-theme',t==='dark'?'dark':'light');}var saved="
              "localStorage.getItem(k);if(saved==='dark'||saved==='light'){apply(saved);}else{apply(sys());"
              "var mq=window.matchMedia&&matchMedia('(prefers-color-scheme: dark)');if(mq&&mq.addEventListener)"
              "{mq.addEventListener('change',function(){try{if(!localStorage.getItem(k))apply(sys());}catch(e){}});}}"
              "}catch(e){}})();</script>")


def _lang_boot(lang, alt_href):
    return (
        "<script>(function(){try{var k='free-game-hot-lang';"
        "if(localStorage.getItem(k))return;"
        "if(/bot|crawler|spider|crawling|slurp|facebookexternal|preview/i"
        ".test(navigator.userAgent||''))return;"
        "var want=(navigator.language||navigator.userLanguage||'en')"
        ".toLowerCase().indexOf('zh')===0?'zh':'en';"
        "localStorage.setItem(k,want);"
        f"if(want!==\"{lang}\")location.replace({json.dumps(alt_href)});"
        "}catch(e){}})();</script>")


def _lang_onclick(other):
    return f"onclick=\"try{{localStorage.setItem('free-game-hot-lang','{other}')}}catch(e){{}}\""


def _nav_items(base, lang):
    if lang == "en":
        labels = [("featured", "Featured"), ("all", "All Items"), ("hot", "Hot List"),
                  ("daily", "Daily"), ("starred", "Saved")]
    else:
        labels = [("featured", "精选"), ("all", "全部动态"), ("hot", "热点榜"),
                  ("daily", "日报"), ("starred", "收藏")]
    icons = {"featured": "zap", "all": "list", "hot": "trend", "daily": "doc", "starred": "bookmark"}
    hrefs = {"featured": f"{base}index.html", "all": f"{base}all.html", "hot": f"{base}hot.html",
             "daily": f"{base}daily.html", "starred": f"{base}starred.html"}
    return [(k, label, icons[k], hrefs[k]) for k, label in labels]


def sidebar_html(active, base, lang, alt_href):
    items = _nav_items(base, lang)
    star_count_span = '<span class="num" id="starCount"></span>'
    links = "".join(
        f'<a class="side-link{" on" if key == active else ""}" href="{href}">'
        f'{icon(ic)}<span>{label}</span>'
        f'{(star_count_span if key == "starred" else "")}</a>'
        for key, label, ic, href in items)
    more_links = (
        f'<a class="side-link{" on" if active == "more" else ""}" href="{base}more.html">{icon("user")}<span>{esc(L(lang, "我的", "My"))}</span></a>'
        f'<a class="side-link" href="{base}weekly.html">{icon("calendar")}<span>{esc(L(lang, "周报", "Weekly"))}</span></a>'
        f'<a class="side-link" href="{base}monthly.html">{icon("calendar")}<span>{esc(L(lang, "月报", "Monthly"))}</span></a>'
        f'<a class="side-link{" on" if active == "changelog" else ""}" href="{base}changelog.html">{icon("doc")}<span>{esc(L(lang, "更新日志", "Changelog"))}</span></a>'
        f'<a class="side-link{" on" if active == "about" else ""}" href="{base}about.html">{icon("rss")}<span>{esc(L(lang, "关于", "About"))}</span></a>'
        f'<a class="side-link" href="{esc(SITE["repo"])}/issues" target="_blank" rel="noopener">{icon("message")}<span>{esc(L(lang, "反馈", "Feedback"))}</span></a>'
        f'<a class="side-link" href="{base}data/games.json">{icon("code")}<span>{esc(L(lang, "数据 JSON", "Data JSON"))}</span></a>')
    subtitle = SITE.get("subtitle_en") or SITE.get("subtitle", "") if lang == "en" else SITE.get("subtitle", "")
    lang_link = ""
    if alt_href:
        other = "en" if lang == "zh" else "zh"
        lang_link = (f'<a class="gh" href="{alt_href}" {_lang_onclick(other)}>'
                     f'{esc(L(lang, "English", "Chinese"))}</a>')
    return (f'<aside class="sidebar"><a class="brand" href="{base}index.html">{logo(32)}'
            f'<span><b>{esc(SITE["name"] if lang == "zh" else SITE["title_en"])}</b><small>{esc(subtitle)}</small></span></a>'
            f'<nav aria-label="{esc(L(lang, "主导航", "Main navigation"))}"><div class="nav-sec"><h3>{esc(L(lang, "内容", "Content"))}</h3>{links}</div>'
            f'<div class="nav-sec"><h3>{esc(L(lang, "更多", "More"))}</h3>{more_links}'
            f'</div></nav>'
            f'<div class="side-foot">'
            f'<a class="gh" href="{esc(SITE["repo"])}" target="_blank" rel="noopener">{esc(L(lang, "GitHub 仓库", "GitHub Repo"))}</a>'
            f'{lang_link}'
            f'{_theme_btn(lang)}'
            f'<p class="note">{esc(L(lang, "每天 " + SITE["edition_time_cst"] + " 出日报", "Daily digest at " + SITE["edition_time_cst"]))}</p>'
            f'</div></aside>')


def rail_html(active, base, lang):
    items = _nav_items(base, lang)
    links = "".join(
        f'<a class="rail-link{" on" if key == active else ""}" href="{href}">'
        f'{icon(ic, 20)}<span>{label}</span></a>'
        for key, label, ic, href in items)
    links += (f'<a class="rail-link{" on" if active == "more" else ""}" href="{base}more.html">'
              f'{icon("user", 20)}<span>{esc(L(lang, "我的", "My"))}</span></a>')
    rail_name = SITE["title_en"] if lang == "en" else SITE["name"]
    return (f'<aside class="rail"><a class="brand" href="{base}index.html" aria-label="{esc(rail_name)}">'
            f'{logo(28)}</a><nav aria-label="{esc(L(lang, "主导航", "Main navigation"))}">{links}</nav></aside>')


def _theme_btn(lang="zh"):
    return ('<button type="button" class="icon-btn theme-btn theme-cycle" aria-label="'
            + esc(L(lang, "外观：跟随系统（点击切换）", "Appearance: system (click to switch)")) + '">'
            f'<span class="ic-moon">{icon("moon", 20)}</span>'
            f'<span class="ic-sun">{icon("sun", 20)}</span>'
            f'<span class="ic-monitor">{icon("monitor", 20)}</span></button>')


def topbar_html(active, base, lang):
    if active in ("daily", "weekly", "monthly"):
        center = ('<span class="title">'
                  + {"daily": L(lang, "日报", "Daily"), "weekly": L(lang, "周报", "Weekly"),
                     "monthly": L(lang, "月报", "Monthly")}[active] + '</span>')
    else:
        center = (f'<span class="switch">'
                  f'<a class="{"on" if active == "featured" else ""}" href="{base}index.html">{esc(L(lang, "精选", "Featured"))}</a>'
                  f'<a class="{"on" if active == "all" else ""}" href="{base}all.html">{esc(L(lang, "全部", "All"))}</a></span>')
    return (f'<header class="topbar"><a class="brand" href="{base}index.html">{logo(26)}<b>{esc(SITE["name"] if lang == "zh" else SITE["title_en"])}</b></a>'
            f'{center}{_theme_btn(lang)}</header>')


def tabbar_html(active, base, lang):
    tabs = [
        ("featured", L(lang, "精选", "Featured"), "zap", f"{base}index.html"),
        ("hot", L(lang, "热点", "Hot"), "trend", f"{base}hot.html"),
        ("daily", L(lang, "日报", "Daily"), "doc", f"{base}daily.html"),
        ("all", L(lang, "全部", "All"), "list", f"{base}all.html"),
        ("starred", L(lang, "收藏", "Saved"), "bookmark", f"{base}starred.html"),
    ]
    links = "".join(
        f'<a class="{"on" if key == active else ""}" href="{href}">'
        f'{icon(ic, 20)}<span>{label}</span></a>'
        for key, label, ic, href in tabs)
    return f'<nav class="tabbar" aria-label="{esc(L(lang, "主导航", "Main navigation"))}"><div class="tabbar-in">{links}</div></nav>'


def footer_html(base, lang):
    name = SITE["name"] if lang == "zh" else SITE["title_en"]
    if lang == "en":
        p1 = (f"{name} is an aggregator and reading index. Titles and summaries "
              "belong to their original sources. Content is for reference "
              "only; full text is never republished.")
        note = SITE.get("footer_note_en", "")
    else:
        p1 = (f"{name} 是聚合摘要与阅读索引，标题与摘要版权归各来源所有。"
              "内容只作资讯参考；本站不转载全文。")
        note = SITE.get("footer_note", "")
    tips = SITE.get("tips") or []
    tip_html = ""
    if tips:
        cards = "".join(
            f'<div class="tip-card"><img class="tip-qr" src="{base}{esc(t["image"])}" alt="{esc(L(lang, "赞赏码：", "Tip QR code: "))}{esc(t["label"])}" width="150" height="150">'
            f'<p class="tip-label">{esc(t["label"])}</p>'
            f'<p class="tip-addr">{esc(t["address"])}</p></div>'
            for t in tips)
        tip_html = (f'<div class="tip"><p class="tip-title">{esc(L(lang, "赞赏支持", "Support " + name))}</p>'
                    f'<div class="tip-cards">{cards}</div></div>')
    return (f'<footer class="foot"><p>{esc(p1)}</p>'
            + (f'<p>{esc(note)}</p>' if note else '')
            + f'<nav class="foot-links" aria-label="{esc(L(lang, "页脚链接", "Footer links"))}">'
            f'<a href="{base}feed.xml">{esc(L(lang, "RSS 订阅", "RSS Feed"))}</a>'
            f'<a href="{base}data/games.json">{esc(L(lang, "数据 JSON", "Data JSON"))}</a>'
            f'<a href="{esc(SITE["repo"])}">{esc(L(lang, "GitHub 仓库", "GitHub Repo"))}</a>'
            f'<a href="{esc(SITE["repo"])}/issues">{esc(L(lang, "反馈", "Feedback"))}</a>'
            f'<a href="{base}more.html">{esc(L(lang, "我的", "My"))}</a>'
            f'<a href="{base}about.html">{esc(L(lang, "关于", "About"))}</a>'
            f'<a href="{base}terms.html">{esc(L(lang, "条款", "Terms"))}</a>'
            f'<a href="{base}privacy.html">{esc(L(lang, "隐私", "Privacy"))}</a></nav>'
            f'{tip_html}</footer>')


def _alt_lang_href(lang, rel_path):
    depth = rel_path.count("/")
    if lang == "zh":
        return "../" * depth + "en/" + (rel_path or "index.html")
    return "../" * (depth + 1) + (rel_path or "index.html")


def page_open(active, title, description, base, lang, rel_path, page_cls=""):
    site_url = SITE["url"].rstrip("/")
    canon = site_url + "/" + rel_path if lang == "zh" else site_url + "/en/" + rel_path
    if rel_path == "":
        canon = site_url + "/" if lang == "zh" else site_url + "/en/"
    zh_url = site_url + "/" + rel_path
    en_url = site_url + "/en/" + rel_path
    hreflang = (f'<link rel="alternate" hreflang="zh-CN" href="{esc(zh_url)}">\n'
                f'<link rel="alternate" hreflang="en" href="{esc(en_url)}">\n'
                f'<link rel="alternate" hreflang="x-default" href="{esc(en_url)}">\n')
    feed_href = site_url + ("/en/feed.xml" if lang == "en" else "/feed.xml")
    feed_title = SITE["title_en"] if lang == "en" else SITE["name"]
    og = (f'<meta property="og:title" content="{esc(title)}">\n'
          f'<meta property="og:description" content="{esc(description)}">\n'
          f'<meta property="og:type" content="website">\n'
          f'<meta property="og:url" content="{esc(canon)}">\n'
          f'<meta property="og:image" content="{site_url}/favicon.svg">\n'
          f'<meta name="twitter:card" content="summary">\n'
          f'<meta name="twitter:title" content="{esc(title)}">\n'
          f'<meta name="twitter:description" content="{esc(description)}">\n'
          f'<meta name="twitter:image" content="{site_url}/favicon.svg">\n')
    ld = {"@context": "https://schema.org", "@type": "WebSite",
          "name": SITE["name"] if lang == "zh" else SITE["title_en"],
          "url": site_url + "/en/" if lang == "en" else site_url,
          "inLanguage": "en" if lang == "en" else "zh-CN",
          "description": description}
    ld_html = f'<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>\n'
    alt_href = _alt_lang_href(lang, rel_path)
    boot = THEME_BOOT + _lang_boot(lang, alt_href)
    return (f'<!DOCTYPE html>\n<html lang="{"en" if lang == "en" else "zh-CN"}"><head><meta charset="utf-8">\n'
            f'<meta name="viewport" content="width=device-width, initial-scale=1">\n'
            f'<title>{esc(title)}</title>\n'
            f'<meta name="description" content="{esc(description)}">\n'
            f'<link rel="canonical" href="{esc(canon)}">\n'
            f'{hreflang}'
            f'<meta name="robots" content="index, follow, max-image-preview:large">\n'
            f'<link rel="alternate" type="application/rss+xml" title="{esc(feed_title)}" href="{feed_href}">\n'
            f'<link rel="icon" type="image/svg+xml" href="{base}favicon.svg">\n'
            f'{og}'
            f'{ld_html}'
            f'{boot}<link rel="stylesheet" href="{base}assets/site.css"></head>\n<body>'
            f'<div class="shell">{sidebar_html(active, base, lang, alt_href)}{rail_html(active, base, lang)}'
            f'<div class="main">{topbar_html(active, base, lang)}<div class="page{page_cls}">')


def beacon_html():
    if not BEACON:
        return ""
    return (f"<!-- Cloudflare Web Analytics --><script type='module' "
            f"src='https://static.cloudflareinsights.com/beacon.min.js' "
            f"data-cf-beacon='{{\"token\": \"{BEACON}\"}}'></script>"
            f"<!-- End Cloudflare Web Analytics -->")



def clarity_html():
    if not CLARITY_ID:
        return ""
    return ("<script type=\"text/javascript\">" + "(function(c,l,a,r,i,t,y){c[a]=c[a]||function(){(c[a].q=c[a].q||[]).push(arguments)};"
            "t=l.createElement(r);t.async=1;t.src=\"https://www.clarity.ms/tag/\"+i;"
            "y=l.getElementsByTagName(r)[0];y.parentNode.insertBefore(t,y);})"
            "(window, document, \"clarity\", \"script\", \"" + CLARITY_ID + "\");</script>")

def page_close(active, base, lang):
    to_top = (f'<button type="button" class="to-top" id="toTop" aria-label="{esc(L(lang, "回到顶部", "Back to top"))}">'
              f'{icon("arrow-up", 18)}</button>')
    return (f"{footer_html(base, lang)}</div></div></div>{to_top}{tabbar_html(active, base, lang)}"
            f"<script src='{base}assets/site.js'></script>{beacon_html()}{clarity_html()}</body></html>\n")


def filter_row(lang, base):
    chips = "".join(
        f'<button type="button" class="chip" data-filter="{k}">{esc(CATS[k].get("label_en") or CATS[k]["label"] if lang == "en" else CATS[k]["label"])}</button>'
        for k in CAT_ORDER)
    search_html = (f'<div class="search" role="search">{icon("search", 16)}'
                   f'<input id="siteSearch" type="text" placeholder="{esc(L(lang, "搜索标题、摘要…", "Search titles and summaries…"))}" '
                   f'maxlength="200" autocomplete="off" aria-label="{esc(L(lang, "搜索标题和摘要", "Search titles and summaries"))}">'
                   f'<button type="button" class="clear" id="searchClear" aria-label="{esc(L(lang, "清空", "Clear"))}">✕</button>'
                   f'<kbd>/</kbd></div>')
    search_trigger = (f'<button type="button" class="search-trigger" aria-label="{esc(L(lang, "打开搜索", "Open search"))}">'
                      f'{icon("search", 16)}<span>{esc(L(lang, "搜索标题、摘要…", "Search titles and summaries…"))}</span></button>')
    return (f'<div class="filter-row"><div class="tabs" role="tablist" aria-label="{esc(L(lang, "分类筛选", "Filter by category"))}">'
            f'<span class="tabs-thumb" id="tabsThumb"></span>'
            f'<button type="button" class="chip on" data-filter="all">{esc(L(lang, "全部", "All"))}</button>{chips}</div>'
            f'{search_trigger}{search_html}</div>')


def search_overlay(lang, base, hot5):
    overlay_cats = "".join(
        f'<button type="button" class="chip" data-filter="{k}">{esc(CATS[k].get("label_en") or CATS[k]["label"] if lang == "en" else CATS[k]["label"])}</button>'
        for k in CAT_ORDER)
    overlay_hot = "".join(
        f'<li><span class="rank{" r1" if i == 0 else (" r2" if i == 1 else (" r3" if i == 2 else ""))}">{i + 1}</span>'
        f'<a href="{base}items/{esc(g["id"])}.html">{esc(g["title"])}</a></li>'
        for i, g in enumerate(hot5))
    return (
        f'<div class="search-overlay" id="searchOverlay" hidden>'
        f'<div class="overlay-bar"><button type="button" class="icon-btn" id="overlayClose" aria-label="{esc(L(lang, "关闭搜索", "Close search"))}">{icon("x", 20)}</button>'
        f'<div class="search overlay-search">{icon("search", 16)}'
        f'<input id="overlaySearch" type="text" placeholder="{esc(L(lang, "搜索标题、摘要…", "Search titles and summaries…"))}" maxlength="200" autocomplete="off" aria-label="{esc(L(lang, "搜索标题和摘要", "Search titles and summaries"))}">'
        f'<button type="button" class="clear" id="overlaySearchClear" aria-label="{esc(L(lang, "清空", "Clear"))}">✕</button></div></div>'
        f'<div class="overlay-sec"><h3>{esc(L(lang, "最近搜索", "Recent searches"))}</h3><div id="recentList"></div>'
        f'<button type="button" class="recent-clear" id="clearRecent">{esc(L(lang, "清除最近搜索", "Clear recent searches"))}</button></div>'
        f'<div class="overlay-sec"><h3>{esc(L(lang, "按分类找", "Browse by category"))}</h3><div class="overlay-cats">{overlay_cats}</div></div>'
        f'<div class="overlay-sec"><h3>{esc(L(lang, "正在热议", "Trending now"))}</h3><ol class="overlay-hot">{overlay_hot}</ol></div>'
        f'</div>')


def empty_state(lang):
    return (
        '<div id="noResult" class="empty-state" hidden>'
        f'<div class="empty-icon" id="noResultIcon">{icon("search", 40)}</div>'
        f'<h3 class="empty-title" id="noResultTitle">{esc(L(lang, "这个分类下暂无动态。", "No items in this category yet."))}</h3>'
        '<p class="empty-text" id="noResultText"></p>'
        '<div class="empty-actions">'
        f'<button type="button" class="empty-btn" data-empty-action="clear">{esc(L(lang, "清除筛选", "Clear filters"))}</button>'
        f'<button type="button" class="empty-btn primary" data-empty-action="featured">{esc(L(lang, "去看精选", "See featured"))}</button>'
        '</div></div>')


def day_sections(games, lang, base):
    """Group games by claim-by date, template day-sec style."""
    groups = {}
    order = []
    for g in games:
        d = parse_deadline(g)
        key = d.date().isoformat() if d else "tbc"
        if key not in groups:
            groups[key] = []
            order.append(key)
        groups[key].append(g)
    out = []
    for key in order:
        gs = groups[key]
        if key == "tbc":
            name = L(lang, "待公布", "To be announced")
            date_txt = ""
        else:
            dt = datetime.fromisoformat(key)
            wd = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"][dt.weekday()]
            wd_en = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][dt.weekday()]
            name = L(lang, "今天" if key == "2026-11-17" else wd,
                     "Today" if key == "2026-11-17" else wd_en)
            date_txt = L(lang, f"{dt.month}月{dt.day}日 · {wd}", f"{dt.strftime('%b %d')} · {wd_en}")
        out.append(
            f'<section class="day-sec" data-date="{esc(key)}">'
            f'<header class="day-head"><span class="dh-name">{esc(name)}</span>'
            + (f'<span class="dh-date">{esc(date_txt)}</span>' if date_txt else '')
            + f'<span class="dh-count"><b class="num">{len(gs)}</b> {esc(L(lang, "款", "games"))}</span></header>'
            + "".join(feed_item(g, lang, base=base) for g in gs)
            + '</section>')
    return "".join(out)


def games_data_json(games, lang):
    return json.dumps([
        {"id": g["id"], "title": g["title"],
         "summary": g["en_summary"] if lang == "en" else g["zh_summary"],
         "source": g["source"], "link": g["link"],
         "claim_by": claim_by_text(g, lang), "category": g["category"]}
        for g in games], ensure_ascii=False)


def steam_gog_note(lang, base):
    return (f'<h2 class="sec">{esc(L(lang, "Steam / GOG 限免", "Steam / GOG freebies"))}</h2>'
            f'<p>{esc(L(lang, "本周 Steam 和 GOG 没有正在进行的免费领取（2026-11-25 核查）。有新的限免会第一时间加进来。",
                         "No free Steam or GOG game is running this week (checked 2026-11-25). New freebies will be added here as soon as they appear."))}</p>')


def why_section(lang):
    return (f'<h2 class="sec">{esc(L(lang, "为什么值得每周看一眼", "Why check every week"))}</h2>'
            f'<p>{esc(L(lang, "Epic 每周四轮换，窗口只有 7 天；Prime 每月分批上架，各自有截止时间。2025 年 Epic 送出 100 款免费游戏，领取 6.62 亿次。领到手就是自己的，过期作废。",
                         "Epic rotates every Thursday, with a 7-day window; Prime adds games in batches through the month, each with its own deadline. In 2025 Epic gave away 100 free games, claimed 662 million times. Once claimed, a game stays in your library; once the window passes, it is gone."))}</p>')


# ---- page builders ----

def sorted_claimable(games):
    return sorted([g for g in games if g["status"] == "claimable"],
                  key=lambda g: (parse_deadline(g) or datetime.max.replace(tzinfo=timezone.utc)))


def sorted_all(games):
    def key(g):
        d = parse_deadline(g)
        return (0, d) if d is not None else (1, datetime.max.replace(tzinfo=timezone.utc))
    return sorted(games, key=key)


def build_index(lang, base, rel_path):
    games = GAMES["games"]
    claimable = sorted_claimable(games)
    coming = [g for g in games if g["status"] == "coming_next"]
    hot5 = claimable[:5]
    title = (f'{SITE["title_en"]} · Featured & Hot List' if lang == "en"
             else f'{SITE["title"]} · 今日精选与热点榜')
    desc = SITE["description_en"] if lang == "en" else SITE["description"]
    lede = (f'Updated {esc(UPDATED)} (Beijing time)<span class="lede-rest"> · {len(games)} games listed · '
            f'{len(claimable)} claimable now · Only titles and summaries are shown; click a title for details and the outbound link.</span>'
            if lang == "en" else
            f'更新于 {esc(UPDATED)}（北京时间）<span class="lede-rest"> · 共 {len(games)} 款在列 · 现在能领 {len(claimable)} 款 · '
            f'只显示标题与摘要，点击标题查看详情，详情页里有原文链接。</span>')
    by_id = {g["id"]: g for g in games}
    featured = [by_id[i] for i in FEATURED_IDS]
    sel_html = "".join(feed_item(g, lang, badge=True, base=base) for g in featured)
    rule = (f'{esc(L(lang, "精选 = 快到期 + 每轮头牌，共 4 款。", "Featured = expiring soonest + each rotation’s headliner, 4 picks."))} '
            f'<a href="{base}all.html">{esc(L(lang, f"查看全部 {len(games)} 款 →", f"See all {len(games)} games →"))}</a>')
    hot_html = "".join(hot_row(g, i + 1, lang, base) for i, g in enumerate(hot5))
    hot_more = (f'<a class="hot-more" href="{base}hot.html">'
                f'{esc(L(lang, "完整榜单", "Full ranking"))} <span aria-hidden="true">→</span></a>') if len(claimable) > 5 else ""
    body = (f'<div class="m-title">{esc(L(lang, "精选", "Featured"))}</div>'
            f'<h1>{esc(L(lang, "精选", "Featured"))}</h1>'
            f'<p class="lede">{lede}</p>'
            f'<p class="lede">{rule}</p>'
            f'{filter_row(lang, base)}'
            f'{search_overlay(lang, base, hot5)}'
            f'{sel_html}'
            f'{empty_state(lang)}'
            f'<h2 class="sec">{esc(L(lang, "热点榜", "Hot List"))}</h2>'
            f'<ol class="hot-list">{hot_html}</ol>{hot_more}'
            f'<h2 class="sec">{esc(L(lang, "按截止时间", "By deadline"))}</h2>'
            f'{day_sections(sorted_all(games), lang, base)}'
            f'{steam_gog_note(lang, base)}'
            f'{deals_block(lang, base)}'
            f'{why_section(lang)}'
            f'<script type="application/json" id="gamesData">{games_data_json(games, lang)}</script>')
    return page_open("featured", title, desc, base, lang, rel_path) + body + page_close("featured", base, lang)


def build_all(lang, base, rel_path):
    games = sorted_all(GAMES["games"])
    title = (f'{SITE["title_en"]} · All Items' if lang == "en" else f'{SITE["title"]} · 全部动态')
    desc = SITE["description_en"] if lang == "en" else SITE["description"]
    lede = (f'Updated {esc(UPDATED)} (Beijing time)<span class="lede-rest"> · {len(games)} games, grouped by claim-by date on a timeline, soonest first.</span>'
            if lang == "en" else
            f'更新于 {esc(UPDATED)}（北京时间）<span class="lede-rest"> · 共 {len(games)} 款，按截止日期排成时间线，从最近的开始。</span>')
    body = (f'<div class="m-title">{esc(L(lang, "全部动态", "All Items"))}</div>'
            f'<h1>{esc(L(lang, "全部动态", "All Items"))}</h1>'
            f'<p class="lede">{lede}</p>'
            f'{filter_row(lang, base)}'
            f'{search_overlay(lang, base, sorted_claimable(GAMES["games"])[:5])}'
            + f'{day_sections(games, lang, base)}'
            + f'{empty_state(lang)}'
            f'{steam_gog_note(lang, base)}'
            f'<script type="application/json" id="gamesData">{games_data_json(games, lang)}</script>')
    return page_open("all", title, desc, base, lang, rel_path) + body + page_close("all", base, lang)


def build_hot(lang, base, rel_path):
    claimable = sorted_claimable(GAMES["games"])
    coming = [g for g in GAMES["games"] if g["status"] == "coming_next"]
    title = (f'{SITE["title_en"]} · Hot List' if lang == "en" else f'{SITE["title"]} · 热点榜')
    desc = SITE["description_en"] if lang == "en" else SITE["description"]
    lede = (f'{esc(L(lang, "按截止时间排序：越快过期，排得越靠前。", "Sorted by deadline: the sooner it expires, the higher it ranks."))}'
            f'<span class="lede-rest"> · {len(claimable)} {esc(L(lang, "款现在能领", "claimable now"))}</span>')
    rows = "".join(hot_row(g, i + 1, lang, base) for i, g in enumerate(claimable))
    coming_rows = "".join(hot_row(g, i + 1, lang, base) for i, g in enumerate(sorted_all(coming)))
    body = (f'<div class="m-title">{esc(L(lang, "热点榜", "Hot List"))}</div>'
            f'<h1>{esc(L(lang, "热点榜", "Hot List"))}</h1>'
            f'<p class="lede">{lede}</p>'
            f'<ol class="hot-list">{rows}</ol>'
            f'<h2 class="sec">{esc(L(lang, "即将上架", "Coming next"))}</h2>'
            f'<ol class="hot-list">{coming_rows}</ol>'
            + "".join(feed_item(g, lang, base=base) for g in claimable)
            + f'<script type="application/json" id="gamesData">{games_data_json(GAMES["games"], lang)}</script>')
    return page_open("hot", title, desc, base, lang, rel_path) + body + page_close("hot", base, lang)


def build_daily(lang, base, rel_path):
    games = sorted_all(GAMES["games"])
    title = (f'{SITE["title_en"]} · Daily' if lang == "en" else f'{SITE["title"]} · 日报')
    desc = SITE["description_en"] if lang == "en" else SITE["description"]
    lede = (f'Nov 17, 2026<span class="lede-rest"> · {len(games)} games on the calendar, grouped by claim-by date.</span>'
            if lang == "en" else
            f'2026年11月17日<span class="lede-rest"> · 共 {len(games)} 款，按截止日期分组。</span>')
    body = (f'<div class="m-title">{esc(L(lang, "日报", "Daily"))}</div>'
            f'<h1>{esc(L(lang, "日报", "Daily"))}</h1>'
            f'<p class="lede">{lede}</p>'
            f'{day_sections(games, lang, base)}'
            f'<nav class="daily-nav"><a href="{base}weekly.html">{esc(L(lang, "去看周报", "See the weekly"))} <span aria-hidden="true">→</span></a>'
            f'<a class="dn-next" href="{base}monthly.html">{esc(L(lang, "去看月报", "See the monthly"))} <span aria-hidden="true">→</span></a></nav>'
            f'<script type="application/json" id="gamesData">{games_data_json(games, lang)}</script>')
    return page_open("daily", title, desc, base, lang, rel_path) + body + page_close("daily", base, lang)


def build_weekly(lang, base, rel_path):
    games = GAMES["games"]
    this_week = [g for g in games if (g.get("claim_from") or "")[:10] <= "2026-11-23"]
    next_week = [g for g in games if (g.get("claim_from") or "")[:10] > "2026-11-23"]
    title = (f'{SITE["title_en"]} · Weekly' if lang == "en" else f'{SITE["title"]} · 周报')
    desc = SITE["description_en"] if lang == "en" else SITE["description"]
    lede = (f'Week of Nov 17 – Nov 23, 2026<span class="lede-rest"> · {len(this_week)} games this week.</span>'
            if lang == "en" else
            f'2026年11月17日—11月23日这一周<span class="lede-rest"> · 本周 {len(this_week)} 款。</span>')
    body = (f'<div class="m-title">{esc(L(lang, "周报", "Weekly"))}</div>'
            f'<h1>{esc(L(lang, "周报", "Weekly"))}</h1>'
            f'<p class="lede">{lede}</p>'
            f'<h2 class="sec">{esc(L(lang, "本周", "This week"))}</h2>'
            + "".join(feed_item(g, lang, base=base) for g in sorted_all(this_week))
            + f'<h2 class="sec">{esc(L(lang, "下周预告", "Next week"))}</h2>'
            + "".join(feed_item(g, lang, base=base) for g in sorted_all(next_week))
            + f'<script type="application/json" id="gamesData">{games_data_json(games, lang)}</script>')
    return page_open("weekly", title, desc, base, lang, rel_path) + body + page_close("weekly", base, lang)


def build_monthly(lang, base, rel_path):
    games = sorted_all(GAMES["games"])
    def month_of(g):
        d = parse_deadline(g)
        return d.date().isoformat()[:7] if d else None
    nov = [g for g in games if month_of(g) == "2026-11"]
    dec = [g for g in games if month_of(g) == "2026-12"]
    jan = [g for g in games if month_of(g) == "2027-01"]
    tbc = [g for g in games if month_of(g) is None]
    title = (f'{SITE["title_en"]} · Monthly' if lang == "en" else f'{SITE["title"]} · 月报')
    desc = SITE["description_en"] if lang == "en" else SITE["description"]
    lede = (f'November 2026<span class="lede-rest"> · {len(nov)} games expire in November, {len(dec)} in December, {len(jan)} in January 2027, {len(tbc)} deadlines not published yet.</span>'
            if lang == "en" else
            f'2026年11月<span class="lede-rest"> · 11 月截止 {len(nov)} 款，12 月截止 {len(dec)} 款，2027 年 1 月截止 {len(jan)} 款，{len(tbc)} 款截止时间尚未公布。</span>')
    body = (f'<div class="m-title">{esc(L(lang, "月报", "Monthly"))}</div>'
            f'<h1>{esc(L(lang, "月报", "Monthly"))}</h1>'
            f'<p class="lede">{lede}</p>'
            f'<h2 class="sec">{esc(L(lang, "11 月截止", "Expiring in November"))}</h2>'
            + "".join(feed_item(g, lang, base=base) for g in nov)
            + f'<h2 class="sec">{esc(L(lang, "12 月截止", "Expiring in December"))}</h2>'
            + "".join(feed_item(g, lang, base=base) for g in dec)
            + f'<h2 class="sec">{esc(L(lang, "2027 年 1 月截止", "Expiring in January 2027"))}</h2>'
            + "".join(feed_item(g, lang, base=base) for g in jan)
            + f'<h2 class="sec">{esc(L(lang, "截止时间待公布", "Deadline not published yet"))}</h2>'
            + "".join(feed_item(g, lang, base=base) for g in tbc)
            + f'<script type="application/json" id="gamesData">{games_data_json(games, lang)}</script>')
    return page_open("monthly", title, desc, base, lang, rel_path) + body + page_close("monthly", base, lang)


def build_topics(lang, base, rel_path):
    games = GAMES["games"]
    title = (f'{SITE["title_en"]} · Topics' if lang == "en" else f'{SITE["title"]} · 主题')
    desc = SITE["description_en"] if lang == "en" else SITE["description"]
    secs = []
    for k in CAT_ORDER:
        cat = CATS[k]
        label = cat.get("label_en") or cat["label"] if lang == "en" else cat["label"]
        gs = [g for g in games if g["category"] == k]
        if gs:
            secs.append(f'<h2 class="sec" id="{esc(k)}">{esc(label)} · {len(gs)}</h2>'
                        + "".join(feed_item(g, lang, base=base) for g in sorted_all(gs)))
        else:
            secs.append(f'<h2 class="sec" id="{esc(k)}">{esc(label)} · 0</h2>'
                        f'<p>{esc(L(lang, "本周暂无。", "Nothing this week."))}</p>')
    body = (f'<div class="m-title">{esc(L(lang, "主题", "Topics"))}</div>'
            f'<h1>{esc(L(lang, "主题", "Topics"))}</h1>'
            f'<p class="lede">{esc(L(lang, "按来源浏览：Epic、Prime、Steam / GOG、Steam 大折扣。", "Browse by source: Epic, Prime, Steam / GOG, Steam big deals."))}</p>'
            + "".join(secs)
            + f'<h2 class="sec" id="steam_deals">{esc(DEALS_CAT.get("label_en") or DEALS_CAT["label"] if lang == "en" else DEALS_CAT["label"])} · {len(DEALS["deals"])}</h2>'
            f'<p>{esc(L(lang, f"本周 Steam 大折扣 {len(DEALS["deals"])} 款，最高 90% off：SEGA 黑五特卖至 11 月 30 日，Steam 周度特卖黑五版 11 月 23–30 日。价格以 Steam 商店为准（美元），每款的截止日逐一核实过。",
                         f"{len(DEALS["deals"])} Steam big deals this week, up to 90% off: SEGA Black Friday sale ends Nov 30, Steam Weeklong Sale Black Friday edition Nov 23–30. Prices are from the Steam store (USD); every deal's end date was checked."))} '
            f'<a href="{base}topics/steam-deals.html">{esc(L(lang, f"查看全部 {len(DEALS["deals"])} 款折扣 →", f"See all {len(DEALS["deals"])} deals →"))}</a></p>'
            + f'<script type="application/json" id="gamesData">{games_data_json(games, lang)}</script>')
    return page_open("more", title, desc, base, lang, rel_path) + body + page_close("more", base, lang)


def build_deals_topic(lang, base, rel_path):
    deals = DEALS["deals"]
    title = (f'{SITE["title_en"]} · Steam Big Deals' if lang == "en" else f'{SITE["title"]} · Steam 大折扣')
    desc = (f'Steam big deals this week: {len(deals)} deals, up to 90% off. Prices from the Steam store (USD); every end date checked.'
            if lang == "en" else
            f'本周 Steam 大折扣：{len(deals)} 款，最高 90% off。价格以 Steam 商店为准（美元），每款截止日逐一核实过。')
    lede = (f'Updated {esc(UPDATED)} (Beijing time)<span class="lede-rest"> · {len(deals)} deals, up to 90% off.</span>'
            if lang == "en" else
            f'更新于 {esc(UPDATED)}（北京时间）<span class="lede-rest"> · 共 {len(deals)} 款，最高 90% off。</span>')
    ev_lines = "".join(
        f'<p>{esc(ev.get("name_en") or ev["name"] if lang == "en" else ev["name"])} — '
        f'{esc(ev.get("note_en") or ev["note"] if lang == "en" else ev["note"])}</p>'
        for ev in DEALS["events"])
    note = (f'<p>{esc(L(lang, "价格以 Steam 商店为准（美元）；每款折扣与截止日都在 Steam 商店与 SteamDB 上逐一核对过。注意：Steam 秋季特卖已于 10 月 8 日结束，11 月没有秋季特卖，本页不写任何秋季特卖日期。",
                         "Prices are from the Steam store (USD); every discount and end date was checked against the Steam store and SteamDB. Note: the Steam Autumn Sale ended Oct 8 — there is no Autumn Sale in November, and no Autumn Sale dates appear on this page."))}</p>')
    group_defs = [
        ("sega-black-friday", None),
        ("auto-battler-fest", None),
        ("other", L(lang, "本周其他大折扣", "More big discounts this week")),
    ]
    secs = []
    for ev_id, other_label in group_defs:
        gs = [d for d in deals if d["event"] == ev_id]
        if not gs:
            continue
        ev = EVENTS.get(ev_id)
        label = other_label or (ev.get("name_en") or ev["name"] if lang == "en" else ev["name"])
        secs.append(f'<h2 class="sec" id="{esc(ev_id)}">{esc(label)} · {len(gs)}</h2>'
                    + "".join(deal_item(d, lang, base=base) for d in gs))
    body = (f'<div class="m-title">{esc(L(lang, "Steam 大折扣", "Steam Big Deals"))}</div>'
            f'<h1>{esc(L(lang, "Steam 大折扣", "Steam Big Deals"))}</h1>'
            f'<p class="lede">{lede}</p>'
            f'{ev_lines}{note}'
            + "".join(secs)
            + f'<script type="application/json" id="gamesData">{deals_data_json(lang)}</script>')
    return page_open("more", title, desc, base, lang, rel_path) + body + page_close("more", base, lang)


def build_deal_item(d, lang, base, rel_path):
    title = f'{d["title"]} · {SITE["title_en"] if lang == "en" else SITE["title"]}'
    desc = d["en_summary"] if lang == "en" else d["zh_summary"]
    body = (f'<div class="m-title">{esc(d["title"])}</div>'
            + deal_item(d, lang, base=base)
            + f'<p><a class="chip" href="{esc(d["link"])}" target="_blank" rel="noopener">{esc(L(lang, "去 Steam 购买", "Buy on Steam"))} · Steam →</a> '
            f'<a class="chip" href="{base}topics/steam-deals.html">{esc(L(lang, "全部 Steam 大折扣", "All Steam big deals"))}</a> '
            f'<a class="chip" href="{base}index.html">{esc(L(lang, "回首页", "Back to home"))}</a></p>'
            f'<p>{esc(L(lang, "价格与截止时间以 Steam 商店页面为准。", "Prices and deadlines are as shown on the Steam store page."))}</p>'
            f'<script type="application/json" id="gamesData">{deals_data_json(lang)}</script>')
    return page_open("", title, desc, base, lang, rel_path) + body + page_close("", base, lang)


def build_starred(lang, base, rel_path):
    title = (f'{SITE["title_en"]} · Saved' if lang == "en" else f'{SITE["title"]} · 收藏')
    desc = SITE["description_en"] if lang == "en" else SITE["description"]
    body = (f'<div class="m-title">{esc(L(lang, "收藏", "Saved"))}</div>'
            f'<h1>{esc(L(lang, "收藏", "Saved"))}</h1>'
            f'<p class="lede">{esc(L(lang, "点卡片右上角的星标，就会留在这里。只存在你自己的浏览器里，不会上传。", "Tap the star on a card and it stays here. Saved only in your own browser, never uploaded."))}</p>'
            f'<div id="starredList"></div>'
            f'<div class="empty-state" id="starredEmpty"><div class="empty-icon">{icon("bookmark", 40)}</div>'
            f'<h3 class="empty-title">{esc(L(lang, "还没有收藏。", "Nothing saved yet."))}</h3>'
            f'<p class="empty-text">{esc(L(lang, "去精选里点一颗星试试。", "Go to Featured and tap a star."))}</p>'
            f'<div class="empty-actions"><a class="empty-btn primary" href="{base}index.html">{esc(L(lang, "去看精选", "See featured"))}</a></div></div>'
            f'<script type="application/json" id="gamesData">{all_data_json(GAMES["games"], lang)}</script>')
    return page_open("starred", title, desc, base, lang, rel_path) + body + page_close("starred", base, lang)


def build_more(lang, base, rel_path):
    title = (f'{SITE["title_en"]} · My' if lang == "en" else f'{SITE["title"]} · 我的')
    desc = SITE["description_en"] if lang == "en" else SITE["description"]
    body = (f'<div class="m-title">{esc(L(lang, "我的", "My"))}</div>'
            f'<h1>{esc(L(lang, "我的", "My"))}</h1>'
            f'<p class="lede">{esc(L(lang, "收藏、外观、数据与关于，都在这里。", "Saved items, appearance, data and about — all in one place."))}</p>'
            f'<h2 class="sec">{esc(L(lang, "收藏", "Saved"))}</h2>'
            f'<p><a href="{base}starred.html">{esc(L(lang, "我的收藏", "My saved items"))}</a> · <span class="num" id="starCountInline"></span></p>'
            f'<h2 class="sec">{esc(L(lang, "外观", "Appearance"))}</h2>'
            f'<p><button type="button" class="chip" data-theme-set="system">{esc(L(lang, "跟随系统", "System"))}</button> '
            f'<button type="button" class="chip" data-theme-set="light">{esc(L(lang, "浅色", "Light"))}</button> '
            f'<button type="button" class="chip" data-theme-set="dark">{esc(L(lang, "深色", "Dark"))}</button></p>'
            f'<h2 class="sec">{esc(L(lang, "数据", "Data"))}</h2>'
            f'<p><a href="{base}data/games.json">{esc(L(lang, "数据 JSON", "Data JSON"))}</a> · '
            f'<a href="{base}feed.xml">{esc(L(lang, "RSS 订阅", "RSS Feed"))}</a> · '
            f'<a href="{base}sitemap.xml">Sitemap</a></p>'
            f'<h2 class="sec">{esc(L(lang, "关于本站", "About this site"))}</h2>'
            f'<p><a href="{base}about.html">{esc(L(lang, "关于", "About"))}</a> · '
            f'<a href="{base}terms.html">{esc(L(lang, "条款", "Terms"))}</a> · '
            f'<a href="{base}privacy.html">{esc(L(lang, "隐私", "Privacy"))}</a> · '
            f'<a href="{base}changelog.html">{esc(L(lang, "更新日志", "Changelog"))}</a></p>')
    return page_open("more", title, desc, base, lang, rel_path) + body + page_close("more", base, lang)


def build_about(lang, base, rel_path):
    title = (f'{SITE["title_en"]} · About' if lang == "en" else f'{SITE["title"]} · 关于')
    desc = SITE["description_en"] if lang == "en" else SITE["description"]
    blocks = SITE.get("about_blocks_en") if lang == "en" else SITE.get("about_blocks")
    secs = "".join(
        f'<h2 class="sec">{esc(b["h"])}</h2>' + "".join(f"<p>{esc(p)}</p>" for p in b["paras"])
        for b in (blocks or []))
    if lang == "en":
        extra = ('<h2 class="sec">Data</h2>'
                 '<p>Content comes from public store claim pages. Game names and store links belong to their stores; '
                 'titles and one-line summaries shown here are written in our own words, and store descriptions are never republished.</p>'
                 '<h2 class="sec">Contact</h2>'
                 f'<p>Questions or a freebie we missed? Leave a note on <a href="{esc(SITE["repo"])}/issues">GitHub Issues</a>.</p>'
                 '<p>Built with the HOT pipeline template; the information architecture and interface style follow the template '
                 '(warm paper background, sidebar navigation). Code is open source under the MIT License.</p>')
    else:
        extra = ('<h2 class="sec">数据说明</h2>'
                 '<p>内容来自各家公开商店领取页，游戏名与商店链接归原商店所有；本站展示的标题与一句简介是我们自己写的，不转载商店的介绍全文。</p>'
                 '<h2 class="sec">联系</h2>'
                 f'<p>有问题或发现漏掉的限免，去 <a href="{esc(SITE["repo"])}/issues">GitHub Issues</a> 留言。</p>'
                 '<p>本站由 HOT 流水线模板生成，信息架构与界面风格沿用模板（暖纸底色与侧栏导航），代码按 MIT 协议开源。</p>')
    body = (f'<div class="m-title">{esc(L(lang, "关于", "About"))}</div>'
            f'<h1>{esc(L(lang, "关于", "About"))}</h1>'
            f'<p class="lede">{esc(L(lang, SITE["name"] + " 是什么、怎么做、谁做的。", SITE["title_en"] + " — what it is, how it works, who made it."))}</p>'
            f'{secs}{extra}')
    return page_open("about", title, desc, base, lang, rel_path) + body + page_close("about", base, lang)


def build_simple(lang, base, rel_path, active, mtitle, paras):
    title = f'{SITE["title_en"] if lang == "en" else SITE["title"]} · {mtitle}'
    desc = SITE["description_en"] if lang == "en" else SITE["description"]
    body = (f'<div class="m-title">{esc(mtitle)}</div>'
            f'<h1>{esc(mtitle)}</h1>'
            + "".join(f"<p>{esc(p)}</p>" for p in paras))
    return page_open(active, title, desc, base, lang, rel_path) + body + page_close(active, base, lang)


def build_changelog(lang, base, rel_path):
    if lang == "en":
        entries = [("2026-11-25", "Prime: Arcadia Fallen is now claimable until Dec 28, 2026 — it appeared on the Luna claims page today, marked 'New', after being expected since Nov 24. Ad Infinitum and Time Travel: Escape Room Game are still claimable today (Nov 25, last day) and leave the featured picks; Kiborg and Trash Goblin (both to Dec 2) take their place. Epic: Mark of the Deep is still claimable until Nov 26, 16:00 UTC; Alien: Isolation is still not free. Steam big deals: 2 expired deals were removed (428: Shibuya Scramble, AI: THE SOMNIUM FILES - nirvanA Initiative — both back to full price on the Steam store and SteamDB), and 4 new deals were added from the Steam Weeklong Sale Black Friday edition — Celeste, Neon White, South Park: The Stick of Truth and Dishonored, up to 75% off; ULTRAKILL (-25%) and Split Fiction (-40%) were checked and excluded, below the 50% threshold. The other 31 deals were re-checked on the Steam store — prices and discounts unchanged."),
                   ("2026-11-24", "Steam big deals: 4 expired deals were removed (Despot's Game, The Witness, Braid, Goat Simulator 3 — all back to full price on the Steam store and SteamDB), and 10 new deals were added from the Steam Weeklong Sale Black Friday edition, up to 90% off — Detroit: Become Human, Fallout 4, Mortal Kombat 1, Injustice 2, Skyrim Special Edition, Sea of Thieves: 2026 Edition, Borderlands 3, Painkiller, 007 First Light and Deep Rock Galactic: Survivor; prices and end dates checked on the Steam store and SteamDB. Epic: Mark of the Deep is still claimable until Nov 26, 16:00 UTC; Alien: Isolation is still $39.99, not free. Prime: all 12 deadlines re-checked on Luna with no changes; Arcadia Fallen still has not appeared on the claims page, although it was expected today, and stays listed with its date not yet published."),
                   ("2026-11-20", "Prime: Werewolf: The Apocalypse - Earthblood and CLeM are now claimable until Dec 23 — both appeared on the Luna claims page today, marked 'New'; Arcadia Fallen still has not appeared and stays listed with its date not yet published. Epic: Mark of the Deep is still claimable until Nov 26, 16:00 UTC; Alien: Isolation is still $39.99, not free. All 27 Steam big deals were re-checked on the Steam store — prices and discounts unchanged, none expired."),
                   ("2026-11-19", "Epic rotation: Knightica expired and was removed; Mark of the Deep is now claimable until Nov 26, 16:00 UTC; next up are Bread & Fred and Firestone – Idle Clicker Online RPG (Nov 26 – Dec 3). Alien: Isolation did not go free as announced — the Epic free page and store search both show $39.99, so it was removed instead of being listed as free. Prime: Swansong expired and was removed; the other 10 deadlines were checked one by one on Luna with no changes; Werewolf: Earthblood, Clem and Arcadia Fallen still have not appeared on the claims page and stay listed with their dates not yet published. All 27 Steam big deals were re-checked on the Steam store — prices and discounts unchanged, none expired."),
                   ("2026-11-18", "Added 13 Steam big deals: Far Cry 5, FOR HONOR, Call of Duty: Black Ops Cold War / 6, Nioh 3, Marathon, HITMAN World of Assassination, Nioh 2 – The Complete Edition, Lies of P, Persona 5 Royal, Total War: WARHAMMER II, Goat Simulator 3 and Black Mesa — prices and end dates checked on the Steam store and SteamDB, up to 85% off."),
                   ("2026-11-17", "Added 4 Prime games missed from the October batch: Trash Goblin, Time Travel: Escape Room Game, Caravan SandWitch and WarBreeds — each deadline checked on the Luna claims pages."),
                   ("2026-11-17", "Added Steam big deals: 14 verified deals, up to 85% off — SEGA Black Friday sale ends Nov 30, Auto-Battler RPG Fest Nov 16–23."),
                   ("2026-11-17", "Restyled to the hot-site-template layout: sidebar, topbar, tabbar, feed-item cards, hot list."),
                   ("2026-11-17", "Launched with 13 games: Epic weekly free games, Prime monthly claims, Steam / GOG freebies.")]
    else:
        entries = [("2026-11-25", "Prime：Arcadia Fallen 今天已上架可领，截止 12 月 28 日，Luna 页上标了 New（自 11 月 24 日预期至今终于出现）。Ad Infinitum 与 Time Travel: Escape Room Game 今天仍可领（11 月 25 日最后一天），退出精选，由 Kiborg 与 Trash Goblin（均至 12 月 2 日）接替。Epic：Mark of the Deep 仍可领至 11 月 26 日 16:00 UTC；Alien: Isolation 仍未免费。Steam 大折扣：2 款过期下架（428：涩谷、AI：梦境档案 涅槃肇始，Steam 商店与 SteamDB 上均已恢复原价），新增 4 款周度特卖黑五版折扣——Celeste、Neon White、南方公园：真理之杖、Dishonored，最高 75% off；ULTRAKILL（-25%）与 Split Fiction（-40%）已核实，未达 50% 门槛，未列入。其余 31 款已在 Steam 商店逐一复核，价格与折扣无变化。"),
                   ("2026-11-24", "Steam 大折扣：4 款过期下架（Despot's Game、The Witness、Braid、模拟山羊 3，Steam 商店与 SteamDB 上均已恢复原价），新增 10 款周度特卖黑五版折扣，最高 90% off——底特律：化身为人、辐射 4、真人快打 1、不义联盟 2、上古卷轴 5：天际特别版、盗贼之海：2026 版、无主之地 3、止痛药、007 初露锋芒、深岩银河：幸存者，价格与截止日已在 Steam 商店与 SteamDB 上逐一核实。Epic：Mark of the Deep 仍可领至 11 月 26 日 16:00 UTC；Alien: Isolation 仍是 $39.99，未免费。Prime：12 款截止日已在 Luna 上逐一复核，无变化；Arcadia Fallen 虽然预计今天上架但仍未出现，继续标截止日待公布。"),
                   ("2026-11-20", "Prime：Werewolf: The Apocalypse - Earthblood 与 CLeM 今天已上架可领，截止 12 月 23 日，Luna 页上标了 New；Arcadia Fallen 仍未出现，继续标截止日待公布。Epic：Mark of the Deep 仍可领至 11 月 26 日 16:00 UTC；Alien: Isolation 仍是 $39.99，未免费。Steam 大折扣 27 款已在 Steam 商店逐一复核，价格与折扣无变化，无过期。"),
                   ("2026-11-19", "Epic 轮换：Knightica 到期下架；Mark of the Deep 开始可领，至 11 月 26 日 16:00 UTC；下周是 Bread & Fred 与 Firestone – Idle Clicker Online RPG（11 月 26 日至 12 月 3 日）。Alien: Isolation 未如期免费——Epic 领取页与商店搜索均显示 $39.99，已从本站下架，不按预期登记为免费。Prime：Swansong 到期下架；其余 10 款截止日已在 Luna 上逐一核对，无变化；Werewolf: Earthblood、Clem、Arcadia Fallen 仍未出现在领取页，继续标截止日待公布。Steam 大折扣 27 款已在 Steam 商店逐一复核，价格与折扣无变化，无过期。"),
                   ("2026-11-18", "新增 Steam 大折扣 13 款：Far Cry 5、FOR HONOR、使命召唤：黑色行动冷战 / 6、仁王 3、马拉松、HITMAN 暗杀世界、仁王 2 完全版、匹诺曹的谎言、女神异闻录 5 皇家版、全面战争：战锤 2、模拟山羊 3、黑山，价格与截止日已在 Steam 商店与 SteamDB 上逐一核实，最高 85% off。"),
                   ("2026-11-17", "补上 10 月批次遗漏的 4 款 Prime 游戏：Trash Goblin、Time Travel: Escape Room Game、Caravan SandWitch、WarBreeds，截止日已在 Luna 领取页逐一核实。"),
                   ("2026-11-17", "新增 Steam 大折扣：14 款逐一核实过的折扣，最高 85% off，SEGA 黑五特卖至 11 月 30 日，自动战斗 RPG 节 11 月 16–23 日。"),
                   ("2026-11-17", "排版改回模板样式：侧栏、顶栏、底栏、卡片、热点榜。"),
                   ("2026-11-17", "上线：13 款游戏，Epic 每周免费、Prime 每月领取、Steam / GOG 限免。")]
    title = (f'{SITE["title_en"]} · Changelog' if lang == "en" else f'{SITE["title"]} · 更新日志')
    desc = SITE["description_en"] if lang == "en" else SITE["description"]
    rows = "".join(f'<h2 class="sec">{d}</h2><p>{esc(t)}</p>' for d, t in entries)
    body = (f'<div class="m-title">{esc(L(lang, "更新日志", "Changelog"))}</div>'
            f'<h1>{esc(L(lang, "更新日志", "Changelog"))}</h1>'
            f'<p class="lede">{esc(L(lang, SITE["name"] + " 每次改版都记在这里。", "Every " + SITE["title_en"] + " change is recorded here."))}</p>'
            f'{rows}')
    return page_open("changelog", title, desc, base, lang, rel_path) + body + page_close("changelog", base, lang)


def build_404(lang, base, rel_path):
    title = (f'{SITE["title_en"]} · Not found' if lang == "en" else f'{SITE["title"]} · 页面不存在')
    desc = SITE["description_en"] if lang == "en" else SITE["description"]
    body = (f'<div class="m-title">404</div><h1>404</h1>'
            f'<p>{esc(L(lang, "这个页面不存在，可能已经过期下架。", "This page does not exist — it may have expired and been removed."))}</p>'
            f'<p><a href="{base}index.html">{esc(L(lang, "回首页", "Back to home"))} →</a></p>')
    return page_open("", title, desc, base, lang, rel_path) + body + page_close("", base, lang)


def build_item(g, lang, base, rel_path):
    title = f'{g["title"]} · {SITE["title_en"] if lang == "en" else SITE["title"]}'
    desc = g["en_summary"] if lang == "en" else g["zh_summary"]
    claim_word = L(lang, "去领取", "Claim") if g["status"] == "claimable" else L(lang, "去查看", "View")
    body = (f'<div class="m-title">{esc(g["title"])}</div>'
            + feed_item(g, lang, base=base)
            + f'<p><a class="chip" href="{esc(g["link"])}" target="_blank" rel="noopener">{esc(claim_word)} · {esc(g["source"])} →</a> '
            f'<a class="chip" href="{base}index.html">{esc(L(lang, "回首页", "Back to home"))}</a></p>'
            f'<p>{esc(L(lang, "领取条件与截止时间以商店页面为准。", "Claim conditions and deadlines are as shown on the store page."))}</p>'
            f'<script type="application/json" id="gamesData">{games_data_json([g], lang)}</script>')
    return page_open("", title, desc, base, lang, rel_path) + body + page_close("", base, lang)


PAGES = [
    ("index.html", build_index), ("all.html", build_all), ("hot.html", build_hot),
    ("daily.html", build_daily), ("weekly.html", build_weekly), ("monthly.html", build_monthly),
    ("topics.html", build_topics), ("starred.html", build_starred), ("more.html", build_more),
    ("about.html", build_about), ("changelog.html", build_changelog), ("404.html", build_404),
]


def build_simple_pages(lang, base):
    out = {}
    if lang == "en":
        out["terms.html"] = build_simple(lang, base, "terms.html", "", "Terms",
            ["Content on this site is for reference only. Claim conditions and deadlines are as shown on the store pages.",
             "Game names and store links belong to their stores."])
        out["privacy.html"] = build_simple(lang, base, "privacy.html", "", "Privacy",
            ["This site does not collect accounts or passwords, and does not ask you to sign in.",
             "If Cloudflare Web Analytics is enabled, it only does anonymous visit statistics."])
    else:
        out["terms.html"] = build_simple(lang, base, "terms.html", "", "条款",
            ["本站内容仅供参考，领取条件与截止时间以商店页面为准。",
             "游戏名与商店链接归原商店所有。"])
        out["privacy.html"] = build_simple(lang, base, "privacy.html", "", "隐私",
            ["本站不收集账号与密码，不要求登录。",
             "如开启 Cloudflare Web Analytics，只做匿名访问统计。"])
    return out


def build_feed(lang):
    games = sorted_all(GAMES["games"])
    deals = sorted(DEALS["deals"], key=lambda d: d["ends"])
    site_url = SITE["url"].rstrip("/")
    if lang == "en":
        items = "".join(
            f'<item><title>{esc(g["title"])} — claim by {esc(g.get("claim_by_label", "TBC"))}</title>'
            f'<link>{esc(g["link"])}</link><description>{esc(g["en_summary"])}</description></item>'
            for g in games)
        items += "".join(
            f'<item><title>{esc(d["title"])} — -{d["discount"]}% ${d["price"]:.2f} (was ${d["original"]:.2f}), ends {esc(d["ends_label"])}</title>'
            f'<link>{esc(d["link"])}</link><description>{esc(d["en_summary"])}</description></item>'
            for d in deals)
        return ('<?xml version="1.0" encoding="UTF-8"?>\n'
                f'<rss version="2.0"><channel><title>{esc(SITE["title_en"])}</title>'
                f'<link>{site_url}/en/</link><description>Weekly free-games claim calendar</description>'
                f'<language>en</language>{items}</channel></rss>')
    items = "".join(
        f'<item><title>{esc(g["title"])} — {esc("截止 " + g.get("claim_by_label", "待公布"))}</title>'
        f'<link>{esc(g["link"])}</link><description>{esc(g["zh_summary"])}</description></item>'
        for g in games)
    items += "".join(
        f'<item><title>{esc(d["title"])} — -{d["discount"]}% ${d["price"]:.2f}（原价 ${d["original"]:.2f}），截止 {esc(d["ends_label"])}</title>'
        f'<link>{esc(d["link"])}</link><description>{esc(d["zh_summary"])}</description></item>'
        for d in deals)
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            f'<rss version="2.0"><channel><title>{esc(SITE["name"])}</title>'
            f'<link>{site_url}/</link><description>每周免费游戏领取日历</description>'
            f'<language>zh-CN</language>{items}</channel></rss>')


def build_sitemap():
    site_url = SITE["url"].rstrip("/")
    urls = []
    for lang in ("zh", "en"):
        prefix = "" if lang == "zh" else "en/"
        for rel, _ in PAGES:
            urls.append(f"{site_url}/{prefix}{rel}")
        urls.append(f"{site_url}/{prefix}terms.html")
        urls.append(f"{site_url}/{prefix}privacy.html")
        urls.append(f"{site_url}/{prefix}topics/steam-deals.html")
        urls.append(f"{site_url}/{prefix}geo-audit.html")
        for g in GAMES["games"]:
            urls.append(f"{site_url}/{prefix}items/{g['id']}.html")
        for d in DEALS["deals"]:
            urls.append(f"{site_url}/{prefix}items/{d['id']}.html")
    body = "".join(f"<url><loc>{esc(u)}</loc><lastmod>{NOW.date().isoformat()}</lastmod></url>" for u in urls)
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
            f"{body}</urlset>")


def main():
    # Template CSS verbatim, favicon from the template logo.
    import shutil
    css_src = pathlib.Path("/tmp/fgh-ref/site.css")
    (ROOT / "assets" / "site.css").write_text(css_src.read_text(encoding="utf-8"), encoding="utf-8")
    (ROOT / "favicon.svg").write_text(LOGO_SVG, encoding="utf-8")
    (ROOT / ".nojekyll").write_text("", encoding="utf-8")
    # Fill the template's web_analytics_token slot from the verified token.
    if not SITE.get("web_analytics_token"):
        CFG["site"]["web_analytics_token"] = CFG.get("web_analytics_token", "")
        (ROOT / "config.json").write_text(json.dumps(CFG, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for lang, base, prefix in (("zh", "", ""), ("en", "../", "en/")):
        outdir = ROOT / prefix
        outdir.mkdir(parents=True, exist_ok=True)
        for rel, fn in PAGES:
            (outdir / rel).write_text(fn(lang, base, rel), encoding="utf-8")
        for rel, html_text in build_simple_pages(lang, base).items():
            (outdir / rel).write_text(html_text, encoding="utf-8")
        items_dir = outdir / "items"
        items_dir.mkdir(parents=True, exist_ok=True)
        for g in GAMES["games"]:
            (items_dir / f'{g["id"]}.html').write_text(
                build_item(g, lang, "../" if lang == "zh" else "../../", f'items/{g["id"]}.html'),
                encoding="utf-8")
        (outdir / "feed.xml").write_text(build_feed(lang), encoding="utf-8")
    (ROOT / "sitemap.xml").write_text(build_sitemap(), encoding="utf-8")
    print("built pages OK")


if __name__ == "__main__":
    main()
