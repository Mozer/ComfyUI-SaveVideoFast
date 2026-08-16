# SaveVideoFast node for ComfyUI

A high performance video output node for [ComfyUI](https://github.com/comfyanonymous/ComfyUI) that encodes image sequences (batches of frames) into MP4 videos with optional audio. Optimised for speed, especially when processing frames generated on the GPU.

<img width="901" height="582" alt="speedup" src="https://github.com/user-attachments/assets/4ca61be1-eb50-4391-8bc3-30e0085f4bad" />


## Features

- **Ultra‑fast encoding** – uses ffmpeg with hardware acceleration (NVENC) when available.
- **Batch conversion on GPU** – frames are scaled and converted to `uint8` on the GPU before transfer, minimising CPU overhead.
- **Audio muxing** – optionally mux an audio track (AAC) into the final MP4.
- **Optimised pipe streaming** – writes raw video data in chunks to prevent deadlocks.
- **Flexible quality settings** – supports CRF (libx264) and CQ (NVENC) for fine‑grained control.
- **Configurable frame rate** and encoder preset.
- **Built‑in web preview** – the generated video is displayed inside an HTML5 `<video>` tag in the ComfyUI interface, allowing you to play, open, or save it directly.

## Requirements

- **ffmpeg** – must be installed and available in your system's `PATH`.  Guide: https://video.stackexchange.com/questions/20495/how-do-i-set-up-and-use-ffmpeg-in-windows
- ComfyUI (latest version recommended).

## Installation

1. Navigate to your ComfyUI `custom_nodes/` directory:
   ```bash
   cd ComfyUI/custom_nodes/
   ```
2. Clone this repository:
   ```bash
   git clone https://github.com/Mozer/ComfyUI-SaveVideoFast
   ```
3. Restart ComfyUI.

The node will appear as "Save Video Fast" in the node menu.

## Usage

Add the **SaveVideoFast** node to your workflow. Connect the `IMAGE` input (any source that outputs a batch of frames) and optionally an `AUDIO` input.

### Input Parameters

| Parameter        | Type    | Description                                                                                                   |
|------------------|---------|---------------------------------------------------------------------------------------------------------------|
| `frames`         | `IMAGE` | **(required)** Batch of image tensors in [N, H, W, C] format (C=3, RGB).                                      |
| `frame_rate`     | `INT`   | Frames per second. Default: `24`. Range: 1 – 120.                                                             |
| `video_quality`  | `INT`   | Quality/bitrate control. Lower = better quality. <br>For `libx264`: CRF value (0–51, default 23).<br>For `h264_nvenc`: CQ value (0–51, default 23). |
| `codec`          | `COMBO` | `h264_nvenc` (GPU, fastest) or `h264` (CPU, fallback). Default: `h264_nvenc`.                                 |
| `preset`         | `COMBO` | NVENC preset: `p1` – `p7` (p1 fastest, p7 best quality). Only used when `codec` is `h264_nvenc`. Default: `p1`. |
| `audio`          | `AUDIO` | **(optional)** Audio input (dict with `waveform` and `sample_rate`) from a ComfyUI audio node.                |

### Output

The node does **not** produce a tensor output. Instead, it:
- Saves the final MP4 file to ComfyUI's `output/` directory.
- Returns a UI preview that displays the video in an embedded HTML5 `<video>` tag, from which you can play, open in a new tab, or save it directly.

## Performance Tips

- **GPU‑to‑CPU transfer** – the node performs a single batch transfer of the entire frame sequence. Make sure your frames are on the GPU (e.g., from a VAE decode or interpolation node) to fully benefit from this optimisation.
- **Use NVENC** – if you have an NVIDIA GPU, select `h264_nvenc` for the fastest encoding. The `preset` can be dialled down (p1) for even higher speed at the cost of compression efficiency.
- **Chunked writing** – the node writes raw video data in 512 MB chunks, preventing pipe buffer exhaustion and ensuring stable encoding even with large batches.
- **Batch size** – encoding time scales with the number of frames and resolution. For very long videos, consider splitting into smaller segments if needed (though the node handles 500+ frames without issues).

## Troubleshooting

| Problem                                 | Solution                                                                               |
|-----------------------------------------|----------------------------------------------------------------------------------------|
| `ffmpeg` not found / error on start     | Ensure ffmpeg is installed and its binary is in your `PATH`. Check with `ffmpeg -version`. |
| Encoding is still slow                  | Verify that `codec` is set to `h264_nvenc` and that your GPU supports NVENC.           |
| Video has wrong length or is corrupted  | Check the frame count and that your `frame_rate` matches the intended duration.        |
| Audio out of sync                       | Confirm that the audio sample rate and length are consistent with the video duration.  |

## Credits

- Original concept based on ComfyUI’s video saving patterns.
- Performance optimisations (GPU‑side conversion, batch transfer) inspired by community discussions and profiling.

## License

[MIT](LICENSE) – feel free to use, modify, and distribute.
