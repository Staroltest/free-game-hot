#!/usr/bin/env python3
"""Regenerate only the pages touched by the Steam big-deals addition.

Do NOT run restyle.main(): it copies template CSS from /tmp/fgh-ref/site.css,
which no longer exists. This driver imports restyle and calls the builders for
the pages that change: index, topics, topics/steam-deals, changelog, starred
(gamesData only), feed, sitemap, and the 14 deal detail pages (ZH + EN).
Everything else (the 13 free games, featured picks, all/hot/daily/weekly/
monthly/more/about/terms/privacy/404) is left untouched.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import restyle as R

ROOT = pathlib.Path(__file__).resolve().parent.parent


def write(rel, text):
    p = ROOT / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def main():
    for lang, base, prefix in (("zh", "", ""), ("en", "../", "en/")):
        write(prefix + "index.html", R.build_index(lang, base, "index.html"))
        write(prefix + "topics.html", R.build_topics(lang, base, "topics.html"))
        write(prefix + "changelog.html", R.build_changelog(lang, base, "changelog.html"))
        write(prefix + "starred.html", R.build_starred(lang, base, "starred.html"))
        write(prefix + "feed.xml", R.build_feed(lang))
        topic_base = "../" if lang == "zh" else "../../"
        write(prefix + "topics/steam-deals.html",
              R.build_deals_topic(lang, topic_base, "topics/steam-deals.html"))
        for d in R.DEALS["deals"]:
            write(prefix + f"items/{d['id']}.html",
                  R.build_deal_item(d, lang, topic_base, f"items/{d['id']}.html"))
    write("sitemap.xml", R.build_sitemap())
    print(f"built: index/topics/changelog/starred/feed x2, "
          f"topics/steam-deals x2, {len(R.DEALS['deals'])} deal items x2, sitemap")


if __name__ == "__main__":
    main()
