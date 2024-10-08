import os

from dotenv import load_dotenv


load_dotenv()


class Env:
    SPOTIFY_CLIENT_ID: str = os.getenv("SPOTIFY_CLIENT_ID")  # type: ignore
    SPOTIFY_CLIENT_SECRET: str = os.getenv("SPOTIFY_CLIENT_SECRET")  # type: ignore
    SPOTIFY_PLAYLIST_ID: str = os.getenv("SPOTIFY_PLAYLIST_ID")  # type: ignore
    SRF_CLIENT_ID: str = os.getenv("SRF_CLIENT_ID")  # type: ignore
    SRF_CLIENT_SECRET: str = os.getenv("SRF_CLIENT_SECRET")  # type: ignore
