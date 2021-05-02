#### Playlist Buddy Discord Bot 
#### Scrapes Discord server channel for links to songs/albums and updates YouTube & Spotify playlists
#### Note: This is the template with placeholders for key information such as playlist ID's and secrect
####        keys to use Discord, YouTube, and Spotify API's. See documentation for discord.py, spotipy, and ytmusicapi
####        for assistance in getting this set up for your own usage.
####        The BotKeys folder is currently empty, but you can save your keys there and update file names in code below.

# Importing Libraries
import discord
import logging
import os
import re
import requests
from datetime import datetime
import pandas as pd
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from ytmusicapi import YTMusic

# Set path for project directory
project_path = os.getcwd()

# Set environment variables for Spotipy Client
# Spotify Developer Account needed to get your keys
# Read in keys from files saved in project folder
os.environ['SPOTIPY_CLIENT_ID'] = open(os.path.join(project_path,'BotKeys/spotify/your_clientid.txt')).read()
os.environ['SPOTIPY_CLIENT_SECRET'] = open(os.path.join(project_path,'/BotKeys/spotify/your_clientsc.txt')).read()
os.environ['SPOTIPY_REDIRECT_URI'] = "https://callback.com/callback/"   # This can be any valid URL, does not have to be real website



# Helper function for writting lines to text file
def save_line(out, message):
    """ This function defines the information to capture when scraping posts
        and writes them to a given text file (out) """

    lines = []
    lines.append('{0}, {1}, {2}, "{3}"'.format(message.channel.name, message.created_at, message.author.name, message.clean_content.replace("\n", " ")))

    for line in lines:
        out.write(line + "\n")

# YouTube Playlist
def build_yt_playlist(channel_name, date_time):
    """ Function to define target YouTube playlist
        Provide the channel name and datetime of most recent scrape
        Finds YouTube links in scrape file and adds them to playlist """
    # Specify URL for YouTube playlist to update (go to your playlist on YouTube Music and copy URL)
    playlist_url = "https://music.youtube.com/playlist?list=your-playlist-id"
    # Create a YouTube Music API Client, see ytmusicapi documentation for details on set up/authentication
    ytmusic = YTMusic(os.path.join(project_path, 'BotKeys/youtube/ytmusic_header.txt'))
    # Specify ID for YouTube playlist to update (last part of the URL above)
    playlistId = "your-playlist-id"

    def get_ytpl_tracks(pl):
        """ Function to get existing tracks from playlist """
        playlist = ytmusic.get_playlist(pl)
        tracks = playlist['tracks']
    
        video_ids = []
        for t in tracks:
            video_ids.append(t['videoId'])
    
        return video_ids

    current_tracks = get_ytpl_tracks(playlistId)

    # Read in file from channel scrape
    col_names = ['channel', 'created_at', 'author', 'content']
    channel_ds = pd.read_csv(f'{project_path}/channel-logs/{channel_name}_{date_time}_scrape.txt', header=None, names = col_names)

    url_content = []
    # Parse post content and match YouTube links with regex
    for cont in channel_ds.content:
        try:
            stuff = cont.split(" ")
        except:
            pass
        for s in stuff:
            if re.search("(?:https?:\/\/)?(?:youtu\.be\/|(?:www\.|m\.)?youtube\.com\/(?:watch|v|embed)(?:\.php)?(?:\?.*v=|\/))([a-zA-Z0-9\_-]+)", str(s)):
                url_content.append(s)
    
    # Parse the Video ID from the link URL using regex
    vid_ids = [re.search("((?<=(v|V)/)|(?<=be/)|(?<=(\?|\&)v=)|(?<=embed/))([\w-]+)", i).group() for i in url_content]
    
    # Check if track is already in the playlist and add if its a new track
    new_tracks = 0
    for vid in vid_ids:
        if vid in current_tracks:
            pass
        else:
            try:
                ytmusic.add_playlist_items(playlistId, [vid])
                new_tracks += 1
            except:
                pass
    
    print(f"Playlist contains {len(current_tracks)} tracks")
    print(f"Discord posts contained {len(vid_ids)} tracks")
    print(f"Adding {new_tracks} new tracks to YouTube playlist")

    return playlist_url

