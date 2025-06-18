import asyncio
import httpx
import time
from datetime import datetime

RPC_ENDPOINTS = [
    {
        "name": "Board_2_SRV",
        "clear": "http://0.0.0.0:4053/iotronic/boards/Board_2_SRV/clear_write_to_db",
        "secure": "http://0.0.0.0:4053/iotronic/boards/Board_2_SRV/secure_write_to_db",
    },
    {
        "name": "Board_3_SRV",
        "clear": "http://0.0.0.0:4053/iotronic/boards/Board_3_SRV/clear_write_to_db",
        "secure": "http://0.0.0.0:4053/iotronic/boards/Board_3_SRV/secure_write_to_db",
    },
    {
        "name": "Board_4_SRV",
        "clear": "http://0.0.0.0:4053/iotronic/boards/Board_4_SRV/clear_write_to_db",
        "secure": "http://0.0.0.0:4053/iotronic/boards/Board_4_SRV/secure_write_to_db",
    }
]

INTERVAL = 5 
PAUSE_BETWEEN_CALLS = 10.0
SLEEP_RPC = 5
LOG_FILE = "rpc_benchmark_log_final.csv"

async def benchmark_rpc(client, name, url_clear, url_secure):
    try:
        now = datetime.utcnow().isoformat()

        # clear_write_to_db
        t0 = time.perf_counter()
        clear_resp = await client.get(url_clear)
        clear_resp.raise_for_status()
        t1 = time.perf_counter()
        clear_duration = t1 - t0
        print(f"\n{name} - clear_write_to_db: {clear_duration:.3f} s")

        #await asyncio.sleep(PAUSE_BETWEEN_CALLS)

        # secure_write_to_db
        t2 = time.perf_counter()
        secure_resp = await client.get(url_secure)
        secure_resp.raise_for_status()
        t3 = time.perf_counter()
        secure_duration = t3 - t2
        print(f"{name} - secure_write_to_db: {secure_duration:.3f} s")

        #await asyncio.sleep(SLEEP_RPC)

        with open(LOG_FILE, "a") as f:
            f.write(f"{now},{name},{clear_duration:.3f},{secure_duration:.3f}\n")

    except Exception as e:
        print(f"Errore su {name}: {e}")

async def main_loop():
    try:
        with open(LOG_FILE, "x") as f:
            f.write("timestamp,board,clear_duration,secure_duration\n")
    except FileExistsError:
        pass

    async with httpx.AsyncClient(timeout=httpx.Timeout(60.0)) as client:
        x=0
        while True and x< 100:
            for board in RPC_ENDPOINTS:
                await benchmark_rpc(client, board["name"], board["clear"], board["secure"])
            await asyncio.sleep(INTERVAL)
            x += 1

if __name__ == "__main__":
    asyncio.run(main_loop())
