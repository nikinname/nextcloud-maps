from dataclasses import dataclass
from email.utils import parsedate_to_datetime
from pathlib import PurePosixPath
from urllib.parse import quote, unquote, urljoin
from xml.etree import ElementTree

import httpx

from app.config import Settings


DAV_NS = {"d": "DAV:", "nc": "http://nextcloud.org/ns", "oc": "http://owncloud.org/ns"}


@dataclass(frozen=True)
class NextcloudFile:
    path: str
    filename: str
    href: str
    etag: str | None
    mime_type: str | None
    size_bytes: int | None
    last_modified: object | None
    file_id: str | None
    is_collection: bool


class NextcloudClient:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.base_url = str(settings.nextcloud_url).rstrip("/")
        self.auth = (settings.nextcloud_username, settings.nextcloud_app_password)

    def _dav_url(self, path: str) -> str:
        normalized = "/" + path.strip("/")
        quoted_path = quote(normalized, safe="/")
        return f"{self.base_url}/remote.php/dav/files/{quote(self.settings.nextcloud_username)}/{quoted_path}"

    def web_url(self, path: str, file_id: str | None = None) -> str:
        directory = quote(str(PurePosixPath(path).parent), safe="/")
        if file_id:
            return f"{self.base_url}/apps/files/files/{quote(file_id)}?dir={directory}&editing=false&openfile=true"
        return f"{self.base_url}/apps/files/files?dir={directory}"

    def list_recursive(self, root_path: str) -> list[NextcloudFile]:
        body = """<?xml version="1.0"?>
<d:propfind xmlns:d="DAV:" xmlns:nc="http://nextcloud.org/ns" xmlns:oc="http://owncloud.org/ns">
  <d:prop>
    <d:getetag />
    <d:getcontenttype />
    <d:getcontentlength />
    <d:getlastmodified />
    <d:resourcetype />
    <nc:fileid />
    <oc:fileid />
  </d:prop>
</d:propfind>"""
        response = httpx.request(
            "PROPFIND",
            self._dav_url(root_path),
            content=body,
            headers={"Depth": "infinity"},
            auth=self.auth,
            timeout=120,
        )
        response.raise_for_status()
        return self._parse_propfind(response.text)

    def download(self, path: str) -> bytes:
        response = httpx.get(self._dav_url(path), auth=self.auth, timeout=120)
        response.raise_for_status()
        return response.content

    def _parse_propfind(self, xml_text: str) -> list[NextcloudFile]:
        root = ElementTree.fromstring(xml_text)
        files: list[NextcloudFile] = []
        dav_prefix = f"/remote.php/dav/files/{self.settings.nextcloud_username}"
        for response in root.findall("d:response", DAV_NS):
            href = response.findtext("d:href", default="", namespaces=DAV_NS)
            prop = response.find("d:propstat/d:prop", DAV_NS)
            if prop is None:
                continue

            resource_type = prop.find("d:resourcetype", DAV_NS)
            is_collection = resource_type is not None and resource_type.find("d:collection", DAV_NS) is not None
            decoded_path = unquote(httpx.URL(urljoin(self.base_url, href)).path)
            path = decoded_path.removeprefix(dav_prefix)
            path = "/" + path.strip("/")
            if is_collection:
                filename = PurePosixPath(path).name
            else:
                filename = PurePosixPath(path).name

            content_length = prop.findtext("d:getcontentlength", namespaces=DAV_NS)
            last_modified = prop.findtext("d:getlastmodified", namespaces=DAV_NS)
            file_id = prop.findtext("nc:fileid", namespaces=DAV_NS) or prop.findtext("oc:fileid", namespaces=DAV_NS)
            files.append(
                NextcloudFile(
                    path=path,
                    filename=filename,
                    href=href,
                    etag=prop.findtext("d:getetag", namespaces=DAV_NS),
                    mime_type=prop.findtext("d:getcontenttype", namespaces=DAV_NS),
                    size_bytes=int(content_length) if content_length else None,
                    last_modified=parsedate_to_datetime(last_modified) if last_modified else None,
                    file_id=file_id,
                    is_collection=is_collection,
                )
            )
        return files
