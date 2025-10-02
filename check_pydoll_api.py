import asyncio
from pydoll.browser import Edge

async def check_api():
    browser = Edge()
    tab = await browser.start()
    print("Tab methods and properties:")
    print('\n'.join([m for m in dir(tab) if not m.startswith('_')]))
    await browser.stop()

asyncio.run(check_api())
