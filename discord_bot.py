import traceback
import asyncio
import aiohttp
import discord
from discord.ext import commands
import time
import datetime
import configparser

config = configparser.ConfigParser()
cfg = config.read("config.ini")
token = config.get("SETTINGS", "DISCORD_BOT_TOKEN")
collection_slug = config.get("SETTINGS", "COLLECTION_SLUG")
traits: list = config.get("SETTINGS", "TRAITS").split('|')
requested_traits: list = config.get("SETTINGS", "TRAITS").split('|')
enable_sales = True if config.get("SETTINGS", "ENABLE_SALES") == 'True' else False
enable_listings = True if config.get("SETTINGS", "ENABLE_LISTINGS") == 'True' else False
enable_status = True if config.get("SETTINGS", "ENABLE_STATUS") == 'True' else False
interval_sales = int(config.get("SETTINGS", "INTERVAL_SALES"))
interval_listings = int(config.get("SETTINGS", "INTERVAL_LISTINGS"))
interval_status = int(config.get("SETTINGS", "INTERVAL_STATUS"))
status_type = config.get("SETTINGS", "STATUS_TYPE")
command_prefix = config.get("SETTINGS", "COMMAND_PREFIX")
api_key = config.get("SETTINGS", "API_KEY")

default_image = "https://storage.googleapis.com/opensea-static/Logomark/Logomark-Blue.png"

collection_data: dict  = {}
trait_data: dict = {}

run_times = {
    'sales': {
        'last_run': int(time.time()) - interval_sales,
        'next_run': int(time.time()),
    },
    'listings': {
        'last_run': int(time.time()) - interval_listings,
        'next_run': int(time.time()),
    },
    'status': {
        'last_run': int(time.time()) - interval_status,
        'next_run': int(time.time()),
    }
}

bot_stats = {
    "one_day_volume": {"commands": ["one_day_volume", "v", "1v", "volume", "vol"], "reply_text": "One Day Volume: "},
    "one_day_change": {"commands": ["one_day_change", "c", "1c", "change"], "reply_text": "One Day Change: "},
    "one_day_sales": {"commands": ["one_day_sales", "s", "1s", "sales"], "reply_text": "One Day Sales: "},
    "one_day_average_price": {"commands": ["one_day_average_price", "1a", "1average"], "reply_text": "One Day Average Price: "},
    "seven_day_volume": {"commands": ["seven_day_volume", "7v"], "reply_text": "Seven Day Volume: "},
    "seven_day_change": {"commands": ["seven_day_change", "7c"], "reply_text": "Seven Day Change: "},
    "seven_day_sales": {"commands": ["seven_day_sales", "7s"], "reply_text": "Seven Day Sales: "},
    "seven_day_average_price": {"commands": ["seven_day_average_price", "7a"], "reply_text": "Seven Day Average Price: "},
    "thirty_day_volume": {"commands": ["thirty_day_volume", "30v"], "reply_text": "Thirty Day Volume: "},
    "thirty_day_change": {"commands": ["thirty_day_change", "30c"], "reply_text": "Thirty Day Change: "},
    "thirty_day_sales": {"commands": ["thirty_day_sales", "30s"], "reply_text": "Thirty Day Sales: "},
    "thirty_day_average_price": {"commands": ["thirty_day_average_price", "30a"], "reply_text": "Thirty Day Average Price: "},
    "total_volume": {"commands": ["total_volume", "tvolume", "tvol"], "reply_text": "Total Volume: "},
    "total_sales": {"commands": ["total_sales", "tsales"], "reply_text": "Total Sales: "},
    "total_supply": {"commands": ["total_supply", "supply"], "reply_text": "Total Supply: "},
    "count": {"commands": ["count"], "reply_text": "Count: "},
    "num_owners": {"commands": ["num_owners", "owners", "own", "hold", "holders"], "reply_text": "Num Owners: "},
    "average_price": {"commands": ["average_price", "ave"], "reply_text": "Average Price: "},
    "num_reports": {"commands": ["num_reports", "reports"], "reply_text": "Num Reports: "},
    "market_cap": {"commands": ["market_cap", "mc", "cap"], "reply_text": "Market Cap: "},
    "floor_price": {"commands": ["floor_price", "floor", "f"], "reply_text": "Floor Price: "}
}

bot_command_list = []
event_list = []
for stat in bot_stats:
    bot_command_list.extend(bot_stats[stat]["commands"])

bot: commands.Bot = commands.Bot(command_prefix=command_prefix, help_command=None)

async def main():
    if requested_traits == ['all']: await update_requested_traits()
    while True:
        if enable_sales and run_times['sales']['next_run'] <= time.time():
            await get_events('sales')
            run_times['sales']['next_run'] = int(time.time()) + interval_sales
        if enable_listings and run_times['listings']['next_run'] <= time.time():
            await get_events('listings')
            run_times['listings']['next_run'] = int(time.time()) + interval_listings
        if enable_status and run_times['status']['next_run'] <= time.time():
            await set_status(status_type)
            run_times['status']['next_run'] = int(time.time()) + interval_status
        await asyncio.sleep(0.1)

