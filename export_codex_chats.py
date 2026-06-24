import json
import pathlib
import re
import sqlite3


THREAD_IDS = [
    "019ef412-6ea0-7791-86cb-d5f30b13a6e9",
    "019ed458-7d58-78d2-8140-c1dc57d86959",
    "019ed441-8958-77c3-947f-8685ca686973",
    "019eed08-0e60-7382-8fac-e8e2370f8028",
    "019eee81-1403-7680-a651-bb2071b79e87",
    "019ed9d2-a30f-7970-afd8-f26578e04045",
]


def slug(value: str) -> str:
    value = re.sub(r'[\\/:*?"<>|]+', "_", value).strip()
    value = re.sub(r"\s+", "_", value)
    return (value[:80] or "thread").strip("_")


def main() -> None:
    root = pathlib.Path(__file__).resolve().parent
    out_dir = root / "chat_exports"
    out_dir.mkdir(exist_ok=True)

    con = sqlite3.connect(r"C:\Users\asia\.codex\state_5.sqlite")
    con.row_factory = sqlite3.Row
    placeholders = ",".join("?" for _ in THREAD_IDS)
    rows = con.execute(
        f"select * from threads where id in ({placeholders}) order by created_at",
        THREAD_IDS,
    ).fetchall()

    index_lines = [
        "# Codex Chat Exports",
        "",
        "이 폴더는 `C:\\Users\\asia\\Documents\\파이널` 프로젝트에 연결된 Codex 채팅 6개의 대화 기록입니다.",
        "",
        "주의: 이 파일들은 Codex 앱의 공식 복원 백업이 아니라, 다른 컴퓨터에서 사람이 읽고 새 Codex 대화에 붙여넣어 맥락을 이어가기 위한 transcript입니다. 원본 JSONL의 시스템 지침, encrypted reasoning, 내부 상태는 제외했습니다.",
        "",
    ]

    for row in rows:
        thread_id = row["id"]
        title = row["title"]
        base_name = f"{row['created_at']}_{slug(title)}_{thread_id[:8]}"
        md_path = out_dir / f"{base_name}.md"
        jsonl_path = out_dir / f"{base_name}.sanitized.jsonl"

        events = []
        rollout_path = pathlib.Path(row["rollout_path"])
        with rollout_path.open(encoding="utf-8", errors="replace") as handle:
            for line in handle:
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if obj.get("type") != "event_msg":
                    continue

                payload = obj.get("payload") or {}
                event_type = payload.get("type")
                event = {"timestamp": obj.get("timestamp"), "type": event_type}

                if event_type == "user_message":
                    event["role"] = "user"
                    event["text"] = payload.get("message", "")
                elif event_type == "agent_message":
                    event["role"] = "assistant"
                    event["phase"] = payload.get("phase")
                    event["text"] = payload.get("message", "")
                elif event_type == "patch_apply_end":
                    changes = payload.get("changes") or {}
                    if isinstance(changes, dict):
                        changed_files = sorted(changes.keys())
                    else:
                        changed_files = []
                    event["summary"] = {
                        "type": event_type,
                        "success": payload.get("success"),
                        "changed_files": changed_files,
                    }
                elif event_type in {
                    "web_search_end",
                    "turn_aborted",
                    "context_compacted",
                    "thread_rolled_back",
                }:
                    event["summary"] = {"type": event_type}
                else:
                    continue
                events.append(event)

        with jsonl_path.open("w", encoding="utf-8", newline="\n") as handle:
            for event in events:
                handle.write(json.dumps(event, ensure_ascii=False) + "\n")

        md_lines = [
            f"# {title}",
            "",
            f"- Thread ID: `{thread_id}`",
            f"- Created: `{row['created_at']}`",
            f"- Updated: `{row['updated_at']}`",
            f"- Original rollout path: `{row['rollout_path']}`",
            "",
            "## Transcript",
            "",
        ]

        for event in events:
            timestamp = event.get("timestamp") or ""
            if event.get("role") == "user":
                md_lines.extend(
                    [f"### User - {timestamp}", "", event.get("text", "").strip(), ""]
                )
            elif event.get("role") == "assistant":
                phase = event.get("phase") or "message"
                md_lines.extend(
                    [
                        f"### Assistant ({phase}) - {timestamp}",
                        "",
                        event.get("text", "").strip(),
                        "",
                    ]
                )
            elif event.get("type"):
                md_lines.extend(
                    [
                        f"### Event: {event.get('type')} - {timestamp}",
                        "",
                        "```json",
                        json.dumps(event.get("summary", {}), ensure_ascii=False, indent=2),
                        "```",
                        "",
                    ]
                )

        md_path.write_text("\n".join(md_lines), encoding="utf-8", newline="\n")
        index_lines.extend(
            [
                f"- [{title}]({md_path.name})",
                f"  - Thread ID: `{thread_id}`",
                f"  - Sanitized JSONL: `{jsonl_path.name}`",
                "",
            ]
        )

    (out_dir / "README.md").write_text(
        "\n".join(index_lines), encoding="utf-8", newline="\n"
    )
    print(f"Exported {len(rows)} threads to {out_dir}")


if __name__ == "__main__":
    main()
