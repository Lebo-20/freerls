import httpx
import logging
from config import BASE_URL, FREEREELS_API_KEY, LANG

logger = logging.getLogger(__name__)

class FreeReelsAPI:
    def __init__(self, token=FREEREELS_API_KEY):
        self.token = token
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "User-Agent": "FreeReelsBot/1.0"
        }
        self.base_params = {"lang": LANG}

    async def _request(self, method, endpoint, params=None, **kwargs):
        url = f"{BASE_URL}/{endpoint.lstrip('/')}"
        combined_params = self.base_params.copy()
        if params:
            combined_params.update(params)
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.request(method, url, params=combined_params, headers=self.headers, **kwargs)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP error occurred: {e.response.status_code} - {e.response.text}")
                return None
            except Exception as e:
                logger.error(f"An error occurred: {str(e)}")
                return None

    # Discovery
    async def get_foryou(self):
        return await self._request("GET", "/foryou")

    async def get_popular(self, page=0):
        return await self._request("GET", "/popular", params={"page": page})

    async def get_new(self, page=0):
        return await self._request("GET", "/new", params={"page": page})

    async def get_coming_soon(self):
        return await self._request("GET", "/coming-soon")

    # Category
    async def get_female(self, page=0):
        return await self._request("GET", "/female", params={"page": page})

    async def get_male(self, page=0):
        return await self._request("GET", "/male", params={"page": page})

    async def get_anime(self, page=0):
        return await self._request("GET", "/anime", params={"page": page})

    async def get_dubbing(self, page=0):
        return await self._request("GET", "/dubbing", params={"page": page})

    # Search
    async def search(self, query, page=0):
        return await self._request("GET", "/search", params={"q": query, "page": page})

    async def search_suggest(self, query):
        return await self._request("GET", "/search/suggest", params={"q": query})

    # Detail
    async def get_drama_detail(self, drama_id):
        return await self._request("GET", f"/dramas/{drama_id}")

    # Episodes
    async def get_episodes(self, drama_id):
        return await self._request("GET", f"/dramas/{drama_id}/episodes")

    # Stream
    async def get_stream(self, drama_id, ep):
        return await self._request("GET", f"/dramas/{drama_id}/play/{ep}")
