import gi
import sys
from gi.repository import Gst, GObject, GLib

gi.require_version('Gst', '1.0')
gi.require_version('GstWebRTC', '1.0')

GstWebRTC = gi.module.get_introspection_module('GstWebRTC')

pipeline = None
bus = None
message = None

# initialize GStreamer
Gst.init(sys.argv[1:])


def main():
    pipeline = Gst.Pipeline.new("pipeline")

    source = Gst.ElementFactory.make("avfvideosrc", "source")
    source.set_property("capture-screen", True)

    videoconvert = Gst.ElementFactory.make("videoconvert", "videoconvert")

    x264enc = Gst.ElementFactory.make("x264enc", "x264enc")
    x264enc.set_property("tune", "zerolatency")

    webrtcsink = Gst.ElementFactory.make("webrtcsink", "webrtcsink")

    if not pipeline or not source or not videoconvert or not x264enc or not webrtcsink:
        print("Not all elements could be created.")
        return

    pipeline.add(source)
    pipeline.add(videoconvert)
    pipeline.add(x264enc)
    pipeline.add(webrtcsink)

    if not source.link(videoconvert):
        print("Source and videoconvert could not be linked.")
        return
    if not videoconvert.link(x264enc):
        print("Videoconvert and x264enc could not be linked.")
        return
    if not x264enc.link(webrtcsink):
        print("x264enc and webrtcsink could not be linked.")
        return

    pipeline.set_state(Gst.State.PLAYING)

    # wait until EOS or error
    bus = pipeline.get_bus()
    msg = bus.timed_pop_filtered(
        Gst.CLOCK_TIME_NONE,
        Gst.MessageType.ERROR | Gst.MessageType.EOS
    )

    # free resources
    pipeline.set_state(Gst.State.NULL)

if __name__ == '__main__':
    main()