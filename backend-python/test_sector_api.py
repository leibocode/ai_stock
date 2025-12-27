import httpx
import asyncio

async def test():
    url = 'https://push2.eastmoney.com/api/qt/clist/get'
    params = {
        'pn': '1',
        'pz': '10',
        'np': '1',
        'fltt': '2',
        'invt': '2',
        'fid': 'f3',
        'fs': 'm:90+t:2',
        'fields': 'f12,f14,f3,f62',
    }
    try:
        async with httpx.AsyncClient(timeout=30, verify=False) as client:
            resp = await client.get(url, params=params)
            print('Status:', resp.status_code)
            data = resp.json()
            print('Data keys:', list(data.keys()))
            diff = data.get('data', {}).get('diff', [])
            print('Diff count:', len(diff))
            if diff:
                print('First item:', diff[0])
    except Exception as e:
        print(f'Error: {type(e).__name__}: {e}')

asyncio.run(test())
