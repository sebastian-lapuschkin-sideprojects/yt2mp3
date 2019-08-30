import argparse
import yt2mp3_utils


def download_convert_split(args_namespace):
    """
    Executes the main functionality of this script:
    Downloads the video, extracts audio as mp3, optionally splits into multiple mp3 files

    Parameters:
    -----------

    args_namespace: argparse.Namespace - A Namespace type object, populated either manually or
        by the command line argument parser
        bundling all options for a single video conversion call.

    Returns:
    --------

    argparse.Namespace object as a configuration container.
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
    archive_file_path, downloaded_file = yt2mp3_utils.download_video_as_mp3(args_namespace.video[0])
    output_destination = yt2mp3_utils.determine_prepare_output(downloaded_file, args_namespace.output, args_namespace.segment_length)
    if args_namespace.segment_length is None:
        # no segments but single file: move output
        yt2mp3_utils.move_download_to_output(downloaded_file, output_destination)
    else:
        # split mp3 into segments
        yt2mp3_utils.split_download_into_segments(downloaded_file, output_destination,
                                                  args_namespace.segment_length, args_namespace.segment_name)

    # clean up
    yt2mp3_utils.remove_download_archive_file(archive_file_path)


def parse_command_line_args(argument_list=None):
    """
    Creates a argparse.Argument parser and parses given command line arguments.
    If not given explicitly, the args are parsed from the terminal input.

    Parameters:
    -----------
    argument_list: list - (optional): ['--a', 'list', '--of', 'params', '--like', 'this']
        where argument key words are distinguished from the values via leading hyphens (short form)
        or double hyphens (long form)
    """

    # define and collect command line arguents (in command line mode.)
    # TODO: add keep-video option
    # TODO: add keep archive-file option
    argument_parser = argparse.ArgumentParser(description='Convert videos from Youtube to mp3 files!')
    argument_parser.add_argument('video', type=str, nargs='*',
                                 help='The URL or ID of the video to download and convert')
    argument_parser.add_argument('-sl', '--segment_length', type=int, default=None,
                                 help='If given, the downloaded mp3 file will be divided into segments of this length (in seconds)')
    argument_parser.add_argument('-sn', '--segment_name', type=str, default='%03d.mp3',
                                 help='the naming pattern of the output mp3 file segments')
    argument_parser.add_argument('-o', '--output', type=str, default=None,
                                 help='The destination file or folder the output shall be written to.')
    argument_parser.add_argument('-n', '--nogui', action='store_true',
                                 help='Setting this option runs yt2mp3 for a single video without showing a GUI')

    if argument_list is None:
        return argument_parser.parse_args()
    else:
        return argument_parser.parse_args(argument_list)


if __name__ == '__main__':
    # check for ffmpeg and youtube-dl
    yt2mp3_utils.check_requirements()

    # read command line args
    args = parse_command_line_args()

    if args.nogui:
        if not args.video:
            # NOTE: terminate command line mode if no video has been given.
            print('[yt2mp3] No video URL or ID argument passed. terminating.')
            exit()  # redundant exit call
        # core idea also for GUI use later: use Namespace object to bundle arguments.
        download_convert_split(args)

    else:
        import qt5_gui as gui
        # change imports to exchange the gui, if furhter options are added.
        # goal: portable, lightweigth, aesthetic. pick 3.
        gui.run()

        # TODO: build gui (qt5? other. ) application and start it.
        # take initial parameterization from args.
        # repurpose argparse.Namespace as container.
        # allow execution of mutiple runs in tabs(?)
        # use threads for those tabs to encapsulate and run download_convert_split()

        # NOTE: does not make sense to execute multiple videos at once. limits:
        # parameterization. either call multiple instances of this script from
        # command line or implement this function later via GUI, ie by using ThreadPoolExecutor
        # to submit jobs and read their state (running, finished, exception happened).
