#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ------------------------------------------------------------------------------
#
#   Copyright 2022 Valory AG
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#
# ------------------------------------------------------------------------------

"""This script checks that the readme is correct."""

import json
import sys
from pathlib import Path


def main() -> None:
    """Main function."""
    el_collectooorr_service_package = "service/elcollectooorr/elcollectooorr/0.1.0"
    packages_path = Path("packages", "packages.json")
    readme_path = Path("README.md")
    with open(readme_path, mode="r", encoding="utf-8") as readme_file, open(
        packages_path, mode="r", encoding="utf-8"
    ) as packages_file:
        readme = readme_file.read()
        packages = json.load(packages_file)
        wanted_hash = packages["dev"].get(el_collectooorr_service_package, None)

        if wanted_hash is None or wanted_hash not in readme:
            # we were not able to find the wanted hash
            not_found = (
                "The ElCollectooorr service package hash was not found on the readme."
            )
            sys.exit(not_found)


if __name__ == "__main__":
    main()
