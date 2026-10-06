# Launch videos (`moneyhub brag`)

Inspired by [latent-spaces/brag](https://github.com/latent-spaces/brag) (MIT). MoneyHub's version is written from scratch in Python and works offline; no code from that project is included.

## What you get
`<product>/brag/` contains `brag.mp4` (12-30 s, H.264 + AAC), `brag.jpg` (poster, also baked in as frame 0 so platforms pick a good thumbnail), `brag-plan.md` (storyboard and the exact facts used), `share-copy.txt` (Pinterest title/description, Instagram, TikTok, X, Reddit, email) and, with voice-over, an `.srt` file.

## Commands
```
moneyhub brag 3                                  # vertical 9:16 video for product #3
moneyhub brag 3 --tone cinematic --format all    # 9:16, 16:9 and 1:1
moneyhub brag 3 --voice auto --captions          # voice-over (Kokoro, macOS say or espeak) + burned captions
moneyhub brag --shop 1,2,3                       # collection / shop video
moneyhub brag --url https://example.com          # website video (needs Playwright + Chromium)
moneyhub brag 3 --music file --music-file my.mp3 # your own licensed track
moneyhub voices install                          # Kokoro model (~350 MB, Apache-2.0)
```
The product page in the web UI has the same options.

## How it works
1. **Facts** come from the product (title, features, audience, pain points, price) or a website. The writer may not claim anything else.
2. **Story**: an LLM (chain `llm.tasks.motion`, e.g. `claude -p`) writes hook, scenes, voice lines and share copy; the result is validated (word limits, banned filler phrases, total length) and retried with feedback; the built-in writer is the fallback, so it works fully offline.
3. **Timeline**: scene lengths honour reading time (0.3 s/word) and voice-over length, and snap to half-beats of the music.
4. **Sound**: procedurally generated music (no samples, no licences), sound effects timed to on-screen events, optional voice-over with ducking, then loudness mastering with ffmpeg.
5. **Render**: every frame is a pure function of time (Pillow), encoded with ffmpeg. Tones: see `src/moneyhub/brag/tones.py` or pass free text such as `--tone "calm and cosy"`.

## Posting
Use the vertical file for Pinterest video pins, Reels, TikTok and Shorts. Read each platform's rules before posting; Reddit communities often restrict self-promotion. Disclose AI assistance where the platform asks. Etsy listing videos must be 5-15 s with no reliance on audio, so trim or use the square cut there.

## Licences
Kokoro (Apache-2.0) and its voices are optional downloads. Generated music and effects are synthesized by MoneyHub code, so you own the output. Your own music file is your responsibility.
