import argparse
import subprocess
import datetime
import os


def check_requirements():
    """
    Checks whether the required applications (ffmpeg, youtube-dl) are installed and callable.
    Suggest installation commands (currently for snap only) if problems are encountered.
    TODO: extend for alternative systems: Windows, OSX, other linux distros and package managers
    """
    try:
        subprocess.check_output(['which',  'ffmpeg'])
        subprocess.check_output(['which',  'youtube-dl'])
    except subprocess.CalledProcessError:
        print('One or both of the requried executables could not be found.'
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
    """
    archive_file = '.downloaded-{}.txt'.format(datetime.datetime.now())
    subprocess.call(['youtube-dl', '--ignore-errors',
                     '-f', 'bestaudio', '--extract-audio',
                     '--audio-format', 'mp3', '--audio-quality', '0',
                     '--download-archive', archive_file, video_url])
    assert os.path.isfile(archive_file), 'Download failed for video "{}"'.format(video_url)
    return archive_file


if __name__ == '__main__':
    # check for ffmpeg and youtube-dl
    check_requirements()

    # define and collect command line arguents (in command line mode.)
    # Note: later add "nogui" switch or sth, once gui exists
    argument_parser = argparse.ArgumentParser(description='Convert videos from Youtube to mp3 files!')
    argument_parser.add_argument('-v', '--video', type=str, help='The URL or ID of the video to download and convert')
    args = argument_parser.parse_args()

    archive_file_path = download_video_as_mp3(args.video)

