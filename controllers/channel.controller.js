import { spawn } from "child_process";
import fs from "fs";
import path from "path";
import axios from "axios";
import { v4 as uuidv4 } from "uuid";
import cloudinary from "cloudinary";
import dotenv from "dotenv";
dotenv.config();

import { addStatus, updateStatus, getStatus } from "../store/channel.store.js";

cloudinary.v2.config({
    cloud_name: process.env.CLOUDINARY_CLOUD_NAME,
    api_key: process.env.CLOUDINARY_API_KEY,
    api_secret: process.env.CLOUDINARY_API_SECRET
});

function runYtDlp(args) {
    return new Promise((resolve, reject) => {
        const proc = spawn("yt-dlp", args);
        let output = "";
        let error = "";

        proc.stdout.on("data", data => {
            output += data.toString();
        });

        proc.stderr.on("data", data => {
            error += data.toString();
        });

        proc.on("close", code => {
            if (code === 0) resolve(output);
            else reject(new Error(error || "yt-dlp failed"));
        });
    });
}

export async function processChannel(channelName, skip = 0, limit = 10) {
    const processId = uuidv4();
    addStatus({
        id: processId,
        type: "channel",
        channelId: channelName,
        skip,
        limit,
        currentProcessing: 0,
        successCount: 0,
        failCount: 0,
        skipCount: 0,
        status: "PROCESSING",
        currentStatus: "Fetching videos..."
    });

    try {
        // ✅ fetch playlist metadata async
        const info = await runYtDlp([
            `https://www.youtube.com/${channelName}/videos`,
            "--skip-download",
            "--flat-playlist",
            "--print-json",
            "--playlist-end",
            String(skip + limit)
        ]);

        const lines = info
            .trim()
            .split("\n")
            .slice(skip, skip + limit);
        const videos = lines.map(l => JSON.parse(l));

        for (let i = 0; i < videos.length; i++) {
            const v = videos[i];
            updateStatus(processId, { currentProcessing: i + 1 });

            const videoId = v.id;
            const url = `https://youtube.com/watch?v=${videoId}`;

            try {
                // ✅ get full metadata async
                const metaOut = await runYtDlp(["-j", "--no-playlist", url]);
                const meta = JSON.parse(metaOut);

                const duration = meta.duration || 0;
                const title = meta.title || "Unknown";

                updateStatus(processId, {
                    title
                });

                // ✅ Check if song already exists (before download)
                const isExistsRes = await axios.post(
                    "https://vivid-music.vercel.app/checkSongExistsByYtId",
                    { id: videoId, title }
                );

                if (isExistsRes.data.exists) {
                    updateStatus(processId, {
                        skipCount: get(processId).skipCount + 1,
                        currentStatus: `SKIPPED (already exists)`
                    });
                    continue;
                }

                // ✅ Check duration range
                if (duration < 120 || duration > 480) {
                    updateStatus(processId, {
                        skipCount: get(processId).skipCount + 1,
                        currentStatus: `SKIPPED (duration)`
                    });
                    continue;
                }

                // ✅ download audio async
                const outFile = path.resolve(`${videoId}.mp3`);
                await runYtDlp([
                    "-x",
                    "--audio-format",
                    "mp3",
                    "-o",
                    outFile,
                    url
                ]);

                // ✅ download thumbnail
                const coverFile = path.resolve(`${videoId}.jpg`);
                if (meta.thumbnail) {
                    const img = await axios.get(meta.thumbnail, {
                        responseType: "arraybuffer"
                    });
                    fs.writeFileSync(coverFile, img.data);
                }

                // ✅ upload to cloudinary
                const songUpload = await cloudinary.v2.uploader.upload(
                    outFile,
                    {
                        resource_type: "video"
                    }
                );
                const coverUpload =
                    await cloudinary.v2.uploader.upload(coverFile);

                // ✅ push to API
                const { data } = await axios.post(
                    "https://vivid-music.vercel.app/addSong",
                    {
                        title,
                        id: videoId,
                        duration,
                        artist: meta.channel,
                        songURL: songUpload.secure_url,
                        coverURL: coverUpload.secure_url
                    }
                );

                if (data.success) {
                    updateStatus(processId, {
                        successCount: get(processId).successCount + 1,
                        currentStatus: `SUCCESS`
                    });
                } else {
                    updateStatus(processId, {
                        failCount: get(processId).failCount + 1,
                        currentStatus: `FAIL API`
                    });
                }

                // ✅ cleanup
                fs.unlinkSync(outFile);
                if (fs.existsSync(coverFile)) fs.unlinkSync(coverFile);
            } catch (err) {
                updateStatus(processId, {
                    failCount: get(processId).failCount + 1,
                    currentStatus: `ERROR`
                });
            }
        }

        updateStatus(processId, { status: "COMPLETED", currentStatus: "Done" });
    } catch (err) {
        updateStatus(processId, {
            status: "FAIL",
            currentStatus: "Failed fetching channel"
        });
    }
}

function get(processId) {
    return getStatus().find(s => s.id === processId) || {};
}
