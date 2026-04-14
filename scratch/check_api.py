import httpx
import json

url = 'https://captain.sapimu.au/freereels/api/v1/dramas/1zCArR6Qya/play/1?lang=id-ID'
headers = {'Authorization': 'Bearer 5cf419a4c7fb1c8585314b9f797bf77e7b10a705f32c91aac65b901559780e12'}

r = httpx.get(url, headers=headers)
d = r.json()
print(f'Video: {d.get("video_url")}')
print(f'M3U8: {d.get("m3u8_url")}')
