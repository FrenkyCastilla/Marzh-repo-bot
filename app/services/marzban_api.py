import aiohttp
import logging
from typing import Optional, Dict, Any
from ..core.config import settings

logger = logging.getLogger(__name__)

class MarzbanAPI:
    def __init__(self):
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
            # FIX: Добавлен ssl=False
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

    async def create_user(self, username: str, data_limit: int, expire: int) -> Optional[Dict[str, Any]]:
        """
        Create a user in Marzban.
        expire: timestamp
        data_limit: in bytes (Marzban uses bytes)
        """
        url = f"{self.host}/api/user"
        headers = await self._get_headers()
        payload = {
            "username": username,
            "proxies": {"vless": {}}, # Default VLESS
            "data_limit": data_limit * 1024 * 1024 * 1024, # GB to Bytes
            "expire": expire
        }
        
        try:
            # FIX: Добавлен ssl=False
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, headers=headers, ssl=False) as response:
                    if response.status == 200:
                        return await response.json()
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
            # FIX: Добавлен ssl=False
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, ssl=False) as response:
                    if response.status == 200:
                        return await response.json()
                    return None
        except Exception as e:
            logger.error(f"Marzban get_user error: {e}")
            return None

    async def modify_user(self, username: str, payload: Dict[str, Any]) -> bool:
        url = f"{self.host}/api/user/{username}"
        headers = await self._get_headers()
        try:
            # FIX: Добавлен ssl=False
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
            # FIX: Добавлен ssl=False
            async with aiohttp.ClientSession() as session:
                async with session.delete(url, headers=headers, ssl=False) as response:
                    return response.status == 200
        except Exception as e:
            logger.error(f"Marzban delete_user error: {e}")
            return False
