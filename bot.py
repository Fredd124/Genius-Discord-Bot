import os
import discord
import responses
import base64
import json
from requests import post
import dotenv
from discord.ext import commands

dotenv.load_dotenv()

def get_token(client_id, client_secret):
    """
    Get token from Spotify API
    :params client_id: Spotify client id
    :params client_secret: Spotify client secret
    :return: Spotify token
    """
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
    """
    Get authorization header
    :params token: Spotify token
    :return: Authorization header
    """
    return {"Authorization": "Bearer " + token}

def run_discord_bot():
    """
    Run discord bot
    """
    discordToken = os.getenv('DISCORD_TOKEN')
    geniusToken = os.getenv('TOKEN')    
    spotipy_client_id = os.getenv("SPOTIFY_CLIENT_ID")
    spotipy_client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
    spotify_token = get_token(spotipy_client_id, spotipy_client_secret)

    intents = discord.Intents.all()
    intents.members = True
    bot = commands.Bot(command_prefix='!', intents=intents)

    @bot.event
    async def on_ready():
        print(f'{bot.user.name} is now running!')

    @bot.command()
    async def game(ctx):
        try:
            await responses.game(ctx, bot, geniusToken, spotify_token)   
        except Exception as e:
            print(e)
            await ctx.send('Error')

    bot.run(discordToken)
