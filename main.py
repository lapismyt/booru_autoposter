import random
from aiogram import Bot, Dispatcher, F
import asyncio
import os
from aiogram.types import URLInputFile, Message
from dotenv import load_dotenv
from loguru import logger
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from booru import DanbooruAdapter, DanbooruError, GelbooruAdapter
from models import DanbooruPost, GelbooruPost

load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
CHANNEL_ID = int(os.getenv('CHANNEL_ID'))
OWNER_ID = int(os.getenv('OWNER_ID'))
CAPTION = os.getenv('CAPTION')
SEARCH_TAGS = os.getenv('SEARCH_TAGS')
DANBOORU_LOGIN = os.getenv('DANBOORU_LOGIN')
DANBOORU_API_KEY = os.getenv('DANBOORU_API_KEY')
INTERVAL = int(os.getenv('INTERVAL'))
PROXY = os.getenv('HTTP_PROXY')
ALLOW_VIDEO = (os.getenv('ALLOW_VIDEO').lower() in ('1', 'true', 'yes', '+'))

bot = Bot(BOT_TOKEN)
dp = Dispatcher()


async def fetch_one_image_dan(tags: str) -> tuple[str, str] | None:
    logger.info('Searching image...')
    adapter = DanbooruAdapter(proxy=(PROXY if PROXY else None))
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
        await adapter.close()
        return None
    result: DanbooruPost = random.choice(srch)
    if not result.media_asset.variants:
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

async def fetch_one_image_gel(tags: str) -> tuple[str, str] | None:
    logger.info('Searching image...')
    adapter = GelbooruAdapter(proxy=(PROXY if PROXY else None))
    try:
        srch = (await adapter.search(tags, limit=100)).post
    except BaseException as err:
        logger.error(repr(err))
        await adapter.close()
        return None
    if not srch:
        await adapter.close()
        return None
    result: GelbooruPost = random.choice(srch)
    if not result.image:
        await adapter.close()
        return None
    await adapter.close()
    logger.info(f'Image found, ID {result.id}.')
    if result.sample_url:
        url = result.sample_url
        logger.info('Using sample image.')
    else:
        url = result.file_url
        logger.info('Using original image.')
    return url, os.path.splitext(url)[1].lstrip('.')

async def post_one_image(tags: str, channel: int, booru_type = 'gel'):
    logger.info('Posting image...')
    if booru_type == 'dan':
        img = await fetch_one_image_dan(tags)
    elif booru_type == 'gel':
        img = await fetch_one_image_gel(tags)
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
                caption=CAPTION,
                parse_mode='HTML'
            )
        case 'gif':
            await bot.send_animation(
                chat_id=channel,
                animation=URLInputFile(img_url),
                caption=CAPTION,
                parse_mode='HTML'
            )
        case 'mp4':
            if ALLOW_VIDEO:
                await bot.send_video(
                    chat_id=channel,
                    video=URLInputFile(img_url),
                    caption=CAPTION,
                    parse_mode='HTML'
                )
            else:
                logger.warning('Video dont allowed, trying search and post again...')
                await post_one_image(tags, channel, booru_type)
        case _:
            logger.info(f'Unknown file type: {file_ext}')
    logger.info('Posted image.')
    return None


@dp.message(F.text)
async def text_handler(message: Message):
    me = await bot.get_me()
    if message.text.startswith('/'):
        return None
    if message.chat.type == 'private':
        await post_one_image(message.text, message.chat.id)
    elif message.text.startswith(f'@{me.username} '):
        await post_one_image(message.text.removeprefix(f'@{me.username} '), message.chat.id)
    return None


async def main():
    scheduler = AsyncIOScheduler()
    me = await bot.get_me()
    logger.info(f'Starting @{me.username}')
    await post_one_image(SEARCH_TAGS, CHANNEL_ID)
    scheduler.add_job(post_one_image, trigger='interval', seconds=INTERVAL, args=(SEARCH_TAGS, CHANNEL_ID))
    scheduler.start()
    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())