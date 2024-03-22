import subprocess as _subprocess
import threading
import logging
import tempfile
import ffmpeg
import base64
import os

from odoo import api, registry

_logger = logging.getLogger(__name__)


class ReactionVideoOverlayer(object):
    """
    A background daemon `thread` that will execute the code for overlaying the question video
    on top of the reaction video
    """

    def __init__(self, environment, user_input_line, question, video_reaction, use_hw_accel=False):
        _logger.info("Initializing video overlay thread...")
        thread = threading.Thread(target=self.run, args=(
            environment, user_input_line, question, video_reaction, use_hw_accel))
        thread.daemon = True
        thread.start()

    def run(self, environment, user_input_line, question, video_reaction, use_hw_accel=False):
        _logger.info("Running video overlay thread...")
        try:
            with api.Environment.manage():
                with registry(environment.cr.dbname).cursor() as new_cr:
                    uid, context = environment.uid, environment.context
                    env = api.Environment(new_cr, uid, context)
                    _user_input_line = user_input_line.with_env(env)
                    _question = question.with_env(env)
                    _video_reaction = video_reaction.with_env(env)

                    with tempfile.TemporaryDirectory() as working_dir:
                        # Changing the current working directory to the temporary working directory
                        os.chdir(working_dir)

                        temp_input_file = tempfile.NamedTemporaryFile(
                            dir=working_dir, suffix=".webm", delete=False)
                        _logger.info("Input File {}".format(os.path.exists(temp_input_file.name)))
                        
                        temp_overlay_file = tempfile.NamedTemporaryFile(
                            dir=working_dir, suffix=".mp4", delete=False)
                    
                        _logger.info("Overlay File {}".format(os.path.exists(temp_overlay_file.name)))
                        temp_output_file = tempfile.NamedTemporaryFile(
                            dir=working_dir, suffix='.mp4', delete=False)

                        temp_input_file_data = base64.b64decode(
                            _video_reaction.datas)
                        temp_overlay_file_data = base64.b64decode(
                            _question.video_file)

                        temp_input_file.write(temp_input_file_data)
                        temp_overlay_file.write(temp_overlay_file_data)
                        
                        _logger.info("Starting video overlay process...")
                        return_code = self.do_overlay(
                            temp_input_file.name,
                            temp_overlay_file.name,
                            temp_output_file.name,
                            380,
                            20,
                            use_hw_accel
                        )

                        if return_code == 0:
                            store_fname = _video_reaction.store_fname
                            if store_fname:
                                # Removing of physical file from server filestore before storing overlayed video
                                full_path = _video_reaction._full_path(store_fname)
                                if os.path.exists(full_path):
                                    os.remove(full_path)
                            _logger.info("Video overlay success, now saving to database...")
                            _video_reaction.sudo().write({
                                'mimetype': 'video/webm',
                                'datas': base64.b64encode(temp_output_file.read()),
                                'attachment_status': 'attached'
                            })
                        else:
                            _logger.error("Video overlay failed...")

        except Exception as e:
            _logger.error("Video overlay thread, unknown error encountered: {}".format(e), exc_info=True)
        finally:
            _logger.info("Done")

    def scale_video(self, stream, width=640, height=480):
        """
        Returns a scaled video stream
        """
        return stream['v'].filter_('scale', width, height)

    def change_audio_volume(self, stream, volume=1.0):
        """
        Returns an audio stream with modified volume
        """
        return stream['a'].filter_('volume', volume=volume)
        
    def log_subprocess_output(self, pipe):
        for line in iter(pipe.readline, b''): # b'\n'-separated lines
            _logger.info('got line from subprocess: %r', line)

    def merge_audio_streams(self, audio_1, audio_2):
        """
        Merges 2 audio streams into one audio stream using ffmpeg `amix`
        """
        return ffmpeg.filter_([audio_1, audio_2], 'amix')

    def do_overlay(self, main_video, overlay_video, final_output_file, overlay_start_x=0, overlay_start_y=0, use_hw_accel=False):
        """
        Overlay a video on top of another video
        """
        main_vid_stream = ffmpeg.input(main_video)
        overlay_vid_stream = ffmpeg.input(overlay_video)
        scaled_main_vid = self.scale_video(main_vid_stream, 640, 480)
        scaled_overlay_vid = self.scale_video(overlay_vid_stream, 240, 180)
        main_vid_audio = self.change_audio_volume(main_vid_stream, 1.25)
        overlay_vid_audio = self.change_audio_volume(overlay_vid_stream, 0.75)
        compiled_overlay_audio = self.merge_audio_streams(main_vid_audio, overlay_vid_audio)
        compiled_overlay_vid = ffmpeg.overlay(
            scaled_main_vid, scaled_overlay_vid, x=overlay_start_x, y=overlay_start_y)
        output = ffmpeg.output(compiled_overlay_audio,
                               compiled_overlay_vid, filename=final_output_file)
        if use_hw_accel:
            output = output.global_args('-movflags', 'faststart', '-nostdin', '-hwaccel')
        else:
            output = output.global_args('-movflags', 'faststart', '-nostdin')
        cmd = ffmpeg.compile(output, overwrite_output=True)
        
        process = _subprocess.Popen(cmd, stdout=_subprocess.PIPE, stderr=_subprocess.STDOUT)
        with process.stdout:
            self.log_subprocess_output(process.stdout)
        exit_code = process.wait()
        return exit_code
        # return _subprocess.check_call(cmd)
