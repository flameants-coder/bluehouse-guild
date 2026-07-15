# -*- coding: utf-8 -*-
"""
Albion 精煉利潤機器人
從 Albion Online Data Project (AODP) 抓市場價，套用你的精煉成本計算機公式，
支援基礎與附魔(.1/.2/.3)，並在原料比陣營之心貴時自動用陣營之心替代。
輸出各階利潤並存成 CSV。

用法：
    python refine_bot.py
設定都在 config.py。
"""
import csv
import os
import sys
import json
import datetime as dt
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor

try:
    import requests
except ImportError:
    sys.exit("缺少 requests 套件，請先執行：pip install requests")

import config as cfg

try:
    sys.stdout.reconfigure(encoding="utf-8")   # Windows 終端機防亂碼
except Exception:
    pass

RESET = "\033[0m"
USE_COLOR = getattr(cfg, "USE_COLOR", True)
if USE_COLOR and os.name == "nt":            # 讓 Windows 終端機吃 ANSI 顏色
    try:
        import ctypes
        k = ctypes.windll.kernel32
        k.SetConsoleMode(k.GetStdHandle(-11), 7)
    except Exception:
        pass


def rating(margin):
    """依利潤率回傳 (評級文字, ANSI顏色)。"""
    for thr, label_, color in cfg.RATING_TIERS:
        if margin >= thr:
            return label_, color
    return "虧損", "\033[91m"

API = "https://{server}.albion-online-data.com/api/v2/stats/prices/{items}?locations={cities}&qualities=1"
UA = {"User-Agent": "albion-refine-bot/2.0"}
NOW = dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)


# ── 返還率 ────────────────────────────────────────────────
def return_rate():
    r = cfg.RETURN_RATE
    total = r["base"] + r["city_bonus"] + r["focus"] + r["event"]
    return total / (100 + total)


# ── 物品 ID ──────────────────────────────────────────────
def item_id(tier, base, ench):
    """T4_HIDE / T4_HIDE_LEVEL1@1 …"""
    if ench == 0:
        return f"T{tier}_{base}"
    return f"T{tier}_{base}_LEVEL{ench}@{ench}"


def item_value(tier, ench):
    return cfg.ITEM_VALUE[tier] * (2 ** ench)


def label(tier, ench):
    return f"T{tier}" + (f".{ench}" if ench else "")


# 這些原料的精煉成品「沒有附魔版」（石材 Stone 只有基礎），只算基礎階
NO_ENCHANT_RAW = {"ROCK"}


def enchants_for(tier, raw=None):
    """附魔資源只存在 T4+；T2/T3 只有基礎(0)；石材(ROCK)全無附魔。"""
    if raw in NO_ENCHANT_RAW:
        return [0]
    return [e for e in cfg.ENCHANT_LEVELS if e == 0 or tier >= 4]


def lower_enchant(tier, ench):
    """下一階(tier-1)成品的附魔等級：若 tier-1 < 4(無附魔) 則用基礎 0，否則同附魔。"""
    return ench if (tier - 1) >= 4 else 0


def ctag(city):
    """城市縮寫 + 顏色，如 Bridgewatch → Brid黃。"""
    return city[:4] + getattr(cfg, "CITY_COLOR", {}).get(city, "")


# ── 抓價 ─────────────────────────────────────────────────
def active_lines():
    return cfg.ONLY_LINES or list(cfg.LINES.keys())


def _as_list(v):
    """接受 None / 單一城市字串 / 清單，統一回傳清單。"""
    if not v:
        return None
    return [v] if isinstance(v, str) else list(v)


def buy_cities():
    return _as_list(getattr(cfg, "BUY_CITIES", None)) or cfg.CITIES


def sell_cities():
    return _as_list(getattr(cfg, "SELL_CITIES", None)) or cfg.CITIES


def all_cities():
    return sorted(set(buy_cities()) | set(sell_cities()))


def build_item_ids():
    ids = set()
    for name in active_lines():
        L = cfg.LINES[name]
        for t in cfg.TIERS:
            for e in enchants_for(t, L["raw"]):
                ids.add(item_id(t, L["raw"], e))
                ids.add(item_id(t, L["refined"], e))
    if cfg.USE_FACTION_HEART:
        for hid in cfg.FACTION_HEARTS.values():
            ids.add(hid)
    return sorted(ids)


def _get_json(url, timeout=60):
    """抓單一 URL 的 JSON，失敗回 None。"""
    try:
        r = requests.get(url, headers=UA, timeout=timeout)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None


def _fetch_all(urls, workers=8):
    """並行抓多個 URL，回傳結果清單（對應順序，失敗為 None）。"""
    if not urls:
        return []
    with ThreadPoolExecutor(max_workers=min(workers, len(urls))) as ex:
        return list(ex.map(_get_json, urls))


def _chunks(seq, size=50):
    return [seq[i:i + size] for i in range(0, len(seq), size)]


def fetch_prices(item_ids):
    """{item_id: {city: rowdict}}，分批並行打 API。"""
    cities = ",".join(all_cities())
    urls = [API.format(server=cfg.SERVER, items=",".join(c), cities=cities)
            for c in _chunks(item_ids)]
    out = defaultdict(dict)
    for data in _fetch_all(urls):
        if not data:
            continue
        for row in data:
            out[row["item_id"]][row["city"]] = row
    return out


