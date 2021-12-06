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
import pathlib


import typing
import tqdm
import mdsuite.file_io.file_read
import mdsuite.database.simulation_database
import mdsuite.file_io.tabular_text_files
from mdsuite.database.simulation_data_class import mdsuite_properties
from mdsuite.utils.meta_functions import optimize_batch_size


column_names = {
    mdsuite_properties.temperature: ["temp"],
    mdsuite_properties.time: ["time"],
    mdsuite_properties.thermal_flux: [
        "c_flux_thermal[1]",
        "c_flux_thermal[2]",
        "c_flux_thermal[3]",
    ],
    mdsuite_properties.stress_viscosity: ["pxy", "pxz", "pyz"],
}


class LAMMPSFluxFile(mdsuite.file_io.tabular_text_files.TabularTextFileProcessor):
    def __init__(
        self,
        file_path: typing.Union[str, pathlib.Path],
        sample_rate: int,
        box_l: list,
        n_header_lines: int = 2,
        custom_data_map: dict = None,
    ):
        """
        Initialize the lammps flux reader. Since the flux file does not have a fixed expected content,
        you need to provide the necessary metadata (sample_rate, box_l) here manually
        Parameters
        ----------
        file_path
            Location of the file
        sample_rate
            Number of time steps between successive samples
        box_l
            Array of box lengths
        n_header_lines
            Number of header lines on the top of the file
            first (n_header_lines-1) lines will be skipped, line n_header_lines must contain the column names
        custom_data_map
            Dictionary connecting the name in the mdsuite database to the name of the corresponding columns
            example: {"Thermal_Flux": ["c_flux_thermal[1]", "c_flux_thermal[2]", "c_flux_thermal[3]"]}
        """
        super(LAMMPSFluxFile, self).__init__(
            file_path,
            file_format_column_names=column_names,
            custom_column_names=custom_data_map,
        )

        self.sample_rate = sample_rate
        self.box_l = box_l

        self.n_header_lines = n_header_lines
        self._properties_dict = None
        self._batch_size = None

    def _get_metadata(self):
        """
        Gets the metadata for database creation as an implementation of the parent class virtual function.
        Side effect: Also creates the lookup dictionaries on where to find the particles and properties in the file for later use when actually reading the file
        """

        with open(self.file_path, "r") as file:
            file.seek(0)
            mdsuite.file_io.tabular_text_files.skip_n_lines(file, self.n_header_lines)
            # lammps log files can have multiple blocks of data interrupted by blocks of log info
            # we read only the first block starting after n_header_lines
            # this will mess up batching if this block is significantly smaller than the total file,
            # but it will only affect performance, not safety

            first_data_line = mdsuite.file_io.tabular_text_files.read_n_lines(file, 1)[
                0
            ]
            n_columns = len(first_data_line.split())
            n_steps = 1
            for line in file:
                if len(line.split()) != n_columns:
                    break
                n_steps += 1

            file.seek(0)
            headers = mdsuite.file_io.tabular_text_files.read_n_lines(
                file, self.n_header_lines
            )
            column_header = headers[-1]
            self._properties_dict = (
                mdsuite.file_io.tabular_text_files.extract_properties_from_header(
                    column_header.split(), self._column_name_dict
                )
            )

        properties_list = []
        for prop_name, prop_idxs in self._properties_dict.items():
            properties_list.append(
                mdsuite.database.simulation_database.PropertyInfo(
                    name=prop_name, n_dims=len(prop_idxs)
                )
            )
        species_list = [
            mdsuite.database.simulation_database.SpeciesInfo(
                name="Observables", n_particles=1, properties=properties_list
            )
        ]
        mdata = mdsuite.database.simulation_database.TrajectoryMetadata(
            n_configurations=n_steps, species_list=species_list, box_l=self.box_l
        )

        self._batch_size = mdsuite.utils.meta_functions.optimize_batch_size(
            filepath=self.file_path, number_of_configurations=n_steps
        )

        return mdata

    def get_configurations_generator(
        self,
    ) -> typing.Iterator[mdsuite.file_io.file_read.TrajectoryChunkData]:
        n_configs = self.metadata.n_configurations
        n_batches, n_configs_remainder = divmod(int(n_configs), int(self._batch_size))
        species_to_line_idx_dict = {self.metadata.species_list[0].name: [0]}

        with open(self.file_path, "r") as file:
            file.seek(0)
            # skip the header
            mdsuite.file_io.tabular_text_files.skip_n_lines(file, self.n_header_lines)
            for _ in tqdm.tqdm(range(n_batches)):
                yield mdsuite.file_io.tabular_text_files.read_process_n_configurations(
                    file,
                    self._batch_size,
                    self.metadata.species_list,
                    species_to_line_idx_dict,
                    self._properties_dict,
                    1,
                    n_header_lines=0,
                )
            if n_configs_remainder > 0:
                yield mdsuite.file_io.tabular_text_files.read_process_n_configurations(
                    file,
                    n_configs_remainder,
                    self.metadata.species_list,
                    species_to_line_idx_dict,
                    self._properties_dict,
                    1,
                    n_header_lines=0,
                )
