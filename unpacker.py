#!/usr/bin/python3 -u

import struct
import bz2
import lzma
import bsdiff4
import binascii
import io
import os
import sys
import argparse
import shutil
from hashlib import sha256
from zipfile import ZipFile
from texttable import Texttable
from update_metadata_pb2 import DeltaArchiveManifest


class DecompressAndWrite:
    """Checks the operations and decompresses accordingly and writes it into a file """

    def __init__(self, operation, fd, img_file, orig_file, data_offset):
        self.operation = operation
        self.fd = fd
        self.img_file = img_file
        self.orig_file = orig_file
        self.data_offset = data_offset

    def decompress(self):
        """Decompresses the data according to the operation type"""

        self.fd.seek(self.data_offset + self.operation.data_offset)
        data = self.fd.read(self.operation.data_length)

        if self.operation.type == self.operation.REPLACE:
            self.img_file.seek(
                self.operation.dst_extents[0].start_block * block_size)
            self.img_file.write(data)

        elif self.operation.type == self.operation.REPLACE_BZ:
            dec = bz2.BZ2Decompressor()
            data = dec.decompress(data)
            self.img_file.seek(
                self.operation.dst_extents[0].start_block * block_size)
            self.img_file.write(data)

        elif self.operation.type == self.operation.REPLACE_XZ:
            dec = lzma.LZMADecompressor()
            data = dec.decompress(data)
            self.img_file.seek(
                self.operation.dst_extents[0].start_block * block_size)
            self.img_file.write(data)

        elif self.operation.type == self.operation.SOURCE_COPY:
            if not args.i:
                print('SOURCE_COPY only supported for incremental OTA')
                error()
            self.img_file.seek(
                self.operation.dst_extents[0].start_block * block_size)
            for src_ext in self.operation.src_extents:
                self.orig_file.seek(src_ext.start_block * block_size)
                data = self.orig_file.read(src_ext.num_blocks * block_size)
                self.img_file.write(data)

        elif self.operation.type == self.operation.SOURCE_BSDIFF:
            if not args.i:
                print('SOURCE_BSDIFF only supported for incremental OTA')
                error()
            self.img_file.seek(
                self.operation.dst_extents[0].start_block * block_size)
            tmp_buff = io.BytesIO()
            for src_ext in self.operation.src_extents:
                self.orig_file.seek(src_ext.start_block * block_size)
                orig_data = self.orig_file.read(
                    src_ext.num_blocks * block_size)
                tmp_buff.write(orig_data)
            tmp_buff.seek(0)
            orig_data = tmp_buff.read()
            tmp_buff.seek(0)
            patch_data = bsdiff4.patch(orig_data, data)
            tmp_buff.write(patch_data)
            num = 0
            tmp_buff.seek(0)
            for dst_ext in self.operation.dst_extents:
                tmp_buff.seek(num * block_size)
                num += dst_ext.num_blocks
                data = tmp_buff.read(dst_ext.start_block * block_size)
                self.img_file.seek(dst_ext.start_block * block_size)
                self.img_file.write(data)

        elif self.operation.type == self.operation.ZERO:
            for dst_ext in self.operation.dst_extents:
                self.img_file.seek(dst_ext.start_block * block_size)
                self.img_file.write(b'\x00' * dst_ext.num_blocks * block_size)

        else:
            print('Unsupported type {}'.format(self.operation.type))


class DumpPartition:
    """Dumps partitions by decompressing various sections"""

    def __init__(self, part, f, data_offset, dest):
        self.part = part
        self.fd = f
        self.dest = dest
        self.data_offset = data_offset

    def extract(self):
        print('Extracting partition : {}'.format(self.part.partition_name), end='  ')

        img_file = open(
            self.dest + '{}.img'.format(self.part.partition_name), 'wb')

        if args.i and cond:
            orig_file = open(
                'temp/{}.img'.format(self.part.partition_name), 'rb')
        else:
            orig_file = None

        for operation in self.part.operations:
            DecompressAndWrite(operation, self.fd, img_file, orig_file,
                               self.data_offset).decompress()
            print('.', end='')
        img_file.close()
        print('...done')


