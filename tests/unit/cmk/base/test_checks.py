#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
import re
from pathlib import Path

import pytest  # type: ignore[import]

import testlib  # type: ignore[import]

import cmk.utils.paths
import cmk.base.config as config
import cmk.base.check_utils


def _search_deprecated_api_feature(check_file_path, deprecated_pattern):
    try:
        with check_file_path.open() as handle:
            return [
                "%s:%d:%s" % (check_file_path.name, line_no, repr(line.strip()))
                for line_no, line in enumerate(handle, 1)
                if re.search(deprecated_pattern, line.strip())
            ]
    except UnicodeDecodeError as exc:
        return ["%s:-1:Unable to reade file: %s" % (check_file_path.name, exc)]


@pytest.mark.parametrize("deprecated_pattern", [
    r"\bservice_description\(",
    r"\bOID_BIN\b",
    r"\bOID_STRING\b",
    r"\bOID_END_BIN\b",
    r"\bOID_END_OCTET_STRING\b",
    r"\ball_matching_hosts\b",
    r"\bbinstring_to_int\b",
    r"\bcheck_type\b",
    r"\bcore_state_names\b",
    r"\bget_http_proxy\b",
    r"\bhosttags_match_taglist\b",
    r"\bin_extraconf_hostlist\b",
    r"\bis_cmc\b",
    r"\bnagios_illegal_chars\b",
    r"\bquote_shell_string\b",
    r"\btags_of_host\b",
])
def test_deprecated_api_features(deprecated_pattern):
    check_files = (pathname for pathname in Path(cmk.utils.paths.checks_dir).glob("*")
                   if os.path.isfile(pathname) and pathname.suffix not in (".swp",))
    with_deprecated_feature = [
        finding  #
        for check_file_path in check_files  #
        for finding in _search_deprecated_api_feature(check_file_path, deprecated_pattern)
    ]
    assert not with_deprecated_feature, "Found %d deprecated API name '%r' usages:\n%s" % (
        len(with_deprecated_feature),
        deprecated_pattern,
        "\n".join(with_deprecated_feature),
    )


def _search_from_imports(check_file_path):
    with open(check_file_path) as f_:
        return [
            "%s:%d:%s" % (Path(check_file_path).stem, line_no, repr(line.strip()))
            for line_no, line in enumerate(f_.readlines(), 1)
            if (re.search(r'from\s.*\simport\s', line.strip()) and
                not line.startswith("from cmk.base.check_legacy_includes."))
        ]


def test_imports_in_checks():
    check_files = config.get_plugin_paths(cmk.utils.paths.checks_dir)
    with_from_imports = [
        finding  #
        for check_file_path in check_files  #
        for finding in _search_from_imports(check_file_path)
    ]
    assert not with_from_imports, "Found %d from-imports:\n%s" % (len(with_from_imports),
                                                                  "\n".join(with_from_imports))


@pytest.mark.parametrize('plugin_path', ['checks', 'inventory'])
def test_check_plugin_header(plugin_path: str):
    for plugin in Path(testlib.repo_path(), plugin_path).iterdir():
        if plugin.name.startswith("."):
            # .f12
            continue
        with plugin.open() as handle:
            shebang = handle.readline().strip()
            encoding_header = handle.readline().strip()

        assert shebang == "#!/usr/bin/env python3", (
            f"Plugin '{plugin.name}' has wrong shebang '{shebang}'",)
        assert encoding_header == "# -*- coding: utf-8 -*-", (
            f"Plugin '{plugin.name}' has wrong encoding header '{encoding_header}'")
