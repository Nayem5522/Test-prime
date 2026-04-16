import asyncio
import logging
import aiohttp
from info import URL

async def ping_server():
    # যদি URL সেট করা না থাকে তবে পিং করার দরকার নেই
    if not URL:
        logging.warning("Keepalive URL is not set. Please set the URL variable.")
        return

    # প্রতি ১০ মিনিট (৬০০ সেকেন্ড) পর পর পিং করবে
    sleep_time = 600 
    logging.info(f"Keepalive started for: {URL}")
    
    while True:
        await asyncio.sleep(sleep_time)
        try:
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=10)
            ) as session:
                async with session.get(URL) as resp:
                    if resp.status == 200:
                        logging.info("Keepalive: Server pinged successfully (Status 200)")
                    else:
                        logging.warning(f"Keepalive: Ping status code {resp.status}")
        except Exception as e:
            logging.error(f"Keepalive Error: {e}")
