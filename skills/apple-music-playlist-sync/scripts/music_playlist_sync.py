#!/usr/bin/env python3
"""Apple Music API matcher plus background Music playlist sync.

This script avoids Music UI control. It uses Apple Music API for catalog search
and library updates, then uses Music AppleScript to copy library tracks into an
existing playlist.
"""

from __future__ import annotations

import argparse
import base64
import json
import re
import ssl
import subprocess
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

import certifi
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, utils

API = "https://api.music.apple.com"


def b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def make_developer_token(team_id: str, key_id: str, key_path: Path, ttl_seconds: int = 3600) -> str:
    private_key = serialization.load_pem_private_key(key_path.read_bytes(), password=None)
    now = int(time.time())
    header = {"alg": "ES256", "kid": key_id}
    payload = {"iss": team_id, "iat": now, "exp": now + ttl_seconds}
    signing_input = (
        b64url(json.dumps(header, separators=(",", ":")).encode("utf-8"))
        + "."
        + b64url(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    )
    der = private_key.sign(signing_input.encode("ascii"), ec.ECDSA(hashes.SHA256()))
    r_value, s_value = utils.decode_dss_signature(der)
    signature = r_value.to_bytes(32, "big") + s_value.to_bytes(32, "big")
    return signing_input + "." + b64url(signature)


def encode_params(params: dict[str, Any] | None) -> str:
    clean: dict[str, str] = {}
    for key, value in (params or {}).items():
        if value is None:
            continue
        if isinstance(value, (list, tuple)):
            value = ",".join(str(item) for item in value)
        else:
            value = str(value)
        if value:
            clean[key] = value
    return urllib.parse.urlencode(clean, quote_via=urllib.parse.quote)


class AppleMusicClient:
    def __init__(self, developer_token: str, user_token: str) -> None:
        self.developer_token = developer_token
        self.user_token = user_token
        self.context = ssl.create_default_context(cafile=certifi.where())

    def request(self, method: str, path: str, body: Any = None, params: dict[str, Any] | None = None) -> Any:
        url = API + path
        query = encode_params(params)
        if query:
            url += "?" + query
        headers = {"Authorization": "Bearer " + self.developer_token, "Music-User-Token": self.user_token}
        data = None
        if body is not None:
            data = json.dumps(body).encode("utf-8")
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, context=self.context, timeout=30) as resp:
                raw = resp.read()
                return resp.status, json.loads(raw.decode("utf-8")) if raw else None
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8", "replace")
            redacted_url = re.sub(r"term=[^&]+", "term=[redacted-term]", url)
            raise RuntimeError(f"{method} {redacted_url} HTTP {exc.code}: {raw[:800]}") from exc

    def paged(self, path: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        data: list[dict[str, Any]] = []
        _, payload = self.request("GET", path, params=params)
        while True:
            data.extend(payload.get("data", []))
            next_path = payload.get("next")
            if not next_path:
                return data
            parsed = urllib.parse.urlparse(next_path)
            query = dict(urllib.parse.parse_qsl(parsed.query))
            _, payload = self.request("GET", parsed.path, params=query)


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKD", text or "")
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.lower().replace("’", "'").replace("‘", "'").replace("&", " and ")
    text = re.sub(r"\bfeat\.?\b|\bfeaturing\b", " ", text)
    text = re.sub(r"\([^)]*(remaster|mono|stereo|single version|deluxe|live|mix|edit|version)[^)]*\)", " ", text)
    text = re.sub(r"\[[^]]*(remaster|mono|stereo|single version|deluxe|live|mix|edit|version)[^]]*\]", " ", text)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def artist_tokens(text: str) -> set[str]:
    text = re.sub(r"\b(the|and|with)\b", " ", normalize(text))
    return {part for part in text.split() if len(part) > 1}


def parse_source(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    pattern = re.compile(r"^\s*(\d+)\.\s*(.*?)\s+(?:—|-)\s+(.*?)\s*(?:\((\d{4})\))?\s*$")
    for line in path.read_text(encoding="utf-8").splitlines():
        match = pattern.match(line)
        if match:
            rows.append(
                {
                    "index": int(match.group(1)),
                    "title": match.group(2).strip(),
                    "artist": match.group(3).strip(),
                    "year": match.group(4),
                }
            )
    return rows


def score_match(wanted: dict[str, Any], song: dict[str, Any]) -> tuple[int, str]:
    attrs = song.get("attributes", {})
    wanted_title = normalize(wanted["title"])
    got_title = normalize(attrs.get("name", ""))
    wanted_artist = artist_tokens(wanted["artist"])
    got_artist = artist_tokens(attrs.get("artistName", ""))
    score = 0
    reasons: list[str] = []
    if got_title == wanted_title:
        score += 70
        reasons.append("exact title")
    elif wanted_title in got_title or got_title in wanted_title:
        score += 45
        reasons.append("near title")
    else:
        wanted_words = set(wanted_title.split())
        got_words = set(got_title.split())
        overlap = len(wanted_words & got_words) / max(1, len(wanted_words | got_words))
        score += int(35 * overlap)
        reasons.append(f"title overlap {overlap:.2f}")
    if wanted_artist and wanted_artist <= got_artist:
        score += 30
        reasons.append("artist contains all tokens")
    elif wanted_artist & got_artist:
        score += int(20 * len(wanted_artist & got_artist) / len(wanted_artist))
        reasons.append("artist partial")
    release_date = attrs.get("releaseDate") or ""
    if wanted.get("year") and release_date.startswith(wanted["year"]):
        score += 5
        reasons.append("year")
    if any(word in got_title for word in ["live ", "karaoke", "tribute"]) and "live" not in wanted_title:
        score -= 25
        reasons.append("version penalty")
    if "remix" in got_title and "remix" not in wanted_title:
        score -= 20
        reasons.append("remix penalty")
    return score, ", ".join(reasons)


def playlist_count(playlist: str) -> str:
    script = f'tell application "Music"\nreturn count of tracks of playlist {json.dumps(playlist)}\nend tell\n'
    return subprocess.check_output(["osascript", "-e", script], text=True).strip()


def copy_to_playlist(source_file: Path, playlist: str) -> str:
    script = f'''
on trimText(t)
  set whiteSpace to {{" ", tab, return, linefeed}}
  repeat while t is not "" and whiteSpace contains character 1 of t
    set t to text 2 thru -1 of t
  end repeat
  repeat while t is not "" and whiteSpace contains character -1 of t
    if (count of t) is 1 then
      set t to ""
      exit repeat
    else
      set t to text 1 thru -2 of t
    end if
  end repeat
  return t
end trimText

on splitText(t, delim)
  set oldDelims to AppleScript's text item delimiters
  set AppleScript's text item delimiters to delim
  set parts to text items of t
  set AppleScript's text item delimiters to oldDelims
  return parts
end splitText

on stripYear(t)
  set parts to my splitText(t, " (")
  return my trimText(item 1 of parts)
end stripYear

on parseLine(lineText)
  set lineText to my trimText(lineText)
  if lineText is "" then return missing value
  set dotParts to my splitText(lineText, ". ")
  if (count of dotParts) < 2 then return missing value
  set bodyParts to items 2 thru -1 of dotParts
  set oldDelims to AppleScript's text item delimiters
  set AppleScript's text item delimiters to ". "
  set body to bodyParts as text
  set AppleScript's text item delimiters to oldDelims
  set dashParts to my splitText(body, " — ")
  if (count of dashParts) < 2 then set dashParts to my splitText(body, " - ")
  if (count of dashParts) < 2 then return missing value
  set titleText to my trimText(item 1 of dashParts)
  set artistText to my stripYear(item 2 of dashParts)
  return {{titleText, artistText}}
end parseLine

tell application "Music"
  set sourceFile to POSIX file {json.dumps(str(source_file))} as alias
  set rawText to read sourceFile as «class utf8»
  set p to playlist {json.dumps(playlist)}
  set lib to library playlist 1
  set beforeCount to count of tracks of p
  set addedLines to {{}}
  set missedLines to {{}}
  repeat with lineText in paragraphs of rawText
    set parsed to my parseLine(lineText as text)
    if parsed is not missing value then
      set wantedTitle to item 1 of parsed
      set wantedArtist to item 2 of parsed
      set q to wantedTitle & " " & wantedArtist
      set alreadyFound to false
      try
        if (count of (search p for q only songs)) > 0 then set alreadyFound to true
      end try
      if not alreadyFound then
        set candidates to {{}}
        try
          set candidates to search lib for q only songs
        end try
        if (count of candidates) is 0 then
          try
            set candidates to search lib for wantedTitle only songs
          end try
        end if
        if (count of candidates) > 0 then
          try
            duplicate item 1 of candidates to p
            set end of addedLines to wantedTitle & " — " & wantedArtist
          on error errMsg
            set end of missedLines to wantedTitle & " — " & wantedArtist & " [duplicate failed: " & errMsg & "]"
          end try
        else
          set end of missedLines to wantedTitle & " — " & wantedArtist
        end if
      end if
    end if
  end repeat
  set afterCount to count of tracks of p
end tell

set oldDelims to AppleScript's text item delimiters
set AppleScript's text item delimiters to linefeed
set addedText to addedLines as text
set missedText to missedLines as text
set AppleScript's text item delimiters to oldDelims
return "before=" & beforeCount & linefeed & "after=" & afterCount & linefeed & "added_count=" & (count of addedLines) & linefeed & addedText & linefeed & "missed_count=" & (count of missedLines) & linefeed & missedText
'''
    return subprocess.check_output(["osascript", "-e", script], text=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Match Apple Music catalog songs and sync them to a Music playlist.")
    parser.add_argument("--source-file", required=True, type=Path)
    parser.add_argument("--playlist", required=True)
    parser.add_argument("--team-id", required=True)
    parser.add_argument("--key-id", required=True)
    parser.add_argument("--key-path", required=True, type=Path)
    parser.add_argument("--user-token-file", required=True, type=Path)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--add-to-library", action="store_true")
    parser.add_argument("--copy-to-playlist", action="store_true")
    parser.add_argument("--score-threshold", default=75, type=int)
    parser.add_argument("--out-prefix", default="/tmp/apple_music_playlist_sync")
    args = parser.parse_args()

    developer_token = make_developer_token(args.team_id, args.key_id, args.key_path)
    user_token = args.user_token_file.read_text(encoding="utf-8").strip()
    client = AppleMusicClient(developer_token, user_token)

    _, storefront_payload = client.request("GET", "/v1/me/storefront")
    storefront = storefront_payload["data"][0]["id"]
    playlists = client.paged("/v1/me/library/playlists", {"limit": 100})
    matches = [item for item in playlists if item.get("attributes", {}).get("name") == args.playlist]
    if not matches:
        raise SystemExit(f"Could not find exact playlist {args.playlist!r}")
    playlist = matches[0]
    playlist_id = playlist["id"]

    source_rows = parse_source(args.source_file)
    results: list[dict[str, Any]] = []
    for row in source_rows:
        _, search = client.request(
            "GET",
            f"/v1/catalog/{storefront}/search",
            params={"term": f"{row['title']} {row['artist']}", "types": "songs", "limit": 10},
        )
        songs = search.get("results", {}).get("songs", {}).get("data", [])
        scored = []
        for song in songs:
            score, why = score_match(row, song)
            scored.append({"score": score, "why": why, "song": song})
        scored.sort(key=lambda item: item["score"], reverse=True)
        best = scored[0] if scored else None
        if best and best["score"] >= args.score_threshold:
            results.append({"source": row, "status": "matched", "match": best})
        elif best:
            results.append({"source": row, "status": "uncertain", "match": best, "alternates": scored[:5]})
        else:
            results.append({"source": row, "status": "unmatched"})

    summary: dict[str, int] = {}
    for result in results:
        summary[result["status"]] = summary.get(result["status"], 0) + 1

    out_json = Path(args.out_prefix + ".json")
    out_md = Path(args.out_prefix + ".md")
    out_json.write_text(
        json.dumps({"storefront": storefront, "playlist_id": playlist_id, "summary": summary, "results": results}, indent=2),
        encoding="utf-8",
    )
    lines = [
        "# Apple Music Playlist Sync Dry Run",
        "",
        f"- Storefront: {storefront}",
        f"- Playlist: {args.playlist}",
        f"- Playlist API id: {playlist_id}",
        f"- Summary: {summary}",
        "",
    ]
    for result in results:
        source = result["source"]
        if result["status"] in {"matched", "uncertain"}:
            attrs = result["match"]["song"]["attributes"]
            prefix = "ADD" if result["status"] == "matched" else "REVIEW"
            lines.append(
                f"- {prefix} #{source['index']}: {source['title']} - {source['artist']} => "
                f"{attrs.get('name')} - {attrs.get('artistName')} [{result['match']['song']['id']}] "
                f"score={result['match']['score']}"
            )
        else:
            lines.append(f"- MISS #{source['index']}: {source['title']} - {source['artist']}")
    out_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"storefront": storefront, "playlist_id": playlist_id, "summary": summary, "dry_run_json": str(out_json), "dry_run_md": str(out_md)}, indent=2))

    matched_ids: list[str] = []
    seen: set[str] = set()
    for result in results:
        if result["status"] == "matched":
            song_id = str(result["match"]["song"]["id"])
            if song_id not in seen:
                seen.add(song_id)
                matched_ids.append(song_id)

    if args.add_to_library:
        for index in range(0, len(matched_ids), 25):
            chunk = matched_ids[index : index + 25]
            client.request("POST", "/v1/me/library", params={"ids[songs]": ",".join(chunk)})
            print(f"library chunk {index // 25 + 1}: accepted {len(chunk)}")
            time.sleep(1.0)

    if args.copy_to_playlist:
        print(copy_to_playlist(args.source_file, args.playlist))
        print(f"verified_count={playlist_count(args.playlist)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
