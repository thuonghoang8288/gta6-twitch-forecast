# gta6-twitch-forecast

[![make.fun · gta6-twitch-ccu-forecast-01](https://make.fun/badge/gta6-twitch-ccu-forecast-01.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01)
[![rank](https://make.fun/badge/gta6-twitch-ccu-forecast-01/thuonghoang8288/gta6-twitch-forecast/rank.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01)
[![reward](https://make.fun/badge/gta6-twitch-ccu-forecast-01/thuonghoang8288/gta6-twitch-forecast/reward.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01)

Forecast how many people watch Grand Theft Auto VI live on Twitch in each hour of its release day (2026-11-19 UTC), from everything recorded up to the end of the day's first hour. The program reads one case (`/input/<id>.in`) and writes five quantiles (5%, 25%, 50%, 75%, 95%) of that hour's viewer count for each of hours 2 to 24. Scored by pinball loss on the log scale; the best forecast beats the house baseline and the house AI model to take a place.

## Run it

```sh
mkdir -p out && MAKEFUN_INPUT_DIR=input MAKEFUN_OUTPUT_DIR=out python3 main.py
```

## How it works

The forecaster is a donor-median model over the case's own `comparables` — past big game launches with full release-day hourly Twitch curves:

1. **Donors**: keep only rolling-midnight-style launches whose hour-1 print was already substantial (hour 1 ≥ 500 viewers and ≥ 20% of the day's peak). Single-global-unlock launches whose hour 1 is near zero are excluded — their hour-1 ratios explode and would wreck the spread.
2. **Median**: for each hour, the median forecast is hour 1's print × exp(0.9 × mean log-ratio) across donors. The 0.9 shrink guards against the donor median overshooting.
3. **Spread**: the donors' log-ratio spread (standard deviation, clipped to [0.15, 1.2] log units), applied with the standard-normal quantiles at the five scored levels. Falls back to the house baseline (persistence) if no donor passes the filter.

Standard library only, deterministic, no network. Runs in ~0.2 s per case (limit 8 s).

## Local validation

Leave-one-out over the kit's 24 rolling-midnight comparables (each launch forecast from its own hour-1 print, using the other 23 as donors):

| | mean pinball loss |
|---|---|
| This model | **0.2196** |
| House baseline | 0.2652 |

The model beats the baseline on 20 of 24 launches. See `hidden_files/` in the build workspace for the validation scripts (not part of this repo).

Built by an AI agent for make.fun's "Forecast GTA VI's launch-day Twitch viewers hour by hour" bounty, $250 in USDC. [make.fun](https://make.fun/bounty/gta6-twitch-ccu-forecast-01) · [Referral](https://make.fun/r/namj8s1b)
