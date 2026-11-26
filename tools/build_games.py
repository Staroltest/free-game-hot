#!/usr/bin/env python3
"""Regenerate only the pages touched by the games-data update.

Do NOT run restyle.main(): it copies template CSS from /tmp/fgh-ref/site.css,
which no longer exists. This driver imports restyle and calls the builders for
the pages that change: index, all, hot, daily, weekly, monthly, topics,
starred (gamesData), changelog, feed, sitemap, and the new game detail pages
(ZH + EN). Everything else (topics/steam-deals, deal detail pages, more/about/
terms/privacy/404, assets/site.css) is left untouched.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import restyle as R

ROOT = pathlib.Path(__file__).resolve().parent.parent
NEW_IDS = ["strange-antiquities-epic", "bread-and-fred-epic",
           "firestone-epic"]


def write(rel, text):
    p = ROOT / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def main():
    by_id = {g["id"]: g for g in R.GAMES["games"]}
    new_games = [by_id[i] for i in NEW_IDS]
    for lang, base, prefix in (("zh", "", ""), ("en", "../", "en/")):
        write(prefix + "index.html", R.build_index(lang, base, "index.html"))
        write(prefix + "all.html", R.build_all(lang, base, "all.html"))
        write(prefix + "hot.html", R.build_hot(lang, base, "hot.html"))
        write(prefix + "daily.html", R.build_daily(lang, base, "daily.html"))
        write(prefix + "weekly.html", R.build_weekly(lang, base, "weekly.html"))
        write(prefix + "monthly.html", R.build_monthly(lang, base, "monthly.html"))
        write(prefix + "topics.html", R.build_topics(lang, base, "topics.html"))
        write(prefix + "starred.html", R.build_starred(lang, base, "starred.html"))
        write(prefix + "changelog.html", R.build_changelog(lang, base, "changelog.html"))
        write(prefix + "feed.xml", R.build_feed(lang))
        item_base = "../" if lang == "zh" else "../../"
        for g in new_games:
            write(prefix + f"items/{g['id']}.html",
                  R.build_item(g, lang, item_base, f"items/{g['id']}.html"))
    write("sitemap.xml", R.build_sitemap())
    print(f"built: index/all/hot/daily/weekly/monthly/topics/starred/changelog/feed x2, "
          f"{len(new_games)} game items x2, sitemap")


if __name__ == "__main__":
    main()
