# Genius-Discord-Bot

## Introduction
This repository contains scripts for a Discord bot, consisting in a music guessing game. The bot uses Discord.py, Spotify API, and Genius API to, given a playlist, fetch song lyrics and other informations from the playlist. Players guess the song and artist based on lyrics snippets.

## Repository Structure
  1. `main.py`: The main script to run the bot on Discord.
  2. `bot.py`: It sets up the Discord bot, its main events and initializes the token for the Spotify API.
  3. `responses.py`: Contains the core functionalities of the Spotify Bot. It includes functions to process user commands, interact with the Spotify API, and send responses back to the Discord server.
  4. `high_scores.txt`: Saves the best scores from all players, to display them later at the end of the games.

## Main Features 
  * Music Guessing Game: Users guess songs and artists based on lyrics snippets.
  * Spotify Integration: Fetches song data and playlists from Spotify.
  * Genius Lyrics: Retrieves song lyrics for the guessing game.

## Requirements
  - Python 3
  - Libraries: discord.py, requests, asyncio, lyricsgenius
  - Spotify and Genius API credentials
  - Discord Bot Token

## Setup and Instalation
  1. Clone the repository or download the scripts.
   ```bash
     git clone git@github.com:Fredd124/Guess-The-Song-Discord-Bot.git
     cd Guess-The-Song-Discord-Bot
   ```
  2. Install the required Python libraries:
   ```bash
   pip install discord.py requests asyncio lyricsgenius
   ````
  3. Set up credentials:
      * Genius Developer Credentials:
        * Register your application on the [Genius Developer Portal](https://genius.com/developers).
        * Obtain CLIENT_ID and CLIENT_SECRET.
      * Spotify Developer Credentials:
        * Register your application on the [Spotify Developer Dashboard](https://developer.spotify.com/dashboard/).
        * Obtain CLIENT_ID and CLIENT_SECRET.
      * Discord Bot Token:
        * Create a new bot on the [Discord Developer Portal](https://discord.com/developers/applications).
        * Generate a bot token under the 'Bot' section.
        * To add the bot to a server, navigate to 'OAuth2' > 'URL Generator', select 'bot' scope, and the necessary permissions. Use the generated URL to invite the bot to your server.
  5. Run `main.py` to start the bot:
   ```bash
   python3 main.py
   ```
## Usage
  * Users can interact with the bot by sending commands on the Discord server. Commands include #artist, #album, #track, and more, each providing specific information or functionalities. For more information about the commands, type `#help` in a discord channel where the bot can read messages.
     
