#
# RTEMS Tools Project (http://www.rtems.org/)
# Copyright 2010-2016 Chris Johns (chrisj@rtems.org)
# All rights reserved.
#
# This file is part of the RTEMS Tools package in 'rtems-tools'.
#
# Permission to use, copy, modify, and/or distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

#
# This code builds a package given a config file. It only builds to be
# installed not to be package unless you run a packager around this.
#

from __future__ import print_function

import base64
import hashlib
import os
import re
import stat
import sys
try:
    import urllib.request as urllib_request
    import urllib.parse as urllib_parse
except ImportError:
    import urllib2 as urllib_request
    import urlparse as urllib_parse

from . import cvs
from . import error
from . import git
from . import log
from . import path
from . import sources
from . import version


def _do_download(opts):
    download = True
    if opts.dry_run():
        download = False
        wa = opts.with_arg('download')
        if wa is not None:
            if wa[0] == 'with_download' and wa[1] == 'yes':
                download = True
    return download


def _humanize_bytes(bytes, precision=1):
    abbrevs = ((1 << 50, 'PB'), (1 << 40, 'TB'), (1 << 30, 'GB'),
               (1 << 20, 'MB'), (1 << 10, 'kB'), (1, ' bytes'))
    if bytes == 1:
        return '1 byte'
    for factor, suffix in abbrevs:
        if bytes >= factor:
            break
    return '%.*f%s' % (precision, float(bytes) / factor, suffix)


def _sensible_url(url, used=0):
    space = 100
    if len(url) > space:
        size = int(space - 14)
        url = url[:size] + '...<see log>'
    return url


def _hash_check(file_, absfile, macros, remove=True):
    failed = False
    hash = sources.get_hash(file_.lower(), macros)
    if hash is not None:
        hash = hash.split()
        if len(hash) != 2:
            raise error.internal('invalid hash format: %s' % (file_))
        if hash[0] == 'NO-HASH':
            return not failed
        try:
            hashlib_algorithms = hashlib.algorithms
        except:
            hashlib_algorithms = [
                'md5', 'sha1', 'sha224', 'sha256', 'sha384', 'sha512'
            ]
        if hash[0] not in hashlib_algorithms:
            raise error.general('invalid hash algorithm for %s: %s' %
                                (file_, hash[0]))
        if hash[0] in ['md5', 'sha1']:
            raise error.general('hash: %s: insecure: %s' % (file_, hash[0]))
        hasher = None
        _in = None
        try:
            hasher = hashlib.new(hash[0])
            _in = open(path.host(absfile), 'rb')
            hasher.update(_in.read())
        except IOError as err:
            log.notice('hash: %s: read error: %s' % (file_, str(err)))
            failed = True
        except:
            msg = 'hash: %s: error' % (file_)
            log.stderr(msg)
            log.notice(msg)
            if _in is not None:
                _in.close()
            raise
        if _in is not None:
            _in.close()
        hash_hex = hasher.hexdigest()
        hash_base64 = base64.b64encode(hasher.digest()).decode('utf-8')
        log.output('checksums: %s: (hex: %s) (b64: %s) => %s' %
                   (file_, hash_hex, hash_base64, hash[1]))
        if hash_hex != hash[1] and hash_base64 != hash[1]:
            log.warning('checksum error: %s' % (file_))
            failed = True
        if failed and remove:
            log.warning('removing: %s' % (file_))
            if path.exists(absfile):
                try:
                    os.remove(path.host(absfile))
                except IOError as err:
                    raise error.general('hash: %s: remove: %s' %
                                        (absfile, str(err)))
                except:
                    raise error.general('hash: %s: remove error' % (file_))
        if hasher is not None:
            del hasher
    else:
        raise error.general('%s: no hash found' % (file_))
    return not failed


def _local_path(source, pathkey, config):
    for p in config.define(pathkey).split(':'):
        local_prefix = path.abspath(p)
        local = path.join(local_prefix, source['file'])
        if source['local'] is None:
            source['local_prefix'] = local_prefix
            source['local'] = local
        if path.exists(local):
            source['local_prefix'] = local_prefix
            source['local'] = local
            _hash_check(source['file'], local, config.macros)
            break


