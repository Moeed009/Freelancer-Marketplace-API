
import httpx

from app.core.config import settings
from app.core.exceptions import AuthProviderError


def _base_headers() -> dict:
    return {
        "apikey": settings.SUPABASE_ANON_KEY,
        "Content-Type": "application/json",
    }


async def _post(path: str, json: dict, headers: dict | None = None) -> dict:
    url = f"{settings.SUPABASE_URL}/auth/v1{path}"
    merged_headers = {**_base_headers(), **(headers or {})}
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.post(url, json=json, headers=merged_headers)

    

    if response.status_code >= 400:
        detail = response.json().get("error_description") or response.json().get("msg") or response.text
        raise AuthProviderError(detail)

    return response.json()


async def sign_up(email: str, password: str, user_metadata: dict) -> dict:
  
    return await _post("/signup", {
        "email": email,
        "password": password,
        "data": user_metadata,  
    })


async def sign_in_with_password(email: str, password: str) -> dict:
   
    return await _post("/token?grant_type=password", {"email": email, "password": password})


async def refresh_session(refresh_token: str) -> dict:
    
    return await _post("/token?grant_type=refresh_token", {"refresh_token": refresh_token})


async def sign_out(access_token: str) -> None:
    
    url = f"{settings.SUPABASE_URL}/auth/v1/logout"
    headers = {**_base_headers(), "Authorization": f"Bearer {access_token}"}
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.post(url, headers=headers)
    if response.status_code >= 400 and response.status_code != 401:
       
        raise AuthProviderError(f"Logout failed: {response.text}")
