import argparse
import subprocess
import datetime
import os
import glob
import shutil

# TODO: refactor into proper module structure, once file gets too long
# TODO: once the gui is WIP, assertions should be replaced with exceptions


def check_requirements():
    """
    Checks whether the required applications (ffmpeg, youtube-dl) are installed and callable.
    Suggest installation commands (currently for snap only) if problems are encountered.
    TODO: extend for alternative systems: Windows, OSX, other linux distros and package managers
    """
    # TODO: infer current system, call corresponding sub-method
    # TODO: upon failure: ask in command prompt,
    # whether the required install commands should be executed, and if so, as sudo
    try:
        subprocess.check_output(['which',  'ffmpeg'])
        subprocess.check_output(['which',  'youtube-dl'])
    except subprocess.CalledProcessError:
        print('[yt2mp3] One or both of the requried executables could not be found.'
              + 'Please make sure ffmpeg and youtube-dl are installed and executable.\n'
              + 'E.g. on systems supporting the snap package manager, execute\n'
              + '   "snap install ffmpeg youtube-dl"')
        exit()


def download_video_as_mp3(video_url):
    """
    Downloads the video behind video_url from youtube using youtube-dl.
    Then converts it to mp3 using ffmpeg.
    Writes the ID of the downloaded video to a (temporary) txt file and returns the file name

    Parameters:
    -----------
    video_url: str - The youtube video url

    Returns:
    --------
    Path to the file containing the IDs of the downloaded/created files
    Path to the downloaded mp3 file
    """
    archive_file = '.downloaded-{}.txt'.format(datetime.datetime.now())
    subprocess.call(['youtube-dl', '--ignore-errors',
                     '-f', 'bestaudio', '--extract-audio',
                     '--audio-format', 'mp3', '--audio-quality', '0',
                     '--download-archive', archive_file, video_url])
    assert os.path.isfile(archive_file), 'Download failed for video "{}"'.format(video_url)

    archive_content = open(archive_file, 'rt').read().split(' ')[1].strip()
    downloaded_file_name = glob.glob('*{}.mp3'.format(archive_content))[0]
    return archive_file, downloaded_file_name


def ensure_dir_exists(path_to_dir):
    """
    Ensures the path to a directory exists by attempting to create it if necessary.

    Parameters:
    -----------

    path_to_dir: str - the path to the directory which should exist after this function has been called
    """
    if not os.path.isdir(path_to_dir):
        os.makedirs(path_to_dir)


def determine_prepare_output(downloaded_file, output_dest, segment_length):
    """
    Determines and prepares the output location of the downloaded file.

    Parameters:
    -----------

    downloaded_file: str - path to the downloaded mp3 file

    output_dest: str or None - optional.
        Either none or a manually given output location

    segment_length: int or None - optional.
        Either a time in seconds or None. Determines whether the output is a directory or a file

    Returns:
    --------

    path_to_downloaded_file, path_to_output_destination

    the output path to either a file or a directory
    """

    output_is_file = segment_length is None

    if output_dest is None:
        output_dest = downloaded_file

    if output_is_file:
        if not output_dest.endswith('.mp3'):
            output_dest += '.mp3'
    else:
        ensure_dir_exists(output_dest)

    return output_dest


def move_download_to_output(downloaded_file_name, output_destination):
    """
    Moves the downloaded mp3 file -- whatever its name may be -- to the desired
    output destination.

    Parameters:
    -----------

    downloaded_file_name: str - the source file path

    output_destination: str - the target file path
    """
    if not downloaded_file_name == output_destination:
        print('[yt2mp3] Moving/Renaming downloaded mp3 to "{}"'.format(output_destination))
        shutil.move(downloaded_file_name, output_destination)


