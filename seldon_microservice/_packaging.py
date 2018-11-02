# -*- coding: utf-8 -*-
"""
Provides PEP-440-compliant project versioning based on a .version file adjacent to the top-level
__init__.py file or the latest git tag.

## Usage

See two different usage options below. Note that the default version of '0.0.0' will be given
if both of the following are true:
  * git is not on path or there is no .git directory at the repo root or the git repo has no tags
  * there is no .version file adjacent to the package's top-level __init__.py file


## Method #1: ._packaging as a run time dependency

Place the following lines in your package's main __init__.py

    from ._packaging import get_version
    __version__ = get_version(__file__)

Optionally, add a .version file next to the project's top-level __init__.py file containing the
version string as the content.


## Method #2: ._packaging as a build time-only dependency

Place the following in your package's setup.py file

    # When executing the setup.py, we need to be able to import ourselves, this
    # means that we need to add the src directory to the sys.path.
    here = os.path.abspath(os.path.dirname(__file__))
    src_dir = os.path.join(here, "<PACKAGE_NAME>")
    sys.path.insert(0, src_dir)

    import <PACKAGE_NAME>._packaging

    setup(
        version=<PACKAGE_NAME>.__version__,
        cmdclass={
            'build_py': <PACKAGE_NAME>._packaging.BuildPyCommand,
            'sdist': <PACKAGE_NAME>._packaging.SDistCommand,
        },
    )

Place the following lines in your package's main __init__.py

    from ._packaging import get_version
    __version__ = get_version(__file__)

"""
from __future__ import absolute_import, division, print_function

from collections import namedtuple
from logging import getLogger
from os import getenv, unlink
from os.path import abspath, dirname, expanduser, isdir, isfile, join
import re
from subprocess import CalledProcessError, PIPE, Popen
import sys

try:
    # NOTE: Setuptools monkey-patches distutils. If setuptools is on sys.path and you don't
    #       want this behavior, remove the setuptools import.
    from setuptools.command.build_py import build_py
    from setuptools.command.sdist import sdist
except ImportError:
    from distutils.command.build_py import build_py
    from distutils.command.sdist import sdist

log = getLogger(__name__)

Response = namedtuple('Response', ('stdout', 'stderr', 'rc'))
GIT_DESCRIBE_REGEX = (r"(?:[_-a-zA-Z]*)"
                      r"v?"
                      r"(?P<version>[a-zA-Z0-9.]+)"
                      r"(?:-(?P<post>\d+)-g(?P<hash>[0-9a-f]{7,}))$")
DEFAULT_VERSION = "0.0.0"


def get_version(dunder_file):
    """Returns a version string for the current package, derived
    either from the latest git tag or from a .version file.

    This function is expected to run in two contexts. In a development
    context, where .git/ exists, the version is pulled from git tags.
    Using the BuildPyCommand and SDistCommand classes for cmdclass in
    setup.py will write a .version file into any dist.

    In an installed context, the .version file written at dist build
    time is the source of version information.

    """
    path = abspath(expanduser(dirname(dunder_file)))
    try:
        version = _get_version_from_version_file(path) or _get_version_from_git_tag(path)
        if version is None:
            version = DEFAULT_VERSION
    except CalledProcessError as e:
        print("WARNING:", repr(e), file=sys.stderr)
        print("Using default version '0.0.0'", file=sys.stderr)
        version = DEFAULT_VERSION
    except Exception:
        import traceback
        print(traceback.format_exc(), file=sys.stderr)
        print("Using default version '0.0.0'", file=sys.stderr)
        version = DEFAULT_VERSION
    return version


class BuildPyCommand(build_py):
    """See usage instructions at top of module."""
    def run(self):
        build_py.run(self)
        target_dir = join(self.build_lib, *self.distribution.metadata.name.split("."))
        _write_version(target_dir, self.distribution.metadata.version)


