# Copyright 2021 AIT Austrian Institute of Technology GmbH
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from datetime import datetime
import os
from ros2bag.api import print_error
from ros2bag.verb import VerbExtension


class ConvertVerb(VerbExtension):
    """Convert storage and/or serialization format of bag and write to new bag."""

    def add_arguments(self, parser, cli_name):  # noqa: D102
        parser.add_argument(
            'bag_file', help='bag file to convert')
        parser.add_argument(
            '-o', '--output',
            help='destination of the bagfile to create, \
            defaults to a timestamped folder in the current directory')
        parser.add_argument(
            '-s', '--in-storage', default='sqlite3',
            help='storage identifier to be used for the input bag, defaults to "sqlite3"')
        parser.add_argument(
            '--out-storage', default='sqlite3',
            help='storage identifier to be used for the output bag, defaults to "sqlite3"')
        parser.add_argument(
            '-f', '--serialization-format', default='',
            help='rmw serialization format in which the messages are read, defaults to the'
                 ' rmw currently in use')
        parser.add_argument(
            '--output-serialization-format', default='cdr',
            help='rmw serialization format in which the messages are saved, defaults to cdr')

    def main(self, *, args):  # noqa: D102
        bag_file = args.bag_file
        if not os.path.exists(bag_file):
            return print_error("bag file '{}' does not exist!".format(bag_file))

        uri = args.output or datetime.now().strftime('rosbag2_%Y_%m_%d-%H_%M_%S')

        if os.path.isdir(uri):
            return print_error("Output folder '{}' already exists.".format(uri))

        # NOTE(hidmic): in merged install workspaces on Windows, Python entrypoint lookups
        #               combined with constrained environments (as imposed by colcon test)
        #               may result in DLL loading failures when attempting to import a C
        #               extension. Therefore, do not import rosbag2_transport at the module
        #               level but on demand, right before first use.
        from rosbag2_py import (
            SequentialReader,
            SequentialWriter,
            StorageOptions,
            ConverterOptions,
        )

        reader = SequentialReader()
        if not args.in_storage:
            args.in_storage = 'sqlite3'

        in_storage_options = StorageOptions(uri=bag_file, storage_id=args.in_storage)
        in_converter_options = ConverterOptions(
            input_serialization_format=args.serialization_format,
            output_serialization_format=args.output_serialization_format)
        reader.open(in_storage_options, in_converter_options)

        writer = SequentialWriter()
        out_storage_options = StorageOptions(uri=uri, storage_id=args.out_storage)
        out_converter_options = ConverterOptions(
            input_serialization_format=args.output_serialization_format,
            output_serialization_format=args.output_serialization_format)
        writer.open(out_storage_options, out_converter_options)

        for topic_metadata in reader.get_all_topics_and_types():
            topic_metadata.serialization_format = args.output_serialization_format
            writer.create_topic(topic_metadata)

        while reader.has_next():
            (topic, data, t) = reader.read_next()
            writer.write(topic, data, t)

        del writer
        del reader

        if os.path.isdir(uri) and not os.listdir(uri):
            os.rmdir(uri)