class DumpImages:

    def __init__(self, file, dest):
        self.file = file
        self.dest = dest
        self.dump()

    def dump(self):

        try:
            f = open(self.file, 'rb')
        except Exception as e:
            print("Error: {}".format(e))
            error()

        try:
            # Check Magic of the file
            assert f.read(4) == b'CrAU'
        except AssertionError:
            print("Invalid Magic Bytes")
            error()

        if not os.path.exists(self.dest):
            os.mkdir(self.dest)

        version = struct.unpack('>Q', f.read(8))[0]

        manifest_size = struct.unpack('>Q', f.read(8))[0]

        if version > 1:
            metadata_siglen = struct.unpack('>I', f.read(4))[0]

        manifest = f.read(manifest_size)
        metadata_sig = f.read(metadata_siglen)

        # data offset for calculating offset of data
        data_offset = f.tell()

        parser = DeltaArchiveManifest()
        parser.ParseFromString(manifest)
        global block_size
        block_size = parser.block_size
        if not cond:
            ListImg(parser)

        for partition in parser.partitions:
            """Dump each of the partition one by one"""

            DumpPartition(partition, f, data_offset, self.dest).extract()


def sizeof_fmt(num, suffix='B'):
    """converts bits into human readable size

    Args: 
        num: no of bits

    Returns:
        Size in human readable form
    """

    for unit in ['', 'Ki', 'Mi', 'Gi', 'Ti', 'Pi', 'Ei', 'Zi']:
        if abs(num) < 1024.0:
            return "%3.1f%s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f%s%s" % (num, 'Yi', suffix)


def getFileFromZip(file):
    """Extract and get path of payload.bin from zip

    Args: 
        file: zip path of the extracted file 

    Returns:
        Either file descriptor of payload.bin or program exits.

    """
    with ZipFile(file, 'r') as zip:
        for files in zip.filelist:
            if 'payload.bin' in files.filename:
                print("Extracting payload.bin from {}".format(file))
                return zip.extract(files.filename, 'temp')

    print('Error: payload.bin not found inside zip')
    error()


def ListImg(parser):
    """List all the images inside OTA file with corresponding size of the file

        Args: 
            parser: Structure like object with partition info

        Returns:
            No return value, just prints the list in the form of table
    """

    rows = [['Images', 'Size']]
    for partition in parser.partitions:
        rows.append([partition.partition_name, sizeof_fmt(
            partition.new_partition_info.size)])
    table = Texttable()
    table.add_rows(rows)
    print(table.draw())


def error():
    """Specifically created this to remove the temp folder before exiting incase of an error"""
    try:
        shutil.rmtree('temp/')
    except:
        pass
    sys.exit(-1)


if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument('file', help='Input file to unpack')
    parser.add_argument('-i', action='store_true',
                        help='option for incremental OTA')
    parser.add_argument('-o', default='orig',
                        help='path to original full update OTA package (incase of incremental ota)')
    try:
        args = parser.parse_args()
    except Exception as e:
        parser.print_help()
        print("Error : {}".format(e))
        sys.exit(-1)

    block_size = 0
    cond = False
    if '.zip' in args.file:
        args.file = getFileFromZip(args.file)

    if args.i:
        if '.zip' in args.o:
            Ffile = getFileFromZip(args.o)
        else:
            Ffile = args.o

        # First Dump payload.bin and extract images from it
        print("Dumping full update images into temp folder")
        DumpImages(Ffile, 'temp/')
        cond = True
        # Now extract the images from the incremental OTA using the images from the full update OTA
        print("Dumping incremental update images")
        DumpImages(args.file, 'output/')

    else:
        DumpImages(args.file, 'output/')
    
    try:
        shutil.rmtree('temp/')
    except:
        pass
