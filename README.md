# oracle2
*Python-based update tracker for NationStates*

##Overview
*Oracle2* is a cross-platform NationStates update tracker written in Python. It uses daily dump data supplied by NationStates to track the progress of the game's twice-daily regional update in order to make accurate predictions of a region's true update. It does so through a combination of linear regression combined with a correction value based off of observed error between its predictions and true observed times, which can be specified manually or be automatically scraped via API. The program can also be used to quickly generate spreadsheets to aid manual triggering.

It consists of two Python classes:

* `oracle.py` -- Parses daily dump data to predict regional update times and calculates error offsets based on supplied true time data.
* `delphi.py` -- Provides a front-end to Oracle allowing interactive terminal use and automatic API scraping for true update times.

The program is somewhat similar to [ADR-20XX](https://github.com/doomjaw/ADR-20XX/), which uses a slightly more sophisticated tracking algorithim implemented in .NET.

##Getting Started
Download a copy of the latest regions.xml.gz to the same directory as the Oracle2 installation, and run Oracle2 by typing

```python3 delphi.py```

You will be asked to supply your nation name -- This is required by the NationStates terms-of-service.

```
Unique identifier (use an email or nation name): khronion
Update speed values generated on 3/26 (major: spear danes; minor: unity)
Ready.
> 
```

At this point, you may issue commands. A listing of commands taken directly from `delphi2.py` is provided for your reference.

```
t <region> - get region time
m <major|minor> - set update mode to major or minor
r - recall last targeted  region
o <hh:mm:ss> - indicate true update time in hh:mm:ss of last targeted region
c <region> <hh:mm:ss> - calibrate update speed based on time of late updating region
export <filename> - export CSV of oracle data using current update mode
targets <filename> - export CSV of oracle data for founderless regions using current update mode
html <filename> - export HTML of oracle data using current update mode
reload - reload regions.xml.gz and reset Oracle settings to default
start - start automatic region tracking via API (engaged by default)
stop - stop automatic region tracking via API
```

##Disclaimer
Oracle2 is designed to respect the NationStates API ratelimit. However, you may inadvertently exceed the ratelimit if you run multiple instances of Oracle2, or run another API-utilizing program at the same time.
