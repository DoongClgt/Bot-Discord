"""tiktok_api.py - Goi API tikwm de lay link TikTok/Douyin khong logo.

Thuan urllib, khong phu thuoc discord/flask. Dung chung boi:
- downloader.py (bot: gui thang vao kenh Discord)
- web.py (dashboard: tai ve may qua trinh duyet)
"""
import json as _json
import re
import time
import unicodedata
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


def find_url(text):
    """Tra ve link TikTok/Douyin dau tien trong text, hoac None."""
    match = URL_PATTERN.search(text or "")
    return match.group(0) if match else None


def http_get(url, timeout=45):
    req = urllib.request.Request(url, headers=HTTP_HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def expand_url(url, timeout=15):
    """Gian link rut gon (vt./vm.tiktok.com, v.douyin.com...) thanh link goc bang cach follow redirect."""
    for method in ("HEAD", "GET"):
        try:
            req = urllib.request.Request(url, headers=HTTP_HEADERS, method=method)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                final = resp.geturl()
                if final and final != url:
                    return final
        except Exception:
            continue
    return url


def _call_tikwm(source_url, timeout=45):
    api_url = TIKWM_API + "?" + urllib.parse.urlencode({"url": source_url, "hd": "1"})
    raw = http_get(api_url, timeout=timeout)
    return _json.loads(raw.decode("utf-8", "replace"))


def _is_douyin(url):
    return "douyin.com" in (url or "").lower()


def _aweme_id(url):
    """Rut aweme_id (video id) tu URL Douyin/TikTok."""
    for pat in (r'/video/(\d+)', r'/note/(\d+)', r'/share/video/(\d+)', r'item_ids=(\d+)', r'(\d{15,})'):
        m = re.search(pat, url or "")
        if m:
            return m.group(1)
    return None


def fetch_douyin_native(source_url):
    """Parse thang tu trang share Douyin khi tikwm bo tay.

    Douyin web API doi chu ky a_bogus (kho), nhung trang share nhung san JSON `_ROUTER_DATA`.
    Link video la ban co logo (playwm) -> doi 'playwm'->'play' de ra ban khong logo.
    Tra ve dict cung dang voi data cua tikwm de extract_media dung chung.
    """
    aweme_id = _aweme_id(source_url) or _aweme_id(expand_url(source_url))
    if not aweme_id:
        raise RuntimeError("Khong tim thay ID video Douyin trong link.")
    page_url = "https://www.iesdouyin.com/share/video/%s/" % aweme_id
    req = urllib.request.Request(page_url, headers={"User-Agent": DOUYIN_MOBILE_UA})
    with urllib.request.urlopen(req, timeout=25) as resp:
        html = resp.read().decode("utf-8", "replace")
    m = re.search(r'window\._ROUTER_DATA\s*=\s*(\{.*?\})\s*</script>', html, re.S)
    if not m:
        raise RuntimeError("Douyin khong tra ve du lieu (video co the bi khoa vung hoac can dang nhap).")
    loader = (_json.loads(m.group(1)).get("loaderData") or {})
    item = None
    for value in loader.values():
        if isinstance(value, dict):
            items = (value.get("videoInfoRes") or {}).get("item_list") or []
            if items:
                item = items[0]
                break
    if not item:
        raise RuntimeError("Douyin khong co du lieu video cho link nay.")

    video = item.get("video") or {}
    images = [im["url_list"][0] for im in (item.get("images") or []) if im.get("url_list")]
    play_urls = (video.get("play_addr") or {}).get("url_list") or []
    wm = play_urls[0] if play_urls else None
    nowm = wm.replace("playwm", "play") if wm else None
    cover_urls = ((video.get("cover") or video.get("origin_cover") or {}).get("url_list")) or []
    duration_ms = video.get("duration") or 0
    return {
        "id": item.get("aweme_id") or aweme_id,
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

    Tu dong: (1) retry khi dinh rate limit (free API tikwm = 1 req/s),
    (2) gian link rut gon roi thu lai neu tikwm khong parse duoc URL,
    (3) neu la link Douyin ma tikwm van bo tay -> parse thang tu trang share Douyin.
    """
    payload = _call_tikwm(source_url)

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

    # (3) tikwm bo tay -> Douyin thi parse truc tiep
    if _is_douyin(source_url) or _is_douyin(expanded):
        return fetch_douyin_native(expanded if _is_douyin(expanded) else source_url)

    raise RuntimeError(payload.get("msg") or "API tikwm tra ve loi.")


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
