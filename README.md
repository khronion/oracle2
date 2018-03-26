**I am no longer developing any of my NationStates-related projects. Any individual may fork this codebase under the terms of the GNU General Public License, v. 3. Please see <http://www.gnu.org/licenses/> for details.**

# oracle2

*Python-based update tracker for NationStates*

## Overview

Oracle2 is a cross-platform NationStates update tracker written in Python. It uses daily dump data supplied by NationStates to track the progress of the game's twice-daily regional update in order to make accurate predictions of a region's true update. It does so through a combination of linear regression combined with a correction value based off of observed error between its predictions and true observed times, which can be specified manually or be automatically scraped via API. The program can also be used to quickly generate spreadsheets to aid manual triggering.

It consists of two Python classes:

* `oracle.py` -- Parses daily dump data to predict regional update times and calculates error offsets based on supplied true time data.
* `delphi.py` -- Provides automatic API scraping and a basic text user interface for making Oracle queries during an update.

The program is similar to [ADR-20XX](https://github.com/doomjaw/ADR-20XX/), which uses a slightly more sophisticated tracking algorithm implemented in C#. Unlike Oracle2, ADR-20XX requires an internet connection during operation, whereas Oracle2 can be operated fully offline once an API dump is downloaded.

## Getting Started

Run Oracle2 by running:

```python3 delphi.py```

You will be asked to supply your nation name for the user-agent, as required by the NationStates Terms of Service.

```
Primary Nation Name: khronion
Do you want to download the latest daily dump? (Y/N) n

Last target:  (Type 'r' to recall time prediction.)
[02:41:22 UTC] DELPHI>
> 
```

At this point, you may issue commands.

```
t <region>      Get region time
r               Recall last targeted region
m <major|minor> Set update mode to major or minor
o <MM SS>       Indicate true update time in minutes and seconds of last targeted region
n <seconds>     Add/subtract from nudge value to offset all future predictions.
                If blank, resets nudge.
start           Start automatic tracking
stop            Stop automatic tracking
pull            Manually trigger an API query (only works if automatic tracking is not running)
                WARNING: calling this command repeatedly could trigger an API rate limit violation!
dbg             Toggle debug messages
```

## Disclaimer

Oracle2 is designed to respect the NationStates API rate limit. However, you may inadvertently exceed the rate limit if you run multiple instances of Oracle2 or run another API-utilizing program at the same time.
