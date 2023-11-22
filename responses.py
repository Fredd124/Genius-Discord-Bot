import os
import requests
from requests import get
import json
import lyricsgenius 
import re
import random
import time
from difflib import SequenceMatcher
import asyncio
from unidecode import unidecode
import discord
import bot

# Utility Functions
def similarity(a, b):
    """
    Return the ratio of similarity between two strings a and b.
    :params a: String a
    :params b: String b
    :return: Ratio of similarity
    """
    return SequenceMatcher(None, a, b).ratio()

def remove_blank_lines(text):
    """
    Remove blank lines from the text.
    :params text: Text
    :return: Text without blank lines
    """
    lines = text.split('\n')
    non_blank_lines = [line for line in lines if line.strip() != '']
    return '\n'.join(non_blank_lines)

def clean_lyrics(text):
    """
    Clean lyrics
    :params text: Lyrics
    :return: Cleaned lyrics
    """
    # Remove content inside brackets (often not part of the lyrics)
    cleaned_text = re.sub(r"\[.*?\]", "", text)
    
    # Remove "Embed" and preceding numbers, with optional spaces
    cleaned_text = re.sub(r"\d*Embed", "", cleaned_text, flags=re.IGNORECASE)
    
    # Remove "You might also like" and anything following it on the same line
    cleaned_text = re.sub(r"You might also like.*", "", cleaned_text, flags=re.IGNORECASE)

    # Optionally, remove lines with certain keywords (e.g., "Lyrics")
    cleaned_text = re.sub(r".*Lyrics", "", cleaned_text, flags=re.IGNORECASE)
    
    cleaned_text = cleaned_text.strip()
    return cleaned_text


def remove_text_inside_parentheses(text):
    """
    Remove text inside parentheses
    :params text: Text
    :return: Text without parentheses
    """
    text_without_parentheses = re.sub(r"\(.*?\)", "", text)
    text_without_hyphen = re.sub(r" - .*", "", text_without_parentheses)
    return text_without_hyphen.strip()

def print_all_points(players_points):
    """
    Print all the points of the players
    :params players_points: Dictionary of players and their points
    :return: String of all the points
    """
    player_points = dict(sorted(players_points.items(), key=lambda item: item[1], reverse=True))
    points_msg = ""
    for idx, player in enumerate(player_points):
        points_msg += f"{idx}. {player}: {players_points[player]}\n"
    return points_msg

def get_random_lyric_snippet(lyrics, snippet_size=4):
    """
    Get a random snippet of consecutive lines from the lyrics.
    :params lyrics: Lyrics
    :params snippet_size: Number of lines in the snippet
    :return: Snippet of lyrics
    """
    lyrics_lines = lyrics.split('\n')
    start_idx = random.randint(0, len(lyrics_lines) - snippet_size)
    snippet = '\n'.join(lyrics_lines[start_idx : start_idx + snippet_size])
    return snippet

# Discord Interaction Functions
async def send(ctx, title, description, field, value):
    """
    Send an embeded message to the channel
    :params ctx: Discord context
    :params title: Title of the embed
    :params description: Description of the embed
    :params field: Field of the embed
    :params value: Value of the field
    """
    embed = discord.Embed(
        title=title,
        description=description,
        color=discord.Color.blue()  
    )
    
    if field != "" or value != "":
        field = "⇨ " +field
        embed.add_field(name=field, value=value, inline=True)

    await ctx.send(embed=embed)

# Spotify API Functions
def search_for_playlist(token, playlist_name):
    """
    Search for a spotify playlist
    :params token: Spotify token
    :params playlist_name: Playlist name
    :return: Playlist info
    """
    url = "https://api.spotify.com/v1/search"
    headers = bot.get_auth_header(token)
    query = f"?q={playlist_name}&type=playlist&limit=1"
    query_url = url + query

    try:
        response = get(query_url, headers=headers)
        response.raise_for_status()

        json_result = json.loads(response.content)["playlists"]["items"]
        return json_result[0] if json_result else None
    except requests.RequestException as e:
        print(f"Error during Spotify search: {e}")
        return None

