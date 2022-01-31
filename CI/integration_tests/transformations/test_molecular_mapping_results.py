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
Test the outcome of molecular mapping.
"""
from typing import List, Tuple

import pytest
from zinchub import DataHub

import mdsuite
import mdsuite.file_io.chemfiles_read
import mdsuite.transformations
from mdsuite.utils import Units
from mdsuite.utils.testing import assertDeepAlmostEqual


@pytest.fixture(scope="session")
def traj_files(tmp_path_factory) -> Tuple[List[str], str]:
    """Download trajectory file into a temporary directory and keep it for all tests"""
    temporary_path = tmp_path_factory.getbasetemp()

    water = DataHub(url="https://github.com/zincware/DataHub/tree/main/Water_14_Gromacs")
    water.get_file(temporary_path)
    file_paths = [(temporary_path / f).as_posix() for f in water.file_raw]

    bmim_bf4 = DataHub(url="https://github.com/zincware/DataHub/tree/main/Bmim_BF4")
    bmim_bf4.get_file(path=temporary_path)

    return file_paths, (temporary_path / bmim_bf4.file_raw).as_posix()


@pytest.fixture()
def mdsuite_project(traj_files, tmp_path) -> mdsuite.Project:
    """
    Create the MDSuite project and add data to be used for the rest of the tests.

    Parameters
    ----------
    traj_files : list
            Files include:
                * Water Simulation
    tmp_path : Path
            Temporary path that may be changed into.

    Returns
    -------
    project: mdsuite.Project
            An MDSuite project to be tested.
    """
    water_files = traj_files[0]
    bmim_file = traj_files[1]

    gmx_units = Units(
        time=1e-12,
        length=1e-10,
        energy=1.6022e-19,
        NkTV2p=1.6021765e6,
        boltzmann=8.617343e-5,
        temperature=1,
        pressure=100000,
    )
    project = mdsuite.Project(storage_path=tmp_path.as_posix())

    file_reader_1 = mdsuite.file_io.chemfiles_read.ChemfilesRead(
        traj_file_path=water_files[2], topol_file_path=water_files[0]
    )
    file_reader_2 = mdsuite.file_io.chemfiles_read.ChemfilesRead(
        traj_file_path=water_files[2], topol_file_path=water_files[1]
    )
    project.add_experiment(
        name="simple_water",
        timestep=0.002,
        temperature=300.0,
        units=gmx_units,
        simulation_data=file_reader_1,
    )
    project.add_experiment(
        name="ligand_water",
        timestep=0.002,
        temperature=300.0,
        units=gmx_units,
        simulation_data=file_reader_2,
    )

    project.add_experiment("bmim_bf4", simulation_data=bmim_file)

    project.run.CoordinateUnwrapper()

    return project


class TestMoleculeMapping:
    """
    Class to wrap test suite so we can run all tests within PyCharm.
    """

    def test_water_molecule_smiles(self, mdsuite_project):
        """
        Test that water molecules are built correctly using a SMILES string. Also check
        that the molecule information is stored correctly in the experiment.

        Parameters
        ----------
        mdsuite_project : Callable
                Callable that returns an MDSuite project created in a temporary
                directory.

        Returns
        -------
        Tests that the molecule groups detected are done so correctly and that the
        constructed trajectory is also correct.
        """
        reference_molecules = {
            "water": {
                "n_particles": 14,
                "mass": 18.015,
                "groups": {
                    "0": {"H": [0, 1], "O": [0]},
                    "1": {"H": [2, 3], "O": [1]},
                    "2": {"H": [4, 5], "O": [2]},
                    "3": {"H": [6, 7], "O": [3]},
                    "4": {"H": [8, 9], "O": [4]},
                    "5": {"H": [10, 11], "O": [5]},
                    "6": {"H": [12, 13], "O": [6]},
                    "7": {"H": [14, 15], "O": [7]},
                    "8": {"H": [16, 17], "O": [8]},
                    "9": {"H": [18, 19], "O": [9]},
                    "10": {"H": [20, 21], "O": [10]},
                    "11": {"H": [22, 23], "O": [11]},
                    "12": {"H": [24, 25], "O": [12]},
                    "13": {"H": [26, 27], "O": [13]},
                },
            }
        }
        water_molecule = mdsuite.Molecule(
            name="water", smiles="[H]O[H]", amount=14, cutoff=1.7, mol_pbc=True
        )
        mdsuite_project.experiments["simple_water"].run.MolecularMap(
            molecules=[water_molecule]
        )
        molecules = mdsuite_project.experiments["simple_water"].molecules
        assert molecules == reference_molecules

        assert "water" not in mdsuite_project.experiments["simple_water"].species

    def test_water_molecule_reference_dict(self, mdsuite_project):
        """
        Test that water molecules are built correctly using a reference dict.

        Parameters
        ----------
        mdsuite_project : Callable
                Callable that returns an MDSuite project created in a temporary
                directory.

        Returns
        -------
        Tests that the molecule groups detected are done so correctly and that the
        constructed trajectory is also correct.
        """
        mdsuite_project.experiments["ligand_water"].species["OW"].mass = [15.999]
        mdsuite_project.experiments["ligand_water"].species["HW1"].mass = [1.00784]
        mdsuite_project.experiments["ligand_water"].species["HW2"].mass = [1.00784]
        reference_molecules = {
            "water": {
                "n_particles": 14,
                "mass": 18.01468,
                "groups": {
                    "0": {"HW1": [0], "OW": [0], "HW2": [0]},
                    "1": {"HW1": [1], "OW": [1], "HW2": [1]},
                    "2": {"HW1": [2], "OW": [2], "HW2": [2]},
                    "3": {"HW1": [3], "OW": [3], "HW2": [3]},
                    "4": {"HW1": [4], "OW": [4], "HW2": [4]},
                    "5": {"HW1": [5], "OW": [5], "HW2": [5]},
                    "6": {"HW1": [6], "OW": [6], "HW2": [6]},
                    "7": {"HW1": [7], "OW": [7], "HW2": [7]},
                    "8": {"HW1": [8], "OW": [8], "HW2": [8]},
                    "9": {"HW1": [9], "OW": [9], "HW2": [9]},
                    "10": {"HW1": [10], "OW": [10], "HW2": [10]},
                    "11": {"HW1": [11], "OW": [11], "HW2": [11]},
                    "12": {"HW1": [12], "OW": [12], "HW2": [12]},
                    "13": {"HW1": [13], "OW": [13], "HW2": [13]},
                },
            }
        }
        water_molecule = mdsuite.Molecule(
            name="water",
            species_dict={"OW": 1, "HW1": 1, "HW2": 1},
            amount=14,
            cutoff=1.7,
            mol_pbc=True,
        )
        mdsuite_project.experiments["ligand_water"].run.MolecularMap(
            molecules=[water_molecule]
        )
        molecules = mdsuite_project.experiments["ligand_water"].molecules
        assertDeepAlmostEqual(molecules, reference_molecules)

        assert "water" not in mdsuite_project.experiments["ligand_water"].species

    def test_ionic_liquid(self, mdsuite_project):
        """
        Test molecule mapping on a more complex ionic liquid.

        This test will ensure that one can pass multiple molecules to the mapper as
        well as check the effect of parsing a specific reference configuration.
        """
        reference_dict = {
            "bmim": {
                "n_particles": 50,
                "mass": 139.22199999999998,
                "groups": {
                    "0": {
                        "C": [0, 1, 2, 3, 4, 5, 6, 7],
                        "N": [0, 1],
                        "H": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14],
                    },
                    "2": {
                        "C": [8, 9, 10, 11, 12, 13, 14, 15],
                        "N": [2, 3],
                        "H": [15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29],
                    },
                    "4": {
                        "C": [16, 17, 18, 19, 20, 21, 22, 23],
                        "N": [4, 5],
                        "H": [30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44],
                    },
                    "6": {
                        "C": [24, 25, 26, 27, 28, 29, 30, 31],
                        "N": [6, 7],
                        "H": [45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59],
                    },
                    "8": {
                        "C": [32, 33, 34, 35, 36, 37, 38, 39],
                        "N": [8, 9],
                        "H": [60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74],
                    },
                    "10": {
                        "C": [40, 41, 42, 43, 44, 45, 46, 47],
                        "N": [10, 11],
                        "H": [75, 76, 77, 78, 79, 80, 81, 82, 83, 84, 85, 86, 87, 88, 89],
                    },
                    "12": {
                        "C": [48, 49, 50, 51, 52, 53, 54, 55],
                        "N": [12, 13],
                        "H": [
                            90,
                            91,
                            92,
                            93,
                            94,
                            95,
                            96,
                            97,
                            98,
                            99,
                            100,
                            101,
                            102,
                            103,
                            104,
                        ],
                    },
                    "14": {
                        "C": [56, 57, 58, 59, 60, 61, 62, 63],
                        "N": [14, 15],
                        "H": [
                            105,
                            106,
                            107,
                            108,
                            109,
                            110,
                            111,
                            112,
                            113,
                            114,
                            115,
                            116,
                            117,
                            118,
                            119,
                        ],
                    },
                    "16": {
                        "C": [64, 65, 66, 67, 68, 69, 70, 71],
                        "N": [16, 17],
                        "H": [
                            120,
                            121,
                            122,
                            123,
                            124,
                            125,
                            126,
                            127,
                            128,
                            129,
                            130,
                            131,
                            132,
                            133,
                            134,
                        ],
                    },
                    "18": {
                        "C": [72, 73, 74, 75, 76, 77, 78, 79],
                        "N": [18, 19],
                        "H": [
                            135,
                            136,
                            137,
                            138,
                            139,
                            140,
                            141,
                            142,
                            143,
                            144,
                            145,
                            146,
                            147,
                            148,
                            149,
                        ],
                    },
                    "20": {
                        "C": [80, 81, 82, 83, 84, 85, 86, 87],
                        "N": [20, 21],
                        "H": [
                            150,
                            151,
                            152,
                            153,
                            154,
                            155,
                            156,
                            157,
                            158,
                            159,
                            160,
                            161,
                            162,
                            163,
                            164,
                        ],
                    },
                    "22": {
                        "C": [88, 89, 90, 91, 92, 93, 94, 95],
                        "N": [22, 23],
                        "H": [
                            165,
                            166,
                            167,
                            168,
                            169,
                            170,
                            171,
                            172,
                            173,
                            174,
                            175,
                            176,
                            177,
                            178,
                            179,
                        ],
                    },
                    "24": {
                        "C": [96, 97, 98, 99, 100, 101, 102, 103],
                        "N": [24, 25],
                        "H": [
                            180,
                            181,
                            182,
                            183,
                            184,
                            185,
                            186,
                            187,
                            188,
                            189,
                            190,
                            191,
                            192,
                            193,
                            194,
                        ],
                    },
                    "26": {
                        "C": [104, 105, 106, 107, 108, 109, 110, 111],
                        "N": [26, 27],
                        "H": [
                            195,
                            196,
                            197,
                            198,
                            199,
                            200,
                            201,
                            202,
                            203,
                            204,
                            205,
                            206,
                            207,
                            208,
                            209,
                        ],
                    },
                    "28": {
                        "C": [112, 113, 114, 115, 116, 117, 118, 119],
                        "N": [28, 29],
                        "H": [
                            210,
                            211,
                            212,
                            213,
                            214,
                            215,
                            216,
                            217,
                            218,
                            219,
                            220,
                            221,
                            222,
                            223,
                            224,
                        ],
                    },
                    "30": {
                        "C": [120, 121, 122, 123, 124, 125, 126, 127],
                        "N": [30, 31],
                        "H": [
                            225,
                            226,
                            227,
                            228,
                            229,
                            230,
                            231,
                            232,
                            233,
                            234,
                            235,
                            236,
                            237,
                            238,
                            239,
                        ],
                    },
                    "32": {
                        "C": [128, 129, 130, 131, 132, 133, 134, 135],
                        "N": [32, 33],
                        "H": [
                            240,
                            241,
                            242,
                            243,
                            244,
                            245,
                            246,
                            247,
                            248,
                            249,
                            250,
                            251,
                            252,
                            253,
                            254,
                        ],
                    },
                    "34": {
                        "C": [136, 137, 138, 139, 140, 141, 142, 143],
                        "N": [34, 35],
                        "H": [
                            255,
                            256,
                            257,
                            258,
                            259,
                            260,
                            261,
                            262,
                            263,
                            264,
                            265,
                            266,
                            267,
                            268,
                            269,
                        ],
                    },
                    "36": {
                        "C": [144, 145, 146, 147, 148, 149, 150, 151],
                        "N": [36, 37],
                        "H": [
                            270,
                            271,
                            272,
                            273,
                            274,
                            275,
                            276,
                            277,
                            278,
                            279,
                            280,
                            281,
                            282,
                            283,
                            284,
                        ],
                    },
                    "38": {
                        "C": [152, 153, 154, 155, 156, 157, 158, 159],
                        "N": [38, 39],
                        "H": [
                            285,
                            286,
                            287,
                            288,
                            289,
                            290,
                            291,
                            292,
                            293,
                            294,
                            295,
                            296,
                            297,
                            298,
                            299,
                        ],
                    },
                    "40": {
                        "C": [160, 161, 162, 163, 164, 165, 166, 167],
                        "N": [40, 41],
                        "H": [
                            300,
                            301,
                            302,
                            303,
                            304,
                            305,
                            306,
                            307,
                            308,
                            309,
                            310,
                            311,
                            312,
                            313,
                            314,
                        ],
                    },
                    "42": {
                        "C": [168, 169, 170, 171, 172, 173, 174, 175],
                        "N": [42, 43],
                        "H": [
                            315,
                            316,
                            317,
                            318,
                            319,
                            320,
                            321,
                            322,
                            323,
                            324,
                            325,
                            326,
                            327,
                            328,
                            329,
                        ],
                    },
                    "44": {
                        "C": [176, 177, 178, 179, 180, 181, 182, 183],
                        "N": [44, 45],
                        "H": [
                            330,
                            331,
                            332,
                            333,
                            334,
                            335,
                            336,
                            337,
                            338,
                            339,
                            340,
                            341,
                            342,
                            343,
                            344,
                        ],
                    },
                    "46": {
                        "C": [184, 185, 186, 187, 188, 189, 190, 191],
                        "N": [46, 47],
                        "H": [
                            345,
                            346,
                            347,
                            348,
                            349,
                            350,
                            351,
                            352,
                            353,
                            354,
                            355,
                            356,
                            357,
                            358,
                            359,
                        ],
                    },
                    "48": {
                        "C": [192, 193, 194, 195, 196, 197, 198, 199],
                        "N": [48, 49],
                        "H": [
                            360,
                            361,
                            362,
                            363,
                            364,
                            365,
                            366,
                            367,
                            368,
                            369,
                            370,
                            371,
                            372,
                            373,
                            374,
                        ],
                    },
                    "50": {
                        "C": [200, 201, 202, 203, 204, 205, 206, 207],
                        "N": [50, 51],
                        "H": [
                            375,
                            376,
                            377,
                            378,
                            379,
                            380,
                            381,
                            382,
                            383,
                            384,
                            385,
                            386,
                            387,
                            388,
                            389,
                        ],
                    },
                    "52": {
                        "C": [208, 209, 210, 211, 212, 213, 214, 215],
                        "N": [52, 53],
                        "H": [
                            390,
                            391,
                            392,
                            393,
                            394,
                            395,
                            396,
                            397,
                            398,
                            399,
                            400,
                            401,
                            402,
                            403,
                            404,
                        ],
                    },
                    "54": {
                        "C": [216, 217, 218, 219, 220, 221, 222, 223],
                        "N": [54, 55],
                        "H": [
                            405,
                            406,
                            407,
                            408,
                            409,
                            410,
                            411,
                            412,
                            413,
                            414,
                            415,
                            416,
                            417,
                            418,
                            419,
                        ],
                    },
                    "56": {
                        "C": [224, 225, 226, 227, 228, 229, 230, 231],
                        "N": [56, 57],
                        "H": [
                            420,
                            421,
                            422,
                            423,
                            424,
                            425,
                            426,
                            427,
                            428,
                            429,
                            430,
                            431,
                            432,
                            433,
                            434,
                        ],
                    },
                    "58": {
                        "C": [232, 233, 234, 235, 236, 237, 238, 239],
                        "N": [58, 59],
                        "H": [
                            435,
                            436,
                            437,
                            438,
                            439,
                            440,
                            441,
                            442,
                            443,
                            444,
                            445,
                            446,
                            447,
                            448,
                            449,
                        ],
                    },
                    "60": {
                        "C": [240, 241, 242, 243, 244, 245, 246, 247],
                        "N": [60, 61],
                        "H": [
                            450,
                            451,
                            452,
                            453,
                            454,
                            455,
                            456,
                            457,
                            458,
                            459,
                            460,
                            461,
                            462,
                            463,
                            464,
                        ],
                    },
                    "62": {
                        "C": [248, 249, 250, 251, 252, 253, 254, 255],
                        "N": [62, 63],
                        "H": [
                            465,
                            466,
                            467,
                            468,
                            469,
                            470,
                            471,
                            472,
                            473,
                            474,
                            475,
                            476,
                            477,
                            478,
                            479,
                        ],
                    },
                    "64": {
                        "C": [256, 257, 258, 259, 260, 261, 262, 263],
                        "N": [64, 65],
                        "H": [
                            480,
                            481,
                            482,
                            483,
                            484,
                            485,
                            486,
                            487,
                            488,
                            489,
                            490,
                            491,
                            492,
                            493,
                            494,
                        ],
                    },
                    "66": {
                        "C": [264, 265, 266, 267, 268, 269, 270, 271],
                        "N": [66, 67],
                        "H": [
                            495,
                            496,
                            497,
                            498,
                            499,
                            500,
                            501,
                            502,
                            503,
                            504,
                            505,
                            506,
                            507,
                            508,
                            509,
                        ],
                    },
                    "68": {
                        "C": [272, 273, 274, 275, 276, 277, 278, 279],
                        "N": [68, 69],
                        "H": [
                            510,
                            511,
                            512,
                            513,
                            514,
                            515,
                            516,
                            517,
                            518,
                            519,
                            520,
                            521,
                            522,
                            523,
                            524,
                        ],
                    },
                    "70": {
                        "C": [280, 281, 282, 283, 284, 285, 286, 287],
                        "N": [70, 71],
                        "H": [
                            525,
                            526,
                            527,
                            528,
                            529,
                            530,
                            531,
                            532,
                            533,
                            534,
                            535,
                            536,
                            537,
                            538,
                            539,
                        ],
                    },
                    "72": {
                        "C": [288, 289, 290, 291, 292, 293, 294, 295],
                        "N": [72, 73],
                        "H": [
                            540,
                            541,
                            542,
                            543,
                            544,
                            545,
                            546,
                            547,
                            548,
                            549,
                            550,
                            551,
                            552,
                            553,
                            554,
                        ],
                    },
                    "74": {
                        "C": [296, 297, 298, 299, 300, 301, 302, 303],
                        "N": [74, 75],
                        "H": [
                            555,
                            556,
                            557,
                            558,
                            559,
                            560,
                            561,
                            562,
                            563,
                            564,
                            565,
                            566,
                            567,
                            568,
                            569,
                        ],
                    },
                    "76": {
                        "C": [304, 305, 306, 307, 308, 309, 310, 311],
                        "N": [76, 77],
                        "H": [
                            570,
                            571,
                            572,
                            573,
                            574,
                            575,
                            576,
                            577,
                            578,
                            579,
                            580,
                            581,
                            582,
                            583,
                            584,
                        ],
                    },
                    "78": {
                        "C": [312, 313, 314, 315, 316, 317, 318, 319],
                        "N": [78, 79],
                        "H": [
                            585,
                            586,
                            587,
                            588,
                            589,
                            590,
                            591,
                            592,
                            593,
                            594,
                            595,
                            596,
                            597,
                            598,
                            599,
                        ],
                    },
                    "80": {
                        "C": [320, 321, 322, 323, 324, 325, 326, 327],
                        "N": [80, 81],
                        "H": [
                            600,
                            601,
                            602,
                            603,
                            604,
                            605,
                            606,
                            607,
                            608,
                            609,
                            610,
                            611,
                            612,
                            613,
                            614,
                        ],
                    },
                    "82": {
                        "C": [328, 329, 330, 331, 332, 333, 334, 335],
                        "N": [82, 83],
                        "H": [
                            615,
                            616,
                            617,
                            618,
                            619,
                            620,
                            621,
                            622,
                            623,
                            624,
                            625,
                            626,
                            627,
                            628,
                            629,
                        ],
                    },
                    "84": {
                        "C": [336, 337, 338, 339, 340, 341, 342, 343],
                        "N": [84, 85],
                        "H": [
                            630,
                            631,
                            632,
                            633,
                            634,
                            635,
                            636,
                            637,
                            638,
                            639,
                            640,
                            641,
                            642,
                            643,
                            644,
                        ],
                    },
                    "86": {
                        "C": [344, 345, 346, 347, 348, 349, 350, 351],
                        "N": [86, 87],
                        "H": [
                            645,
                            646,
                            647,
                            648,
                            649,
                            650,
                            651,
                            652,
                            653,
                            654,
                            655,
                            656,
                            657,
                            658,
                            659,
                        ],
                    },
                    "88": {
                        "C": [352, 353, 354, 355, 356, 357, 358, 359],
                        "N": [88, 89],
                        "H": [
                            660,
                            661,
                            662,
                            663,
                            664,
                            665,
                            666,
                            667,
                            668,
                            669,
                            670,
                            671,
                            672,
                            673,
                            674,
                        ],
                    },
                    "90": {
                        "C": [360, 361, 362, 363, 364, 365, 366, 367],
                        "N": [90, 91],
                        "H": [
                            675,
                            676,
                            677,
                            678,
                            679,
                            680,
                            681,
                            682,
                            683,
                            684,
                            685,
                            686,
                            687,
                            688,
                            689,
                        ],
                    },
                    "92": {
                        "C": [368, 369, 370, 371, 372, 373, 374, 375],
                        "N": [92, 93],
                        "H": [
                            690,
                            691,
                            692,
                            693,
                            694,
                            695,
                            696,
                            697,
                            698,
                            699,
                            700,
                            701,
                            702,
                            703,
                            704,
                        ],
                    },
                    "94": {
                        "C": [376, 377, 378, 379, 380, 381, 382, 383],
                        "N": [94, 95],
                        "H": [
                            705,
                            706,
                            707,
                            708,
                            709,
                            710,
                            711,
                            712,
                            713,
                            714,
                            715,
                            716,
                            717,
                            718,
                            719,
                        ],
                    },
                    "96": {
                        "C": [384, 385, 386, 387, 388, 389, 390, 391],
                        "N": [96, 97],
                        "H": [
                            720,
                            721,
                            722,
                            723,
                            724,
                            725,
                            726,
                            727,
                            728,
                            729,
                            730,
                            731,
                            732,
                            733,
                            734,
                        ],
                    },
                    "98": {
                        "C": [392, 393, 394, 395, 396, 397, 398, 399],
                        "N": [98, 99],
                        "H": [
                            735,
                            736,
                            737,
                            738,
                            739,
                            740,
                            741,
                            742,
                            743,
                            744,
                            745,
                            746,
                            747,
                            748,
                            749,
                        ],
                    },
                },
            },
            "bf4": {
                "n_particles": 50,
                "mass": 86.80361264,
                "groups": {
                    "0": {"B": [0], "F": [0, 1, 2, 3]},
                    "1": {"B": [1], "F": [4, 5, 6, 7]},
                    "2": {"B": [2], "F": [8, 9, 10, 11]},
                    "3": {"B": [3], "F": [12, 13, 14, 15]},
                    "4": {"B": [4], "F": [16, 17, 18, 19]},
                    "5": {"B": [5], "F": [20, 21, 22, 23]},
                    "6": {"B": [6], "F": [24, 25, 26, 27]},
                    "7": {"B": [7], "F": [28, 29, 30, 31]},
                    "8": {"B": [8], "F": [32, 33, 34, 35]},
                    "9": {"B": [9], "F": [36, 37, 38, 39]},
                    "10": {"B": [10], "F": [40, 41, 42, 43]},
                    "11": {"B": [11], "F": [44, 45, 46, 47]},
                    "12": {"B": [12], "F": [48, 49, 50, 51]},
                    "13": {"B": [13], "F": [52, 53, 54, 55]},
                    "14": {"B": [14], "F": [56, 57, 58, 59]},
                    "15": {"B": [15], "F": [60, 61, 62, 63]},
                    "16": {"B": [16], "F": [64, 65, 66, 67]},
                    "17": {"B": [17], "F": [68, 69, 70, 71]},
                    "18": {"B": [18], "F": [72, 73, 74, 75]},
                    "19": {"B": [19], "F": [76, 77, 78, 79]},
                    "20": {"B": [20], "F": [80, 81, 82, 83]},
                    "21": {"B": [21], "F": [84, 85, 86, 87]},
                    "22": {"B": [22], "F": [88, 89, 90, 91]},
                    "23": {"B": [23], "F": [92, 93, 94, 95]},
                    "24": {"B": [24], "F": [96, 97, 98, 99]},
                    "25": {"B": [25], "F": [100, 101, 102, 103]},
                    "26": {"B": [26], "F": [104, 105, 106, 107]},
                    "27": {"B": [27], "F": [108, 109, 110, 111]},
                    "28": {"B": [28], "F": [112, 113, 114, 115]},
                    "29": {"B": [29], "F": [116, 117, 118, 119]},
                    "30": {"B": [30], "F": [120, 121, 122, 123]},
                    "31": {"B": [31], "F": [124, 125, 126, 127]},
                    "32": {"B": [32], "F": [128, 129, 130, 131]},
                    "33": {"B": [33], "F": [132, 133, 134, 135]},
                    "34": {"B": [34], "F": [136, 137, 138, 139]},
                    "35": {"B": [35], "F": [140, 141, 142, 143]},
                    "36": {"B": [36], "F": [144, 145, 146, 147]},
                    "37": {"B": [37], "F": [148, 149, 150, 151]},
                    "38": {"B": [38], "F": [152, 153, 154, 155]},
                    "39": {"B": [39], "F": [156, 157, 158, 159]},
                    "40": {"B": [40], "F": [160, 161, 162, 163]},
                    "41": {"B": [41], "F": [164, 165, 166, 167]},
                    "42": {"B": [42], "F": [168, 169, 170, 171]},
                    "43": {"B": [43], "F": [172, 173, 174, 175]},
                    "44": {"B": [44], "F": [176, 177, 178, 179]},
                    "45": {"B": [45], "F": [180, 181, 182, 183]},
                    "46": {"B": [46], "F": [184, 185, 186, 187]},
                    "47": {"B": [47], "F": [188, 189, 190, 191]},
                    "48": {"B": [48], "F": [192, 193, 194, 195]},
                    "49": {"B": [49], "F": [196, 197, 198, 199]},
                },
            },
        }
        bmim_molecule = mdsuite.Molecule(
            name="bmim",
            species_dict={"C": 8, "N": 2, "H": 15},
            amount=50,
            cutoff=1.9,
            reference_configuration=100,
        )
        bf_molecule = mdsuite.Molecule(
            name="bf4",
            smiles="[B-](F)(F)(F)F",
            amount=50,
            cutoff=2.4,
            reference_configuration=100,
        )
        mdsuite_project.experiments["bmim_bf4"].run.MolecularMap(
            molecules=[bmim_molecule, bf_molecule]
        )

        assertDeepAlmostEqual(
            reference_dict, mdsuite_project.experiments["bmim_bf4"].molecules
        )
