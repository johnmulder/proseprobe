# Tiny-section checks

This guide explains the worker lifecycle and its operational controls.

## Start

Starts the worker.

## Stop

Stops the worker.

## Retry

Retries failed work.

## Detailed behavior

Workers keep state until shutdown completes safely.

## Logs

Writes local logs.

## Metrics

Records request counts.

# API

## Get worker

Returns worker state.

## Stop worker

Stops one worker.

## Retry worker

Retries one worker.

# FAQ

## What starts it?

The command.

## What stops it?

The signal.

## What retries it?

The worker.

# Release notes

## Added

Worker command.

## Changed

Retry timing.

## Fixed

Shutdown handling.

# Examples

## Start command

Runs one worker.

## Stop command

Stops one worker.

## Retry command

Retries one worker.

# Reference

## Create worker

Creates one worker.

## Delete worker

Deletes one worker.

## List workers

Lists all workers.

# Structured bodies

## Flags

- `--force` skips confirmation.

## Output

| Field | Meaning |
| --- | --- |
| state | Worker state |

## Script

```sh
worker start
```
