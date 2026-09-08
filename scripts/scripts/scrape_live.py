#!/usr/bin/env python3
"""Capture live chat from active broadcasts. NOTE: does not fit the GitHub
Actions cron model well (6h job cap, no guaranteed on-time start) -- run as a
separate always-on/polling worker, not via scraper.yml.
"""


def main():
    raise NotImplementedError


if __name__ == "__main__":
    main()
