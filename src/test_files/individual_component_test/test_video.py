from moviepy.editor import ColorClip, TextClip, CompositeVideoClip

# 1. Create a background (Black, 9:16 aspect ratio, 5 seconds)
# Size 1080x1920 is standard for Shorts/TikTok
bg_clip = ColorClip(size=(1080, 1920), color=(0, 0, 0), duration=5)

# 2. Add Text (Requires ImageMagick, installed from brew)
# If this fails, we will switch to a simpler method.
txt_clip = TextClip("TEST VIDEO", fontsize=150, color='white', size=(1080, 1920), method='caption', font="Roboto")
txt_clip = txt_clip.set_duration(5)

# 3. Combine
video = CompositeVideoClip([bg_clip, txt_clip])

# 4. Export
video.write_videofile("test_video.mp4", fps=24)
print("Video successfully rendered!")
