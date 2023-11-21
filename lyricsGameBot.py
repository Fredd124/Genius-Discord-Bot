import os
import dotenv
import base64
import requests
from requests import post, get
import json
import lyricsgenius 
import re
import random
import time
from difflib import SequenceMatcher
import asyncio
from unidecode import unidecode
import discord
from discord.ext import commands

dotenv.load_dotenv()

###### Initialize Global Parameters ######

discordToken = os.getenv('DISCORD_TOKEN')
geniusToken = os.getenv('TOKEN')    
spotipy_client_id = os.getenv("SPOTIFY_CLIENT_ID")
spotipy_client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")

intents = discord.Intents.all()
intents.members = True
bot = commands.Bot(command_prefix='!', intents=intents)

##################### Spotify API #####################

def get_token(client_id, client_secret):
    auth_string = client_id + ":" + client_secret
    auth_bytes =  auth_string.encode("utf-8")
    auth_base64 = str(base64.b64encode(auth_bytes), "utf-8")

    url = "https://accounts.spotify.com/api/token"
    headers = {
        "Authorization": "Basic " + auth_base64,
        "Content-Type": "application/x-www-form-urlencoded"
    }
    data = {"grant_type": "client_credentials"}
    result = post(url, headers=headers, data=data)
    json_result = json.loads(result.content)
    token = json_result["access_token"]
    return token

def get_auth_header(token):
    return {"Authorization": "Bearer " + token}

def search_for_playlist(token, playlist_name):
    url = "https://api.spotify.com/v1/search"
    headers = get_auth_header(token)
    query = f"?q={playlist_name}&type=playlist&limit=1"
    
    query_url = url + query
    result = get(query_url, headers=headers)
    json_result = json.loads(result.content)["playlists"]["items"]
    if len(json_result) == 0:
        print("No playlist found")
        return None
    
    return json_result[0]

def get_playlist_info(token, playlist_name, url):
    if not url:
        info = search_for_playlist(token, playlist_name)
        if info == None:
            return
        url = f"https://api.spotify.com/v1/playlists/{info['id']}"
    else: 
        playlist_id = playlist_name.split('/')[-1]
        playlist_id = playlist_id.split('?')[0]
        url = f"https://api.spotify.com/v1/playlists/{playlist_id}"
    headers = get_auth_header(token)
    result = get(url, headers=headers)
    if result == None:
        return
    playlistInfo = json.loads(result.content)

    track_names_and_artist = []
    
    for track in playlistInfo["tracks"]["items"]:
        artist_names = "; ".join([artist["name"] for artist in track["track"]["artists"]])
        track_names_and_artist.append({"name": track["track"]["name"], "artists": artist_names})
    
    return track_names_and_artist

##################### Genius API #####################

def get_lyrics(token, song_name):
    genius = lyricsgenius.Genius(token)
    song = genius.search_song(song_name)
    
    if song:
        lyrics = song.lyrics
        lyrics = remove_tags(lyrics)
        lyrics = remove_blank_lines(lyrics)
        lyrics = clean_lyrics(lyrics)
        return lyrics
    else:
        print("Song not found.")

def clean_lyrics(text):
    # Remove content inside brackets (often not part of the lyrics)
    cleaned_text = re.sub(r"\[.*?\]", "", text)
    
    # Remove "Embed" and preceding numbers, with optional spaces
    cleaned_text = re.sub(r"\d*Embed", "", cleaned_text, flags=re.IGNORECASE)
    
    # Remove "You might also like" and anything following it on the same line
    cleaned_text = re.sub(r"You might also like.*", "", cleaned_text, flags=re.IGNORECASE)

    # Optionally, remove lines with certain keywords (e.g., "Lyrics")
    cleaned_text = re.sub(r".*Lyrics", "", cleaned_text, flags=re.IGNORECASE)
    
    # Strip leading and trailing whitespaces
    cleaned_text = cleaned_text.strip()
    
    return cleaned_text
            
def remove_blank_lines(text):
    lines = text.split('\n')
    non_blank_lines = [line for line in lines if line.strip() != '']
    return '\n'.join(non_blank_lines)

def remove_tags(lyrics):
    # Using regular expressions to find and replace lines with tags
    cleaned_lyrics = re.sub(r'\[.*?\]\n', '', lyrics)
    return cleaned_lyrics.strip()

#################### Guessing Game #####################