def _http_parser(source, pathkey, config, opts):
    #
    # If the file has not been overrided attempt to recover a possible file name.
    #
    if 'file-override' not in source['options']:
        #
        # Hack for gitweb.cgi patch downloads. We rewrite the various fields.
        #
        if 'gitweb.cgi' in source['url']:
            url = source['url']
            if '?' not in url:
                raise error.general('invalid gitweb.cgi request: %s' % (url))
            req = url.split('?')[1]
            if len(req) == 0:
                raise error.general('invalid gitweb.cgi request: %s' % (url))
            #
            # The gitweb.cgi request should have:
            #    p=<what>
            #    a=patch
            #    h=<hash>
            # so extract the p and h parts to make the local name.
            #
            p = None
            a = None
            h = None
            for r in req.split(';'):
                if '=' not in r:
                    raise error.general('invalid gitweb.cgi path: %s' % (url))
                rs = r.split('=')
                if rs[0] == 'p':
                    p = rs[1].replace('.', '-')
                elif rs[0] == 'a':
                    a = rs[1]
                elif rs[0] == 'h':
                    h = rs[1]
            if p is None or h is None:
                raise error.general('gitweb.cgi path missing p or h: %s' %
                                    (url))
            source['file'] = '%s-%s.patch' % (p, h)
        #
        # Wipe out everything special in the file name.
        #
        source['file'] = re.sub(r'[^a-zA-Z0-9.\-_]+', '-', source['file'])
        max_file_len = 127
        if len(source['file']) > max_file_len:
            raise error.general('file name length is greater than %i (maybe use --rsb-file=FILE option): %s' % \
                                (max_file_len, source['file']))
    #
    # Check local path
    #
    _local_path(source, pathkey, config)
    #
    # Is the file compressed ?
    #
    esl = source['ext'].split('.')
    if esl[-1:][0] == 'gz':
        source['compressed-type'] = 'gzip'
        source['compressed'] = '%{__gzip} -dc'
    elif esl[-1:][0] == 'bz2':
        source['compressed-type'] = 'bzip2'
        source['compressed'] = '%{__bzip2} -dc'
    elif esl[-1:][0] == 'zip':
        source['compressed-type'] = 'zip'
        source['compressed'] = '%{__unzip} -u'
    elif esl[-1:][0] == 'xz':
        source['compressed-type'] = 'xz'
        source['compressed'] = '%{__xz} -dc'


def _patchworks_parser(source, pathkey, config, opts):
    #
    # Check local path
    #
    _local_path(source, pathkey, config)
    source['url'] = 'http%s' % (source['path'][2:])


def _git_parser(source, pathkey, config, opts):
    #
    # Check local path
    #
    _local_path(source, pathkey, config)
    #
    # Symlink.
    #
    us = source['url'].split('?')
    source['path'] = path.dirname(us[0])
    source['file'] = path.basename(us[0])
    source['name'], source['ext'] = path.splitext(source['file'])
    if len(us) > 1:
        source['args'] = us[1:]
    source['local'] = \
        path.join(source['local_prefix'], 'git', source['file'])
    source['symlink'] = source['local']


def _cvs_parser(source, pathkey, config, opts):
    #
    # Check local path
    #
    _local_path(source, pathkey, config)
    #
    # Symlink.
    #
    if not source['url'].startswith('cvs://'):
        raise error.general('invalid cvs path: %s' % (source['url']))
    us = source['url'].split('?')
    try:
        url = us[0]
        source['file'] = url[url[6:].index(':') + 7:]
        source['cvsroot'] = ':%s:' % (url[6:url[6:].index('/') + 6:])
    except:
        raise error.general('invalid cvs path: %s' % (source['url']))
    for a in us[1:]:
        _as = a.split('=')
        if _as[0] == 'module':
            if len(_as) != 2:
                raise error.general('invalid cvs module: %s' % (a))
            source['module'] = _as[1]
        elif _as[0] == 'src-prefix':
            if len(_as) != 2:
                raise error.general('invalid cvs src-prefix: %s' % (a))
            source['src_prefix'] = _as[1]
        elif _as[0] == 'tag':
            if len(_as) != 2:
                raise error.general('invalid cvs tag: %s' % (a))
            source['tag'] = _as[1]
        elif _as[0] == 'date':
            if len(_as) != 2:
                raise error.general('invalid cvs date: %s' % (a))
            source['date'] = _as[1]
    if 'date' in source and 'tag' in source:
        raise error.general('cvs URL cannot have a date and tag: %s' %
                            (source['url']))
    # Do here to ensure an ordered path, the URL can include options in any order
    if 'module' in source:
        source['file'] += '_%s' % (source['module'])
    if 'tag' in source:
        source['file'] += '_%s' % (source['tag'])
    if 'date' in source:
        source['file'] += '_%s' % (source['date'])
    for c in '/@#%.-':
        source['file'] = source['file'].replace(c, '_')
    source['local'] = path.join(source['local_prefix'], 'cvs', source['file'])
    if 'src_prefix' in source:
        source['symlink'] = path.join(source['local'], source['src_prefix'])
    else:
        source['symlink'] = source['local']


