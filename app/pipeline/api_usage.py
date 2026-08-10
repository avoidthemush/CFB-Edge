"""
Tracks how many CFBD API calls a sync script makes in a single run, so we
can keep an eye on our monthly quota (30,000 calls/month on Tier 2) as the
historical backfill grows to cover more endpoints.
"""


class ApiUsageTracker:
    def __init__(self, label: str):
        self.label = label
        self.calls = 0

    def tick(self, n: int = 1):
        self.calls += n

    def report(self):
        print(f"[{self.label}] CFBD API calls made this run: {self.calls}")