def _median(xs):
    xs = sorted(xs)
    n = len(xs)
    if not n:
        return None
    return xs[n // 2] if n % 2 else (xs[n // 2 - 1] + xs[n // 2]) / 2


def fetch_history(item_ids, days=7):
    """抓最近 days 天成交，取每日均價的『中位數』(抗單日異常暴衝)，分批並行。
    回傳 {item_id: {city: (中位均價, 7日成交量)}}。"""
    cities = ",".join(all_cities())
    urls = [(f"https://{cfg.SERVER}.albion-online-data.com/api/v2/stats/history/"
             f"{','.join(c)}?locations={cities}&time-scale=24") for c in _chunks(item_ids)]
    out = defaultdict(dict)
    for data in _fetch_all(urls):
        if not data:
            continue
        for s in data:
            recent = [p for p in (s.get("data") or [])[-days:] if p.get("avg_price")]
            if not recent:
                continue
            med = _median([p["avg_price"] for p in recent])
            vol = sum(p.get("item_count") or 0 for p in recent)
            out[s["item_id"]][s["location"]] = (round(med), vol)
    return out


# 7 天均價資料（全域，供 acquire_price / sell_price 取用）：{iid: {city: (avg7, vol)}}
_HIST = {}


def hist_price(iid, cities_allowed, want_low):
    """從 7 天均價挑城市：want_low=買(最低) / False=賣(最高)。回傳 (價格, 城市, None)。"""
    best = None
    for c, (p, _v) in _HIST.get(iid, {}).items():
        if c not in cities_allowed or not p:
            continue
        if best is None or (want_low and p < best[0]) or (not want_low and p > best[0]):
            best = (p, c, None)
    return best


def hist_volume(iid, city):
    d = _HIST.get(iid, {}).get(city)
    return d[1] if d else None


def current_sell_range(prices, iid):
    """賣品城市裡『當下最低賣單』的範圍 (lo, hi)，給均價 vs 現價偏離提示用。"""
    allowed = set(sell_cities())
    vals = [row.get("sell_price_min") for c, row in prices.get(iid, {}).items()
            if c in allowed and (row.get("sell_price_min") or 0) > 0]
    return (min(vals), max(vals)) if vals else None


def _age_hours(datestr):
    if not datestr:
        return None
    try:
        d = dt.datetime.fromisoformat(datestr.replace("Z", ""))
    except ValueError:
        return None
    return (NOW - d).total_seconds() / 3600.0


def _pick(prices, iid, field, date_field, want_low, allowed=None):
    """回傳 (價格, 城市, 幾小時前)；want_low=買(取最低) / False=賣(取最高)。allowed=只看這些城市。"""
    best = None
    for city, row in prices.get(iid, {}).items():
        if allowed is not None and city not in allowed:
            continue
        p = row.get(field) or 0
        if p <= 0:
            continue
        age = _age_hours(row.get(date_field))
        if best is None or (want_low and p < best[0]) or (not want_low and p > best[0]):
            best = (p, city, age)
    return best


_BUY_FIELD = {"max_buy": ("buy_price_max", "buy_price_max_date"),
              "min_sell": ("sell_price_min", "sell_price_min_date")}
_SELL_FIELD = {"min_sell": ("sell_price_min", "sell_price_min_date"),
               "max_buy": ("buy_price_max", "buy_price_max_date")}


def acquire_price(prices, iid):
    """買料成本；只看 BUY_CITIES。回傳 (價, 城, 時, 基準)：avg7 用 7 天均價，
    抓不到就自動回填即時最低賣單(基準='現')。"""
    allowed = set(buy_cities())
    if getattr(cfg, "PRICE_BASIS", "avg7") == "avg7":
        r = hist_price(iid, allowed, want_low=True)
        if r:
            return (r[0], r[1], r[2], "avg")
    order = ["max_buy", "min_sell"] if cfg.BUY_PRICE == "max_buy" else ["min_sell", "max_buy"]
    for k in order:
        f, d = _BUY_FIELD[k]
        r = _pick(prices, iid, f, d, want_low=True, allowed=allowed)
        if r:
            return (r[0], r[1], r[2], "現")   # 回填：即時掛單
    return None


def sell_price(prices, iid):
    """賣出價；只看 SELL_CITIES。回傳 (價, 城, 時, 基準)：avg7 用 7 天均價，
    抓不到就自動回填即時掛單(基準='現')。"""
    allowed = set(sell_cities())
    if getattr(cfg, "PRICE_BASIS", "avg7") == "avg7":
        r = hist_price(iid, allowed, want_low=False)
        if r:
            return (r[0], r[1], r[2], "avg")
    order = ["max_buy", "min_sell"] if cfg.SELL_PRICE == "max_buy" else ["min_sell", "max_buy"]
    for k in order:
        f, d = _SELL_FIELD[k]
        r = _pick(prices, iid, f, d, want_low=False, allowed=allowed)
        if r:
            return (r[0], r[1], r[2], "現")
    return None


def eff_raw(prices, L, t, e, memo):
    """
    取得 1 個「T{t}.{e} 原料」的最便宜成本，比較三種來源並取最低：
      (a) 直接從市場買
      (b) 升附魔轉換：買 T{t}.{e-1} + 銀幣
      (c) 升階轉換  ：買 T{t-1}.{e} + 銀幣
    可遞迴（下階本身也可能來自轉換）。回傳 (價格, 來源標記, 幾小時前) 或 None。
    """
    key = (t, e)
    if key in memo:
        return memo[key]
    memo[key] = None  # 防遞迴環（理論上 t、e 都遞減不會發生）
    cands = []
    mk = acquire_price(prices, item_id(t, L["raw"], e))
    if mk:
        pre = "買" if mk[3] == "avg" else "現"   # 現=均價抓不到、回填即時掛單
        cands.append((mk[0], f"{pre}{ctag(mk[1])}·{label(t, e)}", mk[2]))
    can_trans = getattr(cfg, "USE_TRANSMUTE", False) and L["raw"] not in getattr(cfg, "TRANSMUTE_EXCLUDE", [])
    if can_trans:
        sil = cfg.TRANSMUTE["enchant"].get((t, e))
        if sil is not None and e >= 1:
            low = eff_raw(prices, L, t, e - 1, memo)
            if low:
                cands.append((low[0] + sil, f"轉附[{low[1]}]", low[2]))
        sil2 = cfg.TRANSMUTE["tier"].get((t, e))
        if sil2 is not None:
            low2 = eff_raw(prices, L, t - 1, e, memo)
            if low2:
                cands.append((low2[0] + sil2, f"轉階[{low2[1]}]", low2[2]))
    res = min(cands, key=lambda x: x[0]) if cands else None
    memo[key] = res
    return res


# ── 利潤計算（你的公式 + 陣營之心）────────────────────────
def stale(*ages):
    return "⚠過期" if any(a is not None and a > cfg.STALE_HOURS for a in ages) else ""


def compute():
    rr = return_rate()
    ids = build_item_ids()
    _cc = lambda cs: ', '.join(f"{c}({getattr(cfg, 'CITY_COLOR', {}).get(c, '')})" for c in cs)
    print(f"伺服器：{cfg.SERVER}   買料城市：{_cc(buy_cities())}   賣品城市：{_cc(sell_cities())}")
    print(f"返還率：{rr:.4f}  (基礎{cfg.RETURN_RATE['base']} + 特產{cfg.RETURN_RATE['city_bonus']}"
          f" + 專注{cfg.RETURN_RATE['focus']} + 活動{cfg.RETURN_RATE['event']})")
    bf, sf = cfg.BUY_FEE[cfg.BUY_PRICE], cfg.SELL_FEE[cfg.SELL_PRICE]
    basis_lbl = "7天均價" if getattr(cfg, "PRICE_BASIS", "avg7") == "avg7" else "即時掛單"
    print(f"價格基準[{basis_lbl}]  買料手續費 +{bf:.1%} / 賣品手續費 -{sf:.1%} / 店鋪費 {cfg.STATION_FEE}"
          f" / 陣營之心替代 {'開' if cfg.USE_FACTION_HEART else '關'}")
    print("抓即時掛單中…")
    prices = fetch_prices(ids)

    global _HIST
    _HIST = {}
    use_avg7 = getattr(cfg, "PRICE_BASIS", "avg7") == "avg7"
    if use_avg7 or getattr(cfg, "SHOW_MARKET_VALUE", False):
        print("抓 7 天成交均價中…")
        _HIST = fetch_history(ids)

    low_vol = getattr(cfg, "LOW_VOLUME", 300)
    show_vol = getattr(cfg, "SHOW_MARKET_VALUE", False)
    csv_rows = []
    report_rows = []  # 給 HTML 用（含數值）
    for name in active_lines():
        L = cfg.LINES[name]
        heart_id = cfg.FACTION_HEARTS.get(L["raw"]) if cfg.USE_FACTION_HEART else None
        heart = acquire_price(prices, heart_id) if heart_id else None
        heart_p = heart[0] if heart else None

        print(f"\n=== {name}（{L['raw']}→{L['refined']}）"
              + (f"　心價 {heart_p:,.0f}" if heart_p else "") + " ===")
        if USE_COLOR:
            legend = "  ".join(f"{c}{lab}{RESET}" for _, lab, c in cfg.RATING_TIERS) + f"  \033[91m虧損{RESET}"
            print("圖例(利潤率)： " + legend)
        vol_hdr = f"{'7日量':>9}" if show_vol else ""
        print(f"{'階':<6}{'原料':>9}{'成品(7日均)':>10}{vol_hdr}{'下階':>9}{'成本':>10}{'利潤/個':>10}{'利潤率':>8} {'評級':>5}  來源/備註")

        # 先把每個(階,附魔)的成品買入價存起來，給上一階當下階原料用
        ref_buy = {}
        for t in cfg.TIERS:
            for e in enchants_for(t, L["raw"]):
                rb = acquire_price(prices, item_id(t, L["refined"], e))
                ref_buy[(t, e)] = (rb[0], rb[3]) if rb else None   # (價, 基準)

        raw_memo = {}  # 原料有效成本（含轉換）快取，per 線
        for e in cfg.ENCHANT_LEVELS:
            for t in cfg.TIERS:
                if e and e not in enchants_for(t, L["raw"]):   # T2/T3、石材 無附魔
                    continue
                raw = eff_raw(prices, L, t, e, raw_memo)
                out = sell_price(prices, item_id(t, L["refined"], e))
                if not raw or not out:
                    continue
                raw_p, raw_src, raw_age = raw
                out_p, out_city, out_age, out_basis = out
                n = cfg.RAW_PER_TIER[t]

                # 下階成品：tier-1 若 <4 用基礎，否則同附魔（T2 沒有下階）
                lower_rec = ref_buy.get((t - 1, lower_enchant(t, e))) if t > 2 else None
                lower = lower_rec[0] if lower_rec else 0
                lower_fallback = bool(lower_rec and lower_rec[1] == "現")

                # 陣營之心：只在附魔 .1~.3(.4 不可用)、且原料比心貴時替代 1 個原料
                heart_nm = cfg.FACTION_HEART_NAME.get(L["raw"], "陣營之心")
                first_unit, note = raw_p, ""
                if 1 <= e <= cfg.HEART_ENCHANT_MAX and heart_p and heart_p < raw_p:
                    first_unit, note = heart_p, f"♥{heart_nm}"
                raws_cost = first_unit + raw_p * (n - 1)

                material = (lower + raws_cost) * (1 - rr) * (1 + bf)
                fee = 0.1125 * item_value(t, e) * (cfg.STATION_FEE / 100.0)
                cost = material + fee
                profit = out_p * (1 - sf) - cost
                margin = profit / cost if cost else 0
                flag = stale(raw_age, out_age)
                rate_label, rate_color = rating(margin)

                # 成品 7 天成交量（賣點城市）→ 判斷均價可靠度
                ref_id = item_id(t, L["refined"], e)
                vol = hist_volume(ref_id, out_city)
                thin = bool(vol is not None and vol < low_vol)
                if thin:
                    rate_color = "\033[95m"  # 洋紅：量少、均價參考性低
                vol_cell = (f"{vol:>9,.0f}" if (show_vol and vol is not None)
                            else (f"{'—':>9}" if show_vol else ""))
                thin_tag = f"⚠量少({vol})" if thin else ""

                # 均價 vs 當下掛單偏離提示
                dev, cur_lo, cur_hi = "", None, None
                cr = current_sell_range(prices, ref_id)
                if cr:
                    cur_lo, cur_hi = cr
                    thr = getattr(cfg, "PRICE_DEVIATION", 0.35)
                    if out_p > cur_hi * (1 + thr):
                        dev = "偏高"
                    elif out_p < cur_lo * (1 - thr):
                        dev = "偏低"
                dev_tag = f"↕偏離現價{cur_lo}~{cur_hi}" if dev else ""

                # 回填提示：均價抓不到、改用即時掛單
                sell_pre = "賣" if out_basis == "avg" else "現賣"
                fills = []
                if out_basis == "現":
                    fills.append("成品")
                if lower_fallback:
                    fills.append("下階")
                fill_tag = f"↺回填現價({'/'.join(fills)})" if fills else ""

                src = f"{raw_src}/{sell_pre}{ctag(out_city)} {note} {thin_tag} {dev_tag} {fill_tag} {flag}".strip()
                row = (f"{label(t, e):<6}{raw_p:>9,.0f}{out_p:>10,.0f}{vol_cell}{lower:>9,.0f}"
                       f"{cost:>10,.0f}{profit:>10,.0f}{margin:>8.1%} {rate_label:>5}  {src}")
                print(f"{rate_color}{row}{RESET}" if USE_COLOR else row)
                csv_rows.append({
                    "線": name, "階": label(t, e),
                    "評級": rate_label,
                    "原料成本": round(raw_p), "原料來源": raw_src,
                    "成品賣價(7日均)": round(out_p), "賣點": out_city,
                    "成品價來源": "7日均" if out_basis == "avg" else "現價回填",
                    "7日成交量": vol if vol is not None else "",
                    "量少": "⚠" if thin else "",
                    "偏離現價": dev, "當下賣單低": cur_lo or "", "當下賣單高": cur_hi or "",
                    "下階成品": round(lower), "回填": "/".join(fills),
                    "用陣營之心": "是" if note else "",
                    "製作成本": round(cost, 1),
                    "利潤/個": round(profit, 1),
                    "利潤率": f"{margin:.2%}",
                    "備註": flag,
                })
                report_rows.append({
                    "line": name, "tier": label(t, e), "t": t, "e": e, "rating": rate_label,
                    "raw": raw_p, "raw_src": raw_src, "sell": out_p, "sell_city": out_city,
                    "sell_basis": out_basis, "fills": fills,
                    "vol": vol, "thin": thin,
                    "dev": dev, "cur_lo": cur_lo, "cur_hi": cur_hi,
                    "lower": lower, "heart": bool(note), "heart_name": heart_nm, "cost": cost,
                    "mbase": lower + raws_cost, "fee": fee,  # 給網頁互動重算返還率用
                    "profit": profit, "margin": margin, "stale": bool(flag),
                })

    if csv_rows:
        with open(cfg.CSV_OUT, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=list(csv_rows[0].keys()))
            w.writeheader()
            w.writerows(csv_rows)
        print(f"\n已存檔：{cfg.CSV_OUT}（{len(csv_rows)} 列）")

    if getattr(cfg, "MAKE_HTML", False) and report_rows:
        R = cfg.RETURN_RATE
        basis = "7天均價" if use_avg7 else "即時掛單"
        # 給網頁互動(城市/專注/活動即時重算)用的價格與結構資料
        pdata = {}
        for iid in ids:
            cd = {}
            for c in all_cities():
                med, vol = _HIST.get(iid, {}).get(c, (None, 0))
                cur = (prices.get(iid, {}).get(c) or {}).get("sell_price_min") or None
                if med is not None or cur is not None:
                    cd[c] = [med, vol, cur]
            if cd:
                pdata[iid] = cd
        struct = {
            "cities": all_cities(),
            "lines": [{"name": n, "raw": cfg.LINES[n]["raw"], "refined": cfg.LINES[n]["refined"],
                       "heart": (cfg.FACTION_HEARTS.get(cfg.LINES[n]["raw"]) if cfg.USE_FACTION_HEART else None),
                       "heartName": cfg.FACTION_HEART_NAME.get(cfg.LINES[n]["raw"], "陣營之心")}
                      for n in active_lines()],
            "rawPerTier": cfg.RAW_PER_TIER, "itemValue": cfg.ITEM_VALUE,
            "transmute": {"enchant": {f"{t},{e}": v for (t, e), v in cfg.TRANSMUTE["enchant"].items()},
                          "tier": {f"{t},{e}": v for (t, e), v in cfg.TRANSMUTE["tier"].items()}},
            "useTransmute": bool(cfg.USE_TRANSMUTE),
            "transmuteExclude": list(getattr(cfg, "TRANSMUTE_EXCLUDE", [])),
            "useHeart": bool(cfg.USE_FACTION_HEART), "heartMax": cfg.HEART_ENCHANT_MAX,
            "rrBase": R["base"], "rrCity": R["city_bonus"],
            "bf": bf, "sf": sf, "stationFee": cfg.STATION_FEE,
            "lowVol": low_vol, "dev": getattr(cfg, "PRICE_DEVIATION", 0.35),
            "cityColor": getattr(cfg, "CITY_COLOR", {}),
        }
        meta = {
            "server": cfg.SERVER, "buy_cities": buy_cities(), "sell_cities": sell_cities(),
            "basis": basis, "bf": bf, "sf": sf, "station_fee": cfg.STATION_FEE,
            "rr_base": R["base"], "rr_city": R["city_bonus"],
            "focus0": R["focus"], "event0": R["event"], "low_vol": low_vol,
            "time": NOW.strftime("%Y-%m-%d %H:%M UTC"),
            "pdata": pdata, "struct": struct,
        }
        write_html(report_rows, meta, cfg.HTML_OUT)
        print(f"已產生網頁：{cfg.HTML_OUT}（用瀏覽器開）")


# ── 網頁報表 ─────────────────────────────────────────────
def write_html(rows, meta, path):
    import html as _h
    RANK = {"賺爛": 5, "不錯": 4, "普通": 3, "微利": 2, "虧損": 1}

    def td(v, cls=""):
        return f'<td class="{cls}">{v}</td>'

    def money(x):
        return f"{x:,.0f}" if x is not None else "—"

    srank = {"賺爛": "s5", "不錯": "s4", "普通": "s3", "微利": "s2", "虧損": "s1"}
    body = []
    for r in rows:
        cls = srank[r["rating"]] + (" thin" if r["thin"] else "")
        tags = []
        if r["heart"]:
            tags.append(f'<span class="tag heart">♥{_h.escape(r["heart_name"])}</span>')
        if r["thin"]:
            tags.append(f'<span class="tag warn">⚠量少 {r["vol"]}</span>')
        if r["dev"]:
            arrow = "↑" if r["dev"] == "偏高" else "↓"
            tags.append(f'<span class="tag dev" title="7天均價與當下掛單差異大">{arrow}{r["dev"]}現價 {money(r["cur_lo"])}~{money(r["cur_hi"])}</span>')
        if r["fills"]:
            tags.append(f'<span class="tag fill" title="該項無7天均價，改用即時掛單回填">↺回填現價 {"/".join(r["fills"])}</span>')
        if r["stale"]:
            tags.append('<span class="tag stale">過期</span>')
        note = " ".join(tags)
        badge = f'<span class="badge b{RANK[r["rating"]]}">{r["rating"]}</span>'
        body.append(
            f'<tr class="{cls}" data-line="{_h.escape(r["line"])}" data-t="{r["t"]}" data-e="{r["e"]}" '
            f'data-margin="{r["margin"]:.4f}" data-ok="1" '
            f'data-thin="{int(r["thin"])}" data-loss="{int(r["margin"] < 0)}" '
            f'data-mbase="{r["mbase"]:.2f}" data-fee="{r["fee"]:.2f}" data-sell="{r["sell"]:.2f}">'
            f'<td>{_h.escape(r["line"])}</td><td class="k">{r["tier"]}</td>'
            f'{td(money(r["raw"]),"num")}{td(money(r["sell"]),"num")}'
            f'{td(money(r["vol"]),"num mv")}{td(money(r["lower"]),"num")}'
            f'<td class="num cost">{money(r["cost"])}</td><td class="num bold profit">{money(r["profit"])}</td>'
            f'<td class="num margin" data-v="{r["margin"]:.4f}">{r["margin"]:.1%}</td>'
            f'<td class="rate">{badge}</td>'
            f'<td class="src">{_h.escape(r["raw_src"])}→{_h.escape(r["sell_city"][:4])} {note}</td></tr>'
        )

    lines = sorted({r["line"] for r in rows})
    line_btns = '<button class="lf active" data-l="">全部</button>' + "".join(
        f'<button class="lf" data-l="{_h.escape(l)}">{_h.escape(l)}</button>' for l in lines)
    n_thin = sum(1 for r in rows if r["thin"])
    n_dev = sum(1 for r in rows if r["dev"])
    n_good = sum(1 for r in rows if r["margin"] >= 0.30 and not r["thin"])
    real = [r for r in rows if not r["thin"] and r["margin"] > 0]
    best = max(real, key=lambda r: r["margin"], default=None)
    best_txt = (f'{_h.escape(best["line"].split()[0])} {best["tier"]}'
                f'<span class="bm">{best["margin"]:.0%}</span>') if best else "—"

    tot0 = meta["rr_base"] + meta["rr_city"] + meta["focus0"] + meta["event0"]
    rr0 = tot0 / (100 + tot0)
    ev_opts = "".join(f'<option value="{v}"{" selected" if v == meta["event0"] else ""}>{v}%</option>'
                      for v in (0, 10, 20))

    tpl = """<style>
*{box-sizing:border-box}
:root{
 --bg:#f6f4ee;--panel:#ffffff;--panel2:#f0ede4;--line:#ddd8cc;--ink:#1e2126;
 --muted:#5f6672;--bronze:#9a6b16;--bronzed:#7d5610;
 --good:#15803d;--ok:#4d7c0f;--mid:#b45309;--low:#6b7280;--bad:#dc2626;--fake:#a21caf;
}
html,body{margin:0;background:var(--bg)}
.wrap{max-width:1120px;margin:0 auto;padding:22px 18px 40px;
 font-family:system-ui,-apple-system,"Segoe UI","Noto Sans TC",sans-serif;
 color:var(--ink);background:var(--bg);min-height:100vh}
.head{display:flex;flex-wrap:wrap;align-items:baseline;gap:10px 16px;border-bottom:2px solid var(--line);padding-bottom:14px}
h1{font-family:Georgia,"Noto Serif TC",serif;font-weight:700;font-size:24px;letter-spacing:.3px;margin:0;color:var(--bronze)}
.sub{color:var(--muted);font-size:12.5px;line-height:1.7}
.sub b{color:var(--ink);font-weight:600}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin:18px 0}
.card{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:12px 14px;box-shadow:0 1px 2px rgba(40,30,10,.04)}
.card .lab{font-size:11px;letter-spacing:.12em;text-transform:uppercase;color:var(--muted)}
.card .val{font-size:26px;font-weight:700;margin-top:4px;font-variant-numeric:tabular-nums;color:var(--ink)}
.card .bm{font-size:15px;font-weight:700;color:var(--good);margin-left:6px}
.card.good .val{color:var(--good)}.card.bad .val{color:var(--fake)}.card.dev .val{color:var(--bronze)}.card.best .val{font-size:19px}
.controls{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:6px 0 14px}
.controls input,.controls select{padding:6px 11px;background:var(--panel);border:1px solid var(--line);border-radius:7px;font-size:13px;color:var(--ink)}
input:focus-visible,button:focus-visible,select:focus-visible{outline:2px solid var(--bronze);outline-offset:1px}
button{cursor:pointer;border:1px solid var(--line);background:var(--panel);color:var(--ink);border-radius:7px;padding:5px 11px;font-size:13px}
button:hover{border-color:var(--bronze)}
button.active{background:var(--bronze);color:#fff;border-color:var(--bronze);font-weight:600}
label.chk{font-size:13px;color:var(--ink);user-select:none;display:inline-flex;gap:5px;align-items:center}
.opts{display:flex;flex-wrap:wrap;gap:14px;align-items:center;background:var(--panel);border:1px solid var(--line);border-radius:9px;padding:9px 13px;margin-bottom:12px;font-size:13px}
.opts .grp{display:flex;gap:6px;align-items:center}.opts label{color:var(--muted)}
.opts .rr{margin-left:auto;color:var(--ink)}.opts .rr b{color:var(--bronze);font-variant-numeric:tabular-nums}
.tablewrap{overflow-x:auto;border:1px solid var(--line);border-radius:10px;background:var(--panel)}
table{border-collapse:collapse;width:100%;font-size:13px;min-width:820px}
th,td{padding:7px 11px;text-align:left;white-space:nowrap;border-bottom:1px solid var(--line)}
tbody tr:last-child td{border-bottom:none}
th{position:sticky;top:0;background:#efece3;cursor:pointer;font-weight:700;color:#3a3f48;font-size:12px;letter-spacing:.03em}
th:hover{color:var(--bronze)}
th.num,td.num{text-align:right;font-variant-numeric:tabular-nums}
td.bold{font-weight:700}.mv{color:var(--muted)}
td.k{font-weight:700;color:var(--ink)}
.src{color:var(--muted);font-size:12px}
tbody tr{background:var(--panel)}
tr.s5{box-shadow:inset 4px 0 var(--good)}tr.s4{box-shadow:inset 4px 0 var(--ok)}
tr.s3{box-shadow:inset 4px 0 var(--mid)}tr.s2{box-shadow:inset 4px 0 var(--low)}
tr.s1{box-shadow:inset 4px 0 var(--bad);background:#fdf3f3}
tr.thin{box-shadow:inset 4px 0 var(--fake);background:#fbf1fb}
tr:hover{background:var(--panel2)}
.badge{padding:2px 9px;border-radius:20px;font-size:11.5px;font-weight:700;color:#fff}
.b5{background:var(--good)}.b4{background:var(--ok)}.b3{background:var(--mid)}.b2{background:var(--low)}.b1{background:var(--bad)}
.tag{font-size:11px;padding:1px 6px;border-radius:5px;margin-left:4px;font-weight:600}
.tag.heart{background:#fce7f3;color:#be185d}.tag.warn{background:#fbe6fb;color:#a21caf}.tag.stale{background:#e5e7eb;color:#555}
.tag.dev{background:#fff2d9;color:#9a6b16;border:1px solid #e8d3a0}
.tag.fill{background:#e7f0fb;color:#2b6cb0;border:1px solid #c3d9f0}
th small{font-weight:400;color:#8a8578;font-size:10px}
.foot{color:var(--muted);font-size:12px;margin-top:14px;line-height:1.6}
.foot b{color:var(--fake)}
@media(max-width:560px){h1{font-size:20px}.card .val{font-size:22px}}
</style>
<div class="wrap">
<div class="head">
<h1>精煉計算器<small style="font-size:14px;font-weight:400;color:var(--muted)">（Blue house 公會內部用）</small></h1>
<div class="sub">伺服器 <b>__SERVER__</b>　買料 <b>__BUYCITIES__</b>　賣品 <b>__SELLCITIES__</b><br>價格基準 <b>__BASIS__</b>　更新 <b>__TIME__</b>　·　<a href="使用說明.html" target="_blank" style="color:var(--bronze);font-weight:600">📖 使用說明</a></div>
</div>
<div class="cards">
<div class="card"><div class="lab">總筆數</div><div class="val" id="cTot">__N__</div></div>
<div class="card good"><div class="lab">值得做 ≥30%</div><div class="val" id="cGood">__NGOOD__</div></div>
<div class="card bad"><div class="lab">量少警示 &lt;__LOWVOL__</div><div class="val" id="cThin">__NTHIN__</div></div>
<div class="card dev"><div class="lab">偏離現價 &gt;35%</div><div class="val" id="cDev">__NDEV__</div></div>
<div class="card best"><div class="lab">最佳機會</div><div class="val" id="cBest">__BEST__</div></div>
</div>
<div class="opts">
<div class="grp"><label>買料城市</label><select id="buyCity">__BUYOPTS__</select></div>
<div class="grp"><label>賣品城市</label><select id="sellCity">__SELLOPTS__</select></div>
<div class="grp"><label class="chk"><input type="checkbox" id="focus"__FOCUSCHK__>灌專注(+59)</label></div>
<div class="grp"><label>活動加成</label><select id="event">__EVOPTS__</select></div>
<div class="rr">返還率 <b id="rrv">__RR0__</b></div>
</div>
<div class="controls">
__LINEBTNS__
<input id="q" placeholder="搜尋 階級 / 城市…" aria-label="搜尋">
<label class="chk"><input type="checkbox" id="hideLoss">隱藏虧損</label>
<label class="chk"><input type="checkbox" id="hideThin">隱藏量少</label>
</div>
<div class="tablewrap"><table id="t">
<thead><tr>
<th data-c="0">線</th><th data-c="1">階</th>
<th data-c="2" class="num">原料</th><th data-c="3" class="num">成品賣價<small>·7日均</small></th>
<th data-c="4" class="num">7日量</th><th data-c="5" class="num">下階</th>
<th data-c="6" class="num">成本</th><th data-c="7" class="num">利潤/個</th>
<th data-c="8" class="num">利潤率</th><th data-c="9">評級</th><th>來源／備註</th>
</tr></thead>
<tbody>__BODY__</tbody>
</table></div>
<p class="foot">買賣價皆採 <b style="color:var(--bronze)">__BASIS__</b>（每日均價取中位數，抗單日暴衝）。<b>量少</b>＝成品 7 天成交量 &lt; __LOWVOL__，參考性低。<span class="tag dev">↑偏離現價</span>＝7天均價與當下掛單差 &gt; 35%，附當前市價供你核對。上方可切換<b style="color:var(--bronze)">專注/活動加成</b>即時重算；點欄位標題可排序。</p>
</div>
<script>
var PRICES=__PRICES__;
var S=__STRUCT__;
var focus=__FOCUS0__,event=__EVENT0__;
var lineMap={};S.lines.forEach(function(l){lineMap[l.name]=l;});
var tb=document.querySelector('#t tbody');
var rows=[].slice.call(tb.rows);
function num(x){return parseFloat((x||'').replace(/[^0-9.\\-]/g,''))||0}
function fmt(x){return x==null?'—':Math.round(x).toLocaleString()}
function sc(c){return c.slice(0,4)}
function ctag(c){return sc(c)+((S.cityColor&&S.cityColor[c])||'')}
function lblTE(t,e){return 'T'+t+(e?'.'+e:'')}
function esc(s){return (s+'').replace(/&/g,'&amp;').replace(/</g,'&lt;')}
function rr(){var t=S.rrBase+S.rrCity+focus+event;return t/(100+t)}
function badgeFor(m){if(m>=.5)return[5,'賺爛'];if(m>=.3)return[4,'不錯'];if(m>=.15)return[3,'普通'];if(m>=0)return[2,'微利'];return[1,'虧損']}
function iid(t,base,e){return e==0?'T'+t+'_'+base:'T'+t+'_'+base+'_LEVEL'+e+'@'+e}
function ival(t,e){return S.itemValue[t]*Math.pow(2,e)}
function lowerE(t,e){return (t-1)>=4?e:0}
function priceFor(id,cities,low){var pd=PRICES[id];if(!pd)return null;
 for(var pass=0;pass<2;pass++){var best=null;  // pass0=7天均價; pass1=回退即時現價
  for(var i=0;i<cities.length;i++){var d=pd[cities[i]];if(!d)continue;
   var p=pass==0?d[0]:d[2];if(p==null)continue;
   if(best==null||(low?p<best.p:p>best.p))best={p:p,city:cities[i],basis:pass==0?'avg':'現'};}
  if(best)return best;}
 return null}
function effRaw(line,t,e,buyC,memo){var k=t+','+e;if(k in memo)return memo[k];memo[k]=null;var cd=[];
 var mk=priceFor(iid(t,line.raw,e),buyC,true);
 if(mk)cd.push({p:mk.p,src:(mk.basis=='avg'?'買':'現')+ctag(mk.city)+'·'+lblTE(t,e)});
 if(S.useTransmute&&S.transmuteExclude.indexOf(line.raw)<0){
  var s1=S.transmute.enchant[t+','+e];
  if(s1!=null&&e>=1){var lo=effRaw(line,t,e-1,buyC,memo);if(lo)cd.push({p:lo.p+s1,src:'轉附['+lo.src+']'});}
  var s2=S.transmute.tier[t+','+e];
  if(s2!=null){var l2=effRaw(line,t-1,e,buyC,memo);if(l2)cd.push({p:l2.p+s2,src:'轉階['+l2.src+']'});}}
 var r=null;for(var i=0;i<cd.length;i++)if(r==null||cd[i].p<r.p)r=cd[i];memo[k]=r;return r}
function buyCities(){var v=document.getElementById('buyCity').value;return v=='ALL'?S.cities:[v]}
function sellCities(){var v=document.getElementById('sellCity').value;return v=='ALL'?S.cities:[v]}
function recompute(){var R=rr();document.getElementById('rrv').textContent=R.toFixed(4);
 var buyC=buyCities(),sellC=sellCities();
 rows.forEach(function(tr){var line=lineMap[tr.dataset.line];var t=+tr.dataset.t,e=+tr.dataset.e;var memo={};
  var raw=effRaw(line,t,e,buyC,memo);
  var out=priceFor(iid(t,line.refined,e),sellC,false);
  if(!raw||!out){tr.dataset.ok='0';tr.style.display='none';return;}
  tr.dataset.ok='1';var n=S.rawPerTier[t];
  var lower=t>2?priceFor(iid(t-1,line.refined,lowerE(t,e)),buyC,true):null;
  var lp=lower?lower.p:0,lfb=!!(lower&&lower.basis=='現');
  var fu=raw.p,heartUsed=false;
  if(e>=1&&e<=S.heartMax&&S.useHeart&&line.heart){var hp=priceFor(line.heart,buyC,true);if(hp&&hp.p<raw.p){fu=hp.p;heartUsed=true;}}
  var mbase=lp+fu+raw.p*(n-1);
  var cost=mbase*(1-R)*(1+S.bf)+0.1125*ival(t,e)*(S.stationFee/100);
  var profit=out.p*(1-S.sf)-cost,m=cost?profit/cost:0;
  var sd=PRICES[iid(t,line.refined,e)];var vol=(sd&&sd[out.city])?sd[out.city][1]:null;
  var thin=vol!=null&&vol<S.lowVol;
  var lo=null,hi=null;for(var i=0;i<sellC.length;i++){var dd=sd&&sd[sellC[i]];if(dd&&dd[2]!=null){if(lo==null||dd[2]<lo)lo=dd[2];if(hi==null||dd[2]>hi)hi=dd[2];}}
  var dev='';if(hi!=null){if(out.p>hi*(1+S.dev))dev='偏高';else if(out.p<lo*(1-S.dev))dev='偏低';}
  var d=tr.dataset;d.margin=m.toFixed(4);d.loss=m<0?'1':'0';d.thin=thin?'1':'0';d.dev=dev?'1':'0';
  tr.cells[2].textContent=fmt(raw.p);tr.cells[3].textContent=fmt(out.p);
  tr.cells[4].textContent=vol!=null?fmt(vol):'—';tr.cells[5].textContent=fmt(lp);
  tr.querySelector('.cost').textContent=fmt(cost);tr.querySelector('.profit').textContent=fmt(profit);
  var mc=tr.querySelector('.margin');mc.textContent=(m*100).toFixed(1)+'%';mc.dataset.v=m.toFixed(4);
  var b=badgeFor(m);tr.className='s'+b[0]+(thin?' thin':'');
  var bd=tr.querySelector('.badge');bd.textContent=b[1];bd.className='badge b'+b[0];
  var tg='';
  if(heartUsed)tg+=' <span class="tag heart">♥'+esc(line.heartName)+'</span>';
  if(thin)tg+=' <span class="tag warn">⚠量少 '+vol+'</span>';
  if(dev)tg+=' <span class="tag dev">'+(dev=='偏高'?'↑':'↓')+dev+'現價 '+fmt(lo)+'~'+fmt(hi)+'</span>';
  var fl=[];if(out.basis=='現')fl.push('成品');if(lfb)fl.push('下階');
  if(fl.length)tg+=' <span class="tag fill">↺回填現價 '+fl.join('/')+'</span>';
  tr.querySelector('.src').innerHTML=esc(raw.src)+'→'+(out.basis=='avg'?'賣':'現賣')+esc(ctag(out.city))+tg;
  tr.style.display='';});
 cards();resort();apply();}
function cards(){var tot=0,good=0,thin=0,dev=0,best=null;rows.forEach(function(r){if(r.dataset.ok==='0')return;tot++;
  var m=+r.dataset.margin,th=r.dataset.thin==='1';if(m>=.3&&!th)good++;if(th)thin++;if(r.dataset.dev==='1')dev++;
  if(!th&&m>0&&(!best||m>+best.dataset.margin))best=r;});
 document.getElementById('cTot').textContent=tot;document.getElementById('cGood').textContent=good;
 document.getElementById('cThin').textContent=thin;document.getElementById('cDev').textContent=dev;
 var bc=document.getElementById('cBest');
 bc.innerHTML=best?esc(best.cells[0].textContent.split(' ')[0]+' '+best.cells[1].textContent)+'<span class="bm">'+Math.round(+best.dataset.margin*100)+'%</span>':'—';}
function resort(){rows.sort(function(a,b){return (+b.dataset.margin)-(+a.dataset.margin)});rows.forEach(function(r){tb.appendChild(r)});}
document.querySelectorAll('th[data-c]').forEach(function(th){var asc=false;
 th.onclick=function(){asc=!asc;var c=+th.dataset.c;
  rows.sort(function(a,b){var x=a.cells[c],y=b.cells[c];
   var xv=x.dataset.v!==undefined?num(x.dataset.v):(x.classList.contains('num')?num(x.textContent):x.textContent);
   var yv=y.dataset.v!==undefined?num(y.dataset.v):(y.classList.contains('num')?num(y.textContent):y.textContent);
   if(xv<yv)return asc?-1:1;if(xv>yv)return asc?1:-1;return 0});
  rows.forEach(function(r){tb.appendChild(r)})}});
var curLine="",hideLoss=false,hideThin=false,q="";
function apply(){rows.forEach(function(r){
 var ok=r.dataset.ok!=='0'&&(!curLine||r.dataset.line===curLine)&&(!hideLoss||r.dataset.loss==="0")&&(!hideThin||r.dataset.thin==="0");
 if(ok&&q){ok=r.textContent.toLowerCase().indexOf(q)>=0}
 r.style.display=ok?"":"none"})}
document.querySelectorAll('.lf').forEach(function(b){b.onclick=function(){
 document.querySelectorAll('.lf').forEach(function(x){x.classList.remove('active')});
 b.classList.add('active');curLine=b.dataset.l;apply()}});
document.getElementById('hideLoss').onchange=function(e){hideLoss=e.target.checked;apply()};
document.getElementById('hideThin').onchange=function(e){hideThin=e.target.checked;apply()};
document.getElementById('q').oninput=function(e){q=e.target.value.toLowerCase();apply()};
document.getElementById('focus').onchange=function(e){focus=e.target.checked?59:0;recompute()};
document.getElementById('event').onchange=function(e){event=+e.target.value;recompute()};
document.getElementById('buyCity').onchange=recompute;
document.getElementById('sellCity').onchange=recompute;
recompute();
</script>
"""
    allc = meta["struct"]["cities"]
    cc = meta["struct"]["cityColor"]

    def _copts(sel):
        cur = sel[0] if (sel and len(sel) == 1 and sel[0] in allc) else "ALL"
        o = '<option value="ALL"' + (" selected" if cur == "ALL" else "") + ">全部</option>"
        for c in allc:
            lab = f"{c}（{cc[c]}城）" if cc.get(c) else c
            o += f'<option value="{_h.escape(c)}"' + (" selected" if cur == c else "") + f">{_h.escape(lab)}</option>"
        return o

    def _cclist(cs):
        return "、".join(f"{c}({cc[c]})" if cc.get(c) else c for c in cs)

    buy_opts, sell_opts = _copts(meta["buy_cities"]), _copts(meta["sell_cities"])
    prices_json = json.dumps(meta["pdata"], ensure_ascii=False, separators=(",", ":"))
    struct_json = json.dumps(meta["struct"], ensure_ascii=False, separators=(",", ":"))

    out = (tpl
           .replace("__SERVER__", _h.escape(meta["server"]))
           .replace("__BUYCITIES__", _h.escape(_cclist(meta["buy_cities"])))
           .replace("__SELLCITIES__", _h.escape(_cclist(meta["sell_cities"])))
           .replace("__BASIS__", meta["basis"])
           .replace("__TIME__", meta["time"])
           .replace("__SF__", f"{meta['sf']:.1%}")
           .replace("__LOWVOL__", str(meta["low_vol"]))
           .replace("__N__", str(len(rows))).replace("__NGOOD__", str(n_good)).replace("__NTHIN__", str(n_thin))
           .replace("__NDEV__", str(n_dev))
           .replace("__BEST__", best_txt)
           .replace("__RR0__", f"{rr0:.4f}")
           .replace("__EVOPTS__", ev_opts)
           .replace("__FOCUSCHK__", " checked" if meta["focus0"] else "")
           .replace("__FOCUS0__", str(meta["focus0"])).replace("__EVENT0__", str(meta["event0"]))
           .replace("__BUYOPTS__", buy_opts).replace("__SELLOPTS__", sell_opts)
           .replace("__LINEBTNS__", line_btns)
           .replace("__BODY__", "".join(body))
           .replace("__PRICES__", prices_json).replace("__STRUCT__", struct_json))
    with open(path, "w", encoding="utf-8") as f:
        f.write(out)


if __name__ == "__main__":
    compute()
