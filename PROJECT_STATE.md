# IRC Media Publishing Suite — Project State

Last updated: 2026-09-15

## Production

- Current verified production version: **126**.
- Production URL: `https://irc-article-audio.michaelbolack.chatgpt.site`
- Do not infer later work as deployed unless a deployment is explicitly verified.

## Video Studio — Current Architecture

Approved direction:

**IRC Video Studio → local Whisper timing → FFmpeg render graph → ASS caption templates → finished MP4**

Normal target workflow: **one-button Generate Video**.

Supported/approved output formats:

- 9:16
- 16:9
- 1:1

Approved inputs/capabilities:

- narration-only audio
- uploaded primary video containing spoken audio
- still images
- additional video clips
- optional script
- optional background music
- automatic scene timing
- pan/zoom/motion and transitions
- dynamic captions
- reusable caption templates
- finished MP4 export

### Completed and deployed foundations — Tasks 1–5

1. Video timing and caption-template foundation.
2. FFmpeg mixed-media render graph foundation.
3. Local/free Whisper alignment foundation with WebGPU and WASM fallback.
4. Shared/versioned caption-template API with admin-only editing rules.
5. Expanded Video Studio project persistence for media, narration, music, timing/alignment data, and caption-template selections.

These foundations exist underneath the Suite. The finished one-button Video Studio interface is **not complete yet**.

## First Unfinished Task

**Task 6 — One-button Video Studio orchestration and preview controls.**

This is the next implementation task. Do not reopen architecture decisions before working it.

## Approved Caption Templates

Initial built-ins:

- IRC News
- Social Bold
- Clean

An Admin Caption Template Manager is approved for a later task so shared templates can be duplicated, customized, versioned, previewed, and reused.

## News Publisher Boundary

Keep the existing Shorts/Reels script and audio-generation workflow in News Publisher.

The old/broken caption-rendering workflow in News Publisher is scheduled for removal later, after the Video Studio workflow replaces it.

## Other Important Project Notes

- Article-less `.ircstory` / `.json` package import is supported and deployed.
- Source/Related Links sections should not be inserted into article bodies.
- Story Projects support social-only, audio-only, media, tags, hashtags, notes, and article workflows.
- 9:16 image and Shorts audio should remain saved with their Story Project.
- Project notes are project-specific; team bulletin notes are author-owned, with admin management rights.
- Tags/hashtags and calendar/UI upgrades are already part of the Suite.

## Paused / Separate Work

### Broadcast Studio / LiveKit

The local LiveKit proof of concept is paused. Do not resume it unless explicitly requested.

### Facebook Attribution

Separate configuration task: investigate changing Facebook attribution from `Posted by IRC Media Publishing Suite` to the public-facing brand `IRC Media`. Keep this separate from Video Studio code.

### White-label / Packaging

A future priority is a minimum white-label configuration foundation so the Suite can be adapted for other independent-media creators. Do not mix this into Task 6.

## Usage-Conservation Rule

At the start of future sessions:

1. Read this file.
2. Read `NEXT_TASK.md`.
3. Read only the specific linked spec/plan/code files needed for that task.
4. Do **not** reconstruct the project by rereading old chats.
5. Do **not** perform broad repository review unless the task requires it.
