import json
import aiohttp
import rebootpy
from rebootpy.ext import commands
import platform
import os
import sys
from pathlib import Path

CONFIG_PATH = "config.json"
API_BASE_URL = "https://fortnite-api.com/v2/cosmetics/br/search/all"

COSMETIC_TYPES = {
    'outfit': {'api_type': 'AthenaCharacter', 'method': 'set_outfit'},
    'emote': {'api_type': 'AthenaDance', 'method': 'set_emote'},
    'backpack': {'api_type': 'AthenaBackpack', 'method': 'set_backpack'},
    'pickaxe': {'api_type': 'AthenaPickaxe', 'method': 'set_pickaxe'},
    'sidekick': {'api_type': 'AthenaPet', 'method': 'set_pet'},
    'shoes': {'api_type': 'AthenaShoes', 'method': 'set_shoes'},
    'glider': {'api_type': 'AthenaGlider', 'method': 'set_glider'},
    'contrail': {'api_type': 'AthenaContrail', 'method': 'set_contrail'}
}

def load_settings():
    if not Path(CONFIG_PATH).exists():
        print(f"Config file missing: {CONFIG_PATH}")
        sys.exit(1)
    
    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    auth = data.get('auth', {})
    bot = data.get('bot', {})
    fortnite = data.get('fortnite', {})
    
    return {
        'device_id': auth.get('device_id', ''),
        'account_id': auth.get('account_id', ''),
        'secret_key': auth.get('secret_key', ''),
        'status_message': bot.get('status_message', 'SizzyBotV1'),
        'platform_type': bot.get('platform_type', 'Windows'),
        'command_prefix': bot.get('command_prefix', '!'),
        'default_cosmetic': fortnite.get('default_cosmetic', {}),
        'banner': fortnite.get('banner', {}),
        'party': fortnite.get('party', {}),
        'add_users': fortnite.get('party', {}).get('add_users', True)
    }

async def get_cosmetic_id(item_name, item_type):
    if item_type not in COSMETIC_TYPES:
        return None
    
    params = {
        'name': item_name,
        'backendType': COSMETIC_TYPES[item_type]['api_type']
    }
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(API_BASE_URL, params=params) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data['data']:
                        return data['data'][0]['id']
        except:
            pass
    return None

def setup_bot(settings):
    if settings['device_id'] and settings['secret_key'] and settings['account_id']:
        auth = rebootpy.DeviceAuth(
            device_id=settings['device_id'],
            secret=settings['secret_key'],
            account_id=settings['account_id']
        )
    else:
        auth = rebootpy.AdvancedAuth(prompt_device_code=True)
    
    bot = commands.Bot(
        auth=auth,
        command_prefix=settings['command_prefix'],
        status=settings['status_message']
    )
    
    return bot

def wipe_console():
    if platform.system() == 'Windows':
        os.system('cls')
    else:
        os.system('clear')

async def equip_cosmetic(bot, cosmetic_type, item_name):
    cosmetic_id = await get_cosmetic_id(item_name, cosmetic_type)
    
    if cosmetic_id and bot.party:
        method_name = COSMETIC_TYPES[cosmetic_type]['method']
        method = getattr(bot.party.me, method_name)
        await method(cosmetic_id)
        print(f"Equipped: {item_name}")
    else:
        print(f"Couldn't find: {item_name}")

async def set_default_cosmetics(bot, settings):
    if not bot.party:
        return
    
    default = settings['default_cosmetic']
    
    if default.get('cid'):
        await bot.party.me.set_outfit(default['cid'])
        print(f"Default outfit: {default['cid']}")
    
    if default.get('eid'):
        await bot.party.me.set_emote(default['eid'])
        print(f"Default emote: {default['eid']}")
    
    if default.get('backpack'):
        await bot.party.me.set_backpack(default['backpack'])
    
    if default.get('pickaxe'):
        await bot.party.me.set_pickaxe(default['pickaxe'])
    
    if default.get('sidekick'):
        await bot.party.me.set_pet(default['sidekick'])
    
    if default.get('shoes'):
        await bot.party.me.set_shoes(default['shoes'])
    
    if default.get('glider'):
        await bot.party.me.set_glider(default['glider'])
    
    if default.get('contrail'):
        await bot.party.me.set_contrail(default['contrail'])
    
    banner = settings['banner']
    if banner.get('icon'):
        await bot.party.me.set_banner(
            icon=banner['icon'],
            color=banner.get('color', 'DefaultColor')
        )

async def join_user_party(bot, username):
    try:
        user_profile = await bot.fetch_user(user=username, cache=True)
        if not user_profile:
            print(f"User not found: {username}")
            return
        
        friend = bot.get_friend(user_profile.id)
        if friend:
            await friend.join_party()
            print(f"Joined {username}'s party")
        else:
            print(f"Not friends with: {username}")
    except Exception as e:
        print(f"Join error: {e}")

def show_help():
    print("Commands:")
    print("!outfit <name>    - Change skin")
    print("!emote <name>     - Change emote")
    print("!backpack <name>  - Change backpack")
    print("!pickaxe <name>   - Change pickaxe")
    print("!sidekick <name>  - Change sidekick/pet")
    print("!shoes <name>     - Change shoes")
    print("!glider <name>    - Change glider")
    print("!contrail <name>  - Change contrail")
    print("!join <username>  - Join someone's party")
    print("!leave            - Leave current party")
    print("!clear / !cls     - Clean console")
    print("!help             - Show commands")
    print("!exit             - Quit")

async def handle_commands(bot, settings):
    while bot.party:
        try:
            cmd_input = input("\nSizzyBot > ").strip()
            if not cmd_input:
                continue
            
            if cmd_input[0] != '!':
                continue
            
            parts = cmd_input[1:].split()
            if not parts:
                continue
            
            cmd = parts[0].lower()
            args = parts[1:]
            
            if cmd in ['clear', 'cls']:
                wipe_console()
            elif cmd == 'outfit':
                await equip_cosmetic(bot, 'outfit', ' '.join(args))
            elif cmd == 'emote':
                await equip_cosmetic(bot, 'emote', ' '.join(args))
            elif cmd == 'backpack':
                await equip_cosmetic(bot, 'backpack', ' '.join(args))
            elif cmd == 'pickaxe':
                await equip_cosmetic(bot, 'pickaxe', ' '.join(args))
            elif cmd == 'sidekick':
                await equip_cosmetic(bot, 'sidekick', ' '.join(args))
            elif cmd == 'shoes':
                await equip_cosmetic(bot, 'shoes', ' '.join(args))
            elif cmd == 'glider':
                await equip_cosmetic(bot, 'glider', ' '.join(args))
            elif cmd == 'contrail':
                await equip_cosmetic(bot, 'contrail', ' '.join(args))
            elif cmd == 'join':
                await join_user_party(bot, ' '.join(args))
            elif cmd == 'leave':
                await bot.party.me.leave()
            elif cmd == 'help':
                show_help()
            elif cmd == 'exit':
                sys.exit()
            else:
                print(f"Unknown: !{cmd}")
                
        except KeyboardInterrupt:
            print("Shutting down...")
            break
        except Exception as e:
            print(f"Error: {e}")

async def bot_ready(bot, settings):
    print(f"Logged in as {bot.user.display_name}")
 
    await set_default_cosmetics(bot, settings)
    
    await handle_commands(bot, settings)

def start_bot():
    settings = load_settings()
    bot = setup_bot(settings)
    
    @bot.event
    async def event_ready():
        await bot_ready(bot, settings)
    
    try:
        bot.run()
    except Exception as e:
        print(f"Startup failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    start_bot()
