# -*- coding: utf-8 -*-

from flask import current_app

import yaml
import os

from app.models.dataset import CsvFileDataset
from app.models.dataset import XlsFileDataset
from app.models.dataset import PgsqlDataset
from app.models.dataset import MysqlDataset
from app.models.framework import Framework

FRAMEWORKS_FILE_NAME = "frameworks.yml"


class Service(object):
    def __init__(self, **kwargs):
        # Default values
        self.cfg_file_path = None
        self.name = "default_service_name"
        self.activated = False
        self.title = "Default service title"
        self.abstract = "Default service abstract"
        self.service_provider = {}
        self.keywords = ["TJS", "geospatial"]
        self.fees = "NONE"
        self.access_constraints = "NONE"
        self.tjs_versions = ["1.0.0"]
        self.languages = ["fr"]
        self.data_dir_path = None
        self.abs_data_dir_path = None
        self.frameworks = {}  # keys of this dictionary are the frameworks uris
        self.datasets = {}

        self.update_service_info(**kwargs)

    def update_service_info(self, **kwargs):

        self.__dict__.update(kwargs)

        # Search for the parameters of the datasets published with this service
        self.abs_data_dir_path = None
        if os.path.isabs(self.data_dir_path):
            temp_path = self.abs_data_dir_path
        else:
            # Concatenating the paths of directory containing the service config file and the data relative path
            temp_path = os.path.join(
                os.path.dirname(self.cfg_file_path), self.data_dir_path
            )

        # print(temp_path)
        if os.path.exists(temp_path):
            self.abs_data_dir_path = temp_path

        # print(u"Répertoire du service {0}".format(self.abs_data_dir_path))

        if self.abs_data_dir_path is not None and os.path.exists(
            self.abs_data_dir_path
        ):
            self.update_frameworks_info()
            self.update_datasets_info()

        self.log_info()

    def update_frameworks_info(self):
        self.frameworks = {}

        # Recherche d'un fichier frameworks.yml
        frwks_yml_path = os.path.join(self.abs_data_dir_path, FRAMEWORKS_FILE_NAME)
        if os.path.exists(frwks_yml_path):

            with open(frwks_yml_path, "r", encoding='utf8') as stream:
                try:
                    frameworks_dict = yaml.safe_load(stream)

                    for k, v in list(frameworks_dict.items()):
                        v["name"] = k
                        f = Framework(**v)
                        self.frameworks[f.uri] = f
                except yaml.YAMLError as e:
                    current_app.logger.exception(e)

    def update_datasets_info(self):
        self.datasets = {}

        # Recherche des autres fichiers yaml correspondant à des jeux de données
        for root, dirs, files in os.walk(self.abs_data_dir_path):
            for f in files:
                if f.endswith(".yml") and f != FRAMEWORKS_FILE_NAME:
                    yaml_file_path = os.path.join(root, f)
                    try:
                        current_app.logger.info("Reading dataset config file:\n{0}...".format(yaml_file_path))
                        ds = self.create_dataset_instance(yaml_file_path)
                        self.datasets[ds.name] = ds
                    except ValueError as e:
                        current_app.logger.exception(e)
                    except KeyError as e:
                        current_app.logger.exception(e)
                        current_app.logger.error(
                            "Some critical fields are missing in the following dataset config file:"
                            " {0}".format(yaml_file_path)
                        )
                    except yaml.YAMLError as e:
                        current_app.logger.exception(e)
                        current_app.logger.error(
                            "The following dataset config file cannot be correctly read:"
                            " {0}".format(yaml_file_path)
                        )

    def log_info(self):
        current_app.logger.info(
            "Service: {0} ({1})".format(
                self.name, "activated" if self.activated else "deactivated"
            )
        )
        current_app.logger.info("- datapath: {0}".format(self.data_dir_path))
        for f in list(self.frameworks.items()):
            current_app.logger.info("- framework: {0} - {1}".format(f[1].title, f[0]))
        for ds in list(self.datasets.items()):
            current_app.logger.info("- dataset: {0} - {1}".format(ds[1].title, ds[0]))

    # factory function for datasets
    def create_dataset_instance(self, dataset_yaml_file_path):
        dataset_subclasses = [CsvFileDataset, XlsFileDataset, MysqlDataset, PgsqlDataset]
        dataset_subclass = None
        data_source_type = None
        frameworks = None

        # Get the data source type
        dataset_dict = {}
        with open(dataset_yaml_file_path, "r", encoding='utf8') as stream:
            # try:
            # Read the yaml file
            dataset_dict = yaml.safe_load(stream)

            # Save the yaml file path
            dataset_dict["yaml_file_path"] = dataset_yaml_file_path

            # Set the reference of the framework using its uri
            data_source = dataset_dict["data_source"]
            data_source_type = data_source["type"]

        if data_source_type is None:
            raise ValueError(
                "'data_source/type' parameter not defined in dataset config file {0}".format(
                    dataset_yaml_file_path
                )
            )

        # Get the dataset class with this data source type
        for sc in dataset_subclasses:
            if sc.DATA_SOURCE_TYPE == data_source_type:
                dataset_subclass = sc

        # Instantiate the right class
        if dataset_subclass is not None:
            return dataset_subclass(self, dataset_dict)

    def get_datasets(self):
        return list(self.datasets.values())

    def get_dataset_with_uri(self, dataset_uri):
        for f in self.get_datasets():
            if f.uri == dataset_uri:
                return f

    def get_datasets_for_framework_uri(self, framework_uri):
        datasets = []
        for dtst in self.get_datasets():
            for fmwk in dtst.get_frameworks():
                if fmwk.uri == framework_uri and dtst not in datasets:
                    datasets.append(dtst)
        return datasets

    def get_dataset_with_name(self, dataset_name):
        return self.datasets[dataset_name]

    def get_frameworks(self):
        return list(self.frameworks.values())

    def get_framework_with_uri(self, framework_uri):
        return self.frameworks.get(framework_uri, None)

    def get_framework_with_name(self, framework_name):
        for f in self.get_frameworks():
            if f.name == framework_name:
                return f

    def __repr__(self):
        return "%s(%r)" % (self.__class__, self.__dict__)
