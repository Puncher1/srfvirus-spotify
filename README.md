# SRF Virus: Trending Now

## About

This application adds songs played on SRF Virus to the Spotify playlist
"SRF Virus: Trending Now". 

If a song is played it's added to the playlist. If a song wasn't played 
within a week, it will be removed.

## Steps

The application follows these steps:

1. Get songs from SRF API (`api.srgssr.ch/audiometadata/v2/radio/songlist`)
2. Search songs to get URI (song identifier)
3. Filter out songs that are redundant from the last request
4. 

## Links

