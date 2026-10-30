"""tiktok_api.py - Goi API tikwm de lay link TikTok/Douyin khong logo.

Thuan urllib, khong phu thuoc discord/flask. Dung boi web.py
(dashboard: tai ve may qua trinh duyet).

Debug:  python tiktok_api.py https://v.douyin.com/xxxx
"""
import json as _json
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request

TIKWM_API = "https://www.tikwm.com/api/"

# Nhan link TikTok (tiktok.com, vt./vm.tiktok.com) va Douyin (douyin.com, iesdouyin.com, douyinvod.com)
URL_PATTERN = re.compile(
    r'https?://[^\s<>]*(?:tiktok\.com|douyin\.com|iesdouyin\.com|douyinvod\.com)[^\s<>]*',
    re.I,
)

MAX_SLIDES = 10
HTTP_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0 Safari/537.36",
}
# tikwm khong parse duoc Douyin -> parse thang tu trang share, can UA mobile de co _ROUTER_DATA
DOUYIN_MOBILE_UA = (
    "Mozilla/5.0 (Linux; Android 12; Pixel 5) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Mobile Safari/537.36"
)
DOUYIN_PAGE_HEADERS = {
    "User-Agent": DOUYIN_MOBILE_UA,
    "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Referer": "https://www.douyin.com/",
}
# Cac host trang share Douyin, thu lan luot
DOUYIN_SHARE_PAGES = (
    "https://www.iesdouyin.com/share/video/%s/",
    "https://www.iesdouyin.com/share/video/%s",
    "https://www.douyin.com/share/video/%s",
)

DEBUG = False


def _log(*args):
    if DEBUG:
        print("[tiktok_api]", *args, file=sys.stderr)


def find_url(text):
    """Tra ve link TikTok/Douyin dau tien trong text, hoac None."""
    match = URL_PATTERN.search(text or "")
    return match.group(0) if match else None


def _media_headers(url):
    """Header cho request toi CDN. Douyin CDN doi Referer, neu khong co the 403."""
    h = dict(HTTP_HEADERS)
    if "douyin" in (url or "").lower() or "snssdk" in (url or "").lower():
        h["Referer"] = "https://www.douyin.com/"
    return h