async def get_playlist_info(ctx, token, playlist_name, url):
    """
    Get a Spotify playlist info 
    :params ctx: Discord context
    :params token: Spotify token
    :params playlist_name: Playlist name
    :params url: If the playlist name is a url
    :return: Playlist info
    """
    try:
        if not url:
            info = search_for_playlist(token, playlist_name)
            if not info:
                await send(ctx, "Something went wrong", "Check the playlist name you have provided.", "", "")
                return 
            playlist_id = info['id']
        else:
            playlist_id = playlist_name.split('/')[-1].split('?')[0]

        url = f"https://api.spotify.com/v1/playlists/{playlist_id}"
        headers = bot.get_auth_header(token)
        response = requests.get(url, headers=headers)
        response.raise_for_status()  
        playlist_info = response.json()

        track_names_and_artists = []
        for track_item in playlist_info.get("tracks", {}).get("items", []):
            track = track_item.get("track")
            if track:
                track_name = track.get("name")
                artist_names = "; ".join(artist["name"] for artist in track.get("artists", []))
                if track_name and artist_names:
                    track_names_and_artists.append({"name": track_name, "artists": artist_names})

        return track_names_and_artists

    except requests.RequestException as e:
        await send(ctx, "Error", f"An error occurred while retrieving playlist information: {e}", "", "")
        return 
    except json.JSONDecodeError:
        await send(ctx, "Error", "Failed to parse playlist information.", "", "")
        return 

# Genius API Functions
async def get_lyrics(token, song_name, artist_name):
    """
    Get lyrics from Genius API
    :params token: Genius token
    :params song_name: Song name
    :params artist_name: Artist name
    :return: Lyrics
    """
    try:
        genius = lyricsgenius.Genius(token)
        song = genius.search_song(song_name, artist_name)
        
        if song:
            lyrics = song.lyrics
            lyrics = remove_blank_lines(lyrics)
            lyrics = clean_lyrics(lyrics)
            return lyrics
        else:
            print("Song not found.")
            return None

    except Exception as e:
        print(f"Failed to retrieve lyrics: {e}")
        return None

# Game Logic Functions
def check_features_guess(guess, feat_artists):
    """
    Check if the guess is a featured artist
    :params guess: Guess
    :params feat_artists: List of featured artists
    :return: Featured artist
    """
    guesses = []
    for artist in feat_artists:
        if similarity(guess, artist.lower()) > 0.95 or similarity(guess, unidecode(artist.lower())) > 0.95:
            guesses.append([artist.lower(), similarity(guess, artist.lower())])
    if guesses == []:
        return None
    else: 
        closest_guess = max(guesses, key=lambda x: x[1])
        return closest_guess[0]
        