def remove_text_inside_parentheses(text):
    # Pattern to match: ( followed by any character, repeated any number of times, and then )
    pattern_parentheses = re.compile(r'\(.*?\)')
    text_without_parentheses = re.sub(pattern_parentheses, '', text)
    # Substitute matched pattern with an empty string

    # Remove text after a hyphen followed by space
    pattern_hyphen = re.compile(r' - .*')
    text_without_hyphen = re.sub(pattern_hyphen, '', text_without_parentheses)

    return text_without_hyphen.strip()

async def send(ctx, title, description, field, value):
    # Create an embed
    embed = discord.Embed(
        title=title,
        description=description,
        color=discord.Color.blue()  # You can set the color of the embed
    )
    
    # Add fields to the embed 
    if field != "" or value != "":
        field = "⇨ " +field
        embed.add_field(name=field, value=value, inline=True)

    # Send the embed as a message
    await ctx.send(embed=embed)

def similarity(a, b):
    """Return the ratio of similarity between two strings a and b."""
    return SequenceMatcher(None, a, b).ratio()

def get_random_lyric_snippet(lyrics, snippet_size=4):
    lyrics_lines = lyrics.split('\n')
    start_idx = random.randint(0, len(lyrics_lines) - snippet_size)
    snippet = '\n'.join(lyrics_lines[start_idx : start_idx + snippet_size])
    return snippet

def remove_blank_lines(text):
    lines = text.split('\n')
    non_blank_lines = [line for line in lines if line.strip() != '']
    return '\n'.join(non_blank_lines)

async def play(ctx, artists, song_name, lyrics, players_points):
    # Give a snippet of the lyrics to the user
    # Get a random snippet of consecutive lines
    snippet = get_random_lyric_snippet(lyrics)

    await send(ctx, "Guess the song and artist(s) from the following lyrics snippet", "Send a message in this channel to make a guess.", "Lyrics snippet", snippet)
    time.sleep(1)
    #await send(ctx, "Lyrics snippet", snippet)

    # Calculate the total points needed to win
    points_needed_to_win = 2 + 2 + (len(artists) - 1)  # main artist + song + features

    # Points the user has scored
    points = 0

    # Flags to indicate whether the main artist/song name has been guessed
    feats_artists = artists[1:]
    main_artist_guessed = False
    song_name_guessed = False

    # A set to keep track of which featured artists have been guessed
    guessed_featured_artists = set()

    def check_features_guess(guess, artist):
        guesses = []
        for artist in feats_artists:
            if similarity(guess, artist.lower()) > 0.95 or similarity(guess, unidecode(artist.lower())) > 0.95:
                guesses.append([artist.lower(), similarity(guess, artist.lower())])
        if guesses == []:
            return None
        else: 
            closest_guess = max(guesses, key=lambda x: x[1])
            return closest_guess[0]

    while points < points_needed_to_win:
        try:
            guess_msg = await bot.wait_for('message', timeout=15.0)

            guess = guess_msg.content.strip().lower()
            author = guess_msg.author.nick

            if not main_artist_guessed and (similarity(guess, artists[0].lower()) > 0.95
                                            or similarity(guess, unidecode(artists[0].lower())) > 0.95):
                main_artist_guessed = True
                points += 2
                if author in players_points:
                    players_points[author] += 2
                else:
                    players_points[author] = 2
                await send(ctx, f"Correct! +2 points.", "", "", "")
            elif not song_name_guessed and (similarity(guess, song_name.lower()) > 0.95 
                                            or similarity(guess, unidecode(song_name.lower())) > 0.95):
                song_name_guessed = True
                points += 2
                if author in players_points:
                    players_points[author] += 2
                else:
                    players_points[author] = 2
                await send(ctx, f"Correct! +2 points.", "", "", "")
            elif guess not in guessed_featured_artists:
                guess = check_features_guess(guess, artists[1:])
                if guess != None:    
                    guessed_featured_artists.add(guess)
                    points += 1
                    if author in players_points:
                        players_points[author] += 1
                    else:
                        players_points[author] = 1
                    await send(ctx, f"Correct! +1 point.", "", "", "")
            
        except asyncio.TimeoutError:
            break

    def print_all_points():
        player_points = dict(sorted(players_points.items(), key=lambda item: item[1], reverse=True))
        points_msg = ""
        for idx, player in enumerate(player_points):
            points_msg += f"{idx}. {player}: {players_points[player]}\n"
        return points_msg
    

    if points >= points_needed_to_win:
        await send(ctx, "Round over", "Congratulations! You guessed all artists and the song name!", "Points table", print_all_points())
    else:
        await send(ctx, "Round over", f"Time's up! The correct answer was: {', '.join(artists)} - {song_name}", "Points table", print_all_points())

    time.sleep(2)
    return players_points

