---
name: apple-music-playlist-sync
description: Add Apple Music catalog songs from a text list to an existing Apple Music playlist using a local MusicKit auth helper, Apple Music API matching, iCloud Music Library updates, and background Music AppleScript. Use when the user wants playlist songs added without controlling the Music UI, when Music import cannot resolve catalog tracks, or when a playlist needs API/local-library syncing.
---

# Apple Music Playlist Sync

Use this skill when the user wants Codex to add songs from a text list into Apple Music without taking over the computer UI.

## Operating Rules

- Do not use Computer Use or click Music UI unless the user explicitly asks for UI control.
- Do not click Play, Pause, artwork, miniplayer controls, queue controls, or search result cells.
- Keep all normal work in terminal/background scripts.
- Never print or paste the `.p8` private key contents or Music user token.
- Do not assume Apple Music import can resolve catalog songs from plain text; Music import is for local files/playlists.
- If direct API playlist editing fails, use the approved workaround: add catalog songs to iCloud Music Library, then copy library tracks into the target playlist with AppleScript.

## Known Brian Defaults

- MusicKit key path: `/Users/brianfopiano/Library/Mobile Documents/com~apple~CloudDocs/HighSecurity/Apple Keys/AuthKey_JK2AW4NZ4K.p8`
- Key ID: `JK2AW4NZ4K`
- Team ID that validated for Apple Music API: `RK2CYG6XRV`
- Prior target playlist: `"Vintage"` including the quote characters.
- Prior readable source list path: `/Users/brianfopiano/Desktop/Vintage_Expanded_Playlist_Readable.md`

Treat these as convenient defaults, not universal requirements. Confirm with the current user request when the playlist or source file differs.

## How To Find Music And Playlists

Use AppleScript for local Music inspection:

```applescript
tell application "Music"
  return player state as text
end tell
```

Count a playlist whose name literally includes quotes:

```applescript
tell application "Music"
  return count of tracks of playlist "\"Vintage\""
end tell
```

Enumerate matching playlists across Music sources when counts look inconsistent:

```applescript
tell application "Music"
  set out to ""
  repeat with s in sources
    set out to out & "SOURCE: " & (name of s as text) & linefeed
    repeat with p in playlists of s
      try
        if (name of p as text) contains "Vintage" then
          set out to out & "  playlist: " & (name of p as text) & " kind=" & (class of p as text) & " count=" & (count of tracks of p) & " id=" & (persistent ID of p as text) & linefeed
        end if
      end try
    end repeat
  end repeat
  return out
end tell
```

Inspect the Music scripting dictionary if needed:

```bash
sdef /System/Applications/Music.app | rg -n "search|playlist|track|location|URL|import|add|duplicate|library"
```

Important dictionary facts:

- `add` adds files to Music; it does not resolve Apple Music catalog tracks from a text list.
- `search` searches local playlists/library; it does not search the Apple Music catalog.
- `duplicate chosenTrack to playlist ...` copies a local/library track into a user playlist in the background.

## Local Authorization Flow

1. Find a MusicKit private key file, normally `AuthKey_*.p8`.
2. Derive Key ID from the filename unless the user supplies another one.
3. Generate an ES256 developer JWT locally.
4. Test candidate Team IDs against `GET https://api.music.apple.com/v1/test`; use the one returning `200`.
5. Start `scripts/music_auth_helper.py` to serve a localhost MusicKit page.
6. Ask the user to open the local URL, click Authorize Apple Music, and tell you when done.
7. Verify `/tmp/apple_music_user_token.txt` exists and the helper `/status` endpoint says `authorized`.

Use this helper:

```bash
python3 /Users/brianfopiano/.codex/skills/apple-music-playlist-sync/scripts/music_auth_helper.py \
  --team-id RK2CYG6XRV \
  --key-id JK2AW4NZ4K \
  --key-path "/Users/brianfopiano/Library/Mobile Documents/com~apple~CloudDocs/HighSecurity/Apple Keys/AuthKey_JK2AW4NZ4K.p8" \
  --port 8765
```

Then the user opens:

```text
http://localhost:8765/
```

## API Playlist Workflow

Use `scripts/music_playlist_sync.py` for the actual work.

Dry run:

```bash
python3 /Users/brianfopiano/.codex/skills/apple-music-playlist-sync/scripts/music_playlist_sync.py \
  --source-file "/Users/brianfopiano/Desktop/Vintage_Expanded_Playlist_Readable.md" \
  --playlist "\"Vintage\"" \
  --team-id RK2CYG6XRV \
  --key-id JK2AW4NZ4K \
  --key-path "/Users/brianfopiano/Library/Mobile Documents/com~apple~CloudDocs/HighSecurity/Apple Keys/AuthKey_JK2AW4NZ4K.p8" \
  --user-token-file /tmp/apple_music_user_token.txt \
  --dry-run
```

Apply the working fallback:

```bash
python3 /Users/brianfopiano/.codex/skills/apple-music-playlist-sync/scripts/music_playlist_sync.py \
  --source-file "/Users/brianfopiano/Desktop/Vintage_Expanded_Playlist_Readable.md" \
  --playlist "\"Vintage\"" \
  --team-id RK2CYG6XRV \
  --key-id JK2AW4NZ4K \
  --key-path "/Users/brianfopiano/Library/Mobile Documents/com~apple~CloudDocs/HighSecurity/Apple Keys/AuthKey_JK2AW4NZ4K.p8" \
  --user-token-file /tmp/apple_music_user_token.txt \
  --add-to-library \
  --copy-to-playlist
```

The script will:

- Parse numbered `Title - Artist (Year)` or `Title — Artist (Year)` lines.
- Call `GET /v1/me/storefront`.
- Call `GET /v1/me/library/playlists` and find the exact target playlist.
- Search catalog songs with `GET /v1/catalog/{storefront}/search`.
- Score by title, artist tokens, and year.
- Save dry-run JSON/Markdown under `/tmp`.
- Add matched songs to iCloud Music Library with `POST /v1/me/library?ids[songs]=...`.
- Copy now-library-visible songs into the target playlist using background AppleScript.

## Direct Playlist Add Caveat

Apple Music API may show the target playlist with `canEdit: false` even when Music.app UI can add songs. In that case, `POST /v1/me/library/playlists/{playlist_id}/tracks` can return:

```text
Unable to update tracks
```

Do not keep retrying direct playlist adds. Use the library-add plus local duplicate workaround.

## Edge Cases

- Artist metadata can differ after catalog add. Example: `The Warrior - Scandal feat. Patty Smyth` may appear as `The Warrior - Scandal & Patty Smyth`.
- If the bulk copy reports a higher count but a quick count reports the old count, enumerate playlists across sources before assuming failure.
- Apple library sync can lag. Poll local Music search for a few representative tracks before copying all tracks.
- The Music API can return `202` for library add; that means accepted, not necessarily immediately visible locally.

## Cleanup

After the task, stop any local auth helper process and keep `/tmp/apple_music_user_token.txt` private. Remove it if the user wants no token left behind.