# Spotify Playlist
def update_spotify_playlist(channel_name, date_time):
    """ Function to define target Spotify playlist
        Povide the channel name and datetime of most recent scrape
        Finds Spotify links in scrape file and adds them to playlist """
    # Instantiate Spotipy Client
    scope = 'playlist-modify-public'  # playlist must be Public to update with Bot
    sp = spotipy.Spotify(auth_manager=SpotifyOAuth(scope=scope))
    # Define target playlist URI and user ID
    void_pl = sp.playlist('spotify:playlist:your-playlist-URI')
    user_id = 'spotify:user:your-user-ID'

    # Get the current tracks in the playlist
    def get_playlist_tracks(user, playlist_id):
        """ Function to get existing tracks from playlist """
        results = sp.user_playlist_tracks(user, playlist_id)
        pl_tracks = results['items']
        while results['next']:
            results = sp.next(results)
            pl_tracks.extend(results['items'])
        return pl_tracks
    
    playlist_current_tracks = get_playlist_tracks(user_id, void_pl['id'])
    pl_tracks = [i['track']['uri'] for i in playlist_current_tracks]
    
    # Get posts from the Discord server scrape file
    music_channel = channel_name
    col_names = ['channel', 'created_at', 'author', 'content']
    channel_ds = pd.read_csv(f'{project_path}/channel-logs/{music_channel}_{date_time}_scrape.txt', header=None, names = col_names)

    # Find Spotify urls with regex
    regex = r"https:\/\/open.spotify.com\/([a-zA-Z]+)\/([a-zA-Z0-9]+).*$"
    url_finds = [re.findall(regex, str(s)) for s in channel_ds.content if len(re.findall(regex, str(s))) > 0]

    # Sort links into tracks, albums, playlists

    tracks = []
    albums = []
    playlists = [] # Playlist that get posted will not be parsed to add tracks (some playlist are very long)

    for i in url_finds:
        if (i[0][0] == "track") & (i[0][1] not in tracks):
            tracks.append(i[0][1])
        elif (i[0][0] == "album") & (i[0][1] not in albums):
            albums.append(i[0][1])
        elif (i[0][0] == "playlist") & (i[0][1] not in playlists):
            playlists.append(i[0][1])
    # Get Spotify URI's for tracks
    track_ids = []
    for t in tracks:
        trk = sp.track(t)
        if trk['uri'] in track_ids:
            pass
        else:
            track_ids.append(trk['uri'])

    # Get Spotify URI's for album tracks
    alb_tracks = []
    for a in albums:
        album = sp.album(a)
        album_length = album['tracks']['total']
        album_tracks = [album['tracks']['items'][i]['uri'] for i in range(album_length)]
        alb_tracks.extend(album_tracks)

    all_tracks = track_ids.copy()
    for alt in alb_tracks:
        if alt in all_tracks:
            pass
        else:
            all_tracks.append(alt)

    # Check if tracks from Discord posts are already in the playlist

    tracks_to_add = []

    for i in all_tracks:
        if i in pl_tracks:
            pass
        else:
            tracks_to_add.append(i)

    # Add new tracks to the playlist
    try:
        sp.playlist_add_items(void_pl['id'], tracks_to_add)
    except:
        pass
    print(f"Playlist contains {len(pl_tracks)} tracks")
    print(f"Discord posts contained {len(all_tracks)} tracks")
    print(f"Adding {len(tracks_to_add)} new tracks to Spotify playlist")

    spotify_url_stem = "https://open.spotify.com/playlist/"
    playlist_url = spotify_url_stem + str(void_pl['id'])
    return playlist_url

# Set up logging
logger = logging.getLogger('discord')
logger.setLevel(logging.INFO)
handler = logging.FileHandler(filename='discord_bot.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

# Get Discord Bot Token from a saved text file
def get_token():
    with open(os.path.join(project_path,'BotKeys/discord/discord_bottoken.txt')) as f:
        tkn = f.read()
    return tkn

# Initialize Discord Client
client = discord.Client()

# Setting up Bot functions executed by the client

async def scrape_channel(channel, date_time, limit=1000):
    """ Function to execute channel scrape """
    with open("{0}/channel-logs/{1}_{2}_scrape.txt".format(project_path, channel.name, date_time), 'w', encoding="utf-8") as f:
        async for msg in channel.history(limit=limit):
            save_line(f, msg)

    await channel.send("Scraping links & updating playlists...")


# Print to console when online & ready
@client.event
async def on_ready():
    print('Logged in and ready to go as {0.user}'.format(client))

# What to do when a message is posted
@client.event    
async def on_message(message):    

    if message.author == client.user:
        return

    # Update Playlists Call Response - Change command as you wish
    elif (message.content.startswith('$playlists')):
        now = datetime.now()
        date_time = now.strftime("%m%d%Y-%H%M%S")
        await scrape_channel(message.channel, date_time, limit=500)
        yt_playlist = build_yt_playlist(message.channel.name, date_time)
        spot_playlist = update_spotify_playlist(message.channel.name, date_time)
        await message.reply(f"Playlists updated:\n YouTube: {yt_playlist}\n Spotify: {spot_playlist}", mention_author=True)


tkn = get_token()
client.run(tkn)