def _file_parser(source, pathkey, config, opts):
    #
    # Check local path
    #
    _local_path(source, pathkey, config)
    #
    # Get the paths sorted.
    #
    source['file'] = source['url'][6:]


parsers = {
    'http': _http_parser,
    'ftp': _http_parser,
    'pw': _patchworks_parser,
    'git': _git_parser,
    'cvs': _cvs_parser,
    'file': _file_parser
}


def set_release_path(release_path, macros):
    if release_path is None:
        release_path = '%{rtems_release_url}/%{rsb_version}/sources'
    macros.define('release_path', release_path)


def parse_url(url, pathkey, config, opts, file_override=None):
    #
    # Split the source up into the parts we need.
    #
    source = {}
    source['url'] = url
    source['options'] = []
    colon = url.find(':')
    if url[colon + 1:colon + 3] != '//':
        raise error.general('malforned URL (no protocol prefix): %s' % (url))
    source['path'] = url[:colon + 3] + path.dirname(url[colon + 3:])
    if file_override is None:
        source['file'] = path.basename(url)
    else:
        bad_chars = [c for c in ['/', '\\', '?', '*'] if c in file_override]
        if len(bad_chars) > 0:
            raise error.general('bad characters in file name: %s' %
                                (file_override))
        log.output('download: file-override: %s' % (file_override))
        source['file'] = file_override
        source['options'] += ['file-override']
    source['name'], source['ext'] = path.splitext(source['file'])
    if source['name'].endswith('.tar'):
        source['name'] = source['name'][:-4]
        source['ext'] = '.tar' + source['ext']
    #
    # Get the file. Checks the local source directory first.
    #
    source['local'] = None
    for p in parsers:
        if url.startswith(p):
            source['type'] = p
            if parsers[p](source, pathkey, config, opts):
                break
    source['script'] = ''
    return source


def _http_downloader(url, local, config, opts):
    if path.exists(local):
        return True
    #
    # Hack for GitHub.
    #
    if url.startswith('https://api.github.com'):
        url = urllib_parse.urljoin(url, config.expand('tarball/%{version}'))
    dst = os.path.relpath(path.host(local))
    log.output('download: (full) %s -> %s' % (url, dst))
    log.notice('download: %s -> %s' % (_sensible_url(url, len(dst)), dst))
    failed = False
    if _do_download(opts):
        _in = None
        _out = None
        _length = None
        _have = 0
        _chunk_size = 256 * 1024
        _chunk = None
        _last_percent = 200.0
        _last_msg = ''
        _have_status_output = False
        _url = url
        try:
            try:
                _in = None
                _ssl_context = None
                # See #2656
                _req = urllib_request.Request(_url)
                _req.add_header('User-Agent', 'Wget/1.16.3 (freebsd10.1)')
                try:
                    import ssl
                    _ssl_context = ssl._create_unverified_context()
                    _in = urllib_request.urlopen(_req, context=_ssl_context)
                except:
                    log.output('download: no ssl context')
                    _ssl_context = None
                if _ssl_context is None:
                    _in = urllib_request.urlopen(_req)
                if _url != _in.geturl():
                    _url = _in.geturl()
                    log.output(' redirect: %s' % (_url))
                    log.notice(' redirect: %s' % (_sensible_url(_url)))
                _out = open(path.host(local), 'wb')
                try:
                    _length = int(_in.info()['Content-Length'].strip())
                except:
                    pass
                while True:
                    _msg = '\rdownloading: %s - %s ' % (dst,
                                                        _humanize_bytes(_have))
                    if _length:
                        _percent = round((float(_have) / _length) * 100, 2)
                        if _percent != _last_percent:
                            _msg += 'of %s (%0.0f%%) ' % (
                                _humanize_bytes(_length), _percent)
                    if _msg != _last_msg:
                        extras = (len(_last_msg) - len(_msg))
                        log.stdout_raw('%s%s' %
                                       (_msg, ' ' * extras + '\b' * extras))
                        _last_msg = _msg
                        _have_status_output = True
                    _chunk = _in.read(_chunk_size)
                    if not _chunk:
                        break
                    _out.write(_chunk)
                    _have += len(_chunk)
                log.stdout_raw('\n\r')
            except:
                if _have_status_output:
                    log.stdout_raw('\n\r')
                raise
        except IOError as err:
            log.notice('download: %s: error: %s' %
                       (_sensible_url(_url), str(err)))
            if path.exists(local):
                os.remove(path.host(local))
            failed = True
        except ValueError as err:
            log.notice('download: %s: error: %s' %
                       (_sensible_url(_url), str(err)))
            if path.exists(local):
                os.remove(path.host(local))
            failed = True
        except:
            msg = 'download: %s: error' % (_sensible_url(_url))
            log.stderr(msg)
            log.notice(msg)
            if _in is not None:
                _in.close()
            if _out is not None:
                _out.close()
            raise
        if _out is not None:
            _out.close()
        if _in is not None:
            _in.close()
            del _in
        if not failed:
            if not path.isfile(local):
                raise error.general('source is not a file: %s' %
                                    (path.host(local)))
            if not _hash_check(path.basename(local), local, config.macros,
                               False):
                raise error.general('checksum failure file: %s' % (dst))
    return not failed