class SDistCommand(sdist):
    """See usage instructions at top of module."""
    def make_release_tree(self, base_dir, files):
        sdist.make_release_tree(self, base_dir, files)
        target_dir = join(base_dir, *self.distribution.metadata.name.split("."))
        _write_version(target_dir, self.distribution.metadata.version)


def _get_version_from_version_file(path):
    file_path = join(path, '.version')
    if isfile(file_path):
        with open(file_path, 'r') as fh:
            return fh.read().strip()


def _git_describe_tags(path):
    try:
        _call(("git", "update-index", "--refresh"), path, raise_on_error=False)
    except CalledProcessError as e:
        # git is probably not installed
        return None
    response = _call(("git", "describe", "--tags", "--long", "--always"), path,
                     raise_on_error=False)
    if response.rc == 0:
        return response.stdout.strip()
    elif response.rc == 128 and "no names found" in response.stderr.lower():
        # directory is a git repo, but no tags found
        return None
    elif response.rc == 128 and "not a git repository" in response.stderr.lower():
        # there is no .git/ directory at the repo root
        return None
    elif response.rc == 127:
        print("git not found on path: PATH={0}".format(getenv('PATH', None)), file=sys.stderr)
        raise CalledProcessError(response.rc, response.stderr)
    else:
        raise CalledProcessError(response.rc, response.stderr)


def _call(command, path=None, raise_on_error=True):
    path = sys.prefix if path is None else abspath(path)
    p = Popen(command, cwd=path, stdout=PIPE, stderr=PIPE)
    stdout, stderr = p.communicate()
    rc = p.returncode
    log.debug("{0} $  {1}\n  stdout: {2}\n  stderr: {3}\n  rc: {4}"
              .format(path, command, stdout, stderr, rc))
    if raise_on_error and rc != 0:
        raise CalledProcessError(rc, command, "stdout: {0}\nstderr: {1}".format(stdout, stderr))
    return Response(stdout.decode('utf-8'), stderr.decode('utf-8'), int(rc))


def _get_version_from_git_tag(path):
    """Return a PEP440-compliant version derived from the git status.
    If that fails for any reason, return None.
    """
    m = re.match(GIT_DESCRIBE_REGEX, _git_describe_tags(path) or '')
    if m is None:
        return None
    version, post_commit, hash = m.groups()
    return version if post_commit == '0' else "{0}.post{1}+{2}".format(version, post_commit, hash)


def _write_version(target_dir, version):
    if not isfile(join(target_dir, "__init__.py")):
        print("WARNING:\n  not found:", target_dir, file=sys.stderr)
        target_dir = dirname(__file__)
        print("  falling back to:", target_dir, file=sys.stderr)
    _write_version_into_init(target_dir, version)
    _write_version_file(target_dir, version)


def _write_version_into_init(target_dir, version):
    target_init_file = join(target_dir, "__init__.py")
    assert isfile(target_init_file), "File not found: {0}".format(target_init_file)
    with open(target_init_file, 'r') as f:
        init_lines = f.readlines()
    for q in range(len(init_lines)):
        if init_lines[q].startswith('__version__'):
            init_lines[q] = '__version__ = "{0}"\n'.format(version)
            print("Hard-coding version '{0}' in {1}".format(version, target_init_file))
        elif '._packaging' in init_lines[q]:
            init_lines[q] = None
            print("Removing line from file:\n  path: {0}\n  line {1}: {2}\n"
                  .format(target_init_file, q+1, init_lines[q]))
    modified_content = ''.join(l for l in init_lines if l is not None)
    unlink(target_init_file)
    with open(target_init_file, 'w') as f:
        f.write(modified_content)


def _write_version_file(target_dir, version):
    assert isdir(target_dir), "Directory not found: {0}".format(target_dir)
    target_file = join(target_dir, ".version")
    print("WRITING {0} with version {1}".format(target_file, version))
    with open(target_file, 'w') as f:
        f.write(version)