def split_download_into_segments(downloaded_file_name, output_destination, segment_length, segment_naming_pattern):
    """
    Splits the downloaded singular mp3 file into segments of equal length,
    and stores the files in the specified output destination.
    Removes the source file after finishing the process.

    Parameters:
    -----------

    downloaded_file_name: str - the path to the mp3 file downloaded earlier

    output_destination: str - path to the output folder. should exist.

    segment_length: int - the length in seconds of the target mp3 segments

    segment_naming_pattern: str - the naming pattern after which the generated segments are to be called.
    """

    assert os.path.isdir(output_destination), "Path to folder {} does not exist!".format(output_destination)
    if not segment_naming_pattern.endswith('.mp3'):
        segment_naming_pattern += '.mp3'

    segment_naming_pattern = '{}/{}'.format(output_destination, segment_naming_pattern)
    print('[yt2mp3] Splitting downloaded file "{}" into segments "{}"'.format(downloaded_file_name, segment_naming_pattern))
    subprocess.call(['ffmpeg', '-i', downloaded_file_name,
                     '-f', 'segment', '-segment_time', '{}'.format(segment_length),
                     '-c', 'copy',
                     segment_naming_pattern
                     ]
                    )

    assert len(glob.glob('{}/*.mp3'.format(output_destination))) > 0,\
        'Warning! No output mp3 segments have been generated at "{}/*.mp3"'.format(output_destination)

    # TODO add command line option for this
    print('[yt2mp3] removing downloaded file "{}"'.format(downloaded_file_name))
    os.remove(downloaded_file_name)


def remove_download_archive_file(archive_file_path):
    """
    After a successful execution of all other functions, remove the left-over
    file containing the download file information.

    Parametres:
    -----------

    archive_file_path: str - the path to the file to remove
    """

    assert os.path.isfile(archive_file_path),\
        "File {} can not be removed, as it does not exist!".format(archive_file_path)
    print('[yt2mp3] Removing download archive file "{}"'.format(archive_file_path))
    os.remove(archive_file_path)


def download_convert_split(args_namespace):
    """
    Executes the main functionality of this script:
    Downloads the video, extracts audio as mp3, optionally splits into multiple mp3 files

    Parameters:
    -----------

    args_namespace: Namespace - A Namespace type object, populated by the command line argument parser
        bundling all options for a single video conversion call.
    """

    # NOTE: Idea. this code describes functions implementing the default work flow.
    # Later, when adding a GUI, allow command line args optionally, as a way to pre-determine
    # the enterable option fields of the GUI.
    # Execute default function upon hitting a button.
    # IE, with the gui, make multiple processes executable after another.
    # maybe even asynchronously, allow configuration as batches.
    # for this it might make sense to introduce a simple batch job description language.
    # time will tell.

    # NOTE: ONLY USES THE FIRST PASSED VIDEO ID OR URL. IGNORES THE REST, FOR NOW. TODO: IMPROVE
    archive_file_path, downloaded_file = download_video_as_mp3(args_namespace.video[0])
    output_destination = determine_prepare_output(downloaded_file, args_namespace.output, args_namespace.segment_length)
    if args_namespace.segment_length is None:
        # no segments but single file: move output
        move_download_to_output(downloaded_file, output_destination)
    else:
        # split mp3 into segments
        split_download_into_segments(downloaded_file, output_destination, args_namespace.segment_length, args_namespace.segment_name)

    # clean up
    remove_download_archive_file(archive_file_path)


if __name__ == '__main__':
    # check for ffmpeg and youtube-dl
    check_requirements()

    # define and collect command line arguents (in command line mode.)
    # NOTE: later add "nogui" switch or sth, once gui exists
    # add keep-video option
    # add keep archive-file option
    argument_parser = argparse.ArgumentParser(description='Convert videos from Youtube to mp3 files!')
    argument_parser.add_argument('video', type=str, nargs='*',
                                 help='The URL or ID of the video to download and convert')
    argument_parser.add_argument('-sl', '--segment_length', type=int, default=None,
                                 help='If given, the downloaded mp3 file will be divided into segments of this length (in seconds)')
    argument_parser.add_argument('-sn', '--segment_name', type=str, default='%03d.mp3',
                                 help='the naming pattern of the output mp3 file segments')
    argument_parser.add_argument('-o', '--output', type=str, default=None,
                                 help='The destination file or folder the output shall be written to.')
    args = argument_parser.parse_args()

    # NOTE: terminate command line mode if no video has been given.
    if len(args.video) < 1:
        print('[yt2mp3] No video URL or ID argument passed. terminating.')
        exit()  # redundant exit call
    else:
        # core idea also for GUI use later: use Namespace object to bundle arguments.
        download_convert_split(args)

    # NOTE: does not make sense to execute multiple videos at once. limits:
    # parameterization. either call multiple instances of this script from
    # command line or implement this function later via GUI, ie by using ThreadPoolExecutor
    # to submit jobs and read their state (running, finished, exception happened).