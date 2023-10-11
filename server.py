import asyncio
import os
import logging
import aiohttp

from pathlib import Path
from aiohttp import web
import aiofiles


log_file_path = 'my_log.log'
file_handler = logging.FileHandler(log_file_path, encoding='utf-8')
logging.basicConfig(format=u'%(filename)s[LINE:%(lineno)d]# %(levelname)-8s [%(asctime)s]  %(message)s',
                    level=logging.DEBUG)


async def check_directory_exists(path):
    return await asyncio.to_thread(Path(path).exists)


async def archive(request):
    response = web.StreamResponse()
    archive_hash = request.match_info.get('archive_hash')
    response.headers['Content-Disposition'] = f'attachment; filename=f"{archive_hash}"'
    response.headers['Content-Type'] = 'application/zip'
    await response.prepare(request)
    file_dir = 'test_photos/' + archive_hash
    if not await check_directory_exists(file_dir):
        raise aiohttp.web.HTTPNotFound(text="404")

    command = 'zip'
    arguments = ['-r', '-', f'{file_dir}/']
    process = await asyncio.create_subprocess_exec(
        command,
        *arguments,
        stdout=asyncio.subprocess.PIPE,
    )
    try:
        while True:
            data = await process.stdout.read(1024)
            logging.info('Sending archive chunk ...')
            if not data:
                break
            await response.write(data)
            await asyncio.sleep(500)
        await response.write_eof()
    except asyncio.CancelledError:
        logging.exception('Download was interrupted')
    except BaseException as e:
        logging.exception(e)
    finally:
        process.kill()
    return response


async def handle_index_page(request):
    async with aiofiles.open('index.html', mode='r') as index_file:
        index_contents = await index_file.read()
    return web.Response(text=index_contents, content_type='text/html')


if __name__ == '__main__':
    app = web.Application()
    app.add_routes([
        web.get('/', handle_index_page),
        web.get('/archive/{archive_hash}/', archive),
    ])
    web.run_app(app)