def http_get(url, timeout=45):
    req = urllib.request.Request(url, headers=_media_headers(url))
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def http_open(url, timeout=45):
    """Mo ket noi va tra ve response file-like de stream theo chunk (caller phai close).

    Dung cho proxy download tren dashboard: tranh doc ca video (co the >100MB) vao RAM.
    resp.headers co the doc Content-Length de forward cho client.
    """
    req = urllib.request.Request(url, headers=_media_headers(url))
    return urllib.request.urlopen(req, timeout=timeout)


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """Khong follow redirect: ta chi can header Location, khong can tai trang dich
    (www.douyin.com hay chan bot -> 403 -> truoc day lam hong ca buoc gian link)."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


_no_redirect_opener = urllib.request.build_opener(_NoRedirect)


def expand_url(url, timeout=15):
    """Gian link rut gon (vt./vm.tiktok.com, v.douyin.com...) thanh link goc.

    Doc thang header Location cua redirect dau tien, khong tai trang dich.
    Thu ca UA desktop lan mobile, HEAD lan GET.
    """
    for ua in (HTTP_HEADERS["User-Agent"], DOUYIN_MOBILE_UA):
        for method in ("HEAD", "GET"):
            try:
                req = urllib.request.Request(url, headers={"User-Agent": ua}, method=method)
                try:
                    resp = _no_redirect_opener.open(req, timeout=timeout)
                    final = resp.geturl()
                    resp.close()
                except urllib.error.HTTPError as e:
                    # 301/302/307/308 -> lay Location
                    loc = e.headers.get("Location") if e.headers else None
                    if e.code in (301, 302, 303, 307, 308) and loc:
                        final = urllib.parse.urljoin(url, loc)
                    else:
                        raise
                if final and final != url:
                    _log("expand:", url, "->", final)
                    return final
            except Exception as e:
                _log("expand fail", method, ua[:20], e)
                continue
    return url


def _call_tikwm(source_url, timeout=45):
    api_url = TIKWM_API + "?" + urllib.parse.urlencode({"url": source_url, "hd": "1"})
    raw = http_get(api_url, timeout=timeout)
    return _json.loads(raw.decode("utf-8", "replace"))


def _is_douyin(url):
    u = (url or "").lower()
    return "douyin.com" in u or "iesdouyin.com" in u


def _aweme_id(url):
    """Rut aweme_id (video id) tu URL Douyin/TikTok."""
    for pat in (r'/video/(\d+)', r'/note/(\d+)', r'/share/video/(\d+)', r'/slides/(\d+)',
                r'item_ids=(\d+)', r'modal_id=(\d+)', r'(\d{15,})'):
        m = re.search(pat, url or "")
        if m:
            return m.group(1)
    return None


def _probe(url, timeout=12):
    """Kiem tra link media co tai duoc that khong (GET 1 byte dau). True neu OK."""
    if not url:
        return False
    try:
        h = _media_headers(url)
        h["Range"] = "bytes=0-0"
        req = urllib.request.Request(url, headers=h)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            ctype = (resp.headers.get("Content-Type") or "").lower()
            ok = resp.status in (200, 206) and not ctype.startswith("text/html")
            _log("probe", resp.status, ctype, url[:90], "->", ok)
            return ok
    except Exception as e:
        _log("probe fail", url[:90], e)
        return False


def _douyin_play_candidates(wm_url):
    """Danh sach link play khong logo, uu tien chat luong cao -> thap.

    Trang share tra ve URL playwm (co logo, 720p). Douyin co nhieu endpoint 'play'
    khong logo; endpoint nao song thi thay doi theo thoi gian nen thu lan luot:
      1. aweme.snssdk.com ... ratio=4k  (Douyin tu cap ve muc that cua video)
      2. www.douyin.com/aweme/v1/play ... ratio=1080p
      3. URL goc doi 'playwm' -> 'play'
    """
    if not wm_url:
        return []
    out = []
    video_id = dict(urllib.parse.parse_qsl(urllib.parse.urlparse(wm_url).query)).get("video_id")
    if video_id:
        q = urllib.parse.quote(video_id, safe="")
        out.append("https://aweme.snssdk.com/aweme/v1/play/?video_id=%s&ratio=4k" % q)
        out.append("https://www.douyin.com/aweme/v1/play/?video_id=%s&ratio=1080p&line=0" % q)
        out.append("https://www.iesdouyin.com/aweme/v1/play/?video_id=%s&ratio=1080p&line=0" % q)
    if "playwm" in wm_url:
        out.append(wm_url.replace("playwm", "play"))
    # bo trung, giu thu tu
    seen, uniq = set(), []
    for u in out:
        if u not in seen:
            seen.add(u)
            uniq.append(u)
    return uniq


def _douyin_hd_url(wm_url, all_play_urls=None):
    """Chon link play khong logo dau tien thuc su tai duoc. Fallback: link co logo."""
    for cand in _douyin_play_candidates(wm_url):
        if _probe(cand):
            return cand
    # cac URL play_addr khac (CDN khac nhau) doi playwm->play
    for u in all_play_urls or []:
        if u != wm_url and "playwm" in u:
            c = u.replace("playwm", "play")
            if _probe(c):
                return c
    _log("khong co link khong logo nao song, dung ban co logo")
    return wm_url


def _fetch_share_html(aweme_id):
    last_err = None
    for tpl in DOUYIN_SHARE_PAGES:
        page_url = tpl % aweme_id
        try:
            req = urllib.request.Request(page_url, headers=DOUYIN_PAGE_HEADERS)
            with urllib.request.urlopen(req, timeout=25) as resp:
                html = resp.read().decode("utf-8", "replace")
            _log("share page", page_url, "len", len(html), "status", resp.status)
            if "_ROUTER_DATA" in html or "RENDER_DATA" in html:
                return html
            last_err = RuntimeError("Trang share khong co du lieu (%s)" % page_url)
        except Exception as e:
            _log("share page fail", page_url, e)
            last_err = e
    raise RuntimeError("Khong tai duoc trang share Douyin: %s" % last_err)


def _parse_router_data(html):
    m = re.search(r'window\._ROUTER_DATA\s*=\s*(\{.*?\})\s*;?\s*</script>', html, re.S)
    if not m:
        return None
    try:
        return _json.loads(m.group(1))
    except ValueError:
        # fallback greedy neu JSON co chua '</script>' trong string
        m2 = re.search(r'window\._ROUTER_DATA\s*=\s*(\{.*\})\s*;?\s*</script>', html, re.S)
        if m2:
            try:
                return _json.loads(m2.group(1))
            except ValueError:
                return None
    return None


def _parse_render_data(html):
    """Trang www.douyin.com (desktop) nhung RENDER_DATA dang URL-encoded JSON."""
    m = re.search(r'<script id="RENDER_DATA" type="application/json">(.*?)</script>', html, re.S)
    if not m:
        return None
    try:
        return _json.loads(urllib.parse.unquote(m.group(1)))
    except ValueError:
        return None


def _find_item(obj, aweme_id, depth=0):
    """Tim dict co aweme_id (hoac awemeId) khop trong JSON long nhau."""
    if depth > 12:
        return None
    if isinstance(obj, dict):
        aid = str(obj.get("aweme_id") or obj.get("awemeId") or "")
        if aid == str(aweme_id) and (obj.get("video") or obj.get("images")):
            return obj
        for v in obj.values():
            r = _find_item(v, aweme_id, depth + 1)
            if r:
                return r
    elif isinstance(obj, list):
        for v in obj:
            r = _find_item(v, aweme_id, depth + 1)
            if r:
                return r
    return None


def fetch_douyin_native(source_url):
    """Parse thang tu trang share Douyin khi tikwm bo tay.

    Douyin web API doi chu ky a_bogus (kho), nhung trang share nhung san JSON `_ROUTER_DATA`.
    Link video la ban co logo (playwm) -> thu cac endpoint 'play' de ra ban khong logo.
    Tra ve dict cung dang voi data cua tikwm de extract_media dung chung.
    """
    aweme_id = _aweme_id(source_url)
    if not aweme_id:
        expanded = expand_url(source_url)
        aweme_id = _aweme_id(expanded)
    if not aweme_id:
        raise RuntimeError("Khong tim thay ID video Douyin trong link (khong gian duoc link rut gon).")
    _log("aweme_id", aweme_id)

    html = _fetch_share_html(aweme_id)
    data = _parse_router_data(html) or _parse_render_data(html)
    if not data:
        raise RuntimeError("Douyin khong tra ve du lieu (video co the bi khoa vung hoac can dang nhap).")

    item = None
    loader = data.get("loaderData") or {}
    for value in loader.values():
        if isinstance(value, dict):
            vres = value.get("videoInfoRes") or {}
            items = vres.get("item_list") or []
            if items:
                item = items[0]
                break
            # Douyin tra ly do khong co video (xoa, rieng tu...)
            for f in vres.get("filter_list") or []:
                reason = f.get("filter_reason") or f.get("notice")
                if reason:
                    raise RuntimeError("Douyin: %s" % reason)
    if not item:
        item = _find_item(data, aweme_id)
    if not item:
        raise RuntimeError("Douyin khong co du lieu video cho link nay (video bi xoa/rieng tu?).")

    video = item.get("video") or {}
    images = []
    for im in item.get("images") or []:
        urls = im.get("url_list") or im.get("urlList") or []
        if urls:
            images.append(urls[0])
    play_addr = video.get("play_addr") or video.get("playAddr") or {}
    play_urls = play_addr.get("url_list") or play_addr.get("urlList") or []
    wm = play_urls[0] if play_urls else None
    nowm = _douyin_hd_url(wm, play_urls) if (wm and not images) else wm
    cover = video.get("cover") or video.get("origin_cover") or video.get("originCover") or {}
    cover_urls = cover.get("url_list") or cover.get("urlList") or []
    duration_ms = video.get("duration") or 0
    return {
        "id": str(item.get("aweme_id") or item.get("awemeId") or aweme_id),
        "title": (item.get("desc") or "").strip(),
        "author": {"nickname": (item.get("author") or {}).get("nickname") or ""},
        "images": images,
        "play": nowm,
        "hdplay": nowm,
        "wmplay": wm,
        "cover": cover_urls[0] if cover_urls else "",
        "duration": int(duration_ms // 1000) if duration_ms else 0,
    }


def fetch_media_info(source_url):
    """Lay thong tin media, tra ve dict data (dang tikwm) hoac raise RuntimeError.

    Douyin: parse thang tu trang share truoc (tikwm hau nhu khong xu ly duoc Douyin),
    neu hong moi thu tikwm. TikTok: tikwm, co retry rate-limit va gian link rut gon.
    """
    douyin_err = None
    if _is_douyin(source_url):
        try:
            return fetch_douyin_native(source_url)
        except Exception as e:
            douyin_err = e
            _log("douyin native fail:", e)

    try:
        payload = _call_tikwm(source_url)
    except Exception as e:
        if douyin_err:
            raise RuntimeError("Douyin: %s | tikwm: %s" % (douyin_err, e))
        raise

    # (1) Rate limit -> cho hon 1s roi thu lai 1 lan
    if payload.get("code") != 0 and "limit" in str(payload.get("msg", "")).lower():
        time.sleep(1.2)
        payload = _call_tikwm(source_url)

    # (2) tikwm khong parse duoc -> tu follow redirect roi thu lai bang link goc
    expanded = source_url
    if payload.get("code") != 0:
        expanded = expand_url(source_url)
        if expanded != source_url:
            retry = _call_tikwm(expanded)
            if retry.get("code") != 0 and "limit" in str(retry.get("msg", "")).lower():
                time.sleep(1.2)
                retry = _call_tikwm(expanded)
            payload = retry

    if payload.get("code") == 0 and (payload.get("data") or {}):
        return payload["data"]

    # (3) link rut gon hoa ra la Douyin (vd. redirect) -> parse truc tiep
    if not douyin_err and _is_douyin(expanded):
        return fetch_douyin_native(expanded)

    msg = payload.get("msg") or "API tikwm tra ve loi."
    if douyin_err:
        raise RuntimeError("Douyin: %s | tikwm: %s" % (douyin_err, msg))
    raise RuntimeError(msg)


def pick_video_url(data):
    """Uu tien link HD -> khong logo -> co logo."""
    return data.get("hdplay") or data.get("play") or data.get("wmplay")


def safe_filename_base(media, source_url="", max_len=60):
    """Tao ten file goi (chua co duoi) tu tieu de clip + video id.

    Bo dau tieng Viet + moi ky tu non-ASCII (emoji, chu Han...) de tranh loi ten
    file/encoding tren proxy/OS. Cac tu ngan cach bang "_". Gan id lam hau to.
    Vi du: "Replying_to_user_7438266140897430817". Douyin/chu Han -> chi con id.
    """
    raw = (media.get("title") or media.get("author") or "")
    raw = raw.replace("đ", "d").replace("Đ", "D")  # đ/Đ khong tach dau qua NFKD
    ascii_str = unicodedata.normalize("NFKD", raw).encode("ascii", "ignore").decode("ascii")
    base = re.sub(r"[^A-Za-z0-9]+", "_", ascii_str).strip("_")
    if len(base) > max_len:
        base = base[:max_len].strip("_")
    vid = str(media.get("id") or "").strip() or _aweme_id(source_url)
    if vid:
        base = f"{base}_{vid}" if base else vid
    return base or "tiktok"


def extract_media(data):
    """Chuan hoa data tikwm ve dict gon cho ca bot lan dashboard."""
    images = (data.get("images") or [])[:MAX_SLIDES]
    return {
        "id": str(data.get("id") or "").strip(),
        "title": (data.get("title") or "").strip(),
        "author": ((data.get("author") or {}).get("nickname") or "").strip(),
        "cover": data.get("cover") or data.get("origin_cover") or "",
        "images": images,
        "is_slideshow": bool(images),
        "video_url": None if images else pick_video_url(data),
        "duration": data.get("duration") or 0,
    }


if __name__ == "__main__":
    # Debug: python tiktok_api.py <link>
    DEBUG = True
    link = find_url(" ".join(sys.argv[1:]))
    if not link:
        print("Dung: python tiktok_api.py <link tiktok/douyin>")
        sys.exit(1)
    try:
        info = extract_media(fetch_media_info(link))
        print(_json.dumps(info, ensure_ascii=False, indent=2))
    except Exception as e:
        print("LOI:", e)
        sys.exit(2)
