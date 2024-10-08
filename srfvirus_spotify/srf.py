import requests
import time
import datetime
import logging
from requests.auth import HTTPBasicAuth
from typing import List, Dict, Any, Optional

from .env import Env
from .cache_handler import TokenCacheFileHandler
from .errors import SRFHTTPException
from .storage_handler import SongsStorageFileHandler, SongsMetadataFileHandler
from .song import Song
from .spotify import search_title


logger = logging.getLogger(__name__)


SRF_BASE_URL = "https://api.srgssr.ch"
SRF_OAUTH_BASE_URL = f"{SRF_BASE_URL}/oauth/v1"
SRF_AUDIO_BASE_URL = f"{SRF_BASE_URL}/audiometadata/v2"
WAIT_UNTIL_NEXT_SEARCH = 1  # seconds


class _SRFClient:

    def __init__(
        self,
        *,
        client_id: str,
        client_secret: str,
        cache_handler: TokenCacheFileHandler,
    ):
        self.client_id: str = client_id
        self.client_secret: str = client_secret
        self.cache_handler: TokenCacheFileHandler = cache_handler

        self.__token: str = self._get_token()

    def _request_token(self) -> Dict[str, Any]:
        response = requests.post(
            f"{SRF_OAUTH_BASE_URL}/accesstoken?grant_type=client_credentials",
            auth=HTTPBasicAuth(self.client_id, self.client_secret),
        )

        data = response.json()
        if 300 > response.status_code >= 200:
            return data
        else:
            raise SRFHTTPException(response=response, data=data)

    def _get_token(self) -> str:
        token_info = self.cache_handler.get_cached_token()
        if not token_info:
            token_info = self._request_token()
            self._save_token_info(token_info)

        return token_info["access_token"]

    def _save_token_info(self, token_info: Dict[str, Any]) -> None:
        # add expire time to token info
        now = int(time.time())
        expires_at = now + token_info["expires_in"]
        token_info["expires_at"] = expires_at

        self.cache_handler.save_token_to_cache(token_info)

    def _request(
        self,
        method: str,
        url: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        payload: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        # check if new token must be requested
        token_info = self.cache_handler.get_cached_token()
        expires_at = token_info["expires_at"]
        now = int(time.time())

        # use an offset of 1 minute as a buffer
        if now >= (expires_at + 60):
            token_info = self._request_token()
            self._save_token_info(token_info)
            self.__token = self._get_token()

        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {self.__token}",
        }

        response = requests.request(
            method=method,
            url=f"{SRF_AUDIO_BASE_URL}{url}",
            headers=headers,
            params=params,
            json=payload,
        )

        data = response.json()

        if 300 > response.status_code >= 200:
            return data
        else:
            raise SRFHTTPException(response=response, data=data)

    def fetch_radio_channels(self) -> List[Dict[str, Any]]:
        params = {"bu": "srf"}
        data = self._request("GET", "/radio/channels", params=params)
        return data["channelList"]

    def fetch_song_list(self, channel_id: str) -> List[Dict[str, Any]]:
        params = {"bu": "srf", "channelId": channel_id}
        data = self._request("GET", "/radio/songlist", params=params)
        return data["songList"]


class SRF:

    def __init__(self):
        self.client: _SRFClient = _SRFClient(
            client_id=Env.SRF_CLIENT_ID,
            client_secret=Env.SRF_CLIENT_SECRET,
            cache_handler=TokenCacheFileHandler("./.cache/.cache_srf"),
        )
        self.songs = SongsStorageFileHandler("./storage/songs.json")
        self.songs_metadata = SongsMetadataFileHandler("./storage/songs_metadata.json")

    def _search_channel(self, q: str) -> Optional[str]:
        channels = self.client.fetch_radio_channels()

        result: Optional[str] = None
        for channel in channels:
            if q.lower() in channel["title"].lower():
                result = channel["id"]
                break

        return result

    def _get_songs(self) -> List[Song]:
        query = "virus"
        channel_id = self._search_channel(query)
        if channel_id is None:
            raise ValueError(f"channel with query '{query}' not found")

        data = self.client.fetch_song_list(channel_id)
        ret = []
        for i, raw_song in enumerate(data):
            try:
                uri = search_title(title=raw_song["title"], artist=raw_song["artist"]["name"])
            except (ConnectionResetError, requests.ConnectionError):
                logger.warning(
                    f"ConnectionResetError for search_title at {i=}, retry in {WAIT_UNTIL_NEXT_SEARCH}s"
                )
                time.sleep(WAIT_UNTIL_NEXT_SEARCH)
                try:
                    uri = search_title(title=raw_song["title"], artist=raw_song["artist"]["name"])
                except (ConnectionResetError, requests.ConnectionError):
                    logger.error(f"ConnectionResetError for search_title at {i=}, abort")
                    continue

            if uri is not None:
                ret.append(Song(data=raw_song, uri=uri))

            time.sleep(WAIT_UNTIL_NEXT_SEARCH)

        return ret

    def get_new_songs(self) -> List[Song]:
        songs = self._get_songs()
        last_timestamp = self.songs_metadata.get("last_timestamp")

        new_songs = []
        for song in songs:
            if song.timestamp == last_timestamp:
                break
            new_songs.append(song)
            self.songs.set(song)

        if new_songs:
            self.songs_metadata.set("last_timestamp", new_songs[0].timestamp)

        return new_songs

    def get_old_songs(self) -> List[Song]:
        now = int(time.time())
        save_time = int(datetime.timedelta(weeks=2).total_seconds())
        songs = self.songs.get_all()

        old_songs = []
        for song in songs:
            if now >= (song.timestamp + save_time):
                old_songs.append(song)
                self.songs.remove(song)

        return old_songs
