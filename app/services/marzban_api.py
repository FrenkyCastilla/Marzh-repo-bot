import aiohttp
import logging
from typing import Optional, Dict, Any, List, Union
from ..core.config import settings

logger = logging.getLogger(__name__)

class MarzbanAPI:
    def __init__(self):
        self.host = settings.MARZBAN_HOST.rstrip('/')
        self.username = settings.MARZBAN_USERNAME
        self.password = settings.MARZBAN_PASSWORD
        self.token: Optional[str] = None
        self.cached_tag: Optional[str] = None 

    async def _get_token(self) -> Optional[str]:
        url = f"{self.host}/api/admin/token"
        data = {"username": self.username, "password": self.password}
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, data=data, ssl=False) as response:
                    if response.status == 200:
                        self.token = (await response.json()).get("access_token")
                        return self.token
                    logger.error(f"Auth failed: {response.status}")
                    return None
        except Exception as e:
            logger.error(f"Auth error: {e}")
            return None

    async def _get_headers(self):
        if not self.token:
            await self._get_token()
        return {"Authorization": f"Bearer {self.token}"}

    async def _get_real_inbound_tag(self) -> str:
        """Находит реальный тег VLESS"""
        if self.cached_tag:
            return self.cached_tag

        url = f"{self.host}/api/inbounds"
        headers = await self._get_headers()
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, ssl=False) as response:
                    if response.status == 200:
                        data = await response.json()
                        inbounds_list = []
                        if isinstance(data, dict):
                            if "inbounds" in data and isinstance(data["inbounds"], list):
                                inbounds_list = data["inbounds"]
                            elif "data" in data and isinstance(data["data"], list):
                                inbounds_list = data["data"]
                            else:
                                for key, val in data.items():
                                    if "vless" in str(key).lower() and isinstance(val, list) and len(val) > 0:
                                        self.cached_tag = val[0].get("tag")
                                        return self.cached_tag
                        elif isinstance(data, list):
                            inbounds_list = data

                        for inbound in inbounds_list:
                            if isinstance(inbound, dict) and inbound.get("protocol") == "vless":
                                self.cached_tag = inbound.get("tag")
                                return self.cached_tag
        except Exception:
            pass
        
        return settings.INBOUND_TAG

    def _fix_subscription_url(self, data: Dict[str, Any]) -> Dict[str, Any]:
        if not data: return data
        sub_url = data.get("subscription_url", "")
        if sub_url.startswith("/"):
            data["subscription_url"] = f"{self.host}{sub_url}"
        return data

    async def create_user(self, username: str, data_limit: int, expire: int) -> Optional[Dict[str, Any]]:
        url = f"{self.host}/api/user"
        headers = await self._get_headers()
        
        target_tag = await self._get_real_inbound_tag()
        
        # LYRA FIX: РАЗДЕЛЕНИЕ СУЩНОСТЕЙ
        # 1. Proxies отвечает за настройки протокола (flow)
        proxies = {
            "vless": {
                "flow": ""
            }
        }

        # 2. Inbounds отвечает за ВКЛЮЧЕНИЕ протокола (галочка)
        inbounds = {
            "vless": [target_tag]
        }

        # Собираем правильную структуру JSON
        payload = {
            "username": username,
            "proxies": proxies,
            "inbounds": inbounds, 
            "data_limit": data_limit * 1024 * 1024 * 1024,
            "expire": expire,
            "status": "active"
        }

        logger.info(f"📤 SENDING CORRECT PAYLOAD: {payload}")
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, headers=headers, ssl=False) as response:
                    if response.status == 200:
                        return self._fix_subscription_url(await response.json())
                    elif response.status == 409:
                        modify_url = f"{self.host}/api/user/{username}"
                        async with session.put(modify_url, json=payload, headers=headers, ssl=False) as mod_resp:
                            if mod_resp.status == 200:
                                return self._fix_subscription_url(await mod_resp.json())
                            return None
                    elif response.status == 401:
                        self.token = None
                        return await self.create_user(username, data_limit, expire)
                    else:
                        logger.error(f"Error {response.status}: {await response.text()}")
                        return None
        except Exception as e:
            logger.error(f"Connection error: {e}")
            return None

    # Остальные методы (get/modify/delete)
    async def get_user(self, username: str) -> Optional[Dict[str, Any]]:
        url = f"{self.host}/api/user/{username}"
        headers = await self._get_headers()
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, ssl=False) as res:
                    return self._fix_subscription_url(await res.json()) if res.status == 200 else None
        except: return None

    async def modify_user(self, username: str, payload: Dict[str, Any]) -> bool:
        url = f"{self.host}/api/user/{username}"
        headers = await self._get_headers()
        try:
            async with aiohttp.ClientSession() as session:
                async with session.put(url, json=payload, headers=headers, ssl=False) as res:
                    return res.status == 200
        except: return False

    async def delete_user(self, username: str) -> bool:
        url = f"{self.host}/api/user/{username}"
        headers = await self._get_headers()
        try:
            async with aiohttp.ClientSession() as session:
                async with session.delete(url, headers=headers, ssl=False) as res:
                    return res.status == 200
        except: return False
