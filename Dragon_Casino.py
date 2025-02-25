from locale import currency
import discord
from discord.ext import commands
from discord import app_commands
import sqlite3
from sqlite3 import Error
import asyncio
import random


# Database Engine
def initDatabase():
    conn = sqlite3.connect("dragoncasino.db")
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ddtickets (
            ticket_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user INTEGER,
            num1 INTEGER,
            num2 INTEGER,
            num3 INTEGER,
            num4 INTEGER,
            num5 INTEGER
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS dddraws (
            draw_id INTEGER PRIMARY KEY AUTOINCREMENT,
            jackpot INTEGER,
            total_pot INTEGER DEFAULT 0,
            winning_num1 INTEGER,
            winning_num2 INTEGER,
            winning_num3 INTEGER,
            winning_num4 INTEGER,
            winning_num5 INTEGER,
            winner INTEGER,
            draw_date TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS balances (
            user INTEGER PRIMARY KEY,
            balance INTEGER DEFAULT 0,
            totalwon INTEGER DEFAULT 0
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY,
            user INTEGER,
            type TEXT CHECK(type IN ('deposit', 'withdrawal')),
            amount INTEGER,
            timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
            status TEXT CHECK(status IN ('pending', 'approved', 'denied'))
            FOREIGN KEY (user) REFERENCES balances(user)
        )
    """)

    conn.commit()  # Save changes
    conn.close()  # Close connection


# Main Engine
class Client(commands.Bot):
    async def on_ready(self):
        print(f'{self.user} is now online!')
        try:
            guild = discord.Object(id=1341986883282014220)
            synced = await self.tree.sync(guild=guild)
            print(f'{len(synced)} commands are now synced.')
        except Exception as e:
            print(f'There was an error syncing commands: {e}.')
        await client.change_presence(activity=discord.Activity(name="Dragon Draw", type=discord.ActivityType.playing))
        try:
            initDatabase()
            print("The database has been successfully initialized.")
        except Error as e:
            print(f'There was an error initializing the database: {e}.')
     
intents = discord.Intents.default()
intents.message_content = True
client = Client(command_prefix="%", intents=intents)
serverid = 1341986883282014220
adminid = 1342022479228698687
logid = 1342027034733576243


# Permissions Manager
async def checkEmployeePerms(interaction: discord.Interaction, message: str) -> bool:
    allowed_roles = ["General Manager", "Manager", "Dealer", "Customer Service"]
    user_roles = [role.name for role in interaction.user.roles]
    user = interaction.user.name
    print(f"{user} has roles: {user_roles}")
    if any(role.name in allowed_roles for role in interaction.user.roles):
        return True
    else:
        await interaction.response.send_message(content=f"You **do not have permission** to {message}.", ephemeral=True)

async def checkAdminPerms(interaction: discord.Interaction, message: str) -> bool:
    allowed_roles = ["General Manager", "Manager"]
    user_roles = [role.name for role in interaction.user.roles]
    user = interaction.user.name
    print(f"{user} has roles: {user_roles}")
    if any(role.name in allowed_roles for role in interaction.user.roles):
        return True
    else:
        await interaction.response.send_message(content=f"You **do not have permission** to {message}.", ephemeral=True)
    


# Chips System
chipsgroup = app_commands.Group(name="chips", description="Commands for the Dragon Casino chips balance system.", guild_ids=[serverid])
client.tree.add_command(chipsgroup)
balance = 0

@chipsgroup.command(name="balance", description="Display your chips balance!")
@app_commands.describe(user="The user whose balance you wish to check. (Optional)")
async def showChipsBalance(interaction: discord.Interaction, user: discord.Member = None):
    if user == None:
        user = interaction.user
        await interaction.response.send_message(content=f"You have **{balance:,}** chips.", ephemeral=True)
    else:
        if await checkEmployeePerms(interaction, "check the balance of other users") == True:
            await interaction.response.send_message(content=f"{user.mention} has **{balance:,}** chips.", ephemeral=True)
    
@chipsgroup.command(name="deposit", description="Buy chips and add them to your balance!")
@app_commands.describe(quantity="The amount you wish to deposit.", proof="Attach proof of your deposit to Dragon Casino. See #policies for supported payment methods.")
async def depositChips(interaction: discord.Interaction, quantity: int, proof: discord.Attachment):
    if quantity > 0:
        await interaction.response.send_message(content=f"You have submitted a deposit request for **{quantity:,}** chips. It will be reviewed by a manager as soon as possible.\n{proof}", ephemeral=True)
        conn = sqlite3.connect("dragoncasino.db")
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO transactions (user, type, amount, status)
            VALUES (?, 'deposit', ?, 'pending')
            """, (interaction.user.id, quantity)
        )
        conn.commit()
        conn.close()
    else:
        await interaction.response.send_message(content="You must deposit an amount greater than zero.", ephemeral=True)
    
@chipsgroup.command(name="withdraw", description="Cash chips out to a supported currency and location!")
@app_commands.describe(quantity="The amount you wish to withdraw.", currency="The currency you wish to cash your chips out to. The exchange rate may not be 1:1, see #policies.", location="The location you wish to have your money sent to.")
@app_commands.choices(currency=[app_commands.Choice(name="Redmont Dollars", value="dollars"), app_commands.Choice(name="Alexandria Pounds", value="pounds")], location=[app_commands.Choice(name="In-Game Balance", value="ingame"), app_commands.Choice(name="Vanguard Bank", value="vanguard"), app_commands.Choice(name="Volt Bank", value="volt"), app_commands.Choice(name="Voyager Bank", value="voyager")])
async def withdrawChips(interaction: discord.Interaction, quantity: int, currency: app_commands.Choice[str], location: app_commands.Choice[str]):
    if quantity > 0:
        await interaction.response.send_message(content=f"You have submitted a withdraw request for **{quantity:,}** chips to {currency.name} at {location.name}. It will be actioned by a manager as soon as possible.", ephemeral=True)
        conn = sqlite3.connect("dragoncasino.db")
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO transactions (user, type, amount, status)
            VALUES (?, 'withdrawal', ?, 'pending')
            """, (interaction.user.id, quantity)
        )
        conn.commit()
        conn.close()
    else:
        await interaction.response.send_message(content="You must withdraw an amount greater than zero.", ephemeral=True)
    

@chipsgroup.command(name="mint", description="Mint a number of chips to someone's balance!")
@app_commands.describe(quantity="The amount you wish to mint.", user="The person to mint chips to.")
@app_commands.default_permissions(view_audit_log=True)
async def mintChips(interaction: discord.Interaction, quantity: int, user: discord.Member):
    if await checkEmployeePerms(interaction, "mint chips to someone's balance") == True:
        await interaction.response.send_message(content=f"You have minted **{quantity:,}** chips to {user.mention}.", ephemeral=True)

@chipsgroup.command(name="delete", description="Delete a number of chips from someone's balance!")
@app_commands.describe(quantity="The amount you wish to delete.", user="The person to delete chips from.")
@app_commands.default_permissions(ban_members=True)
async def deleteChips(interaction: discord.Interaction, quantity: int, user: discord.Member):
    if await checkAdminPerms(interaction, "delete chips from someone's balance") == True:
        await interaction.response.send_message(content=f"You have deleted **{quantity:,}** chips from {user.mention}.", ephemeral=True)

@chipsgroup.command(name="set", description="Set someone's chip balance to a certain value!")
@app_commands.describe(quantity="The amount you wish to set the user\'s balance to.", user="The person to adjust the balance of.")
@app_commands.default_permissions(ban_members=True)
async def setChips(interaction: discord.Interaction, quantity: int, user: discord.Member):
    if await checkAdminPerms(interaction, "set someone's chip balance") == True:
        await interaction.response.send_message(content=f"You have set {user.mention}\'s balance to **{quantity:,}** chips.", ephemeral=True)



# Bingo
bingogroup = app_commands.Group(name="bingo", description="Commands for the Dragon Casino bingo game.", guild_ids=[serverid])
client.tree.add_command(bingogroup)

@bingogroup.command(name="buy", description="Purchase cards for bingo!")
async def buyBingoTickets(interaction: discord.Interaction):
    await interaction.response.send_message("You have purchased X cards for bingo.")


# Blackjack
blackjackgroup = app_commands.Group(name="blackjack", description="Commands for the Dragon Casino blackjack game.", guild_ids=[serverid])
client.tree.add_command(blackjackgroup)

@blackjackgroup.command(name="join", description="Join the blackjack table!")
async def joinBlackjack(interaction: discord.Interaction):
    await interaction.response.send_message("You have joined the blackjack table.")


# Craps
crapsgroup = app_commands.Group(name="craps", description="Commands for the Dragon Casino craps game.", guild_ids=[serverid])
client.tree.add_command(crapsgroup)

@crapsgroup.command(name="join", description="Join the craps table!")
async def joinCraps(interaction: discord.Interaction):
    await interaction.response.send_message("You have joined the craps table.")


# Dragon Draw
dragondrawgroup = app_commands.Group(name="dragondraw", description="Commands for the Dragon Casino Dragon Draw game.", guild_ids=[serverid])
client.tree.add_command(dragondrawgroup)
ddjackpot = 10000
dddrawtime = 12
ticketprice = 10

def performDDDraw():
    ...

def buyDDTickets(quanity: int):
    ...

@dragondrawgroup.command(name="buy", description="Purchase tickets for Dragon Draw manually!")
@app_commands.describe(num1="Your first number.", num2="Your second number.", num3="Your third number.", num4="Your fourth number.", num5="Your fifth number.")
async def buyDDManual(interaction: discord.Interaction, num1: int, num2: int, num3: int, num4: int, num5: int):
    await interaction.response.send_message(content=f"You have purchased a ticket for the Dragon Draw with the following numbers: {num1}, {num2}, {num3}, {num4}, and {num5}.", ephemeral=True)

@dragondrawgroup.command(name="autobuy", description="Purchase tickets for Dragon Draw automatically!")
@app_commands.describe(number="The number of tickets you wish to purchase.")
async def buyDDAuto(interaction: discord.Interaction, number: int):
    await interaction.response.send_message(content=f"You have purchased {number} tickets for the Dragon Draw.", ephemeral=True)

@dragondrawgroup.command(name="jackpot", description="Check the current Dragon Draw jackpot and next drawing!")
async def checkDDJackpot(interaction: discord.Interaction):
    await interaction.response.send_message(content=f"The jackpot is now ${ddjackpot:,.2f} and the next drawing is in {dddrawtime:.2f} hours. Buy tickets now!", ephemeral=True)

@dragondrawgroup.command(name="draw", description="Manually perform a Dragon Draw drawing!")
@app_commands.default_permissions(ban_members=True)
async def checkDDJackpot(interaction: discord.Interaction):
    if await checkAdminPerms(interaction, "perform a manual Dragon Drawing") == True:
        performDDDraw()
        await interaction.response.send_message(content=f"Drawing", ephemeral=True)



# Poker
pokergroup = app_commands.Group(name="poker", description="Commands for the Dragon Casino poker game.", guild_ids=[serverid])
client.tree.add_command(pokergroup)

@pokergroup.command(name="buy-in", description="Offer your buy-in to the dealer for safekeeping!")
async def buyinPoker(interaction: discord.Interaction):
    await interaction.response.send_message("You have bought in to the poker table with $X.")


# Roulette
roulettegroup = app_commands.Group(name="roulette", description="Commands for the Dragon Casino roulette game.", guild_ids=[serverid])
client.tree.add_command(roulettegroup)

@roulettegroup.command(name="bet", description="Place a bet at the roulette table!")
async def betRoulette(interaction: discord.Interaction):
    await interaction.response.send_message("You have placed a bet on X for $Y at the roulette table.")


# Slots
slotsgroup = app_commands.Group(name="slots", description="Commands for the Dragon Casino slots game.", guild_ids=[serverid])
client.tree.add_command(slotsgroup)

@slotsgroup.command(name="create", description="Purchase tickets for the Dragon Draw game!")
@app_commands.default_permissions(ban_members=True)
async def createSlots(interaction: discord.Interaction):
    if await checkAdminPerms(interaction, "create slot machines") == True:
        await interaction.response.send_message("You have created a new slot machine.")



client.run('MTM0MjM3NDE1MjMzNzc1MjE5Ng.G3dTng.kUsLbGhb1WQ0kc0g-KdjjeFudzG58Vu5805bcY')