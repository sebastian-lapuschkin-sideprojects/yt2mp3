# collects all utility functions

import subprocess
import datetime
import os
import glob
import shutil


def video_id(video_id_or_url):
    """
    Returns video id from given video id or url

    Parameters:
    -----------
    video_id_or_url: str - either a video id or url

    Returns:
    --------
    the video id
    """

    if 'watch?v=' in video_id_or_url:
        return video_id_or_url.split('watch?v=')[1]
    else:
        # assume we already have an video id
        return video_id_or_url

def video_url(video_id_or_url):
    """
    Returns video url from given video id or url

    Parameters:
    -----------
    video_id_or_url: str - either a video id or url

    Returns:
    --------
    the video url
    """
    # prepare building of proper url
    vid = video_id(video_id_or_url)
    return 'https://www.youtube.com/watch?v={}'.format(vid)


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


def download_video(video_url, process_watcher=None):
    """
    Downloads the video behind video_url from youtube using youtube-dl.
    Writes the ID of the downloaded video to a (temporary) txt file and returns the file name

    Parameters:
    -----------
    video_url: str - The youtube video url or id

    process_watcher: object - (optional) some object instance containing a field child_processes of type list expecting a registration of child processes.
        This is hacky, but currently the only solution I am aware of.

    Returns:
    --------
    Path to the file containing the IDs of the downloaded/created files
    Path to the downloaded mp3 file
    """
    download_dir = '.tmp-{}'.format(video_id(video_url)) #, datetime.datetime.now())
    archive_file = '{}/downloaded.txt'.format(download_dir)
    ensure_dir_exists(download_dir)
    # youtube-dl also provides a command line interface which is more
    # rich and clear than its python API
    cmd = ['youtube-dl',
            '--ignore-errors',
            '--format', 'bestaudio',
            '--download-archive', archive_file,
            '--output', '{}/%(title)s-%(id)s.%(ext)s'.format(download_dir),
            video_url
            ]
    proc = subprocess.Popen(cmd)
    if process_watcher:
        process_watcher.child_processes.append(proc)
    proc.wait()

    assert os.path.isfile(archive_file), 'Download failed for video "{}"'.format(video_url)
    return download_dir, archive_file


def video_to_mp3(download_dir, archive_file, process_watcher=None):
    """
    Converts a downloaded video to mp3

    Parameters:
    -----------
    download_dir: str - the directory the video is currently located in

    archive_file: str - the path to the during the download created archive file holding the video id

    process_watcher: object - (optional) some object instance containing a field child_processes of type list expecting a registration of child processes.
        This is hacky, but currently the only solution I am aware of.

    Returns:
    --------

    path to the downloaded mp3 file name
    """

    assert os.path.isdir(download_dir), "Download directory {} missing!".format(download_dir)
    assert os.path.isfile(archive_file), "Archive file {} missing! Did the download fail?".format(archive_file)
    video_id = None
    with open(archive_file,'rt') as f:
        video_id = f.read().split(' ')[1].strip()
    pattern = '{}/*{}.*'.format(download_dir, video_id)
    downloaded_file_name = glob.glob(pattern)[0]
    mp3_file_name = os.path.splitext(downloaded_file_name)[0] + '.mp3'
    tmp_mp3_file_name = mp3_file_name.replace('.mp3', '.tmp.mp3')

    # redundant
    assert os.path.isfile(downloaded_file_name), 'Downloaded file has magically vanished?'

    # convert
    cmd = ['ffmpeg',
           '-i', downloaded_file_name,
           '-q:a', '2',
           '-vn', tmp_mp3_file_name]
    proc = subprocess.Popen(cmd)
    if process_watcher:
        process_watcher.child_processes.append(proc)
    proc.wait()

    assert os.path.isfile(tmp_mp3_file_name), 'Conversion from Video to MP3 file failed! (pre-rename)'
    shutil.move(tmp_mp3_file_name, mp3_file_name)
    assert os.path.isfile(mp3_file_name), 'Conversion from Video to MP3 file failed! (post-rename)'
    print('[yt2mp3] MP3 output saved to {}'.format(mp3_file_name))
    return mp3_file_name, downloaded_file_name, tmp_mp3_file_name




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


def split_download_into_segments(downloaded_file_name, output_destination, segment_length, segment_naming_pattern, process_watcher=None):
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

    process_watcher: object - (optional) some object instance containing a field child_processes of type list expecting a registration of child processes.
        This is hacky, but currently the only solution I am aware of.
    """

    assert os.path.isdir(output_destination), "Path to folder {} does not exist!".format(output_destination)
    if not segment_naming_pattern.endswith('.mp3'):
        segment_naming_pattern += '.mp3'

    segment_naming_pattern = '{}/{}'.format(output_destination, segment_naming_pattern)
    cmd = ['ffmpeg',
           '-i', downloaded_file_name,
           '-f', 'segment',
           '-segment_time', '{}'.format(segment_length),
           '-c', 'copy',
           segment_naming_pattern
           ]

    print('[yt2mp3] Splitting downloaded file "{}" into segments "{}"'.format(downloaded_file_name, segment_naming_pattern))
    proc = subprocess.Popen(cmd)
    if process_watcher:
        process_watcher.child_processes.append(proc)
    proc.wait()

    assert len(glob.glob('{}/*.mp3'.format(output_destination))) > 0,\
        'Warning! No output mp3 segments have been generated at "{}/*.mp3"'.format(output_destination)

    # TODO add command line option for this
    print('[yt2mp3] removing downloaded file "{}"'.format(downloaded_file_name))
    os.remove(downloaded_file_name)


def cleanup(download_dir, archive_file, video_file, tmp_mp3_file_name):
    """
    After a successful execution of all other functions, remove the left-over
    file containing the download file information.

    Parameters:
    -----------

    download_dir: str or None - the directory the temp files are/have been in

    archive_file: str or None - the path to the file to remove

    video_file: str or None - the downloaded video file

    tmp_mp3_file_name: str or None - a temporary file location for mp3 file conversion
    """

    print(download_dir, archive_file, video_file, tmp_mp3_file_name)

    if archive_file and os.path.isfile(archive_file):
        print('[yt2mp3] Removing download archive file "{}"'.format(archive_file))
        os.remove(archive_file)

    if video_file and os.path.isfile(video_file):
        print('[yt2mp3] Removing downloaded youtube media file "{}"'.format(video_file))
        os.remove(video_file)

    if tmp_mp3_file_name and os.path.isfile(tmp_mp3_file_name):
        print('[yt2mp3] Removing temporary mp3 file "{}"'.format(tmp_mp3_file_name))
        os.remove(tmp_mp3_file_name)

    if download_dir and os.path.isdir(download_dir):
        if os.listdir(download_dir):
            print('[yt2mp3] Keeping non-empty output directory {}'.format(download_dir))
        else:
            print('[yt2mp3] Removing empty output directory "{}"'.format(download_dir))
            os.rmdir(download_dir)

