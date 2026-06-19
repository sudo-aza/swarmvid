# swarmvid

Swarm-based AI video production pipeline. A blackboard of tasks drives multiple agents to research, write, narrate, illustrate, and deliver a finished documentary video — one task at a time, each deleted on completion.

## Current Project

**Die Geschichte Hannovers** — A short documentary about the history of Hannover, Germany. Narrated in German with Qwen 3 TTS, animated visuals, and source citations.

## How It Works

1. A `BLACKBOARD.md` tracks all tasks in a single table
2. Each task is assigned to an agent and worked independently
3. Completed tasks are deleted from the board
4. When the board is empty — the video is done

## Pipeline

```
Research → Script → TTS → Illustration → Animation → Assembly → Upload
```

## Repo Structure

```
swarmvid/
├── BLACKBOARD.md      ← active task board (only tracking doc)
├── README.md
├── output/             ← final video + assets
└── scripts/            ← generation scripts
```

## License

MIT
