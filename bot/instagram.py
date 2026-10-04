from __future__ import annotations

import time

import requests

from . import config


class InstagramError(RuntimeError):
    pass


def _url(path: str) -> str:
    return f"https://{config.IG_GRAPH_HOST}/{config.IG_API_VERSION}/{path}"


def _call(method: str, path: str, **params) -> dict:
    params["access_token"] = config.IG_ACCESS_TOKEN
    resp = requests.request(method, _url(path), data=params if method == "POST" else None,
                            params=params if method == "GET" else None, timeout=60)
    data = resp.json()
    if resp.status_code != 200 or "error" in data:
        raise InstagramError(f"{method} {path} 실패 ({resp.status_code}): {data.get('error', data)}")
    return data


def _wait_ready(container_id: str, timeout: int = 300) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        status = _call("GET", container_id, fields="status_code").get("status_code")
        if status == "FINISHED":
            return
        if status in ("ERROR", "EXPIRED"):
            raise InstagramError(f"미디어 컨테이너 {container_id} 상태: {status}")
        time.sleep(5)
    raise InstagramError(f"미디어 컨테이너 {container_id} 처리 시간 초과")


def publish_carousel(image_urls: list[str], caption: str) -> str:
    if not config.IG_USER_ID or not config.IG_ACCESS_TOKEN:
        raise InstagramError("IG_USER_ID / IG_ACCESS_TOKEN 환경변수가 없습니다")
    user = config.IG_USER_ID
    children = []
    for url in image_urls:
        item = _call("POST", f"{user}/media", image_url=url, is_carousel_item="true")
        children.append(item["id"])
    for child in children:
        _wait_ready(child)
    carousel = _call("POST", f"{user}/media", media_type="CAROUSEL",
                     children=",".join(children), caption=caption)
    _wait_ready(carousel["id"])
    published = _call("POST", f"{user}/media_publish", creation_id=carousel["id"])
    return published["id"]