def _git_downloader(url, local, config, opts):
    repo = git.repo(local, opts, config.macros)
    rlp = os.path.relpath(path.host(local))
    us = url.split('?')
    #
    # Handle the various git protocols.
    #
    # remove 'git' from 'git://xxxx/xxxx?protocol=...'
    #
    url_base = us[0][len('git'):]
    for a in us[1:]:
        _as = a.split('=')
        if _as[0] == 'protocol':
            if len(_as) != 2:
                raise error.general('invalid git protocol option: %s' % (_as))
            if _as[1] == 'none':
                # remove the rest of the protocol header leaving nothing.
                us[0] = url_base[len('://'):]
            else:
                if _as[1] not in [
                        'ssh', 'git', 'http', 'https', 'ftp', 'ftps', 'rsync'
                ]:
                    raise error.general('unknown git protocol: %s' % (_as[1]))
                us[0] = _as[1] + url_base
    if not repo.valid():
        log.notice('git: clone: %s -> %s' % (us[0], rlp))
        if _do_download(opts):
            repo.clone(us[0], local)
    else:
        repo.clean(['-f', '-d'])
        repo.reset('--hard')
        default_branch = repo.default_branch()
        repo.checkout(default_branch)
    for a in us[1:]:
        _as = a.split('=')
        if _as[0] == 'branch' or _as[0] == 'checkout':
            if len(_as) != 2:
                raise error.general('invalid git branch/checkout: %s' % (_as))
            log.notice('git: checkout: %s => %s' % (us[0], _as[1]))
            if _do_download(opts):
                repo.checkout(_as[1])
        elif _as[0] == 'submodule':
            if len(_as) != 2:
                raise error.general('invalid git submodule: %s' % (_as))
            log.notice('git: submodule: %s <= %s' % (us[0], _as[1]))
            if _do_download(opts):
                repo.submodule(_as[1])
        elif _as[0] == 'fetch':
            log.notice('git: fetch: %s -> %s' % (us[0], rlp))
            if _do_download(opts):
                repo.fetch()
        elif _as[0] == 'merge':
            log.notice('git: merge: %s' % (us[0]))
            if _do_download(opts):
                repo.merge()
        elif _as[0] == 'pull':
            log.notice('git: pull: %s' % (us[0]))
            if _do_download(opts):
                repo.pull()
        elif _as[0] == 'reset':
            arg = []
            if len(_as) > 1:
                arg = ['--%s' % (_as[1])]
            log.notice('git: reset: %s' % (us[0]))
            if _do_download(opts):
                repo.reset(arg)
                repo.submodule_foreach(['reset'] + arg)
        elif _as[0] == 'clean':
            arg = []
            if len(_as) > 1:
                arg = ['--%s' % (_as[1])]
            log.notice('git: clean: %s' % (us[0]))
            if _do_download(opts):
                repo.clean(arg)
                repo.submodule_foreach(['clean'] + arg)
        elif _as[0] == 'protocol':
            pass
        else:
            raise error.general('invalid git option: %s' % (_as))
    return True


