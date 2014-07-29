#!/usr/bin/env python
# encoding: utf-8
"""
untitled.py

"""
import os
import sys
import subprocess
import argparse
from urlparse import urlparse

import requests
from pyquery import PyQuery
from clint.textui import colored, puts, indent
from progressbar import Percentage, Bar, ETA, FileTransferSpeed, ProgressBar


class UnsupportedFileFormatError(Exception):
    pass


class ConvertError(Exception):
    pass


class AlreadyExistError(Exception):
    pass


def get_converted_filename(filename):
    basename, ext = os.path.splitext(filename)
    return "%s.%s" % (basename, 'm4v')


def convert_video(filename, extensions=['mov', 'mp4', 'avi', 'm4v']):
    _, ext = os.path.splitext(filename)
    ext = ext.replace('.', '')

    if ext not in extensions:
        raise UnsupportedFileFormatError('Unsupported video file format')

    output = subprocess.check_output(["transcoder", filename],
                                     stderr=subprocess.STDOUT)
    msg = "[E] Nothing to convert. Exiting."
    new_filename = get_converted_filename(filename)
    if msg in output:
        # just rename
        os.rename(filename, new_filename)
    elif not os.path.exists(new_filename):
        raise ConvertError("Could not convert file '%s' to m4v" % filename)
    else:
        os.remove(filename)

    return new_filename


cookies = {}
HEADERS = {
    'User-Agent': ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9) '
                   'AppleWebKit/537.73.9 (KHTML, like Gecko) Version/7.0.1 '
                   'Safari/537.73.9')
}


def download_file(path, filename, url):
    if not url:
        raise Exception('No URL given. Abort')

    headers = HEADERS
    headers.update({
        'Referer': url,
    })
    r = requests.post(url, headers=HEADERS, cookies=cookies, stream=True)

    file_size = int(r.headers['content-length'])
    content_disposition = r.headers['content-disposition'].split('; ')

    for d in content_disposition:
        if d.startswith('filename'):
            filename = d.replace('filename=', '').replace('"', '') \
                                                 .replace("/", "_")

    local_filename = os.path.join(path, filename)
    converted_filename = get_converted_filename(local_filename)

    if os.path.exists(converted_filename):
        puts(colored.red('converted file already exist. skip.'))
        return converted_filename

    if os.path.exists(local_filename):
        if os.stat(local_filename).st_size != file_size:
            puts(colored.red('bad size. redownload it'))
        else:
            puts(colored.red('already exist. skip.'))
            return local_filename
    else:
        puts()

    widgets = ['   > ', Percentage(), ' ',
               Bar(marker='=', left='[', right=']'),
               ' ', ETA(), ' ', FileTransferSpeed()]

    pbar = ProgressBar(widgets=widgets, maxval=file_size)
    pbar.start()

    with open(local_filename, 'wb') as f:
        downloaded = 0
        for chunk in r.iter_content(chunk_size=1024):
            if not chunk:
                continue

            f.write(chunk)
            downloaded += len(chunk)
            pbar.update(downloaded)

    r.close()
    pbar.finish()

    return local_filename


def fetch_course_data(url):
    global cookies

    r = requests.get(url, headers=HEADERS, cookies=cookies)

    cookies.update(r.cookies)
    pq = PyQuery(r.text, parser='html')

    data = {
        'title': pq('.content-header .content-header__title').text()
                                                             .encode('utf-8'),
        'author': pq('.content-header__author-link').text(),
        'lessons': [],
    }

    base_url = "%s://%s" % (urlparse(url)[:2])
    for link in pq('.lesson-index__lesson-link'):
        link_url = link.attrib.get('href', '')
        if link_url and link_url.startswith('/'):
            link_url = "%s%s" % (base_url, link_url)

        data['lessons'].append(link_url)

    return data


def fetch_lesson(url):
    global cookies

    r = requests.get(url, headers=HEADERS, cookies=cookies)
    cookies.update(r.cookies)
    pq = PyQuery(r.text)

    lesson_title = pq('.lesson-description__lesson-title')
    description = pq('.lesson-description__description')
    download_url = pq('.lesson__download-video-link')
    return {
        'title': lesson_title.text().encode('utf-8'),
        'description': description.text().encode('utf-8'),
        'download_url': download_url.attr('href')
    }


def main():
    global cookies

    parser = argparse.ArgumentParser(description=(
        'Convert video Tutorials from TutsPlus.com to m4v and fill with data'))
    parser.add_argument('--url', metavar='URL', type=str, dest='url',
                        help='tutorial url', required=True)
    parser.add_argument('-d', dest='directory',
                        help='root directory to save course', required=True)
    parser.add_argument('-s', '--session', dest='sesssion_id',
                        help='_tuts_session cookie for tutsplus.com',
                        required=True)

    args = parser.parse_args()

    cookies.update({'_tuts_session': args.sesssion_id})

    puts("Downloading course from '%s'" % colored.green(args.url))
    course = fetch_course_data(args.url)
    save_directory = os.path.join(args.directory, course['title'])
    if not os.path.exists(save_directory):
        os.mkdir(save_directory)

    puts('title: %s' % colored.green(course['title']))
    puts('author: %s' % colored.green(course['author']))
    for i, lesson_url in enumerate(course['lessons']):
        name = 'Lesson %s' % (i + 1)

        puts(colored.green("\n%s" % name))
        puts("-" * len(name))
        with indent(5, quote='   >'):
            data = fetch_lesson(lesson_url)
            puts("url: %s" % lesson_url)
            puts("title: %s" % data['title'])
            puts("description: %s" % (data['description'] or "")[:100])

        with indent(5, quote='   >'):
            puts('Downloading... ', newline=False)
        filename = download_file(save_directory, name, data['download_url'])

        with indent(5, quote='   >'):
            puts('Coverting... ', newline=False)

        try:
            filename = convert_video(filename)
        except (ConvertError, UnsupportedFileFormatError):
            puts(colored.red('ERROR'))
            sys.exit(1)
        except AlreadyExistError:
            puts(colored.green('aready exist. skip'))
        else:
            puts(colored.green('ok'))

        cmd = [
            'AtomicParsley',
            filename,
            "--stik=%s" % "TV Show",
            "--title=%s" % data['title'],
            "--longdesc=%s" % data['description'],
            "--description=%s" % data['description'],
            "--TVShowName=%s" % course['title'],
            "--artist=%s" % course['author'],
            "--album=%s" % course['title'],
            "--TVEpisodeNum=%s" % (i + 1),
            "--genre=%s" % 'Tutorial',
            "--artwork=%s" % '/Users/spoof/Downloads/tutsplus.jpg',
            "--overWrite"
        ]
        subprocess.check_output(cmd, stderr=subprocess.STDOUT)
        with indent(5, quote='   >'):
            puts("Saved to '%s'" % colored.green(filename))

        with indent(3, quote=""):
            puts(colored.green('Done.'))


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print colored.red('\nAborted by user')
        sys.exit(1)
