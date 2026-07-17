import logging
import os

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from db import clear_seen_listings, get_effective_filters, get_stats, increment_stats, is_seen, mark_seen, set_filter
from scrapers import search_all
from scrapers.base import Listing

logger = logging.getLogger(__name__)
router = Router()

CHAT_ID = int(os.getenv("CHAT_ID", "0"))

_FILTER_KEYS: dict[str, tuple[str, type]] = {
    "city": ("city", str),
    "prezzo_max": ("price_max", int),
    "locali": ("rooms_min", int),
}


@router.message(Command("start"))
async def cmd_start(message: Message) -> None:
    await message.answer(
        "🏠 <b>Bot Casa</b>\n\n"
        "Ricerca annunci ogni 6 ore su immobiliare.it, idealista.it, subito.it e tecnocasa.it.\n\n"
        "<b>Comandi:</b>\n"
        "/filtri — mostra i filtri attivi\n"
        "/set city &lt;città&gt; — imposta la città\n"
        "/set prezzo_max &lt;€&gt; — imposta il prezzo massimo\n"
        "/set locali &lt;n&gt; — imposta il numero minimo di locali\n"
        "/cerca — avvia una ricerca adesso\n"
        "/stats — statistiche annunci controllati e inviati\n"
        "/clear — svuota la cache degli annunci già inviati"
    )


@router.message(Command("filtri"))
async def cmd_filtri(message: Message) -> None:
    f = await get_effective_filters()
    await message.answer(
        "<b>Filtri attivi:</b>\n"
        f"• Città: {f['city']}\n"
        f"• Prezzo max: €{int(f['price_max']):,}\n"
        f"• Locali min: {f['rooms_min']}\n"
    )


@router.message(Command("set"))
async def cmd_set(message: Message) -> None:
    parts = (message.text or "").split(maxsplit=2)
    if len(parts) < 3:
        await message.answer(
            "Uso: /set &lt;chiave&gt; &lt;valore&gt;\n"
            f"Chiavi disponibili: {', '.join(_FILTER_KEYS)}"
        )
        return

    key, value = parts[1].lower(), parts[2].strip()
    if key not in _FILTER_KEYS:
        await message.answer(f"Chiave non valida. Usa: {', '.join(_FILTER_KEYS)}")
        return

    db_key, cast = _FILTER_KEYS[key]
    try:
        cast(value)
    except ValueError:
        await message.answer(f"Valore non valido per <b>{key}</b>.")
        return

    await set_filter(db_key, value)
    await message.answer(f"✅ <b>{key}</b> impostato a: {value}")


@router.message(Command("stats"))
async def cmd_stats(message: Message) -> None:
    s = await get_stats()
    checked = s.get("total_checked", 0)
    sent = s.get("total_sent", 0)
    await message.answer(
        "<b>Statistiche:</b>\n"
        f"• Annunci controllati: <b>{checked:,}</b>\n"
        f"• Annunci inviati: <b>{sent:,}</b>\n"
    )


_CLEAR_KB = InlineKeyboardMarkup(inline_keyboard=[[
    InlineKeyboardButton(text="✅ Sì, svuota", callback_data="clear_confirm"),
    InlineKeyboardButton(text="❌ Annulla", callback_data="clear_cancel"),
]])


@router.message(Command("clear"))
async def cmd_clear(message: Message) -> None:
    await message.answer(
        "⚠️ Tutti gli annunci già inviati verranno dimenticati e "
        "<b>ritrasmessi alla prossima ricerca</b>. Procedere?",
        reply_markup=_CLEAR_KB,
    )


@router.callback_query(F.data == "clear_confirm")
async def cb_clear_confirm(callback: CallbackQuery) -> None:
    count = await clear_seen_listings()
    await callback.message.edit_text(
        f"🗑️ Cache svuotata — {count} annunci rimossi.\n"
        "Al prossimo /cerca verranno reinviati tutti gli annunci trovati."
    )
    await callback.answer()


@router.callback_query(F.data == "clear_cancel")
async def cb_clear_cancel(callback: CallbackQuery) -> None:
    await callback.message.edit_text("Operazione annullata.")
    await callback.answer()


@router.message(Command("cerca"))
async def cmd_cerca(message: Message) -> None:
    await message.answer("🔍 Ricerca in corso…")
    count = await run_search(message.bot)
    if count:
        await message.answer(f"✅ Trovati <b>{count}</b> nuovi annunci.")
    else:
        await message.answer("Nessun nuovo annuncio trovato.")


async def run_search(bot: Bot) -> int:
    if not CHAT_ID:
        logger.warning("CHAT_ID not set — skipping scheduled search")
        return 0

    filters = await get_effective_filters()
    logger.info(f"Search started with filters: {filters}")
    listings, blocked = await search_all(filters)
    logger.info(f"Total listings found: {len(listings)}")

    if "immobiliare" in blocked:
        await _notify_immobiliare_blocked(bot)

    new_count = 0
    for listing in listings:
        if await is_seen(listing.id):
            continue
        await mark_seen(listing.id, listing.source, listing.url)
        try:
            await bot.send_message(CHAT_ID, _format(listing), disable_web_page_preview=True)
            new_count += 1
        except Exception as e:
            logger.error(f"Failed to send listing {listing.id}: {e}")

    await increment_stats(checked=len(listings), sent=new_count)
    return new_count


async def _notify_immobiliare_blocked(bot: Bot) -> None:
    text = (
        "⚠️ <b>immobiliare.it</b> ha bloccato lo scraper (anti-bot).\n\n"
        "Per sbloccarlo, da un PC con schermo, nella cartella <code>t-bots</code>:\n\n"
        "<code>docker compose stop bot-casa\n"
        "cd bot-casa\n"
        ".venv/bin/python scripts/solve_captcha.py</code>\n\n"
        "Risolvi il captcha nella finestra che si apre, premi INVIO nel terminale, poi:\n\n"
        "<code>cd ..\n"
        "docker compose start bot-casa</code>"
    )
    try:
        await bot.send_message(CHAT_ID, text)
    except Exception as e:
        logger.error(f"Failed to send blocked-notification: {e}")


def _format(listing: Listing) -> str:
    price = f"€{int(listing.price):,}".replace(",", ".") if listing.price else "N/D"
    details = " · ".join(filter(None, [
        f"{listing.rooms} locali" if listing.rooms else None,
        f"{listing.size_sqm} m²" if listing.size_sqm else None,
    ]))
    parts = [
        f"🏠 <b>{listing.title or 'Annuncio'}</b>",
        f"💰 {price}",
        details or None,
        f"📍 {listing.address}" if listing.address else None,
        f'🔗 <a href="{listing.url}">Vedi annuncio</a>',
        f"<i>Fonte: {listing.source}</i>",
    ]
    return "\n".join(p for p in parts if p)
