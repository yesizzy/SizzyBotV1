import json
import aiohttp
import rebootpy
from rebootpy.ext import commands
import pydantic
import platform
import os
from typing import Optional
from pathlib import Path

class BotSettings(pydantic.BaseModel):
    device_id: Optional[str] = None
    account_id: Optional[str] = None
    secret_key: Optional[str] = None
    status_message: str
    platform_type: str
    command_prefix: str = "!"

class Config:
    def __init__(self, config_path: str = "config.json"):
        self.config_path = Path(config_path)

    def load_configuration(self) -> BotSettings:
        if not self.config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")
        
        with self.config_path.open('r', encoding='utf-8') as config_file:
            config_data = json.load(config_file)
            return BotSettings(**config_data)

class CosmeticsService:
    COSMETIC_TYPES = {
        'outfit': {'api_type': 'AthenaCharacter', 'method': 'set_outfit'},
        'emote': {'api_type': 'AthenaDance', 'method': 'set_emote'},
        'backpack': {'api_type': 'AthenaBackpack', 'method': 'set_backpack'},
        'pickaxe': {'api_type': 'AthenaPickaxe', 'method': 'set_pickaxe'}
    }
    
    def __init__(self):
        self.api_base_url = "https://fortnite-api.com/v2/cosmetics/br/search/all"
    
    async def find_cosmetic_id(self, item_name: str, item_type: str) -> Optional[str]:
        async with aiohttp.ClientSession() as session:
            params = {
                'name': item_name,
                'backendType': self.COSMETIC_TYPES[item_type]['api_type']
            }
            
            async with session.get(self.api_base_url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return data['data'][0]['id']
        return None

class SizzyBot:
    def __init__(self):
        self.config_manager = Config()
        self.cosmetics_service = CosmeticsService()
        self.settings = self.config_manager.load_configuration()
        self.bot = self._initialize_bot()
    
    def _initialize_bot(self) -> commands.Bot:
        if self.settings.device_id and self.settings.secret_key and self.settings.account_id:
            auth = rebootpy.DeviceAuth(
                device_id=self.settings.device_id,
                secret=self.settings.secret_key,
                account_id=self.settings.account_id
            )
        else:
            auth = rebootpy.AdvancedAuth(prompt_device_code=True)
        
        return commands.Bot(
            auth=auth,
            command_prefix=self.settings.command_prefix,
            status=self.settings.status_message
        )
    
    def clear_console(self):
        os.system('cls' if platform.system() == 'Windows' else 'clear')
    
    async def handle_cosmetic_command(self, cosmetic_type: str, item_name: str):
        if cosmetic_type not in self.cosmetics_service.COSMETIC_TYPES:
            print(f"Unknown cosmetic type: {cosmetic_type}")
            return
        
        cosmetic_id = await self.cosmetics_service.find_cosmetic_id(item_name, cosmetic_type)
        
        if cosmetic_id and self.bot.party:
            method_name = self.cosmetics_service.COSMETIC_TYPES[cosmetic_type]['method']
            method = getattr(self.bot.party.me, method_name)
            await method(cosmetic_id)
            print(f"Equipped: {item_name}")
        else:
            print(f"Cosmetic not found: {item_name}")
    
    async def handle_party_join(self, username: str):
        try:
            user_profile = await self.bot.fetch_user(user=username, cache=True)
            if user_profile:
                friend_connection = self.bot.get_friend(user_profile.id)
                if friend_connection:
                    await friend_connection.join_party()
                    print(f"Joined {username}'s party")
                else:
                    print(f"User not in friends list: {username}")
            else:
                print(f"User not found: {username}")
        except Exception as e:
            print(f"Party join error: {e}")
    
    async def command_interface(self):
        while self.bot.party:
            try:
                user_input = input("\nSizzyBot > ").strip()
                if not user_input:
                    continue
                
                if user_input.startswith('!'):
                    parts = user_input[1:].split()
                    if not parts:
                        continue
                    
                    command = parts[0].lower()
                    args = parts[1:]
                    
                    if command == 'clear' or command == 'cls':
                        self.clear_console()
                    elif command == 'outfit':
                        await self.handle_cosmetic_command('outfit', ' '.join(args))
                    elif command == 'emote':
                        await self.handle_cosmetic_command('emote', ' '.join(args))
                    elif command == 'backpack':
                        await self.handle_cosmetic_command('backpack', ' '.join(args))
                    elif command == 'pickaxe':
                        await self.handle_cosmetic_command('pickaxe', ' '.join(args))
                    elif command == 'join':
                        await self.handle_party_join(' '.join(args))
                    elif command == 'leave':
                        await self.bot.party.me.leave()
                    elif command == 'exit':
                        exit()
                    elif command == 'help':
                        self.display_help()
                    else:
                        print(f"Unknown command: !{command}")
  
            except KeyboardInterrupt:
                print("Shutting down...")
                break
            except Exception as e:
                print(f"Command error: {e}")
    
    def display_help(self):
        print("Available Commands:")
        print("!outfit <name>    - Change your outfit")
        print("!emote <name>     - Change your emote")
        print("!backpack <name>  - Change your backpack")
        print("!pickaxe <name>   - Change your pickaxe")
        print("!join <username>  - Join a user's party")
        print("!leave            - Leave current party")
        print("!clear / !cls     - Clear console")
        print("!help             - Show this help message")
        print("!exit             - Exit the bot")
    
    async def on_ready(self):
        print(f"Bot is ready as {self.bot.user.display_name}")
        await self.command_interface()
    
    def launch(self):
        @self.bot.event
        async def event_ready():
            await self.on_ready()
        
        try:
            self.bot.run()
        except Exception as e:
            print(f"Bot startup failed: {e}")

if __name__ == "__main__":
    app = SizzyBot()
    app.launch()
