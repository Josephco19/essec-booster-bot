#!/usr/bin/env python3
"""Ouvre le booster gratuit d'Essec Masters s'il est disponible.

Le cookie de session est lu dans la variable d'environnement ESSEC_COOKIE
(un secret GitHub). Aucune dépendance : bibliothèque standard uniquement.

Codes de sortie :
  0 -> booster ouvert, ou pas encore disponible (normal)
  1 -> problème (cookie expiré, site modifié...) : GitHub t'envoie un mail
"""
import json
import os
import re
import sys
import urllib.error
import urllib.request

BASE = "https://www.essecmasters.com"
PAGE = BASE + "/home"
ACTION_NAME = "openBoosterAction"
# Identifiant vu le 19/11/2026 ; il change quand le site est redéployé,
# c'est pourquoi le script le recherche d'abord automatiquement.
FALLBACK_ACTION_ID = "40c3bb7cab49319c23f10e680bf561756130193580"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0 Safari/537.36")


def fail(msg):
    print("ERREUR : " + msg)
    sys.exit(1)


def get_cookie():
    raw = os.environ.get("ESSEC_COOKIE", "").strip()
    if not raw:
        fail("le secret ESSEC_COOKIE est vide ou absent.")
    if raw.lower().startswith("cookie:"):
        raw = raw.split(":", 1)[1].strip()
    return raw


def request(url, cookie, data=None, headers=None):
    h = {"User-Agent": UA, "Cookie": cookie}
    h.update(headers or {})
    req = urllib.request.Request(url, data=data, headers=h,
                                 method="POST" if data is not None else "GET")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, r.geturl(), r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, url, e.read().decode("utf-8", "replace")


def find_action_id(html, cookie):
    """Cherche l'identifiant de openBoosterAction dans les fichiers JS du site."""
    chunks = sorted(set(re.findall(r'/_next/static/chunks/[\w\-.]+\.js', html)))
    pattern = re.compile(
        r'createServerReference\)\(\s*"([0-9a-f]{20,})"[^;]{0,300}?"'
        + ACTION_NAME + '"')
    for path in chunks:
        status, _, js = request(BASE + path, cookie)
        if status != 200 or ACTION_NAME not in js:
            continue
        m = pattern.search(js)
        if m:
            return m.group(1)
    return None


def parse_result(body):
    """La réponse est au format RSC : des lignes 'id:json'. On cherche {ok: ...}."""
    for line in body.splitlines():
        _, _, payload = line.partition(":")
        try:
            obj = json.loads(payload)
        except ValueError:
            continue
        if isinstance(obj, dict) and "ok" in obj:
            return obj
    return None


RARITY_ORDER = ["common", "rare", "epic", "legendary", "creator"]
RARITY_EMOJI = {"common": "⚪", "rare": "🔵", "epic": "🟣",
                "legendary": "🟡", "creator": "🌟"}


def find_cards(obj):
    """Renvoie la liste des cartes (dicts avec name + rarity) dans la réponse."""
    cards = []

    def walk(x):
        if isinstance(x, dict):
            if isinstance(x.get("name"), str) and x.get("rarity"):
                cards.append(x)
                return
            for v in x.values():
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)

    walk(obj)
    return cards


def local_time(iso):
    """Convertit l'heure UTC du site en heure de Paris/Rome."""
    try:
        from datetime import datetime
        from zoneinfo import ZoneInfo
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return dt.astimezone(ZoneInfo("Europe/Paris")).strftime("%H:%M")
    except Exception:
        return iso + " (UTC)"


def write_notification(result):
    """Prépare le message du mail et indique au workflow s'il faut l'envoyer."""
    out = os.environ.get("GITHUB_OUTPUT")
    if not out:
        return
    cards = find_cards(result)
    min_rarity = os.environ.get("NOTIFY_MIN_RARITY", "common").strip().lower()
    min_rank = RARITY_ORDER.index(min_rarity) if min_rarity in RARITY_ORDER else 0
    best = max((RARITY_ORDER.index(c["rarity"]) for c in cards
                if c["rarity"] in RARITY_ORDER), default=0)
    notify = bool(cards) and best >= min_rank

    lines = ["### 🎁 Booster ouvert", ""]
    for c in cards:
        labels = c.get("labels") or {}
        rarity = labels.get("rarity") or c["rarity"]
        details = " · ".join(x for x in (labels.get("program"), labels.get("classOf"),
                                         c.get("subtitle")) if x)
        line = "- %s **%s** (%s)" % (RARITY_EMOJI.get(c["rarity"], "▫️"),
                                     c["name"], rarity)
        if details:
            line += " — " + details
        if c.get("isNew"):
            line += " — 🆕 nouvelle"
        lines.append(line)
    if result.get("nextAt"):
        lines += ["", "Prochain booster vers **%s**." % local_time(result["nextAt"])]
    with open("message.md", "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    with open(out, "a", encoding="utf-8") as f:
        f.write("notify=%s\n" % ("true" if notify else "false"))


def card_names(obj):
    """Essaie d'extraire les noms des cartes obtenues, quelle que soit la forme."""
    names = []

    def walk(x):
        if isinstance(x, dict):
            name = x.get("name") or x.get("title")
            rarity = x.get("rarity")
            if isinstance(name, str) and rarity:
                names.append("%s (%s)%s" % (name, rarity,
                                            " NOUVELLE" if x.get("isNew") else ""))
                return
            for v in x.values():
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)

    walk(obj)
    return names


def main():
    cookie = get_cookie()

    status, final_url, html = request(PAGE, cookie)
    if status != 200 or not final_url.rstrip("/").endswith("/home"):
        fail("pas connecté (redirigé vers %s, code %s). Le cookie a "
             "probablement expiré : remets-le dans le secret ESSEC_COOKIE."
             % (final_url, status))

    action_id = find_action_id(html, cookie)
    if action_id:
        print("Identifiant d'action trouvé : " + action_id)
    else:
        print("Identifiant introuvable dans le JS, utilisation de la valeur connue.")
        action_id = FALLBACK_ACTION_ID

    status, _, body = request(
        PAGE, cookie,
        data=json.dumps([{"force": False}]).encode(),
        headers={
            "Next-Action": action_id,
            "Accept": "text/x-component",
            "Content-Type": "text/plain;charset=UTF-8",
            "Origin": BASE,
            "Referer": PAGE,
        })

    if status != 200:
        fail("le site a répondu %s : %s" % (status, body[:300]))

    result = parse_result(body)
    if result is None:
        fail("réponse inattendue : " + body[:300])

    if result.get("ok"):
        names = card_names(result)
        print("Booster ouvert !" + (" Cartes : " + ", ".join(names) if names else ""))
        if result.get("nextAt"):
            print("Prochain booster : " + local_time(str(result["nextAt"])))
        write_notification(result)
    else:
        # Cas normal quand le timer n'est pas encore à zéro.
        print("Pas de booster pour l'instant : %s" % result.get("message", result))


if __name__ == "__main__":
    main()
