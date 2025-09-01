import { spawn } from "child_process";
import path from "path";
import { fileURLToPath } from "url";
import axios from "axios";

import { uploadImage, uploadSong } from "./upload.controller.js";
import { generateId, addVideo, updateStatus } from "../store/video.store.js";

const downloadFolder = "downloads/";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const uploadFromVideo = videoUrl => {
    const processId = generateId();
    addVideo(processId, videoUrl);

    const args = [
        "-f",
        "bestaudio",
        "-x",
        "--audio-format",
        "mp3",
        "--audio-quality",
        "0",
        "--add-metadata",
        "--write-thumbnail",
        "--convert-thumbnails",
        "jpg",
        "--restrict-filenames",
        "-o",
        path.join(downloadFolder, "%(title)s.%(ext)s"),
        "--print-json",
        "--cookies",
        path.resolve(__dirname, "../cookies.txt"),

        videoUrl
    ];

    const ytdlp = spawn("yt-dlp", args);

    let stdoutData = "";
    ytdlp.stdout.on("data", chunk => {
        stdoutData += chunk.toString();
    });

    ytdlp.stderr.on("data", data => {
        updateStatus(processId, {
            currentStatus: "ytdlp failed!",
            status: "FAIL",
            error: data.toString()
        });
        console.error("yt-dlp error:", data.toString());
    });

    ytdlp.on("close", async code => {
        console.log("yt-dlp exited with code:", code);
        try {
            const info = JSON.parse(stdoutData);
            const title = info.title;
            const duration = info.duration;
            const id = info.id;
            const artist = "unknown";

            updateStatus(processId, {
                currentStatus: "checking database...",
                title
            });
            const isExistsRes = await axios.post(
                "https://vivid-music.vercel.app/checkSongExistsByYtId",
                { id, title }
            );

            if (isExistsRes.data.exists) {
                updateStatus(processId, {
                    currentStatus: "song already exist.",
                    status: "EXIST"
                });
                return false;
            }

            const parsed = path.parse(info._filename);
            const audioPath = path.join(parsed.dir, parsed.name + ".mp3");
            const coverPath = path.join(parsed.dir, parsed.name + ".jpg");

            updateStatus(processId, {
                currentStatus: "Uploading...",
                coverPath,
                audioPath
            });
            const [songPublicUrl, coverPublicUrl] = await Promise.all([
                uploadSong(audioPath),
                uploadImage(coverPath)
            ]);

            updateStatus(processId, {
                currentStatus: "Uploaded successfully 🥳"
            });

            if (songPublicUrl && coverPublicUrl) {
                updateStatus(processId, {
                    currentStatus: "Updating database..."
                });
                console.log("uploading to database....");
                const { data } = await axios.post(
                    "https://vivid-music.vercel.app/addSong",
                    {
                        title,
                        id,
                        duration,
                        artist,
                        songURL: songPublicUrl,
                        coverURL: coverPublicUrl
                    }
                );
                if (data.success) {
                    try {
                        updateStatus(processId, {
                            currentStatus: "Process Completed 🥳",
                            status: "SUCCESS"
                        });
                    } catch (err) {
                        updateStatus(processId, {
                            currentStatus: "file cleanup failed!",
                            status: "FAIL",
                            error: err
                        });
                        console.error("Error deleting files:", err);
                    }
                } else
                    updateStatus(processId, {
                        currentStatus: "Updating database failed!",
                        status: "FAIL"
                    });
            } else
                updateStatus(processId, {
                    currentStatus: "Updating to cloudinary failed!",
                    status: "FAIL"
                });
        } catch (err) {
            updateStatus(processId, {
                currentStatus: "Process failed!",
                status: "FAIL",
                error: err
            });
            console.error("Processing error:", err);
        }
    });

    ytdlp.on("error", err => {
        updateStatus(processId, {
            currentStatus: "ytdlp failed!",
            status: "FAIL",
            error: err
        });
        console.error("Failed to start yt-dlp:", err);
    });
};

export default uploadFromVideo;
