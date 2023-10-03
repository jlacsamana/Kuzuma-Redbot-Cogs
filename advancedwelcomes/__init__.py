from .advancedwelcomes import AdvancedWelcomes


async def setup(bot):
    await bot.add_cog(AdvancedWelcomes(bot))