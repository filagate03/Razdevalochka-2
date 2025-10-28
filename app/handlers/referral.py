from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

from app.repositories import ReferralRepository, TransactionRepository, UserRepository
from app.services.referral import ReferralService

router = Router()


@router.message(CommandStart(deep_link=True))
async def cmd_start_referral(
    message: Message,
    user_repo: UserRepository,
    referral_repo: ReferralRepository,
    transaction_repo: TransactionRepository,
) -> None:
    args = message.text.split()
    if len(args) < 2 or not args[1].startswith("ref_"):
        return
    try:
        referrer_id = int(args[1].split("_", 1)[1])
    except ValueError:
        await message.answer("❌ Неверная реферальная ссылка")
        return
    if referrer_id == message.from_user.id:
        await message.answer("❌ Нельзя использовать свою ссылку")
        return

    await user_repo.get_or_create_user(
        message.from_user.id,
        message.from_user.username if message.from_user else None,
    )

    referral_service = ReferralService(user_repo, referral_repo, transaction_repo)
    success = await referral_service.register_referral(referrer_id, message.from_user.id)
    if success:
        await message.answer(
            "🎉 Вы зарегистрированы по реферальной ссылке!\n\n"
            "При первой покупке получите +2 токена бонусом."
        )
    else:
        await message.answer("👋 Вы уже зарегистрированы в системе.")


@router.message(Command("ref"))
async def cmd_ref(
    message: Message,
    user_repo: UserRepository,
    referral_repo: ReferralRepository,
    transaction_repo: TransactionRepository,
) -> None:
    user = await user_repo.get_or_create_user(
        message.from_user.id,
        message.from_user.username if message.from_user else None,
    )
    bot = await message.bot.get_me()
    referral_service = ReferralService(user_repo, referral_repo, transaction_repo)
    link = await referral_service.get_referral_link(user.chat_id, bot.username)
    stats = await referral_service.get_referral_stats(user.id)
    await message.answer(
        "🔗 Ваша ссылка:\n"
        f"`{link}`\n\n"
        f"📊 Рефералов: {stats['total_referrals']}\n"
        f"💰 Заработано токенов: {stats['total_earned']}",
        parse_mode="Markdown",
    )


@router.message(Command("refstats"))
async def cmd_refstats(
    message: Message,
    user_repo: UserRepository,
    referral_repo: ReferralRepository,
    transaction_repo: TransactionRepository,
) -> None:
    user = await user_repo.get_or_create_user(
        message.from_user.id,
        message.from_user.username if message.from_user else None,
    )
    referral_service = ReferralService(user_repo, referral_repo, transaction_repo)
    stats = await referral_service.get_referral_stats(user.id)
    if not stats["referrals"]:
        await message.answer("У вас пока нет рефералов")
        return
    lines = [
        "📊 Детальная статистика:",
        f"Всего рефералов: {stats['total_referrals']}",
        f"Заработано токенов: {stats['total_earned']}",
        "",
        "Топ рефералов:",
    ]
    for idx, referral in enumerate(sorted(stats["referrals"], key=lambda r: r.total_earned, reverse=True)[:10], start=1):
        referee = await user_repo.get_by_id(referral.referee_id)
        username = f"@{referee.username}" if referee and referee.username else f"ID: {referral.referee_id}"
        lines.append(f"{idx}. {username} — {referral.total_earned} токенов")
    await message.answer("\n".join(lines))
