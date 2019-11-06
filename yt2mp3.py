import argparse
import yt2mp3_utils


def download_convert_split(args_namespace, process_watcher=None):
    """
    Executes the main functionality of this script:
    Downloads the video, extracts audio as mp3, optionally splits into multiple mp3 files

    Parameters:
    -----------

    args_namespace: argparse.Namespace - A Namespace type object, populated either manually or
        by the command line argument parser
        bundling all options for a single video conversion call.

    process_watcher: object - (optional) some object instance containing a field child_processes
        of type list expecting a registration of child processes.
        This is hacky, but currently the only solution I am aware of.

    Returns:
    --------

    argparse.Namespace object as a configuration container.
    """

    # prepare some variables
    # NOTE: PREPARE PATH VARIABLES IN EXTRA FUNCTION. MUST EXIST/BE RETURNED BEFORE subprocess.Popen calls!
    download_dir = None
    archive_file = None
    video_file   = None
    mp3_file     = None
    tmp_mp3_file = None

    try:
        # NOTE: ONLY USES THE FIRST PASSED VIDEO ID OR URL. IGNORES THE REST, FOR NOW.
        download_dir, archive_file = yt2mp3_utils.download_video(args_namespace.video[0], process_watcher)
        mp3_file, video_file, tmp_mp3_file = yt2mp3_utils.video_to_mp3(download_dir, archive_file, process_watcher)
        output_destination = yt2mp3_utils.determine_prepare_output(mp3_file, args_namespace.output, args_namespace.segment_length)

        if args_namespace.segment_length is None:
            # no segments but single file: move output
            yt2mp3_utils.move_download_to_output(mp3_file, output_destination)
        else:
            # split mp3 into segments
            yt2mp3_utils.split_download_into_segments(mp3_file, output_destination,
                                                      args_namespace.segment_length,
                                                      args_namespace.segment_name,
                                                      process_watcher)
        print('[yt2mp3] SUCCESS! OUTPUTS CAN BE FOUND AT {}'.format(output_destination))
    except Exception as e:
        print('[yt2mp3] Bollocks! Process did not finish!')
        raise e

    finally:
        # clean up
        yt2mp3_utils.cleanup(download_dir, archive_file, video_file, tmp_mp3_file)


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
    # TODO: infer default output outside of .tmp folder
    # TODO: extend cleanup routine to catch orphaned .tmp folders in failure cases
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
    # read command line args
    args = parse_command_line_args()

    if args.nogui:
        # check for ffmpeg and youtube-dl
        yt2mp3_utils.check_requirements()

        if not args.video:
            # NOTE: terminate command line mode if no video has been given.
            print('[yt2mp3] No video URL or ID argument passed. terminating.')
            exit()  # redundant exit call
        # core idea also for GUI use later: use Namespace object to bundle arguments.
        download_convert_split(args)

    else:
        import qt5_gui as gui
        # change imports to exchange the gui, if furhter options are added in the future.
        # goal: portable, lightweigth, aesthetic. pixk and maximize n.
        gui.run()
