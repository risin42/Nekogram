import contextlib
import os
from pathlib import Path
from sys import argv

from pyrogram import Client
from pyrogram.types import InputMediaDocument

api_id = os.environ.get("APP_ID")
api_hash = os.environ.get("APP_HASH")
artifacts_path = Path("artifacts")
metadata_chat_id = argv[3] if len(argv) > 3 else None
ABI_ORDER = ["arm64-v8a", "universal"]


def find_apk(abi: str) -> Path | None:
    return next((apk for apk in artifacts_path.rglob("*.apk") if abi in apk.name), None)


def get_apks() -> list[Path]:
    apks: list[Path] = []
    for abi in ABI_ORDER:
        if apk := find_apk(abi):
            apks.append(apk)
    return apks


def get_commit_info() -> tuple[str, str, str]:
    commit_id_raw = os.environ.get("COMMIT_ID") or "unknown"
    commit_id = commit_id_raw[:7]
    commit_url = os.environ.get("COMMIT_URL") or "https://github.com/risin42/Nekogram/commits"
    commit_message = os.environ.get("COMMIT_MESSAGE") or "unknown"
    return commit_id, commit_url, commit_message


def get_caption() -> str:
    commit_id, commit_url, commit_message = get_commit_info()
    caption = ""
    caption += f"Commit Message:\n<blockquote expandable>{commit_message}</blockquote>\n\n"
    caption += f"See commit details [{commit_id}]({commit_url})"
    return caption


def get_document() -> list[InputMediaDocument]:
    apks = get_apks()
    if not apks:
        raise FileNotFoundError("No APKs found in downloaded artifacts.")

    documents = [InputMediaDocument(media=str(apk)) for apk in apks]

    caption = get_caption()
    if len(caption) > 1024:
        caption = caption[:1020] + "..."
    documents[-1].caption = caption
    return documents


def get_metadata() -> str:
    commit_id = "<code>" + (os.environ.get("COMMIT_ID") or "unknown")[:7] + "</code>"
    commit_message = "<code>" + (os.environ.get("COMMIT_MESSAGE") or "unknown") + "</code>"
    build_timestamp = "<code>" + (os.environ.get("BUILD_TIMESTAMP") or "-1") + "</code>"
    return build_timestamp + " " + commit_id + "\n" + commit_message


def retry(func):
    async def wrapper(*args, **kwargs):
        for attempt in range(3):
            try:
                return await func(*args, **kwargs)
            except Exception as exc:
                print(exc)
                if attempt == 2:
                    raise

    return wrapper


@retry
async def send_to_channel(client: Client, chat_id: str):
    with contextlib.suppress(ValueError):
        chat_id = int(chat_id)
    await client.send_media_group(chat_id, media=get_document())


@retry
async def send_metadata(client: Client, chat_id: str):
    with contextlib.suppress(ValueError):
        chat_id = int(chat_id)
    await client.send_message(chat_id=chat_id, text=get_metadata())


def get_client(bot_token: str) -> Client:
    return Client(
        "helper_bot",
        api_id=api_id,
        api_hash=api_hash,
        bot_token=bot_token,
    )


async def main():
    bot_token = argv[1]
    chat_id = argv[2]
    client = get_client(bot_token)
    await client.start()
    await send_to_channel(client, chat_id)
    if metadata_chat_id:
        await send_metadata(client, metadata_chat_id)
    await client.log_out()


if __name__ == "__main__":
    from asyncio import run

    run(main())
