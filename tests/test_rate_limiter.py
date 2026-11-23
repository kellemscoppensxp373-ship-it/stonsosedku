import asyncio

from app.rate_limiter import RateLimiter


class FakeClock:
    def __init__(self):
        self.now = 0.0
        self.calls = []

    def clock(self):
        return self.now

    async def sleep(self, delay):
        await asyncio.sleep(0)
        self.now += delay


def test_first_call_is_immediate_and_next_waits_full_interval():
    fake = FakeClock()
    limiter = RateLimiter(15, fake.clock, fake.sleep)
    async def run():
        await limiter.wait_turn()
        assert fake.now == 0
        assert limiter.seconds_until_slot() == 15
        await limiter.wait_turn()
        assert fake.now == 15
        assert limiter.seconds_until_slot() == 15
    asyncio.run(run())


def test_concurrent_calls_are_serialized_by_single_lock():
    fake = FakeClock()
    limiter = RateLimiter(15, fake.clock, fake.sleep)
    async def run():
        await asyncio.gather(*(limiter.wait_turn() for _ in range(5)))
    asyncio.run(run())
    assert fake.now == 60
