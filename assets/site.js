/* Free Game HOT — small front-end: theme, countdown, filters, search, stars.
   Class names and localStorage keys follow the hot-site-template shell. */
(function () {
  'use strict';
  var THEME_KEY = 'free-game-hot-theme';
  var STAR_KEY = 'free-game-hot-starred';
  var RECENT_KEY = 'free-game-hot-recent';
  var $ = function (s, r) { return (r || document).querySelector(s); };
  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };

  /* ---- theme ---- */
  function applyTheme(t) {
    if (t === 'dark' || t === 'light') { document.documentElement.setAttribute('data-theme', t); return; }
    var dark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
    document.documentElement.setAttribute('data-theme', dark ? 'dark' : 'light');
  }
  function cycleTheme() {
    var cur = null;
    try { cur = localStorage.getItem(THEME_KEY); } catch (e) {}
    var next = cur === 'dark' ? 'light' : (cur === 'light' ? null : 'dark');
    try {
      if (next) { localStorage.setItem(THEME_KEY, next); } else { localStorage.removeItem(THEME_KEY); }
    } catch (e) {}
    applyTheme(next);
  }
  $$('.theme-btn').forEach(function (b) { b.addEventListener('click', cycleTheme); });
  $$('[data-theme-set]').forEach(function (b) {
    b.addEventListener('click', function () {
      var v = b.getAttribute('data-theme-set');
      try {
        if (v === 'system') { localStorage.removeItem(THEME_KEY); applyTheme(null); }
        else { localStorage.setItem(THEME_KEY, v); applyTheme(v); }
      } catch (e) {}
    });
  });

  /* ---- countdown on [data-deadline] ---- */
  function tick() {
    var now = new Date();
    $$('[data-deadline]').forEach(function (el) {
      if (el.dataset.done) { return; }
      var end = new Date(el.getAttribute('data-deadline'));
      var diff = end - now;
      if (diff <= 0) { el.textContent += ' · ' + (document.documentElement.lang === 'en' ? 'expired' : '已过期'); el.dataset.done = '1'; return; }
      var d = Math.floor(diff / 86400000), h = Math.floor(diff % 86400000 / 3600000);
      var base = el.getAttribute('data-base');
      if (!base) { base = el.textContent; el.setAttribute('data-base', base); }
      el.textContent = base + ' · ' + (document.documentElement.lang === 'en'
        ? ('about ' + d + 'd ' + h + 'h left') : ('还剩约 ' + d + ' 天 ' + h + ' 小时'));
    });
  }
  tick(); setInterval(tick, 60000);

  /* ---- category filter chips ---- */
  var noResult = $('#noResult');
  function applyFilter(cat, q) {
    var shown = 0;
    $$('.feed-item').forEach(function (it) {
      var okCat = !cat || cat === 'all' || it.getAttribute('data-category') === cat;
      var okQ = true;
      if (q) {
        var text = (it.textContent || '').toLowerCase();
        okQ = text.indexOf(q.toLowerCase()) !== -1;
      }
      it.style.display = (okCat && okQ) ? '' : 'none';
      if (okCat && okQ) { shown++; }
    });
    if (noResult) { noResult.hidden = shown !== 0; }
    var sc2 = $('#searchCount');
    if (sc2) {
      sc2.textContent = (q || (cat && cat !== 'all'))
        ? (document.documentElement.lang === 'en' ? shown + ' result' + (shown === 1 ? '' : 's') : '找到 ' + shown + ' 款')
        : '';
    }
    $$('.tabs .chip').forEach(function (c) {
      c.classList.toggle('on', c.getAttribute('data-filter') === (cat || 'all'));
    });
    return shown;
  }
  /* ---- sort (all page) ---- */
  $$('[data-sort]').forEach(function (b) {
    b.addEventListener('click', function () {
      var list = $('#feedList'); if (!list) { return; }
      $$('[data-sort]').forEach(function (x) { x.classList.toggle('on', x === b); });
      var items = $$('.feed-item', list);
      var mode = b.getAttribute('data-sort');
      items.sort(function (a, c) {
        if (mode === 'source') {
          var k = a.getAttribute('data-category') + '|' + (a.getAttribute('data-deadline') || 'zzz');
          var k2 = c.getAttribute('data-category') + '|' + (c.getAttribute('data-deadline') || 'zzz');
          return k < k2 ? -1 : (k > k2 ? 1 : 0);
        }
        var d1 = a.getAttribute('data-deadline') || 'zzz';
        var d2 = c.getAttribute('data-deadline') || 'zzz';
        return d1 < d2 ? -1 : (d1 > d2 ? 1 : 0);
      });
      items.forEach(function (it) { list.appendChild(it); });
    });
  });
  $$('.chip[data-filter]').forEach(function (c) {
    c.addEventListener('click', function () {
      var f = c.getAttribute('data-filter');
      var q = ($('#siteSearch') || {}).value || '';
      applyFilter(f, q);
      if (f !== 'all') { try { history.replaceState(null, '', '#' + f); } catch (e) {} }
    });
  });
  $$('.empty-btn[data-empty-action="clear"]').forEach(function (b) {
    b.addEventListener('click', function () {
      var s = $('#siteSearch'); if (s) { s.value = ''; }
      applyFilter('all', '');
    });
  });
  $$('.empty-btn[data-empty-action="featured"]').forEach(function (b) {
    b.addEventListener('click', function () { location.href = 'index.html'; });
  });
  if (location.hash) {
    var h = location.hash.slice(1);
    if (['epic', 'prime', 'steam_gog'].indexOf(h) !== -1) { applyFilter(h, ''); }
  }

  /* ---- search ---- */
  var siteSearch = $('#siteSearch');
  if (siteSearch) {
    siteSearch.addEventListener('input', function () {
      var active = ($('.tabs .chip.on') || {}).getAttribute ? $('.tabs .chip.on').getAttribute('data-filter') : 'all';
      applyFilter(active || 'all', siteSearch.value.trim());
    });
    var clear = $('#searchClear');
    if (clear) { clear.addEventListener('click', function () { siteSearch.value = ''; applyFilter('all', ''); siteSearch.focus(); }); }
    siteSearch.addEventListener('keydown', function (e) { if (e.key === '/') { e.stopPropagation(); } });
  }
  document.addEventListener('keydown', function (e) {
    if (e.key === '/' && !/INPUT|TEXTAREA/.test((document.activeElement || {}).tagName || '')) {
      var s = $('#siteSearch') || $('#overlaySearch');
      if (s) { e.preventDefault(); openOverlay(); if (s.id === 'overlaySearch') { s.focus(); } }
    }
    if (e.key === 'Escape') { closeOverlay(); }
  });

  /* ---- search overlay: full search over all games in #gamesData ---- */
  var overlay = $('#searchOverlay');
  function getGames() {
    var el = $('#gamesData'); if (!el) { return []; }
    try { return JSON.parse(el.textContent || '[]'); } catch (e) { return []; }
  }
  function escHtml(s) {
    return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }
  function searchGames(q) {
    q = (q || '').trim().toLowerCase();
    if (!q) { return []; }
    return getGames().filter(function (g) {
      return ((g.title || '') + ' ' + (g.summary || '') + ' ' + (g.source || '') + ' ' + (g.category || ''))
        .toLowerCase().indexOf(q) !== -1;
    });
  }
  function renderOverlayResults(q) {
    var sec = $('#overlayResultsSec'), box = $('#overlayResults');
    if (!sec || !box) { return; }
    var results = searchGames(q);
    var base = (overlay && overlay.getAttribute('data-base')) || '';
    var en = document.documentElement.lang === 'en';
    if (!q || !q.trim()) { sec.hidden = true; box.innerHTML = ''; return; }
    sec.hidden = false;
    if (!results.length) {
      box.innerHTML = '<p class="more-note">' + (en ? 'No results for "' + escHtml(q) + '".' : '没有找到“' + escHtml(q) + '”相关的内容。') + '</p>';
      return;
    }
    box.innerHTML = '<p class="more-note">' + results.length + (en ? ' result' + (results.length === 1 ? '' : 's') : ' 款') + '</p>' +
      results.map(function (g) {
        return '<div class="recent-row"><a href="' + base + 'items/' + g.id + '.html"><b>' + escHtml(g.title) + '</b><br>' +
          escHtml(g.summary) + '<br><span class="more-note">' + escHtml(g.source) + ' · ' + escHtml(g.claim_by) + '</span></a></div>';
      }).join('');
  }
  function openOverlay() {
    if (!overlay) { return; }
    overlay.hidden = false;
    renderRecent();
    var o = $('#overlaySearch'); if (o) { o.focus(); }
  }
  function closeOverlay() { if (overlay) { overlay.hidden = true; } }
  $$('.search-trigger').forEach(function (b) { b.addEventListener('click', openOverlay); });
  var oc = $('#overlayClose'); if (oc) { oc.addEventListener('click', closeOverlay); }
  function getRecent() { try { return JSON.parse(localStorage.getItem(RECENT_KEY) || '[]'); } catch (e) { return []; } }
  function renderRecent() {
    var list = $('#recentList'); if (!list) { return; }
    var items = getRecent();
    list.innerHTML = items.length ? items.map(function (q) {
      return '<div class="recent-row"><button type="button" class="chip" data-recent="' +
        q.replace(/"/g, '&quot;') + '">' + q.replace(/</g, '&lt;') + '</button></div>';
    }).join('') : '<p class="more-note">' + (document.documentElement.lang === 'en' ? 'No searches yet.' : '还没有搜索过。') + '</p>';
    $$('[data-recent]', list).forEach(function (b) {
      b.addEventListener('click', function () {
        var q = b.getAttribute('data-recent');
        var o = $('#overlaySearch'); if (o) { o.value = q; }
        renderOverlayResults(q);
      });
    });
  }
  var overlaySearch = $('#overlaySearch');
  if (overlaySearch) {
    overlaySearch.addEventListener('input', function () {
      var q = overlaySearch.value.trim();
      renderOverlayResults(q);
      if (q) {
        var items = getRecent().filter(function (x) { return x !== q; });
        items.unshift(q);
        try { localStorage.setItem(RECENT_KEY, JSON.stringify(items.slice(0, 5))); } catch (e) {}
      }
    });
    overlaySearch.addEventListener('keydown', function (e) {
      if (e.key === 'Enter') {
        var q = overlaySearch.value.trim();
        var first = searchGames(q)[0];
        if (first) {
          var base = (overlay && overlay.getAttribute('data-base')) || '';
          location.href = base + 'items/' + first.id + '.html';
          return;
        }
        closeOverlay();
        var s = $('#siteSearch'); if (s) { s.value = q; }
        applyFilter('all', q);
      }
    });
    var osc = $('#overlaySearchClear');
    if (osc) { osc.addEventListener('click', function () { overlaySearch.value = ''; renderOverlayResults(''); overlaySearch.focus(); }); }
  }
  var clr = $('#clearRecent');
  if (clr) { clr.addEventListener('click', function () { try { localStorage.removeItem(RECENT_KEY); } catch (e) {} renderRecent(); }); }
  $$('.overlay-cats .chip').forEach(function (c) {
    c.addEventListener('click', function () {
      // Go to All Items filtered by this category (the overlay only
      // filters the current page, so navigating is the honest behaviour).
      var allLink = document.querySelector('a[href$="all.html"]');
      var href = allLink ? allLink.getAttribute('href') : 'all.html';
      location.href = href + '#' + c.getAttribute('data-filter');
    });
  });

  /* ---- stars (saved items) ---- */
  function getStars() { try { return JSON.parse(localStorage.getItem(STAR_KEY) || '[]'); } catch (e) { return []; } }
  function setStars(list) { try { localStorage.setItem(STAR_KEY, JSON.stringify(list)); } catch (e) {} }
  function refreshStars() {
    var list = getStars();
    $$('.star-btn[data-star]').forEach(function (b) {
      b.classList.toggle('on', list.indexOf(b.getAttribute('data-star')) !== -1);
    });
    var sc = $('#starCount'); if (sc) { sc.textContent = list.length ? ' ' + list.length : ''; }
    var sci = $('#starCountInline'); if (sci) { sci.textContent = list.length ? list.length + (document.documentElement.lang === 'en' ? ' saved' : ' 条已收藏') : (document.documentElement.lang === 'en' ? '0 saved' : '暂无收藏'); }
    var stc = $('#starredCount'); if (stc) { stc.textContent = list.length ? (document.documentElement.lang === 'en' ? list.length + ' saved' : '已收藏 ' + list.length + ' 款') : (document.documentElement.lang === 'en' ? '0 saved' : '暂无收藏'); }
  }
  $$('[data-clear-stars]').forEach(function (b) {
    b.addEventListener('click', function () {
      setStars([]);
      refreshStars();
      location.reload();
    });
  });
  $$('.star-btn[data-star]').forEach(function (b) {
    b.addEventListener('click', function () {
      var id = b.getAttribute('data-star');
      var list = getStars();
      var i = list.indexOf(id);
      if (i === -1) { list.push(id); } else { list.splice(i, 1); }
      setStars(list);
      refreshStars();
    });
  });
  refreshStars();

  /* starred page: render saved items from the embedded games data */
  var starredList = $('#starredList');
  if (starredList) {
    var dataEl = $('#gamesData');
    var games = [];
    try { games = JSON.parse(dataEl ? dataEl.textContent : '[]'); } catch (e) { games = []; }
    var saved = getStars();
    var items = games.filter(function (g) { return saved.indexOf(g.id) !== -1; });
    var empty = $('#starredEmpty');
    if (items.length) {
      if (empty) { empty.hidden = true; }
      starredList.innerHTML = items.map(function (g) {
        return '<article class="feed-item" data-id="' + g.id + '" data-category="' + g.category + '">' +
          '<header class="fi-head"><span class="src">' + g.source.replace(/</g, '&lt;') + '</span>' +
          '<span class="sp"><button type="button" class="star-btn on" data-unstar="' + g.id + '" aria-label="unsave">★</button></span></header>' +
          '<h2><a href="items/' + g.id + '.html">' + g.title.replace(/</g, '&lt;') + '</a></h2>' +
          '<p class="sum">' + g.summary.replace(/</g, '&lt;') + '</p>' +
          '<div class="fi-foot"><span class="when">' + g.claim_by.replace(/</g, '&lt;') + '</span>' +
          '<a class="chip" href="' + g.link + '" target="_blank" rel="noopener">' +
          (document.documentElement.lang === 'en' ? 'Claim' : '去领取') + ' →</a></div></article>';
      }).join('');
      $$('[data-unstar]', starredList).forEach(function (b) {
        b.addEventListener('click', function () {
          var list = getStars().filter(function (x) { return x !== b.getAttribute('data-unstar'); });
          setStars(list);
          location.reload();
        });
      });
    }
  }

  /* ---- back to top ---- */
  var toTop = $('#toTop');
  if (toTop) {
    toTop.addEventListener('click', function () { window.scrollTo({ top: 0, behavior: 'smooth' }); });
    window.addEventListener('scroll', function () {
      toTop.classList.toggle('show', window.scrollY > 400);
    }, { passive: true });
  }
})();
