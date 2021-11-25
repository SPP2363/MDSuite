"""
MDSuite: A Zincwarecode package.

License
-------
This program and the accompanying materials are made available under the terms
of the Eclipse Public License v2.0 which accompanies this distribution, and is
available at https://www.eclipse.org/legal/epl-v20.html

SPDX-License-Identifier: EPL-2.0

Copyright Contributors to the Zincwarecode Project.

Contact Information
-------------------
email: zincwarecode@gmail.com
github: https://github.com/zincware
web: https://zincwarecode.com/

Citation
--------
If you use this module please cite us with:

Summary
-------
"""
import json
import os
import pytest
import numpy as np
from pathlib import Path
import mdsuite as mds
from zinchub import DataHub


@pytest.fixture(scope="session")
def traj_file(tmp_path_factory) -> str:
    """Download trajectory file into a temporary directory and keep it for all tests"""
    temporary_path = tmp_path_factory.getbasetemp()

    NaCl = DataHub(url="https://github.com/zincware/DataHub/tree/main/NaCl_gk_i_q")
    NaCl.get_file(path=temporary_path)

    return (temporary_path / NaCl.file_raw).as_posix()


@pytest.fixture(scope="session")
def true_values() -> dict:
    """Example fixture for downloading analysis results from github"""
    NaCl = DataHub(url="https://github.com/zincware/DataHub/tree/main/NaCl_gk_i_q")
    return NaCl.get_analysis(analysis="NernstEinsteinIonicConductivity.json")


def test_neic_project(traj_files, true_values, tmp_path):
    """Test the nernst_einstein_ionic_conductivity called from the project class"""
    os.chdir(tmp_path)
    project = mds.Project()
    project.add_experiment("NaCl", data=traj_files[0], timestep=0.002, temperature=1400)

    project.run.NernstEinsteinIonicConductivity(plot=False)

    data_dict = project.load.NernstEinsteinIonicConductivity()[0].data_dict

    data = Path(
        r"C:\Users\fabia\Nextcloud\DATA\JupyterProjects\MDSuite\CI\integration_tests\
        calculators\data\nernst_einstein_ionic_conductivity.json"
    )

    data.write_text(json.dumps(data_dict))

    np.testing.assert_array_almost_equal(data_dict["x"], true_values["x"])
    np.testing.assert_array_almost_equal(
        data_dict["uncertainty"], true_values["uncertainty"]
    )


def test_neic_experiment(traj_files, true_values, tmp_path):
    """Test the nernst_einstein_ionic_conductivity called from the experiment class"""
    os.chdir(tmp_path)
    project = mds.Project()
    project.add_experiment("NaCl", data=traj_files[0], timestep=0.002, temperature=1400)

    project.experiments["NaCl"].run.NernstEinsteinIonicConductivity(plot=False)

    data_dict = (
        project.experiments["NaCl"].load.NernstEinsteinIonicConductivity()[0].data_dict
    )

    np.testing.assert_array_almost_equal(data_dict["x"], true_values["x"])
    np.testing.assert_array_almost_equal(
        data_dict["uncertainty"], true_values["uncertainty"]
    )
