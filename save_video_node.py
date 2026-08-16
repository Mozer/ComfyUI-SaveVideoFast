import os
import subprocess
import tempfile
import time
import numpy as np
import torch
import folder_paths

class SaveVideoFast:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "frames": ("IMAGE", {"tooltip": "Input image batch (frames) to encode as video."}),
                "frame_rate": ("INT", {
                    "default": 24,
                    "min": 1,
                    "max": 120,
                    "step": 1,
                    "tooltip": "Frames per second. 24 is film standard, 30 for TV, 60 for smooth motion."
                }),
                "video_quality": ("INT", {
                    "default": 23,
                    "min": 2,
                    "max": 31,
                    "step": 1,
                    "tooltip": "Lower = better quality (higher bitrate). 23 is a good balance. Range: 2 (near lossless) – 31 (very low)."
                }),
                "codec": (["h264_nvenc", "h264"], {
                    "default": "h264_nvenc",
                    "tooltip": "h264_nvenc uses NVIDIA GPU (fastest). h264 uses CPU (slower, but works without GPU)."
                }),
                "preset": (["p1", "p2", "p3", "p4", "p5", "p6", "p7"], {
                    "default": "p1",
                    "tooltip": "p1 = fastest encode (lowest quality). p7 = slowest (best quality). p1 is recommended for speed."
                }),
            },
            "optional": {
                "audio": ("AUDIO", {"tooltip": "Optional AUDIO input. If provided, it will be muxed into the MP4."}),
            }
        }

    RETURN_TYPES = ()
    RETURN_NAMES = ()
    FUNCTION = "save_video"
    OUTPUT_NODE = True
    CATEGORY = "video"

    def save_video(self, frames, frame_rate, video_quality, codec, preset, audio=None):
        # ---------- 1. Validate frames ----------
        if frames is None or len(frames) == 0:
            print("[SaveVideoFast] No frames provided.")
            return {"ui": {"gifs": []}}

        num_frames = len(frames)
        H, W = frames.shape[1], frames.shape[2]

        # ---------- 2. Prepare output path ----------
        output_dir = folder_paths.get_output_directory()
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        out_filename = f"video_{timestamp}.mp4"
        out_path = os.path.join(output_dir, out_filename)

        # ---------- 3. Handle audio (write to temp PCM) ----------
        audio_temp = None
        audio_input_spec = None
        if audio is not None and "waveform" in audio and "sample_rate" in audio:
            waveform = audio["waveform"]
            sample_rate = audio["sample_rate"]

            if isinstance(waveform, torch.Tensor):
                wav_np = waveform.detach().cpu().numpy()
            else:
                wav_np = np.array(waveform)

            if wav_np.ndim == 1:
                wav_np = wav_np.reshape(1, -1)
            elif wav_np.ndim > 2:
                wav_np = wav_np.reshape(-1, wav_np.shape[-1])

            wav_int16 = (wav_np * 32767).astype(np.int16)
            if wav_int16.shape[0] > 1:
                wav_int16 = wav_int16.transpose(1, 0).reshape(-1)
            else:
                wav_int16 = wav_int16.flatten()

            channels = wav_np.shape[0]

            audio_temp = tempfile.NamedTemporaryFile(delete=False, suffix=".pcm")
            audio_temp.write(wav_int16.tobytes())
            audio_temp.close()

            audio_input_spec = {
                "path": audio_temp.name,
                "sample_rate": sample_rate,
                "channels": channels,
            }

        # ---------- 4. Build ffmpeg command ----------
        cmd = ["ffmpeg", "-y", "-loglevel", "quiet"]

        cmd += [
            "-f", "rawvideo",
            "-pix_fmt", "rgb24",
            "-s", f"{W}x{H}",
            "-r", str(frame_rate),
            "-i", "pipe:0"
        ]

        if audio_input_spec is not None:
            cmd += [
                "-f", "s16le",
                "-ar", str(audio_input_spec["sample_rate"]),
                "-ac", str(audio_input_spec["channels"]),
                "-i", audio_input_spec["path"]
            ]
            cmd += ["-map", "0:v", "-map", "1:a", "-c:a", "aac"]
        else:
            cmd += ["-map", "0:v"]

        if codec == "h264_nvenc":
            cmd += [
                "-c:v", "h264_nvenc",
                "-preset", preset,
                "-cq", str(video_quality),
                "-movflags", "+faststart"
            ]
        else:
            cmd += [
                "-c:v", "libx264",
                "-crf", str(video_quality),
                "-movflags", "+faststart"
            ]

        cmd += ["-pix_fmt", "yuv420p", out_path]

        # ---------- 5. Spawn ffmpeg & stream frames ----------
        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

        # --- Batch conversion and write (optimised) ---
        try:
            # Convert to uint8 on GPU if needed, then transfer to CPU
            if frames.is_cuda:
                if frames.dtype == torch.uint8:
                    frames_cpu = frames.cpu(non_blocking=True)
                else:
                    frames_uint8 = (frames * 255).byte().contiguous()
                    frames_cpu = frames_uint8.cpu(non_blocking=True)
                torch.cuda.synchronize()
            else:
                if frames.dtype == torch.uint8:
                    frames_cpu = frames.cpu()
                else:
                    frames_cpu = (frames * 255).byte().contiguous().cpu()

            frames_np = frames_cpu.numpy()
            if frames_np.shape[-1] == 4:
                frames_np = frames_np[:, :, :, :3]
            frames_np = np.ascontiguousarray(frames_np)
            data = frames_np.tobytes()

            # Write in chunks to avoid pipe limits (512 MB)
            CHUNK_SIZE = 512 * 1024 * 1024
            total_bytes = len(data)
            written = 0
            while written < total_bytes:
                chunk = data[written:written + CHUNK_SIZE]
                proc.stdin.write(chunk)
                written += len(chunk)
            proc.stdin.close()
        except BrokenPipeError:
            pass

        # Wait for ffmpeg to finish
        stdout, stderr = proc.communicate()
        if proc.returncode != 0:
            print(f"[SaveVideoFast] ffmpeg error:\n{stderr.decode()}")
            raise RuntimeError(f"ffmpeg failed: {stderr.decode()}")

        # ---------- 6. Clean up audio temp file ----------
        if audio_temp is not None:
            try:
                os.unlink(audio_temp.name)
            except OSError:
                pass

        # ---------- 7. Build UI preview ----------
        return {
            "ui": {
                "video": [
                    {
                        "filename": out_filename,
                        "subfolder": "",
                        "type": "output"
                    }
                ]
            }
        }