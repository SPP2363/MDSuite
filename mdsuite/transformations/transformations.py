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
Parent class for the transformations.
"""
from __future__ import annotations

import abc
import copy
import logging
import os
import time
import typing
from typing import TYPE_CHECKING, Union

import numpy as np
import tensorflow as tf
import tqdm

import mdsuite.database.simulation_database
from mdsuite.database.data_manager import DataManager
from mdsuite.database.simulation_database import Database
from mdsuite.memory_management.memory_manager import MemoryManager
from mdsuite.utils.meta_functions import join_path

if TYPE_CHECKING:
    from mdsuite.experiment import Experiment

switcher_transformations = {
    "Translational_Dipole_Moment": "TranslationalDipoleMoment",
    "Ionic_Current": "IonicCurrent",
    "Integrated_Heat_Current": "IntegratedHeatCurrent",
    "Thermal_Flux": "ThermalFlux",
    "Momentum_Flux": "MomentumFlux",
    "Kinaci_Heat_Current": "KinaciIntegratedHeatCurrent",
}


class Transformations:
    """
    Parent class for MDSuite transformations.

    Attributes
    ----------
    database : Database
            database class object for data loading and storing
    experiment : object
            Experiment class instance to update
    batch_size : int
            batch size for the computation
    n_batches : int
            Number of batches to be looped over
    remainder : int
            Remainder amount to add after the batches are looped over.
    data_manager : DataManager
            data manager for handling the data transfer
    memory_manager : MemoryManager
            memory manager for the computation.
    """

    def __init__(
        self,
        experiment: Experiment,
        input_properties: typing.Iterable[
            mdsuite.database.simulation_database.PropertyInfo
        ] = None,
        output_property: mdsuite.database.simulation_database.PropertyInfo = None,
        batchable_axes: typing.Iterable[int] = None,
        scale_function=None,
        dtype=tf.float64,
    ):
        """
        Init of the transformator base class.

        Parameters
        ----------
        experiment:
            experiment on which to perform the transformation
        input_properties : typing.Iterable[
                    mdsuite.database.simulation_database.PropertyInfo]
            The properties needed to perform the transformation.
            e.g. unwrapped positions for the wrap_coordinates transformation.
            Properties from this list are provided to the self.transform_batch(),
            in which the actual transformation happens.
        output_property : mdsuite.database.simulation_database.PropertyInfo
            The property that is the result of the transformation
        scale_function :
            specifies memory requirements of the transformation
        dtype :
            data type of the processed values
        """
        self._experiment = None
        self._database = None
        self.batchable_axes = batchable_axes
        # todo: list of int indicating along which axis batching is performed, e.g.
        # rdf : batchable along time, but not particles or dimension: [1]
        # msd : batchable along particles and dimension, but not time [0,2]
        # unwrap_coordinates : batchable along all 3 axes [0,1,2]
        # this information should then be used by the batch generator further down
        # the current batching along tine only is arbitrary and should be generalized.
        # then, minibatching is a natural consequence of transformations which have more
        # than one batchable axis.

        self.input_properties = input_properties
        self.output_property = output_property
        self.logger = logging.getLogger(__name__)
        self.scale_function = scale_function
        self.dtype = dtype

        self.batch_size: int
        self.n_batches: int
        self.remainder: int

        self.dependency = None  # todo: legacy, to be replaced by input_property
        self.offset = 0

        self.data_manager: DataManager
        self.memory_manager: MemoryManager

    @property
    def database(self):
        """Update the database

        replace for https://github.com/zincware/MDSuite/issues/404
        """
        if self._database is None:
            self._database = Database(
                name=(self.experiment.database_path / "database.hdf5").as_posix(),
                architecture="simulation",
            )
        return self._database

    @property
    def experiment(self) -> Experiment:
        """TODO replace for https://github.com/zincware/MDSuite/issues/404"""
        return self._experiment

    @experiment.setter
    def experiment(self, value):
        self._experiment = value

    def update_from_experiment(self):
        """Update all self attributes that depend on the experiment

        Temporary method until https://github.com/zincware/MDSuite/issues/404
        is solved.
        """
        pass

    def _run_dataset_check(self, path: str):
        """
        Check to see if the database dataset already exists. If it does, the
        transformation should extend the dataset and add data to the end of
        it rather than try to add data.

        Parameters
        ----------
        path : str
                dataset path to check.
        Returns
        -------
        outcome : bool
                If True, the dataset already exists and should be extended.
                If False, a new dataset should be built.
        """
        return self.database.check_existence(path)

    def _run_dependency_check(self):
        """
        Check that dependencies are fulfilled.

        Returns
        -------
        Calls a resolve method if dependencies are not met.
        """
        truth_array = []
        path_list = [
            join_path(species, self.dependency) for species in self.experiment.species
        ]
        for item in path_list:
            truth_array.append(self.database.check_existence(item))
        if all(truth_array):
            return
        else:
            self._resolve_dependencies(self.dependency)

    def _resolve_dependencies(self, dependency):
        """
        Resolve any calculation dependencies if possible.

        Parameters
        ----------
        dependency : str
                Name of the dependency to resolve.

        Returns
        -------

        """

        def _string_to_function(argument):
            """
            Select a transformation based on an input

            Parameters
            ----------
            argument : str
                    Name of the transformation required

            Returns
            -------
            transformation call.
            """

            switcher_unwrapping = {"Unwrapped_Positions": self._unwrap_choice()}

            switcher = {**switcher_unwrapping, **switcher_transformations}

            try:
                return switcher[argument]
            except KeyError:
                raise KeyError("Data not in database and can not be generated.")

        transformation = _string_to_function(dependency)
        self.experiment.perform_transformation(transformation)

    def _unwrap_choice(self):
        """
        Unwrap either with indices or with box arrays.
        Returns
        -------

        """
        indices = self.database.check_existence("Box_Images")
        if indices:
            return "UnwrapViaIndices"
        else:
            return "UnwrapCoordinates"

    def _update_type_dict(self, dictionary: dict, path_list: list, dimension: int):
        """
        Update a type spec dictionary.

        Parameters
        ----------
        dictionary : dict
                Dictionary to append
        path_list : list
                List of paths for the dictionary
        dimension : int
                Dimension of the property
        Returns
        -------
        type dict : dict
                Dictionary for the type spec.
        """
        for item in path_list:
            dictionary[str.encode(item)] = tf.TensorSpec(
                shape=(None, None, dimension), dtype=tf.float64
            )

        return dictionary

    def _update_species_type_dict(
        self, dictionary: dict, path_list: list, dimension: int
    ):
        """
        Update a type spec dictionary for a species input.

        Parameters
        ----------
        dictionary : dict
                Dictionary to append
        path_list : list
                List of paths for the dictionary
        dimension : int
                Dimension of the property
        Returns
        -------
        type dict : dict
                Dictionary for the type spec.
        """
        for item in path_list:
            species = item.split("/")[0]
            n_atoms = self.experiment.species[species].n_particles
            dictionary[str.encode(item)] = tf.TensorSpec(
                shape=(n_atoms, None, dimension), dtype=tf.float64
            )

        return dictionary

    def _remainder_to_binary(self):
        """
        If a remainder is > 0, return 1, else, return 0
        Returns
        -------
        binary_map : int
                If remainder > 0, return 1, else,  return 0
        """
        return int(self.remainder > 0)

    def _save_output(
        self,
        data: Union[tf.Tensor, np.array],
        index: int,
        batch_size: int,  # legacy
        data_structure: dict,
        system_tensor=False,  # legacy
        tensor=True,  # legacy
    ):
        """
        Save the tensor_values into the database_path

        Returns
        -------
        saves the tensor_values to the database_path.
        """

        # turn data into trajectory chunk
        # data_structure is dict {'/path/to/property':{'indices':irrelevant,
        #                           'columns':deduce->deduce n_dims, 'length':n_particles}
        species_list = list()
        # data structure only has 1 element
        key, val = list(data_structure.items())[0]
        path = str(copy.copy(key))
        path.rstrip("/")
        path = path.split("/")
        prop_name = path[-1]
        sp_name = path[-2]
        n_particles = val.get("length")
        if n_particles is None:
            try:
                # if length is not available try indices next
                n_particles = len(val.get("indices"))
            except TypeError:
                raise TypeError("Could not determine number of particles")
        if len(np.shape(data)) == 2:
            # data not for multiple particles, instead one value for all
            # -> create the n_particle axis
            data = data[np.newaxis, :, :]
        prop = mdsuite.database.simulation_database.PropertyInfo(
            name=prop_name, n_dims=len(val["columns"])
        )
        species_list.append(
            mdsuite.database.simulation_database.SpeciesInfo(
                name=sp_name, properties=[prop], n_particles=n_particles
            )
        )
        chunk = mdsuite.database.simulation_database.TrajectoryChunkData(
            chunk_size=np.shape(data)[1], species_list=species_list
        )
        # data comes from transformation with time in 1st axis, add_data needs it
        # in 0th axis
        chunk.add_data(
            data=np.swapaxes(data, 0, 1),
            config_idx=0,
            species_name=sp_name,
            property_name=prop_name,
        )

        try:
            self.database.add_data(chunk=chunk, start_idx=index + self.offset)
        except OSError:
            """
            This is used because in Windows and in WSL we got the error that
            the file was still open while it should already be closed. So, we
            wait, and we add again.
            """
            time.sleep(0.5)
            self.database.add_data(chunk=chunk, start_idx=index + self.offset)

    def _prepare_monitors(self, data_path: Union[list, np.array]):
        """
        Prepare the tensor_values and memory managers.

        Parameters
        ----------
        data_path : list
                List of tensor_values paths to load from the hdf5
                database_path.

        Returns
        -------

        """
        self.memory_manager = MemoryManager(
            data_path=data_path,
            database=self.database,
            memory_fraction=0.5,
            scale_function=self.scale_function,
            offset=self.offset,
        )
        (
            self.batch_size,
            self.n_batches,
            self.remainder,
        ) = self.memory_manager.get_batch_size()
        self.data_manager = DataManager(
            data_path=data_path,
            database=self.database,
            batch_size=self.batch_size,
            n_batches=self.n_batches,
            remainder=self.remainder,
            offset=self.offset,
        )

    def _prepare_database_entry(self, species: str):
        """
        Add or extend the dataset in which the transformation result is stored

        Parameters
        ----------
        species : str
                Species for which transformation is performed
        Returns
        -------
        tensor_values structure for use in saving the tensor_values to the
        database_path.
        """
        path = join_path(species, self.output_property.name)

        n_particles = self.experiment.species[species].n_particles
        n_dims = self.output_property.n_dims

        existing = self._run_dataset_check(path)
        if existing:
            old_shape = self.database.get_data_size(path)
            resize_structure = {
                path: (
                    n_particles,
                    self.experiment.number_of_configurations - old_shape[0],
                    n_dims,
                )
            }
            self.offset = old_shape[0]
            self.database.resize_dataset(resize_structure)

        else:
            number_of_configurations = self.experiment.number_of_configurations
            dataset_structure = {path: (n_particles, number_of_configurations, n_dims)}
            self.database.add_dataset(dataset_structure)

        data_structure = {
            path: {
                "indices": np.s_[:],
                "columns": list(range(n_dims)),
                "length": n_particles,
            }
        }

        return data_structure

    def run_transformation(self, species: list = None):
        """
        Perform the transformation
        """
        # species should be provided by caller (the experiment), for now we use the usual
        # pseudoglobal variable
        if species is None:
            species = self.experiment.species

        for species in species:

            # this check should be done by the caller
            if self.database.check_existence(
                os.path.join(species, self.output_property.name)
            ):
                self.logger.info(
                    f"{self.output_property.name} already exists for {species}, "
                    "skipping transformation"
                )
                continue

            output_data_structure = self._prepare_database_entry(species)

            type_spec = {
                str.encode(join_path(species, prop.name)): tf.TensorSpec(
                    shape=(None, None, prop.n_dims), dtype=self.dtype
                )
                for prop in self.input_properties
            }
            self._prepare_monitors(list(type_spec.keys()))
            batch_generator, batch_generator_args = self.data_manager.batch_generator()
            type_spec.update(
                {
                    str.encode("data_size"): tf.TensorSpec(shape=(), dtype=tf.int32),
                }
            )
            data_set = tf.data.Dataset.from_generator(
                batch_generator, args=batch_generator_args, output_signature=type_spec
            )
            data_set = data_set.prefetch(tf.data.experimental.AUTOTUNE)
            for index, batch_dict in tqdm.tqdm(
                enumerate(data_set),
                ncols=70,
                desc=f"Applying transformation to {species}",
            ):
                # remove species information from batch:
                # the transformation only has to know about the property
                # ideally, the keys of the batch dict are already ProprtyInfo instances
                batch_dict_wo_species = {}
                for key, val in batch_dict.items():
                    batch_dict_wo_species[str(key).split("/")[-1].strip("'")] = val
                transformed_batch = self.transform_batch(batch_dict_wo_species)
                self._save_output(
                    data=transformed_batch,
                    data_structure=output_data_structure,
                    index=index * self.batch_size,
                    batch_size=None,
                )

    @abc.abstractmethod
    def transform_batch(self, batch: typing.Dict[str, tf.Tensor]) -> tf.Tensor:
        """
        Do the actual transformation.
        Parameters
        ----------
        batch : dict
            The batch to be transformed. The keys are the names of the properties
            specified in self.input_properties, the values are the corresponding tensors.

        Returns
        -------
        The transformed batch, one tf.Tensor.
        """
        raise NotImplementedError("transformation of a batch must be implemented")
