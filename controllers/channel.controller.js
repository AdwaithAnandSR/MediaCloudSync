import { spawn } from "child_process";
import fs from "fs";
import path from "path";
import axios from "axios";
import { v4 as uuidv4 } from "uuid";
import cloudinary from "cloudinary";
import dotenv from "dotenv";
dotenv.config();

import { addStatus, updateStatus, getStatus } from "../store/channel.store.js";

// ✅ Cloudinary config
cloudinary.v2.config({
    cloud_name: process.env.CLOUDINARY_CLOUD_NAME,
    api_key: process.env.CLOUDINARY_API_KEY,
    api_secret: process.env.CLOUDINARY_API_SECRET
});

const COOKIES_FILE = path.resolve("cookies.txt");
const TMP_DIR = path.resolve("tmp");
if (!fs.existsSync(TMP_DIR)) fs.mkdirSync(TMP_DIR);

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
            else {
                console.error("yt-dlp error:", error);
                reject(new Error(error || "yt-dlp failed"));
            }
        });
    });
}

function get(processId) {
    return getStatus().find(s => s.id === processId) || {};
}

function markSkip(processId, reason) {
    updateStatus(processId, {
        skipCount: get(processId).skipCount + 1,
        currentStatus: `SKIPPED (${reason})`
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
        currentStatus: "Fetching videos...",
        progress: 0
    });

    try {
        const baseUrl = channelName.startsWith("http")
            ? channelName
            : `https://www.youtube.com/${channelName}`;

        const info = await runYtDlp([
            baseUrl,
            "--skip-download",
            "--flat-playlist",
            "--print-json",
            "--playlist-end",
            String(skip + limit),
            "--extractor-args",
            "youtubetab:skip=authcheck",
            "--user-agent",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "--cookies",
            COOKIES_FILE
        ]);

        console.log("info fetched 📝");

        const lines = info
            .trim()
            .split("\n")
            .slice(skip, skip + limit);
        const videos = lines.map(l => JSON.parse(l));

        for (let i = 0; i < videos.length; i++) {
            const v = videos[i];
            updateStatus(processId, {
                currentProcessing: i + 1,
                progress: Math.round(((i + 1) / videos.length) * 100)
            });

            const videoId = v.id;
            const url = `https://youtube.com/watch?v=${videoId}`;
            let outFile = "";
            let coverFile = "";

            try {
                // ✅ get full metadata
                const metaOut = await runYtDlp([
                    "-j",
                    "--no-playlist",
                    "--extractor-args",
                    "youtubetab:skip=authcheck",
                    "--user-agent",
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
                    "--retries",
                    "infinite",
                    "--fragment-retries",
                    "infinite",
                    "--cookies",
                    COOKIES_FILE,
                    url
                ]);

                let meta;
                try {
                    meta = JSON.parse(metaOut);
                } catch (e) {
                    markSkip(processId, "Invalid JSON");
                    continue;
                }

                const duration = meta.duration || 0;
                const title = meta.title || "Unknown";
                updateStatus(processId, { title });

                // ✅ skip logic
                if (meta.categories && !meta.categories.includes("Music")) {
                    markSkip(processId, "not Music");
                    continue;
                }

                const isExistsRes = await axios.post(
                    "https://vivid-music.vercel.app/checkSongExistsByYtId",
                    { id: videoId, title }
                );

                if (isExistsRes.data.exists) {
                    markSkip(processId, "already exists");
                    continue;
                }

                if (duration < 120 || duration > 480) {
                    markSkip(processId, "duration");
                    continue;
                }

                // ✅ download audio
                outFile = path.join(TMP_DIR, `${videoId}.mp3`);
                await runYtDlp([
                    "-x",
                    "--audio-format",
                    "mp3",
                    "-o",
                    path.join(TMP_DIR, `${videoId}.%(ext)s`),
                    "--sleep-interval",
                    "5",
                    "--max-sleep-interval",
                    "15",
                    "--extractor-args",
                    "youtubetab:skip=authcheck",
                    "--user-agent",
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
                    "--cookies",
                    COOKIES_FILE,
                    "--retries",
                    "infinite",
                    "--fragment-retries",
                    "infinite",
                    url
                ]);

                // yt-dlp may create weird filenames → normalize
                const files = fs.readdirSync(TMP_DIR);
                const audioFile = files.find(
                    f => f.startsWith(videoId) && f.endsWith(".mp3")
                );
                if (!audioFile)
                    throw new Error("Audio file not found after yt-dlp");
                outFile = path.join(TMP_DIR, audioFile);

                // ✅ download thumbnail
                if (meta.thumbnail) {
                    coverFile = path.join(TMP_DIR, `${videoId}.jpg`);
                    const img = await axios.get(meta.thumbnail, {
                        responseType: "arraybuffer"
                    });
                    fs.writeFileSync(coverFile, img.data);
                }

                // ✅ upload to cloudinary
                const songUpload = await cloudinary.v2.uploader.upload(
                    outFile,
                    {
                        resource_type: "auto"
                    }
                );

                let coverUpload = { secure_url: "" };
                if (coverFile && fs.existsSync(coverFile)) {
                    coverUpload =
                        await cloudinary.v2.uploader.upload(coverFile);
                }

                // ✅ push to API
                const { data } = await axios.post(
                    "https://vivid-music.vercel.app/addSong",
                    {
                        title,
                        id: videoId,
                        duration,
                        artist: meta.channel || meta.uploader || "Unknown",
                        songURL: songUpload.secure_url,
                        coverURL: coverUpload.secure_url
                    }
                );

                if (data.success) {
                    updateStatus(processId, {
                        successCount: get(processId).successCount + 1,
                        currentStatus: "SUCCESS"
                    });
                } else {
                    console.log("failed to update db");
                    updateStatus(processId, {
                        failCount: get(processId).failCount + 1,
                        currentStatus: "FAIL API"
                    });
                }
            } catch (err) {
                console.error("Processing failed", {
                    videoId,
                    error: err.message
                });
                updateStatus(processId, {
                    failCount: get(processId).failCount + 1,
                    currentStatus: "ERROR"
                });
            } finally {
                // ✅ cleanup files
                if (outFile && fs.existsSync(outFile)) fs.unlinkSync(outFile);
                if (coverFile && fs.existsSync(coverFile))
                    fs.unlinkSync(coverFile);
            }
        }

        updateStatus(processId, { status: "COMPLETED", currentStatus: "Done" });
    } catch (err) {
        console.error("Channel fetch failed:", err.message);
        updateStatus(processId, {
            status: "FAIL",
            currentStatus: "Failed fetching channel"
        });
    }
}