@bot.event
async def on_ready():
    print(time.strftime("%Y-%m-%d %H:%M:%S") + ": " + "Logged as: " + bot.user.name + " : " + str(bot.user.id))
    await main()

@bot.command(name="get_one_stat", aliases=bot_command_list)
async def get_one_stat(ctx: discord.Message):
    try:
        command = ctx.invoked_with
        if ctx.author.id == bot.user.id: return  
        reply = ""
        for stat in bot_stats:
            if command in bot_stats[stat]["commands"]:
                stat_value = str(collection_data['stats'][stat])
                try:
                    stat_value = str(round(float(stat_value), 4))
                except ValueError:
                    stat_value = str(stat_value)                   
                reply = bot_stats[stat]["reply_text"] + stat_value
                break
        if reply:            
            message: discord.Embed = discord.Embed(
            color = 0x2081e2,
            description = reply     
            )
            await ctx.channel.send(embed=message)
        print(time.strftime("%Y-%m-%d %H:%M:%S") + ": Message: " + command + " | Reply: " + reply)
    except:
        print(time.strftime("%Y-%m-%d %H:%M:%S") + ": " + traceback.format_exc())
        return False 

@bot.command(name="stats", aliases=["stat", "all_stats", "statistics"])
async def stats(ctx: discord.Message):
    try:
        if ctx.author.id == bot.user.id: return  
        reply = ""
        for stat in bot_stats:
            reply += bot_stats[stat]["reply_text"] + ", ".join(bot_stats[stat]["commands"]) + "\n"
        if reply:            
            message: discord.Embed = discord.Embed(
            color = 0x2081e2,
            description = reply     
            )
            await ctx.channel.send(embed=message)
    except:
        print(time.strftime("%Y-%m-%d %H:%M:%S") + ": " + traceback.format_exc())
        return False

@bot.command(name="help", aliases=["h"])
async def help(ctx: discord.Message):
    try:
        if ctx.author.id == bot.user.id: return  
        reply = ""
        for stats in bot_stats:
            reply += bot_stats[stats]["reply_text"] + ", ".join(bot_stats[stats]["commands"]) + "\n"
        if reply:            
            message: discord.Embed = discord.Embed(
            title = "Bot Commands",
            color = 0x2081e2,
            description = reply     
            )
            await ctx.channel.send(embed=message)
    except:
        print(time.strftime("%Y-%m-%d %H:%M:%S") + ": " + traceback.format_exc())
        return False  

async def set_status(stat):
    try:
        await get_stats()
        stat_value = str(collection_data['stats'][stat])
        try:
            stat_value = str(round(float(stat_value), 4))
        except ValueError:
            stat_value = str(stat_value)            
        print(time.strftime("%Y-%m-%d %H:%M:%S") + ": " + stat + ":" + stat_value)
        status = bot_stats[stat]["reply_text"] + stat_value
        game = discord.Activity(type=discord.ActivityType.watching, name=status)
        await bot.change_presence(status=discord.Status.idle, activity=game)
    except:
        print(time.strftime("%Y-%m-%d %H:%M:%S") + ": " + traceback.format_exc())
        return False    

async def get_stats():
    try:
        global collection_data
        url = "https://api.opensea.io/api/v1/collection/" + collection_slug
        response = await get_data(url)
        collection_data = response['collection']
        return True
    except:
        print(time.strftime("%Y-%m-%d %H:%M:%S") + ": " + traceback.format_exc())
        return False

async def get_events(type):
    try:        

        if type == 'sales': event_type = 'successful'
        if type == 'listings': event_type = 'created'

        url = "https://api.opensea.io/api/v1/events?"
        params = {
            'event_type': event_type,
            'only_opensea': 'true',
            'collection_slug': collection_slug
        }

        events = await get_data(url, params)
        for event in events['asset_events']:            
            await send_event_message(event, type)
        run_times[type]['last_run'] = int(time.time())
        return True

    except:
        print(time.strftime("%Y-%m-%d %H:%M:%S") + ": " + traceback.format_exc())
        return False

