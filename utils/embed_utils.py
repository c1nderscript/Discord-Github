import discord
from typing import List


def split_embed_fields(embed: discord.Embed, max_fields: int = 25) -> List[discord.Embed]:
    """Split an embed into multiple embeds if it has more than ``max_fields``."""
    if len(embed.fields) <= max_fields:
        return [embed]

    chunks: List[discord.Embed] = []
    fields = list(embed.fields)
    for i in range(0, len(fields), max_fields):
        new_embed = discord.Embed(
            title=embed.title,
            description=embed.description,
            color=embed.color,
            url=embed.url,
        )
        for field in fields[i:i + max_fields]:
            new_embed.add_field(name=field.name, value=field.value, inline=field.inline)
        chunks.append(new_embed)

    return chunks
