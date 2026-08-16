import { app } from "../../scripts/app.js";

app.registerExtension({
    name: "SaveVideoFast.Preview",
    async beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData.name === "SaveVideoFast") {
            const onExecuted = nodeType.prototype.onExecuted;
            nodeType.prototype.onExecuted = function (message) {
                onExecuted?.apply(this, arguments);

                if (message?.video) {
                    const videoInfo = message.video[0];
                    const url = `/api/view?filename=${encodeURIComponent(videoInfo.filename)}&type=${videoInfo.type}&subfolder=${encodeURIComponent(videoInfo.subfolder)}`;

                    // Find or create video widget container
                    let widget = this.widgets?.find((w) => w.name === "video_preview");
                    if (!widget) {
                        const videoEl = document.createElement("video");
                        videoEl.controls = true;
                        videoEl.autoplay = false;
                        videoEl.muted = true;
                        videoEl.loop = true;
                        videoEl.style.width = "100%";

                        widget = this.addDOMWidget("video_preview", "video", videoEl, {
                            serialize: false,
                        });
                    }

                    // Update video source
                    const videoEl = widget.element;
                    videoEl.src = url;
                    videoEl.load();
                }
            };
        }
    },
});