async def send_event_message(event: dict, event_type):
    try:
        global event_list
        event_id = event['created_date'] + event_type
        event_time = datetime.datetime.fromisoformat(event['created_date'])
        if event_type == 'sales': start_time = datetime.datetime.utcnow() - datetime.timedelta(0, 5 * interval_sales)
        else: start_time = datetime.datetime.utcnow() - datetime.timedelta(0, 5 * interval_listings)
        if event_time < start_time:
            print(time.strftime("%Y-%m-%d %H:%M:%S") + ": Event rejected as too old: " + event_id)
            return True
        if event_id in event_list:            
            print(time.strftime("%Y-%m-%d %H:%M:%S") + ": Event message already sent: " + event_id)
            return True
        else:
            event_list.append(event_id)

        if event.get('asset'):
            asset_type = 'asset'
            token_contract_address = event['asset']['asset_contract']['address']
            token_id = event['asset']['token_id']
            asset = await get_asset(token_contract_address, token_id)
        else:
            asset_type = 'asset_bundle'

        try:
            seller_name = event['seller']['user']['username']
            if seller_name == None: seller_name = event['seller']['address']
        except:
            seller_name = event['seller']['address']

        if event_type == 'sales':
            try:
                buyer_name = event['winner_account']['user']['username']
                if buyer_name == None: buyer_name = event['winner_account']['address']
            except:
                buyer_name = event['winner_account']['address']

            title_string = "Sale: " + event[asset_type]['name']

        if event_type == 'listings' :
            title_string = "Listing: " + event[asset_type]['name']

        trait_message_data = []
        if requested_traits == ['all']: await update_requested_traits()        
        if requested_traits and asset_type == 'asset':
            if trait_data == {}: await update_trait_data()
            if collection_data == {}: await get_stats()
            for trait in requested_traits:
                for asset_trait in asset['traits']:
                    if asset_trait['trait_type'].lower() == trait.lower():
                        trait_value = str(asset_trait['value'])    
                        if trait_data.get(trait.lower()).get(trait_value.lower()):               
                            stat_count = trait_data[trait.lower()][trait_value.lower()]
                            rarity = " (" + str(round(100*stat_count/collection_data["stats"]["count"], 2)) + "%)"
                        else:
                            rarity = ""                        
                        trait_message_data.append([trait, trait_value + rarity])

        message: discord.Embed = discord.Embed(
            color = 0x2081e2,
            title = title_string,
            url = event[asset_type]['permalink'],        
            timestamp = datetime.datetime.strptime((event['created_date']), '%Y-%m-%dT%H:%M:%S.%f')        
            )
        if asset_type == 'asset':         
            image = event[asset_type]['image_preview_url']
            if collection_data == {}: await get_stats()
            thumbnail = collection_data.get("image_url")
        else:
            if collection_data == {}: await get_stats()
            image = collection_data.get("image_url")
            thumbnail = collection_data.get("image_url") 
        message.set_image(url = image)
        message.set_thumbnail(url = thumbnail)
        message.set_author(name = "OpenSea Bot", url = "https://opensea.io", icon_url = default_image)       
        if event_type == 'sales' : price = round(float(event['total_price'])*10**(-18),4)
        if event_type == 'listings' : price = round(float(event['starting_price'])*10**(-18),4)
        message.add_field(name='Price', value=price, inline=False)
        message.add_field(name='Seller', value=seller_name, inline=False)
        if event_type == 'sales' : message.add_field(name='Buyer', value=buyer_name, inline=False)
        for trait in trait_message_data:            
            message.add_field(name=trait[0], value=trait[1], inline=True)
        if event_type == 'sales' : channel = await bot.fetch_channel(int(config.get("SETTINGS", "DISCORD_CHANNEL_ID_SALES")))
        if event_type == 'listings' : channel = await bot.fetch_channel(int(config.get("SETTINGS", "DISCORD_CHANNEL_ID_LISTINGS")))

        await channel.send(embed=message)
    except:
        print(time.strftime("%Y-%m-%d %H:%M:%S") + ": " + traceback.format_exc())
        return False

async def get_asset(token_contract_address: str, token_id: str):
    try:
        url = "https://api.opensea.io/api/v1/asset/" + token_contract_address + "/" + token_id
        asset = await get_data(url)
        return asset
    except:
        print(time.strftime("%Y-%m-%d %H:%M:%S") + ": " + traceback.format_exc())
        return False

async def update_requested_traits():
    try:
        global requested_traits
        if requested_traits == ['all']:
            if collection_data.get('traits') == None: await get_stats()
            requested_traits = []
            if collection_data.get('traits'):
                for t in collection_data['traits']:
                    requested_traits.append(t.lower())
        return True
    except:
        print(time.strftime("%Y-%m-%d %H:%M:%S") + ": " + traceback.format_exc())
        return False

async def update_trait_data():
    try:
        global trait_data
        if collection_data.get('traits') == None: await get_stats()
        if collection_data.get('traits'):
            for t in collection_data['traits']:
                trait_data[t.lower()] = {}
                for v in collection_data['traits'][t]:
                    trait_data[t.lower()][v.lower()] = collection_data['traits'][t][v]
        return True
    except:
        print(time.strftime("%Y-%m-%d %H:%M:%S") + ": " + traceback.format_exc())
        return False

async def get_data(url: str, params: dict = {}):
    try:
        print(time.strftime("%Y-%m-%d %H:%M:%S") + ": Fetching:" + url + " | Parameters: " + str(params))
        fail_count = 0
        headers = {"X-API-KEY": api_key}
        while fail_count < 3:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, headers=headers) as response:
                    if response.ok:
                        JSON_response = await response.json()
                        print(time.strftime("%Y-%m-%d %H:%M:%S") + ": Successful response. Length:" + str(len(str(JSON_response))))
                        return JSON_response
                    else:
                        fail_count += 1
                        await asyncio.sleep(fail_count)
                        print(time.strftime("%Y-%m-%d %H:%M:%S") + ": " + "API error. Count: " + str(fail_count) + " | " + response.reason)
        return True
    except:
        print(time.strftime("%Y-%m-%d %H:%M:%S") + ": " + traceback.format_exc())
        return False



bot.run(token)