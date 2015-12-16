# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import logging
import codecs
from itertools import takewhile

from drb.docker import Docker
from drb.spawn import sp
from drb.tempdir import TempDir
from drb.which import which
from drb.path import getpath
import os
import re

_logger = logging.getLogger("drb.downloadsources")

def downloadsources(source_directory, specfilename, target_image):
    """Leverages rpmbuild to complete the macros in a spec file, then
    uses wget to fetch source and patch files."""
    _logger.info("Downloading additional sources")

    lines = get_spec_with_resolved_macros(specfilename, target_image)
    urls = get_source_and_patches_urls(lines)
    download_files(urls, source_directory)

def get_spec_with_resolved_macros(specfilename, target_image):
    lines_upto_prep = list(takewhile(lambda line: not line.startswith("%prep"),
                                    codecs.open(specfilename, encoding="utf-8")))



    with TempDir.platformwise() as tmpdir:
        tempspec_path = os.path.join(tmpdir.path, os.path.basename(specfilename))
        tempspec = codecs.getwriter("utf-8")(open(tempspec_path, "wb"))
        tempspec.writelines(lines_upto_prep)
        tempspec.write("%prep\n")
        tempspec.write("cat<<__EOF__\n")
        tempspec.writelines(lines_upto_prep)
        tempspec.write("__EOF__\n")
        tempspec.close()

        docker = Docker().rm().image(target_image)
        rpmbuild = docker.cmd_and_args("which", "rpmbuild").run()
        with_macros = docker.bindmount_dir(tmpdir.path, tmpdir.path).cmd_and_args(rpmbuild, "--nodeps", "-bp",
                                                                                  tempspec_path).run()

    return with_macros.split("\n")

SOURCE_PATCH_PATTERN = re.compile("^(?:Source|Patch)\d*:\s*((?:http://|https://|ftp://)\S+?)\s*$")

def get_source_and_patches_urls(speclines):
    match_results = (SOURCE_PATCH_PATTERN.match(line) for line in speclines)
    only_matches = (result for result in match_results if result is not None)
    return [result.group(1) for result in only_matches]

def download_files(urls, download_dir):
    wget = which("wget")
    #TODO: think about URL sanitization.
    #TODO: think about whether it's better to use URLLib or something like that
    #to download files. We use wget right now because it's easier and has
    #builtin timestamping support.
    joined_urls = " ".join(urls)
    sp("{wget} --directory-prefix={download_dir} --timestamping {joined_urls}", **locals())






