def _cvs_downloader(url, local, config, opts):
    rlp = os.path.relpath(path.host(local))
    us = url.split('?')
    module = None
    tag = None
    date = None
    src_prefix = None
    for a in us[1:]:
        _as = a.split('=')
        if _as[0] == 'module':
            if len(_as) != 2:
                raise error.general('invalid cvs module: %s' % (a))
            module = _as[1]
        elif _as[0] == 'src-prefix':
            if len(_as) != 2:
                raise error.general('invalid cvs src-prefix: %s' % (a))
            src_prefix = _as[1]
        elif _as[0] == 'tag':
            if len(_as) != 2:
                raise error.general('invalid cvs tag: %s' % (a))
            tag = _as[1]
        elif _as[0] == 'date':
            if len(_as) != 2:
                raise error.general('invalid cvs date: %s' % (a))
            date = _as[1]
    repo = cvs.repo(local, opts, config.macros, src_prefix)
    if not repo.valid():
        if not path.isdir(local):
            log.notice('Creating source directory: %s' % \
                           (os.path.relpath(path.host(local))))
            if _do_download(opts):
                path.mkdir(local)
            log.notice('cvs: checkout: %s -> %s' % (us[0], rlp))
            if _do_download(opts):
                repo.checkout(':%s' % (us[0][6:]), module, tag, date)
    for a in us[1:]:
        _as = a.split('=')
        if _as[0] == 'update':
            log.notice('cvs: update: %s' % (us[0]))
            if _do_download(opts):
                repo.update()
        elif _as[0] == 'reset':
            log.notice('cvs: reset: %s' % (us[0]))
            if _do_download(opts):
                repo.reset()
    return True


def _file_downloader(url, local, config, opts):
    if not path.exists(local):
        try:
            src = url[7:]
            dst = local
            log.notice('download: copy %s -> %s' % (src, dst))
            path.copy(src, dst)
        except:
            return False
    return True


downloaders = {
    'http': _http_downloader,
    'ftp': _http_downloader,
    'pw': _http_downloader,
    'git': _git_downloader,
    'cvs': _cvs_downloader,
    'file': _file_downloader
}


def get_file(url, local, opts, config):
    if local is None:
        raise error.general('source/patch path invalid')
    if not path.isdir(path.dirname(local)) and not opts.download_disabled():
        log.notice('Creating source directory: %s' % \
                       (os.path.relpath(path.host(path.dirname(local)))))
    log.output('making dir: %s' % (path.host(path.dirname(local))))
    if _do_download(opts):
        path.mkdir(path.dirname(local))
    if not path.exists(local) and opts.download_disabled():
        raise error.general('source not found: %s' % (path.host(local)))
    #
    # Check if a URL has been provided on the command line. If the package is
    # released push the release path URLs to the start the RTEMS URL list
    # unless overriden by the command line option --without-release-url. The
    # variant --without-release-url can override the released check.
    #
    url_bases = opts.urls()
    if url_bases is None:
        url_bases = []
    #
    # See if a release path has been specified and this is a release?
    #
    try:
        rtems_release_url_value = config.macros.expand('%{release_path}')
    except:
        rtems_release_url_value = None
    rtems_release_url = None
    rtems_release_urls = []
    if version.released() and rtems_release_url_value:
        rtems_release_url = rtems_release_url_value
    #
    # A with/without release URL is a testing option
    #
    with_rel_url = opts.with_arg('release-url')
    if with_rel_url[1] == 'not-found':
        if config.defined('without_release_url'):
            with_rel_url = ('without_release-url', 'yes')
    if with_rel_url[0] == 'with_release-url':
        if with_rel_url[1] == 'yes':
            if rtems_release_url_value is None:
                raise error.general('no valid release URL')
            rtems_release_url = rtems_release_url_value
        elif with_rel_url[1] == 'no':
            pass
        else:
            rtems_release_url = with_rel_url[1]
    elif with_rel_url[0] == 'without_release-url' and with_rel_url[1] == 'yes':
        rtems_release_url = None
    if rtems_release_url is not None:
        rtems_release_urls = rtems_release_url.split(',')
        for release_url in rtems_release_urls:
            log.trace('release url: %s' % (release_url))
            #
            # If the URL being fetched is under the release path do not add
            # the sources release path because it is already there.
            #
            if not url.startswith(release_url):
                url_bases = [release_url] + url_bases
    urls = []
    if len(url_bases) > 0:
        #
        # Split up the URL we are being asked to download.
        #
        url_path = urllib_parse.urlsplit(url)[2]
        slash = url_path.rfind('/')
        url_file = path.basename(local)
        log.trace('url_file: %s' % (url_file))
        for base in url_bases:
            if base[-1:] != '/':
                base += '/'
            next_url = urllib_parse.urljoin(base, url_file)
            log.trace('url: %s' % (next_url))
            urls.append(next_url)
    urls += url.split()
    for url in urls:
        log.trace('url: get: %s -> %s' % (url, local))
    for url in urls:
        for dl in downloaders:
            if url.startswith(dl):
                if downloaders[dl](url, local, config, opts):
                    return
    if _do_download(opts):
        raise error.general(
            'downloading %s: all paths have failed, giving up' % (url))
