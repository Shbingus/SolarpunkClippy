import asyncio
import discord
import os
import sqlite3
import youtube_dl
from dotenv import load_dotenv


load_dotenv()

helpmsg = "__**Commands:**__\n**~List**: I'll list all of the Glossary terms\n**~Define [*term*]**: I'll give you the definition for the term, if we have it! (Example: \"~Define DND\")\n~**Add [*term*], [*definition*]**: Add a new entry for the Glossary! (Example: \"~Add d10, A Ten Sided Die\"\)\n**~Remove [*term*]**: I'll remove the term from the Glossary (Example: \"~Remove d100\"\)"
client = discord.Client()

queue = []

ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0' # bind to ipv4 since ipv6 addresses cause issues sometimes
}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)

ffmpeg_options = {
    'options': '-vn'
}

class queueObject:
    def __init__(self, title, url):
        self.title = title
        self.url = url

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)

        self.data = data

        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    async def from_url(cls, url, *, loop=None, isPlaying=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=False))
    
        if 'entries' in data:
            for entries in data['entries']:
                queue.append( queueObject( str(entries['title']),str(entries['url']) ) )
        else:
            queue.append( queueObject( str(data['title']),str(data['url']) ) )

        if not isPlaying:
            filename = queue[0].url
            return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)
        else:
            print("we're already playing something!")
            return

@client.event
async def on_ready():
    print('We have logged in as {0.user}'.format(client))
    conn = None
    try:
        conn = sqlite3.connect(r"db\botGlossary.db")
        print(sqlite3.version)
    except Error as e:
        print(e)

# @client.command(pass_context=True)
# async def play(ctx, url):
    # server = ctx.message.server
    # voice_client = client.voice_client_in(server)
    # player = await voice_client.create_ytdl_player(url)
    # players[server.id] = player
    # player.start()

@client.event
async def on_message(message):
    if message.author == client.user:
        return
        
    conn = sqlite3.connect(r"db\botGlossary.db")
    curs = conn.cursor()
    serverID = message.guild.id
    stringServerID = str(serverID)

    if message.content.lower().startswith('~def') or message.content.lower().startswith('~term'):
        call = message.content.split(" ")[0]
        query = message.content.replace(call + " ","")
        key = query.lower()
        dbSelect = curs.execute("SELECT Definition FROM Glossary WHERE ServerID = ? AND Term = ?", (stringServerID, key))
        existingKey = dbSelect.fetchone()
        if existingKey:
            await message.channel.send("**" + query + ":** " + existingKey[0])
        else:
            await message.channel.send("The phrase **\"" + query + "\"** was not recognized")
    
    if message.content.lower().startswith('~add') or message.content.lower().startswith('~new ') or message.content.lower().startswith('~a '):
        call = message.content.split(" ")[0]
        query = message.content.replace(call + " ","")
        if not ',' in query:
            await message.channel.send("You need to put a comma between the term and the definition. Example: \"~Add sp, Solarpunk!\"")
            return
        split = query.split(", ", 1)
        originalKey = split[0]
        definition = split[1]
        key = originalKey.lower()
        dbSelect = curs.execute("SELECT Definition FROM Glossary WHERE ServerID = ? AND Term = ?", (stringServerID, key))
        existingKey = dbSelect.fetchone()
        if existingKey:
            print(existingKey)
            await message.channel.send("**\"" + originalKey + "\"** is already stored. Definition: " + existingKey[0])
        else:
            curs.execute("INSERT INTO Glossary values (?, ?, ?)", (stringServerID, key, definition))
            conn.commit()
            await message.channel.send("**\"" + originalKey + "\"** added with definition: " + definition)

    if message.content.lower().startswith('~rem') or message.content.lower().startswith('~rm '):
        call = message.content.split(" ")[0]
        query = message.content.replace(call + " ","")
        key = query.lower()
        dbSelect = curs.execute("SELECT Definition FROM Glossary WHERE ServerID = ? AND Term = ?", (stringServerID, key))
        existingKey = dbSelect.fetchone()
        if existingKey:
            curs.execute("DELETE FROM Glossary WHERE ServerID = ? AND Term = ?", (stringServerID, key))
            conn.commit()
            await message.channel.send("Glossary entry **\"" + query + "\"** removed")
        else:
            await message.channel.send("**\"" + query + "\"** is not in the Glossary")
      
    if message.content.lower().startswith('~terms') or message.content.lower().startswith('~list'):
        keys = curs.execute("SELECT Term, Definition FROM Glossary WHERE ServerID = " + stringServerID)
        msg = "**List of all terms in the Glossary:**"
        for term in keys:
            msg += "\n**" + term[0] + ":** " + term[1]
        await message.channel.send(msg)
        
    if message.content.lower().startswith('~help'):
        await message.channel.send(helpmsg)

    # music commands
    if message.content.lower().startswith('~play ') or message.content.lower().startswith('~p '):
        if not message.author.voice:
            await message.channel.send("You're not in a voice channel!")
        else:
            user = message.author
            channel = message.author.voice.channel
            call = message.content.split(" ")[0]
            url = message.content.replace(call + " ","")
            voice_client = None
            for vc in client.voice_clients:
                if vc.guild.id == message.guild.id:
                    voice_client = vc
            if not voice_client:
                voice_client = await channel.connect()
            
            is_playing = voice_client.is_playing()
            player = await YTDLSource.from_url(url, loop=None, isPlaying=is_playing)
            if(not is_playing):
                voice_client.play(player, after=lambda e: print(f'Player error: {e}') if e else None)
      
    if message.content.lower().startswith('~leave') or message.content.lower().startswith('~dc'):
        if not client.voice_clients:
            await message.channel.send("I'm not in a voice channel right now!")
        for vc in client.voice_clients:
            if vc.guild.id == message.guild.id:
                queue.clear()
                await vc.disconnect()
            else:
                await message.channel.send("I'm not in a voice channel right now!")
                
    if message.content.lower() == '~clear':
        queue.clear()
        await message.channel.send("The queue has been cleared")
                
    if message.content.lower().startswith('~queue') or message.content.lower() == '~q':
        if len(queue) < 1:
            await message.channel.send("The queue is empty")
        else:
            msg = 'Queue: '
            count = 0
            for obj in queue:
                msg += obj.title + ', '
                count += 1
                if count > 4:
                    break
            msg = msg[0:len(msg)-2]
            await message.channel.send(msg)
    
    #Below lies the dumb stuff
    if message.content.lower() == ('~gob'):
      await message.channel.send("They're not **tricks** Michael, they're ***illusions***")
      
    if message.content.lower().startswith('~debug'):
      msg = "voice_clients: "
      for vc in client.voice_clients:
        msg += str(vc) + ", "
      await message.channel.send(msg)

client.run(os.getenv('DISCORD_TOKEN'))