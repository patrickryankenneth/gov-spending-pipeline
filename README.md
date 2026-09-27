# gov-spending-pipeline

**Status: work in progress / exploratory.** This is a data-gathering and pipeline testbed, not a packaged tool — the goal is volume, not polish.

## What this is

A resumable bulk downloader for USASpending.gov's Prime Award transaction data, pulled via the [official bulk download API](https://github.com/fedspendingtransparency/usaspending-api/blob/master/usaspending_api/api_contracts/contracts/v2/bulk_download/awards.md) rather than scraping or pagination.

`rank_agencies.py` ranks toptier federal agencies by budget authority so the puller can target high-spend agencies first instead of working through the list alphabetically. `bulk_download.py` then loops agencies × year-quarters, requests a CSV export per slice, polls until generation finishes, and downloads the result — skipping anything already on disk via a manifest, so a crash or a Ctrl-C partway through a multi-hour pull doesn't cost you the progress already made.

## Why

[civic-data-pipeline](https://github.com/patrickryankenneth/civic-data-pipeline) worked with a fundamentally small dataset — a few thousand contract records, a few hundred vendors. The joins and transforms that project needed didn't come close to justifying distributed tooling.

This one is the opposite case on purpose: multi-year, multi-agency federal transaction data at a scale where single-machine pandas starts to strain, as a reason to actually reach for Spark, Kafka, or similar rather than simulating the need for them. Early stage — right now this is download infrastructure; the transform/analysis layer (temporal analysis, large joins, cleanup at scale) hasn't been built yet.

## Stack so far

Python, `requests`. Rate-limited and resumable by design — a politeness delay between new download requests, and a manifest-backed skip so re-runs don't redo completed work.

## Status

Not a published package (unlike `alpine-fleet` and `python-wheels`, which ship to PyPI) — this is pipeline/data-engineering material, built to demonstrate handling real volume rather than to be installed or used by others.