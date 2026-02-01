import aiohttp
import logging
from typing import Optional, Dict, Any
from ..core.config import settings

logger = logging.getLogger(__name__)

class MarzbanAPI:
    def __init__(self):
        # Гарантируем, что в конце хоста нет слеша, чтобы не было двойных //
        self.host = settings.MARZBAN_HOST.rstrip('/')
        self.username = settings.MARZBAN_USERNAME
        self.password = settings.MARZBAN_PASSWORD
        self.token: Optional[str] = None

    async def _get_token(self) -> Optional[str]:
        url = f"{self.host}/api/admin/token"
        data = {
            "username": self.username,
            "password": self.password
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, data=data, ssl=False) as response:
                    if response.status == 200:
                        result = await response.json()
                        self.token = result.get("access_token")
                        return self.token
                    else:
                        logger.error(f"Failed to get Marzban token: {response.status}")
                        return None
        except Exception as e:
            logger.error(f"Error connecting to Marzban: {e}")
            return None

    async def _get_headers(self):
        if not self.token:
            await self._get_token()
        return {"Authorization": f"Bearer {self.token}"}

    def _fix_subscription_url(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Магия: Если ссылка относительная (/sub/...), превращаем её в абсолютную (https://...)
        """
        if not data:
            return data
            
        sub_url = data.get("subscription_url", "")
        if sub_url and sub_url.startswith("/"):
            # Склеиваем хост и путь
            data["subscription_url"] = f"{self.host}{sub_url}"
            logger.info(f"Fixed subscription URL: {data['subscription_url']}")
            
        return data

    async def create_user(self, username: str, data_limit: int, expire: int) -> Optional[Dict[str, Any]]:
        """
        Create OR Update (Renew) a user in Marzban.
        """
        url = f"{self.host}/api/user"
        headers = await self._get_headers()
        payload = {
            "username": username,
            "proxies": {"vless": {}}, 
            "data_limit": data_limit * 1024 * 1024 * 1024, # GB to Bytes
            "expire": expire,
            "status": "active"
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                # 1. Попытка создания
                async with session.post(url, json=payload, headers=headers, ssl=False) as response:
                    if response.status == 200:
                        data = await response.json()
                        return self._fix_subscription_url(data) # <--- ЧИНИМ ССЫЛКУ ТУТ
                    
                    # 2. Если юзер уже есть - ОБНОВЛЯЕМ
                    elif response.status == 409:
                        logger.info(f"User {username} exists. Updating...")
                        modify_url = f"{self.host}/api/user/{username}"
                        async with session.put(modify_url, json=payload, headers=headers, ssl=False) as mod_response:
                            if mod_response.status == 200:
                                data = await mod_response.json()
                                return self._fix_subscription_url(data) # <--- И ТУТ
                            else:
                                logger.error(f"Failed to renew user. Status: {mod_response.status}")
                                return None

                    elif response.status == 401: # Token expired
                        self.token = None
                        return await self.create_user(username, data_limit, expire)
                    else:
                        logger.error(f"Marzban create_user error: {response.status}")
                        return None
        except Exception as e:
            logger.error(f"Marzban connection error: {e}")
            return None

    async def get_user(self, username: str) -> Optional[Dict[str, Any]]:
        url = f"{self.host}/api/user/{username}"
        headers = await self._get_headers()
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, ssl=False) as response:
                    if response.status == 200:
                        data = await response.json()
                        return self._fix_subscription_url(data)
                    return None
        except Exception as e:
            logger.error(f"Marzban get_user error: {e}")
            return None

    async def modify_user(self, username: str, payload: Dict[str, Any]) -> bool:
        url = f"{self.host}/api/user/{username}"
        headers = await self._get_headers()
        try:
            async with aiohttp.ClientSession() as session:
                async with session.put(url, json=payload, headers=headers, ssl=False) as response:
                    return response.status == 200
        except Exception as e:
            logger.error(f"Marzban modify_user error: {e}")
            return False

    async def delete_user(self, username: str) -> bool:
        url = f"{self.host}/api/user/{username}"
        headers = await self._get_headers()
        try:
            async with aiohttp.ClientSession() as session:
                async with session.delete(url, headers=headers, ssl=False) as response:
                    return response.status == 200
        except Exception as e:
            logger.error(f"Marzban delete_user error: {e}")
            return False
