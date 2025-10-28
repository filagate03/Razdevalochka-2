from __future__ import annotations

from typing import Dict

from app.config import get_settings
from app.repositories import ReferralRepository, TransactionRepository, UserRepository


class ReferralService:
    def __init__(
        self,
        user_repo: UserRepository,
        referral_repo: ReferralRepository,
        transaction_repo: TransactionRepository,
    ) -> None:
        self.user_repo = user_repo
        self.referral_repo = referral_repo
        self.transaction_repo = transaction_repo
        self.settings = get_settings()

    async def register_referral(self, referrer_chat_id: int, referee_chat_id: int) -> bool:
        referrer = await self.user_repo.get_by_chat_id(referrer_chat_id)
        referee = await self.user_repo.get_by_chat_id(referee_chat_id)
        if not referrer or not referee:
            return False
        existing = await self.referral_repo.get_by_referee(referee.id)
        if existing:
            return False
        await self.referral_repo.create(referrer.id, referee.id)
        await self.user_repo.set_referrer(referee_chat_id, referrer.id)
        return True

    async def process_purchase(self, user_chat_id: int, tokens: int) -> None:
        user = await self.user_repo.get_by_chat_id(user_chat_id)
        if not user or not user.referrer_id:
            return
        referral = await self.referral_repo.get_by_referee(user.id)
        if not referral:
            return

        # First purchase bonus for referee
        if not referral.first_purchase_bonus_given:
            bonus_tokens = self.settings.referral_bonus_tokens
            await self.user_repo.update_balance(user_chat_id, bonus_tokens, reason="Referral first purchase bonus")
            await self.transaction_repo.create(
                user_id=user.id,
                amount=bonus_tokens,
                reason="referral_bonus",
                payment_method="bonus",
                external_id=f"ref_first_{referral.id}",
            )
            await self.referral_repo.mark_first_bonus_given(referral.id)

        commission_percent = self.settings.referral_commission_percent
        commission_tokens = int(tokens * commission_percent / 100)
        if commission_tokens <= 0:
            return
        referrer = await self.user_repo.get_by_id(user.referrer_id)
        if not referrer:
            return
        await self.user_repo.update_balance(referrer.chat_id, commission_tokens, reason="Referral commission")
        await self.transaction_repo.create(
            user_id=referrer.id,
            amount=commission_tokens,
            reason="referral_commission",
            payment_method="bonus",
            external_id=f"ref_comm_{referral.id}",
        )
        await self.referral_repo.update_earned(referral.id, commission_tokens)

    async def get_referral_link(self, user_chat_id: int, bot_username: str) -> str:
        return f"https://t.me/{bot_username}?start=ref_{user_chat_id}"

    async def get_referral_stats(self, user_id: int) -> Dict:
        referrals = await self.referral_repo.get_by_referrer(user_id)
        total_earned = sum(ref.total_earned for ref in referrals)
        return {
            "total_referrals": len(referrals),
            "total_earned": total_earned,
            "referrals": referrals,
        }


__all__ = ["ReferralService"]
