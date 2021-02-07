"""
Parent class for file processing

Summary
-------
"""

import abc
from typing import TextIO


class FileProcessor(metaclass=abc.ABCMeta):
    """
    Parent class for file reading and processing

    Attributes
    ----------
    obj, project : object
            File object to be opened and read in.
    header_lines : int
            Number of header lines in the file format being read.
    """

    def __init__(self, obj, header_lines, file_path):
        """
        Python constructor

        Parameters
        ----------
        obj : object
                Experiment class instance to add to.

        header_lines : int
                Number of header lines in the given file format.
        """

        self.project = obj  # Experiment class instance to add to.
        self.header_lines = header_lines  # Number of header lines in the given file format.
        self.file_path = file_path   # path to the file being read

    @abc.abstractmethod
    def process_trajectory_file(self):
        """
        Get property groups from the trajectory
        This method is dependent on the code that generated the file. So it should be implemented in a grandchild class.
        """

        return

    @abc.abstractmethod
    def build_database_skeleton(self):
        """
        Build skeleton of the hdf5 database.py

        This method is dependent on the type of data (atoms, flux, etc.), therefore it should be implemented in a child
        class.

        Gathers all of the properties of the system using the relevant functions. Following the gathering
        of the system properties, this function will read through the first configuration of the dataset, and
        generate the necessary database structure to allow for the following generation to take place. This will
        include the separation of species, atoms, and properties. For a full description of the data structure,
        look into the documentation.
        """
        return

    @abc.abstractmethod
    def build_file_structure(self):
        """
        Build a skeleton of the file so that the database class can process it correctly.
        """

        return

    @abc.abstractmethod
    def read_configurations(self, number_of_configurations: int, file_object: TextIO, skip: bool = True):
        """
        Read in a number of configurations from a file

        Parameters
        ----------
        skip : bool
                If true, the header lines will be skipped, if not, the returned data will include the headers.
        number_of_configurations : int
                Number of configurations to be read in.
        file_object : obj
                File object to be read from.

        Returns
        -------
        configuration data : np.array
                Data read in from the file object.
        """

        return

    @staticmethod
    def _extract_properties(database_correspondence_dict, column_dict_properties):
        """
        Construct generalized property array

        Takes the lammps properties dictionary and constructs and array of properties which can be used by the species
        class.

        agrs:
            properties_dict (dict) -- A dictionary of all the available properties in the trajectory. This dictionary is
            built only from the LAMMPS symbols and therefore must be again processed to extract the useful information.

        returns:
            trajectory_properties (dict) -- A dictionary of the keyword labelled properties in the trajectory. The
            values of the dictionary keys correspond to the array location of the specific piece of data in the set.
        """

        # for each property label (position, velocity,etc) in the lammps definition
        for property_label, property_names in database_correspondence_dict.items():
            # for each coordinate for a given property label (position: x, y, z), get idx and the name
            for idx, property_name in enumerate(property_names):
                if property_name in column_dict_properties.keys():  # if this name (x) is in the input file properties
                    # we change the lammps_properties_dict replacing the string of the property name by the column name
                    database_correspondence_dict[property_label][idx] = column_dict_properties[property_name]

        # trajectory_properties only needs the labels with the integer columns, then we one copy those
        trajectory_properties = {}
        for property_label, properties_columns in database_correspondence_dict.items():
            if all([isinstance(property_column, int) for property_column in properties_columns]):
                trajectory_properties[property_label] = properties_columns

        print("I have found the following properties with the columns in []: ")
        [print(key, value) for key, value in trajectory_properties.items()]

        return trajectory_properties

    @staticmethod
    def _get_column_properties(header_line, skip_words=0):
        """
        Given a line of text with the header, split it, enumerate and put in a dictionary.
        This is used to create the column - variable correspondance (see self._extract_properties)

        :param header_line: str
        :return: dict
        """
        header_line = header_line[skip_words:]
        properties_summary = {variable: idx for idx, variable in enumerate(header_line)}
        return properties_summary