async def play(ctx, bot, artists, song_name, lyrics, players_points):
    """
    Play the guessing game
    :params ctx: Discord context
    :params artists: List of artists to guess
    :params song_name: Song name to guess
    :params lyrics: Lyrics of the song
    :params players_points: Dictionary of players and their points
    :return: Dictionary of players and their points
    """
    snippet = get_random_lyric_snippet(lyrics)
    await send(ctx, "Guess the song and artist(s) from the following lyrics snippet", "Send a message in this channel to make a guess.", "Lyrics snippet", snippet)
    time.sleep(1)

    points_needed_to_win = 2 + 2 + (len(artists) - 1)  # main artist + song + features
    users_points = 0
    feat_artists = artists[1:]
    main_artist_guessed = False
    song_name_guessed = False
    guessed_featured_artists = set()

    while users_points < points_needed_to_win:
        try:
            guess_msg = await bot.wait_for('message', timeout=15.0)
            guess = guess_msg.content.strip().lower()
            author = guess_msg.author.display_name
            
            if not main_artist_guessed and (similarity(guess, artists[0].lower()) > 0.95
                                            or similarity(guess, unidecode(artists[0].lower())) > 0.95):
                main_artist_guessed = True
                users_points += 2
                if author in players_points:
                    players_points[author] += 2
                else:
                    players_points[author] = 2
                await send(ctx, f"Correct! +2 points.", "", "", "")
            elif not song_name_guessed and (similarity(guess, song_name.lower()) > 0.95 
                                            or similarity(guess, unidecode(song_name.lower())) > 0.95):
                song_name_guessed = True
                users_points += 2
                if author in players_points:
                    players_points[author] += 2
                else:
                    players_points[author] = 2
                await send(ctx, f"Correct! +2 points.", "", "", "")
            elif guess not in guessed_featured_artists:
                guess = check_features_guess(guess, feat_artists)
                if guess != None:    
                    guessed_featured_artists.add(guess)
                    users_points += 1
                    if author in players_points:
                        players_points[author] += 1
                    else:
                        players_points[author] = 1
                    await send(ctx, f"Correct! +1 point.", "", "", "")
            
        except asyncio.TimeoutError:
            break
    
    if users_points >= points_needed_to_win:
        await send(ctx, "Round over", "Congratulations! You guessed all artists and the song name!", "Points table", print_all_points(players_points))
    else:
        await send(ctx, "Round over", f"Time's up! The correct answer was: {', '.join(artists)} - {song_name}", "Points table", print_all_points(players_points))

    time.sleep(2)
    return players_points

# Main Game Function
async def game(ctx, bot, genius_token, spotify_token):
    """
    Run the guessing game
    :params ctx: Discord context
    :params genius_token: Genius token
    :params spotify_token: Spotify token
    """
    p_message = ctx.message.content
    message = p_message[6:]
 
    pattern = r"(.*?)(?: num_rounds=(\d+))?$"
    match = re.search(pattern, message)

    if match:
        playlist_name = match.group(1).strip()  
        number = int(match.group(2)) if match.group(2) else None  

        if number is not None:
            num_rounds = number
        else:
            num_rounds = 1
        
        if playlist_name == "":
            await send(ctx, "Something went wrong", "Check the playlist url or the name you have provided.", "", "")
            return
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

    if url_mode:
        playlist_info = await get_playlist_info(ctx, spotify_token, playlist_name, True)
    else:
        playlist_name = playlist_name.lower()
        playlist_info = await get_playlist_info(ctx, spotify_token, playlist_name, False)

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

        song_info = playlist_info[random_num]
        main_artist = song_info['artists'].split("; ")[0]
        all_artists = song_info['artists'].split("; ")
    
        # Remove text inside parentheses (often not part of the song name)
        name = remove_text_inside_parentheses(song_info['name'])
        song_name = f"{main_artist} {name}"

        # Compare possible artist names with the main artist name
        try:
            genius = lyricsgenius.Genius(genius_token)
            genius_artist = genius.search_artist(main_artist, max_songs=0)
            genius_artist.save_lyrics("lyrics.json")
            with open("lyrics.json", "r") as f:
                lyrics = json.load(f)
            all_artist_names = lyrics["alternate_names"]
            all_artist_names.append(main_artist)
            valid_artist_name = False
            os.remove("lyrics.json")
            for artist in all_artist_names:
                if artist.lower() in main_artist.lower():
                    valid_artist_name = True
                    break
            if not valid_artist_name:
                await send(ctx, f"Couldn't fetch the lyrics for {song_name}", "Let's skip this song!", "", "")
                continue
        except Exception as e:
            await send(ctx, f"Couldn't fetch the lyrics for {song_name}", "Let's skip this song!", "", "")
            continue
        
        try:
            lyrics = await get_lyrics(genius_token, song_name, main_artist)
        except Exception as e:
            print(f"Failed to retrieve lyrics: {e}")
            lyrics = None
        
        if lyrics:
            lyrics = remove_blank_lines(lyrics)
            players_points = await play(ctx, bot, all_artists, name, lyrics, players_points)
        else:
            await send(ctx, f"Couldn't fetch the lyrics for {song_name}", "Let's skip this song!", "", "")
            continue

    await send(ctx, "Game over! Thanks for playing.", "", "", "")