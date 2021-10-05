import discord
import os
import sqlite3
from dotenv import load_dotenv

load_dotenv()

helpmsg = "__**Commands:**__\n**~List**: I'll list all of the Glossary terms\n**~Define [*term*]**: I'll give you the definition for the term, if we have it! (Example: \"~Define DND\")\n~**Add [*term*], [*definition*]**: Add a new entry for the Glossary! (Example: \"~Add d10, A Ten Sided Die\"\)\n**~Remove [*term*]**: I'll remove the term from the Glossary (Example: \"~Remove d100\"\)"
client = discord.Client()

@client.event
async def on_ready():
    print('We have logged in as {0.user}'.format(client))
    conn = None
    try:
        conn = sqlite3.connect(r"db\botGlossary.db")
        print(sqlite3.version)
    except Error as e:
        print(e)

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
      
    # if message.content.lower().startswith('~debug'):
      # msg = "serverID: " + str(serverID)
      # msg += "\nobjectType: " + str(type(serverID))
      # await message.channel.send(msg)

    
    #Below lies the dumb stuff
    if message.content.lower() == ('~gob'):
      await message.channel.send("They're not **tricks** Michael, they're ***illusions***")

client.run(os.getenv('DISCORD_TOKEN'))
