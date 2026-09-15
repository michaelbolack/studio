# IRC Media Publishing Suite — Working Changelog

This file is a high-level project checkpoint, not a replacement for Git history.

## Version 126 — Current verified production checkpoint

- Video Studio Tasks 1–5 foundations deployed.
- Expanded Video Studio project persistence deployed.
- Current first unfinished task: Task 6 one-button Video Studio orchestration.

## Version 125

- Shared/versioned caption-template API foundation deployed.
- Admin-only shared template editing rules established.

## Version 124

- Local/free Whisper alignment foundation deployed.
- WebGPU preferred with WASM fallback.
- Word-level speech timing foundation added.

## Version 123

- FFmpeg mixed-media render-graph foundation deployed.
- Aspect-ratio, scene/motion/transition, narration/music, and caption-render support established.

## Version 122

- Article-less story-package importer fix deployed.
- Social-only, audio-only, media, notes, tags, and other non-article packages no longer require article body text to import.

## Version 121

- Shorts audio save/render activation fix deployed.

## Version 120

- Initial Shorts caption-generator MVP deployed; later architectural direction moved captions/rendering into Video Studio instead.

## Repository Memory Rule

When production or the next task changes, update at minimum:

- `PROJECT_STATE.md`
- `NEXT_TASK.md`
- `CHANGELOG.md`

Update `ROADMAP.md` when priorities or ordering change.