def get_lyrics_with_retry(genius, song_name, max_retries=3):
    for retry in range(max_retries):
        try:
            # Attempt to get lyrics
            lyrics = get_lyrics(geniusToken, song_name)
            return lyrics
        except requests.exceptions.Timeout:
            print(f"Request timed out (retry {retry + 1}/{max_retries})")
    
    # If all retries fail, raise an exception or return None
    raise Exception("Failed to retrieve lyrics after multiple retries")

######## Discord Bot ########

@bot.event
async def on_ready():
    print(f'{bot.user} is now running!')

@bot.command()
async def game(ctx):
    p_message = ctx.message.content
    message = p_message[6:]
 
    # Regular expression pattern
    pattern = r"(.*?)(?: num_rounds=(\d+))?$"

    match = re.search(pattern, message)

    if match:
        playlist_name = match.group(1).strip()  # Words before "num_rounds=" if present
        number = int(match.group(2)) if match.group(2) else None  # The digit after "num_rounds=" if present

        if number is not None:
            num_rounds = number
        else:
            num_rounds = 1
    else:
        await send(ctx, "Something went wrong", "Check the playlist url or the name you have provided.", "", "")
        return

    playlist_name_list = playlist_name.split(" ")
    if ("num_rounds=" in playlist_name_list[-1]):
        playlist_name_list.pop(-1)
        playlist_name = " ".join(playlist_name_list)
    
    playlist_name = playlist_name.strip()

    url_mode = False
    if playlist_name.startswith("https://"):
        url_mode = True

    spotify_token = get_token(spotipy_client_id, spotipy_client_secret)

    if url_mode:
        playlist_info = get_playlist_info(spotify_token, playlist_name, True)
    else:
        playlist_name = playlist_name.lower()
        playlist_info = get_playlist_info(spotify_token, playlist_name, False)

    if playlist_info == None:
        await send(ctx, "Something went wrong", "Check the playlist url or the name you have provided.", "", "")
        return

    players_points = {}
    music_chosen = []

    if num_rounds > len(playlist_info):
        reduce_rounds = send(ctx, "Cannot play {num_rounds} rounds with only {len(playlist_info)} songs.", "Reducing rounds to match song count.", "", "")
        await ctx.send(reduce_rounds)
        num_rounds = len(playlist_info)

    for round_num in range(num_rounds):
        round_msg = f"Round {round_num + 1}"
        await send(ctx, round_msg, "The round will start shortly.", "", "")

        # Take a random song from the playlist
        random_num = random.randint(0, len(playlist_info) - 1)  
        while random_num in music_chosen:
            random_num = random.randint(0, len(playlist_info) - 1)
        music_chosen.append(random_num)

        # Get the song info
        song_info = playlist_info[random_num]
        # Assume the main artist is the first listed
        main_artist = song_info['artists'].split("; ")[0]
        # All artists (including featured)
        all_artists = song_info['artists'].split("; ")
        
        main_artist = unidecode(main_artist)
        all_artists = [unidecode(artist) for artist in all_artists]
    
        # Remove text inside parentheses (often not part of the song name)
        name = remove_text_inside_parentheses(song_info['name'])

        # Song info for later guesses
        song_name = f"{main_artist} {name}"

        try:
            lyrics = get_lyrics(geniusToken, song_name)
        except Exception as e:
            print(f"Failed to retrieve lyrics: {e}")
            lyrics = None
        
        if lyrics and lyrics != None:
            lyrics = remove_blank_lines(lyrics)
            if "•" in lyrics or ";" in lyrics:
                await send(ctx, f"The lyrics for {song_name} were wrong", "Let's skip this song!", "", "")
                continue
            players_points = await play(ctx, all_artists, name, lyrics, players_points)
        else:
            await send(ctx, f"Couldn't fetch the lyrics for {song_name}", "Let's skip this song!", "", "")
            continue

    await send(ctx, "Game over! Thanks for playing.", "", "", "")
    
bot.run(discordToken)

###### Can still have problems with the lyrics formating ######
###### Concurrent players can be a problem if they write a right guess at the same time ######