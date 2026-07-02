"""Telegram → AgentCore bridge: 4 bots in one group, each fronting one Runtime.

Privacy mode (default ON) means each bot only receives messages that @mention it,
reply to it, or are slash commands — so @incident_rca_bot routes straight to that
bot with no central router. On a mention, the bot forwards the text to its
deployed AgentCore Runtime and posts the reply.

Sessions are PER GROUP: session_id = chat + bot (+ /reset epoch). Everyone in the
room shares one conversation per bot. See README.md for the design.

Run:  python bridge.py   (needs the TG_TOKEN_* env vars + AWS creds for the region)
"""
import asyncio
import json
import logging

import boto3
from telegram.ext import Application, CommandHandler, MessageHandler, filters

from config import BOTS, REGION

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
log = logging.getLogger("tg-bridge")

_runtime = boto3.client("bedrock-agentcore", region_name=REGION)
_epochs: dict[tuple[int, str], int] = {}   # (chat_id, bot) → epoch, bumped by /reset


def _session_id(chat_id: int, bot: str) -> str:
    """Per-group session key, ≥33 chars (AgentCore requires it). Deterministic →
    the same room+bot resumes the same microVM; /reset bumps the epoch."""
    epoch = _epochs.get((chat_id, bot), 0)
    return f"tg-{bot}-{chat_id}-e{epoch}".ljust(33, "0")


def _invoke_runtime(arn: str, session_id: str, actor_id: str, prompt: str) -> str:
    """Blocking boto3 call — run via asyncio.to_thread from the async handler."""
    resp = _runtime.invoke_agent_runtime(
        agentRuntimeArn=arn,
        runtimeSessionId=session_id,
        payload=json.dumps({"prompt": prompt, "actor_id": actor_id}).encode(),
    )
    body = resp["response"].read()
    try:
        data = json.loads(body)
        return data.get("response") or json.dumps(data)
    except (ValueError, TypeError):
        return body.decode(errors="replace")


def _make_message_handler(name: str, cfg: dict, username: str):
    async def handler(update, context):
        msg = update.effective_message
        if not msg or not msg.text:
            return
        prompt = msg.text.replace(f"@{username}", "").strip()
        if not prompt:
            await msg.reply_text(f"Hi — I'm the *{name}* agent ({cfg['blurb']}). "
                                 "Mention me with your question.", parse_mode="Markdown")
            return
        chat_id = update.effective_chat.id
        session_id = _session_id(chat_id, name)
        actor_id = f"tg-room-{chat_id}"
        await context.bot.send_chat_action(chat_id, "typing")
        try:
            answer = await asyncio.to_thread(
                _invoke_runtime, cfg["runtime_arn"], session_id, actor_id, prompt)
        except Exception as e:                      # noqa: BLE001 — surface to chat
            log.exception("%s invoke failed", name)
            answer = f"⚠️ runtime error: {e}"
        await msg.reply_text(answer)
    return handler


def _make_reset_handler(name: str):
    async def reset(update, context):
        chat_id = update.effective_chat.id
        _epochs[(chat_id, name)] = _epochs.get((chat_id, name), 0) + 1
        await update.effective_message.reply_text(
            f"🔄 {name}: started a fresh session (state cleared).")
    return reset


async def _start_bot(name: str, cfg: dict) -> Application:
    app = Application.builder().token(cfg["token"]).build()
    me = await app.bot.get_me()
    app.add_handler(CommandHandler("reset", _make_reset_handler(name)))
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND, _make_message_handler(name, cfg, me.username)))
    await app.initialize()
    await app.start()
    await app.updater.start_polling(drop_pending_updates=True)
    log.info("started %s as @%s → %s", name, me.username, cfg["runtime_arn"].split("/")[-1])
    return app


async def main():
    apps = []
    for name, cfg in BOTS.items():
        if not cfg["token"]:
            log.warning("skipping %s — no token (set TG_TOKEN_%s)", name, name.upper())
            continue
        apps.append(await _start_bot(name, cfg))
    if not apps:
        raise SystemExit("No bot tokens set. Export at least one TG_TOKEN_* and retry.")
    log.info("%d bot(s) polling. Ctrl-C to stop.", len(apps))
    try:
        await asyncio.Event().wait()
    finally:
        for app in apps:
            await app.updater.stop()
            await app.stop()
            await app.shutdown()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass
