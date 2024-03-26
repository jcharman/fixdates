#!/usr/bin/python3

import argparse
from os import listdir, path, utime
import subprocess
from datetime import datetime
from pathlib import Path
from shutil import move
import logging

logger = logging.getLogger(__name__)


def list(directory: str) -> list:
    files = []
    for item in listdir(directory):
        if path.isdir(path.join(directory, item)):
            files += list(path.join(directory, item))
        else:
            files.append(path.join(directory, item))
    return files

def get_exif(exiftool, file) -> dict:
    ret_dict = {}
    exiftool_proc = subprocess.Popen([exiftool, '-d', '%Y:%m:%d %H:%M:%S', file], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = exiftool_proc.communicate()
    if exiftool_proc.returncode == 0:
        for line in out.decode().strip().split('\n'):
            line = line.strip().split(':', 1)
            ret_dict.update({line[0].strip():line[1].strip()})
        return ret_dict
    else:
        return None
    
def exif_to_date(exif):
    return datetime.strptime(exif['Create Date'], '%Y:%m:%d %H:%M:%S')

def sort_file(file, exif, output_dir):
    exif_date = exif_to_date(exif)
    logger.debug('EXIF has date %s', exif_date)
    dest_dir = path.join(output_dir, str(exif_date.year), str(exif_date.month).rjust(2, '0'))
    logger.debug('Creating \'%s\'', dest_dir)
    Path(dest_dir).mkdir(exist_ok=True, parents=True)
    logger.info('Moving \'%s\' -> \'%s\'', file, path.join(dest_dir, path.basename(file)))
    move(file, path.join(dest_dir, path.basename(file)))
    update_file(path.join(dest_dir, path.basename(file)), exif_date)
    
def update_file(file, timestamp):
    logger.info('Updating timestamps on \'%s\' to \'%s\'',file, timestamp)
    utime((file), (timestamp.timestamp(), timestamp.timestamp()))

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG, format="[%(asctime)s] %(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description='Script to match Linux file timestamps to EXIF data')
    parser.add_argument('directory', type=str, nargs='+', help='Directory containing source images.')
    parser.add_argument('-s', '--sort', action='store_true', help='Sort images into year/month subdirectories.')
    parser.add_argument('-o', '--output', type=str, help='Output directory (for use with --sort)')
    args = parser.parse_args()
    if args.sort:
        if args.output is None:
            parser.error('--sort requires --output directory to be set')
        logger.info('Creating output directory \'%s\'', args.output)
        Path(args.output).mkdir(exist_ok=True, parents=True)
    
    logger.debug('Attempting to find \'exiftool\'')
    which_proc = subprocess.Popen(['which', 'exiftool'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = which_proc.communicate()
    if which_proc.returncode == 0:
        exiftool = out.decode().strip()
        logger.info('Found \'exiftool\' at \'%s\'', exiftool)
    else:
        logger.critical('Failed to find \'exiftool\' is it installed?')
        raise FileNotFoundError('Could not find exiftool')

    for dir in args.directory:
        for file in list(dir):
            logger.info('Processing file: \'%s\'', file)
            if get_exif(exiftool, file) is None:
                logger.warning('\'%s\' has no EXIF data. Will not process further', file)
                continue
            if args.sort:
                try:
                    sort_file(file, get_exif(exiftool, file), args.output)
                except Exception as e:
                    logger.error(e)
            else:
                try:
                    update_file(file, exif_to_date(get_exif(exiftool, file)))
                except Exception as e:
                    logger.error(e)


