import logging
import datetime

import sentry_sdk as sentry
from apscheduler.schedulers.blocking import BlockingScheduler

from srfvirus_spotify.spotify import Spotify
from srfvirus_spotify.srf import SRF
from srfvirus_spotify.env import Env


logger = logging.getLogger(__name__)


def setup() -> None:
    ignore_errors = [KeyboardInterrupt]
    sentry.init(
        dsn=Env.SENTRY_DSN,
        ignore_errors=ignore_errors,
    )
    logging.basicConfig(
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
        datefmt="%d.%m.%y %H:%M:%S %Z",
        level=logging.INFO,
        handlers=[logging.FileHandler("./logs/logging.log"), logging.StreamHandler()],
    )


scheduler = BlockingScheduler()


@scheduler.scheduled_job("interval", minutes=15, next_run_time=datetime.datetime.now())
def main():
    spotify = Spotify()
    srf = SRF(spotify=spotify)

    # add new songs to playlist
    new_songs = srf.get_trending_songs()
    if new_songs:
        spotify.add_to_playlist(new_songs)

    # remove old songs from playlist
    old_songs = srf.get_old_songs()
    if old_songs:
        spotify.remove_from_playlist(old_songs)


if __name__ == "__main__":
    setup()
    scheduler.start()
