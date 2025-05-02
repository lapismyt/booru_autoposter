import asyncio
import os
import random
from urllib.parse import urlparse

import toml
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import URLInputFile, Message
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from loguru import logger

from booru import DanbooruAdapter, DanbooruError, GelbooruAdapter, SafebooruAdapter, Rule34Adapter
from models import DanbooruPost, GelbooruPost

with open('config.toml', 'r') as f:
    config = toml.load(f)

BOT_TOKEN = config['BOT_TOKEN']
OWNER_ID = config['OWNER_ID']
DANBOORU_LOGIN = config.get('DANBOORU_LOGIN')
DANBOORU_API_KEY = config.get('DANBOORU_API_KEY')
PROXY = config.get('HTTP_PROXY')

bot = Bot(BOT_TOKEN)
dp = Dispatcher()


async def fetch_one_image_dan(tags: str) -> tuple[str, str] | None:
    logger.info(f'Searching image using DanbooruAdapter...')

    adapter = DanbooruAdapter(proxy=(PROXY if PROXY else None), api_key=DANBOORU_API_KEY, username=DANBOORU_LOGIN)
    try:
        srch = await adapter.search(tags, limit=100, random=True)
    except DanbooruError as err:
        logger.error(repr(err))
        await adapter.close()
        return None
    for r in srch:
        if r.is_banned or r.is_deleted or r.is_pending:
            srch.remove(r)
    if not srch:
        logger.info('Empty search')
        await adapter.close()
        return None
    result: DanbooruPost = random.choice(srch)
    if not result.media_asset.variants:
        logger.info('Empty media asset variants')
        await adapter.close()
        return None
    await adapter.close()
    last = ''
    logger.info(f'Image found, ID {result.id}.')
    for var in result.media_asset.variants:
        last = var.url, var.file_ext
        if var.type == 'sample':
            logger.info('Returning original image URL.')
            return var.url, var.file_ext
    logger.info('Sample not found (somehow), using image from last iteration.')
    return last

async def fetch_one_image_gel(tags: str, use_adapter = GelbooruAdapter) -> tuple[str, str] | None:
    logger.info(f'Searching image using {use_adapter}...')
    adapter = use_adapter(proxy=(PROXY if PROXY else None))
    try:
        posts = await adapter.search(tags, limit=100)
    except BaseException as err:
        logger.error(repr(err))
        await adapter.close()
        return None
    if not posts:
        await adapter.close()
        logger.info('Empty search')
        return None
    # if isinstance(posts, GelbooruSearchResponse):
    #     posts = posts.post
    result: GelbooruPost = random.choice(posts)
    if not result.image:
        logger.info('Now image')
        await adapter.close()
        return None
    await adapter.close()
    logger.info(f'Image found, ID {result.id}.')
    if result.sample_url and 'gif' not in result.file_url and 'mp4' not in result.file_url:
        url = result.sample_url
        logger.info('Using sample image.')
    else:
        url = result.file_url
        logger.info('Using original image.')
    return url, os.path.splitext(url)[1].lstrip('.')

async def post_one_image(tags: str, channel: int, booru_type = 'gel', gel_adapter = GelbooruAdapter, caption = 'autopost', allow_video = True):
    logger.info('Posting image...')
    if booru_type == 'dan':
        img = await fetch_one_image_dan(tags)
    elif booru_type == 'gel':
        img = await fetch_one_image_gel(tags, gel_adapter)
    else: return None
    if not img:
        await bot.send_message(
            chat_id=channel,
            text='NOT FOUND',
        )
        return None
    else:
        img_url, file_ext = img
    match file_ext:
        case 'png' | 'jpg' | 'jpeg':
            await bot.send_photo(
                chat_id=channel,
                photo=URLInputFile(img_url),
                caption=caption,
                parse_mode='HTML'
            )
        case 'gif':
            filename = os.path.split(urlparse(img_url).path)[1]
            await bot.send_animation(
                chat_id=channel,
                animation=URLInputFile(img_url, filename=filename),
                caption=caption,
                parse_mode='HTML'
            )
        case 'mp4':
            if allow_video:
                await bot.send_video(
                    chat_id=channel,
                    video=URLInputFile(img_url),
                    caption=caption,
                    parse_mode='HTML'
                )
            else:
                logger.warning('Video dont allowed, trying search and post again...')
                await post_one_image(tags, channel, booru_type, gel_adapter, caption, allow_video)
        case _:
            logger.info(f'Unknown file type: {file_ext}')
    logger.info('Posted image.')
    return None


@dp.message(Command('gel'))
async def safe_handler(message: Message):
    if len(message.text) < 7:
        await message.answer('WRONG USE')
        return None
    await post_one_image(message.text.removeprefix('/gel '), message.chat.id, 'gel', caption='')
    return None

@dp.message(Command('sfb'))
async def safe_handler(message: Message):
    if len(message.text) < 7:
        await message.answer('WRONG USE')
        return None
    await post_one_image(message.text.removeprefix('/sfb '), message.chat.id, 'gel', SafebooruAdapter, caption='')
    return None

@dp.message(Command('dan'))
async def dan_handler(message: Message):
    if len(message.text) < 7:
        await message.answer('WRONG USE')
        return None
    elif len(message.text.split()) > 3:
        await message.answer('/dan allows no more than 2 tags')
        return None
    await post_one_image(message.text.removeprefix('/dan '), message.chat.id, 'dan', caption='')
    return None

@dp.message(Command('r34'))
async def r34_handler(message: Message):
    if len(message.text) < 7:
        await message.answer('WRONG USE')
        return None
    await post_one_image(message.text.removeprefix('/r34 '), message.chat.id, 'gel', Rule34Adapter, caption='')
    return None


@dp.message(F.text)
async def text_handler(message: Message):
    me = await bot.get_me()
    if message.text.startswith('/'):
        return None
    if message.chat.type == 'private':
        await post_one_image(message.text, message.chat.id, 'gel', SafebooruAdapter)
    elif message.text.startswith(f'@{me.username} '):
        await post_one_image(message.text.removeprefix(f'@{me.username} '), message.chat.id, 'gel', SafebooruAdapter)
    return None


async def add_autopost_channel(scheduler: AsyncIOScheduler, channel_data: dict):
    match channel_data['adapter'].lower():
        case 'gelbooru':
            adapter = GelbooruAdapter
            booru_type = 'gel'
        case 'rule34':
            adapter = Rule34Adapter
            booru_type = 'gel'
        case 'danbooru':
            adapter = DanbooruAdapter
            booru_type = 'dan'
        case 'safebooru':
            adapter = SafebooruAdapter
            booru_type = 'gel'
        case _:
            adapter = SafebooruAdapter
            booru_type = 'gel'
    await post_one_image(
        tags=channel_data['search_tags'],
        channel=channel_data['chat_id'],
        booru_type=booru_type,
        gel_adapter=adapter,
        caption=channel_data['caption'],
        allow_video=channel_data['allow_video']
    )
    scheduler.add_job(
        post_one_image,
        trigger='interval',
        seconds=channel_data['interval'],
        args=(
            channel_data['search_tags'],
            channel_data['chat_id'],
            booru_type,
            adapter,
            channel_data['caption'],
            channel_data['allow_video']
        )
    )

async def main():
    scheduler = AsyncIOScheduler()
    me = await bot.get_me()
    logger.info(f'Starting @{me.username}')
    if 'autopost' in config:
        tasks = []
        for autopost_name in config['autopost']:
            tasks.append(asyncio.create_task(add_autopost_channel(scheduler, config['autopost'][autopost_name])))
        await asyncio.gather(*tasks)
    scheduler.start()
    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())