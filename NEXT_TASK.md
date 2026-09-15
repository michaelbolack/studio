# NEXT TASK — Video Studio Task 6

## Goal

Finish the **one-button Generate Video** workflow inside Video Studio using the already-built Tasks 1–5 foundations.

Do not redesign the architecture. Do not start Task 7.

## Required User Workflow

The normal workflow should be:

1. Choose/upload narration or a primary video containing narration.
2. Add images and/or additional video clips.
3. Optionally provide the script.
4. Optionally add background music.
5. Choose output format: 9:16, 16:9, or 1:1.
6. Choose caption template.
7. Press **Generate Video** once.
8. Receive a finished MP4.

## Generate Video Pipeline

The button should orchestrate the existing foundations in this order:

1. Prepare media.
2. Reuse cached alignment if narration fingerprint is unchanged; otherwise run local Whisper.
3. Build word-timestamp-aligned caption data.
4. Create automatic scene timing around natural speech pauses.
5. Apply existing motion/transitions.
6. Mix narration and optional music with narration priority/ducking.
7. Build ASS captions from the selected template.
8. Render through the FFmpeg graph.
9. Produce/download the final MP4.

## Required UI Behavior

Show clear stages:

- Preparing
- Aligning speech
- Building scenes
- Rendering
- Ready

Required controls:

- Generate Video
- Cancel while generating
- Retry after failure
- Preview Play/Pause
- Preview Stop
- Scrubbing where practical
- Download finished MP4

The last successful MP4 must remain available if a later render fails or is cancelled.

## Inputs

Support from the start:

- audio narration
- primary uploaded video with spoken audio
- images
- extra video clips
- optional script
- optional music

One primary source supplies spoken narration. Extra video clips are silent by default unless a later feature explicitly changes that.

## Persistence

Use Task 5 project persistence. Reopening a project should restore the media and render configuration needed to continue working.

Do not create a second persistence system.

## Mobile / Desktop

- Full desktop support is required.
- Project controls should remain usable on mobile.
- Heavy mobile rendering is best-effort due browser memory limits.

## Acceptance Criteria

Task 6 is complete only when:

- one click executes the full pipeline;
- real local Whisper timing is used rather than estimated pacing;
- all three output formats are selectable;
- captions are included in the finished MP4;
- images/video scenes render with motion/transitions;
- narration + optional music are mixed correctly;
- progress/cancel/retry work;
- preview can Play/Pause/Stop;
- existing saved-project behavior remains compatible;
- automated tests pass;
- production build passes.

## Stop Condition

After Task 6 is tested and deployed, stop.

Do not start:

- Task 7 template manager UI
- Task 8 News Publisher caption cleanup
- Task 9 final broad verification
- LiveKit work
- white-label work
