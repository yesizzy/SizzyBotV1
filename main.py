import json 
import aiohttp
import rebootpy
from rebootpy.ext import commands 
import pydantic
import logging
import platform
import os
from typing import Optional, Dict, Any 
from pathlib import Path

class AuthCredentials(pydantic.BaseModel):
    device_id: Optional[str] = None
    account_id: Optional[str] = None
    secret_key: Optional[str] = None

class BotSettings(pydantic.BaseModel):
    auth: AuthCredentials
    status_message: str
    platform_type: str
    command_prefix: str = "!"

class Config:
    def __init__(self, config_path: str = "config.json"):
        self.config_path = Path(config_path)

    def load_configuration(self) -> BotSettings:
        if not self.config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")
        
        try:
            with self.config_path.open('r', encoding='utf-8') as config_file:
                config_data = json.load(config_file)
                return BotSettings(**config_data)
        except json.JSONDecodeError as error:
            raise ValueError(f"Invalid JSON configuration: {error}")
        except pydantic.ValidationError as error:
            raise ValueError(f"Configuration validation failed: {error}")



class AuthenticationService:
    @staticmethod
    def create_auth_handler(settings: BotSettings) -> rebootpy.Auth:
        auth_data = settings.auth
        
        if auth_data.device_id and auth_data.secret_key and auth_data.account_id:
            try:
                return rebootpy.DeviceAuth(
                    device_id=auth_data.device_id,
                    secret=auth_data.secret_key,
                    account_id=auth_data.account_id
                )
            except:
                return rebootpy.AdvancedAuth(prompt_device_code=True)
        else:
            return rebootpy.AdvancedAuth(prompt_device_code=True)



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
            
            try:
                async with session.get(self.api_base_url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data['data'][0]['id']
            except Exception as error:
                logging.error(f"Cosmetic search error: {error}")
                return None


class SizzyBot:
    
    def __init__(self):
        self.config_manager = Config()
        self.cosmetics_service = CosmeticsService()
        self.settings = self.config_manager.load_configuration()
        self.bot_instance = self._initialize_bot()
        self._setup_logging()
    
    def _initialize_bot(self) -> commands.Bot:
        auth_handler = AuthenticationService.create_auth_handler(self.settings)
        
        return commands.Bot(
            auth=auth_handler,
            command_prefix=self.settings.command_prefix,
            status=self.settings.status_message
        )
    
    def _setup_logging(self):
        system_user = platform.node() or "neura-user"
        log_format = f"┌[{system_user}]──[SizzyBot]──[%(levelname)s]\n└─ $ %(message)s"
        
        logging.basicConfig(
            level=logging.INFO,
            format=log_format,
            datefmt='%H:%M:%S'
        )
        
        self.logger = logging.getLogger('SizzyBot')
    
    def clear_console(self):
        os_name = platform.system().lower()
        if 'windows' in os_name:
            os.system('cls')
        else:
            os.system('clear')
    
    async def handle_cosmetic_command(self, cosmetic_type: str, item_name: str):
        if cosmetic_type not in self.cosmetics_service.COSMETIC_TYPES:
            self.logger.error(f"Unknown cosmetic type: {cosmetic_type}")
            return
        
        cosmetic_id = await self.cosmetics_service.find_cosmetic_id(item_name, cosmetic_type)
        
        if cosmetic_id and self.bot_instance.party:
            method_name = self.cosmetics_service.COSMETIC_TYPES[cosmetic_type]['method']
            method = getattr(self.bot_instance.party.me, method_name)
            await method(cosmetic_id)
            self.logger.info(f"✓ Equipped: {item_name}")
        else:
            self.logger.error(f"✗ Cosmetic not found: {item_name}")
    
    async def handle_party_join(self, username: str):
        try:
            user_profile = await self.bot_instance.fetch_user(user=username, cache=True)
            if user_profile:
                friend_connection = self.bot_instance.get_friend(user_profile.id)
                if friend_connection:
                    await friend_connection.join_party()
                    self.logger.info(f"✓ Joined {username}'s party")
                else:
                    self.logger.error(f"✗ User not in friends list: {username}")
            else:
                self.logger.error(f"✗ User not found: {username}")
        except Exception as error:
            self.logger.error(f"Party join error: {error}")
    
    async def command_interface(self):
        while self.bot_instance.party:
            try:
                user_input = input("\n🎮 SizzyBot > ").strip()
                if not user_input:
                    continue
                
                if user_input.startswith('!'):
                    parts = user_input[1:].split()  
                    if not parts:
                        continue
                    
                    primary_command = parts[0].lower()
                    arguments = parts[1:]
                    
                    if primary_command == 'clear' or primary_command == 'cls':
                        self.clear_console()
                    elif primary_command == 'outfit':
                        await self.handle_cosmetic_command('outfit', ' '.join(arguments))
                    elif primary_command == 'emote':
                        await self.handle_cosmetic_command('emote', ' '.join(arguments))
                    elif primary_command == 'backpack':
                        await self.handle_cosmetic_command('backpack', ' '.join(arguments))
                    elif primary_command == 'pickaxe':
                        await self.handle_cosmetic_command('pickaxe', ' '.join(arguments))
                    elif primary_command == 'join':
                        await self.handle_party_join(' '.join(arguments))
                    elif primary_command == 'leave':
                        await self.bot_instance.party.me.leave()
                    elif primary_command == 'exit':
                        exit()
                    elif primary_command == 'help':
                        self.display_help()
                    else:
                        self.logger.warning(f"Unknown command: !{primary_command}")
                else:
                    self.logger.info("Type !help for available commands")
                    
            except KeyboardInterrupt:
                self.logger.info("Shutting down SizzyBot...")
                break
            except Exception as error:
                self.logger.error(f"Command error: {error}")
    
    def display_help(self):
        help_text = """
╔═══════════════════════════════════════╗
║             SizzyBot Commands            ║
╠═══════════════════════════════════════╣
║ !outfit <name>    Change skin         ║
║ !emote <name>     Change emote        ║
║ !backpack <name>  Change backpack     ║
║ !pickaxe <name>   Change pickaxe      ║
║ !join <username>  Join party          ║
║ !leave            Leave party         ║
║ !clear/!cls       Clear screen        ║
║ !help             Show this message   ║
║ !exit             Quit application    ║
╚═══════════════════════════════════════╝
        """
        print(help_text)
    
    async def on_ready(self):
        self.clear_console()
        print("╔══════════════════════════════════════╗")
        print("║            SizzyBot Online              ║")
        print("╠══════════════════════════════════════╣")
        self.logger.info(f"Account: {self.bot_instance.user.display_name}")
        self.logger.info(f"Platform: {self.bot_instance.platform.name}")
        self.logger.info("Type !help for available commands")
        print("╚══════════════════════════════════════╝")
        
        await self.command_interface()
    
    def launch(self):
        @self.bot_instance.event
        async def event_ready():
            await self.on_ready()
        
        try:
            self.bot_instance.run()
        except Exception as error:
            self.logger.error(f"Bot startup failed: {error}")

if __name__ == "__main__":
    app = SizzyBot()
    app.launch()
