"""
This program and the accompanying materials are made available under the terms of the
Eclipse Public License v2.0 which accompanies this distribution, and is available at
https://www.eclipse.org/legal/epl-v20.html
SPDX-License-Identifier: EPL-2.0

Copyright Contributors to the Zincware Project.

Description: Test for the Einstein_Helfand_Ionic_Conductivity
"""
import pytest
import os
import mdsuite as mds
import urllib.request
import json
import shutil
from . import base_path
from mdsuite.utils.testing import assertDeepAlmostEqual


@pytest.fixture(scope="session")
def traj_file(tmp_path_factory) -> str:
    """Download trajectory file into a temporary directory and keep it for all tests"""
    compressed_file = "NaCl_gk_i_q.zip"
    uncompressed_file = 'NaCl_gk_i_q.lammpstraj'

    conv_raw = "?raw=true"
    compressed_file_path = base_path + compressed_file + conv_raw

    temporary_path = tmp_path_factory.getbasetemp()
    urllib.request.urlretrieve(
        compressed_file_path, filename=temporary_path / compressed_file
    )

    shutil.unpack_archive(
        filename=temporary_path / compressed_file,
        extract_dir=temporary_path
    )

    return (temporary_path / uncompressed_file).as_posix()



@pytest.fixture(scope="session")
def true_values() -> dict:
    """Example fixture for downloading analysis results from github"""
    # --- Change Me --- #
    file = "EinsteinHelfandIonicConductivity.json"
    # ----------------- #

    conv_raw = "?raw=true"

    with urllib.request.urlopen(base_path + "analysis/" + file + conv_raw) as url:
        out = json.loads(url.read().decode())

    return out


def test_project(traj_file, true_values, tmp_path):
    """Test the Einstein_Helfand_Ionic_Conductivity called from the project class

    Notes
    ------
    Test uncertainty is very high!
    """
    os.chdir(tmp_path)
    project = mds.Project()
    project.add_experiment("NaCl", data=traj_file, timestep=0.002, temperature=1400)

    computation = project.run.EinsteinHelfandIonicConductivity(plot=False)

    assertDeepAlmostEqual(computation["NaCl"].data_dict, true_values, decimal=-6)
