import express from "express";
import cloudinary from "cloudinary";
import cors from "cors";
import axios from "axios";
import { config as dotenvConfig } from "dotenv";

dotenvConfig();
const app = express();
const PORT = 5000;

app.use(express.json());
app.use(cors());
app.set("view engine", "ejs");
app.use(express.static("public"));

import uploadFromVideo from "./controllers/video.controller.js";
import  { processChannel } from "./controllers/channel.controller.js";
import  { processPlaylist } from "./controllers/playlist.controller.js";
import { getVideos } from "./store/video.store.js";
import { getStatus } from "./store/channel.store.js";

app.get("/", (req, res) => {
    res.render("index", { title: "Media Cloud Sync", API: process.env.API });
});

app.get("/status", (req, res) => {
    const videos = getVideos();
    const channels = getStatus();

    res.json({ status: [...videos, ...channels] });
});

app.post("/processVideo", (req, res) => {
    const { url } = req.body;

    if (url) uploadFromVideo(url);
});

app.post("/processChannel", (req, res) => {
    const { channelId, limit, skip } = req.body;

    if (channelId && !Number.isNaN(limit) && !Number.isNaN(skip)) {
        console.log("request received", channelId, limit, skip);
        processChannel(channelId, skip, limit); // async, fire and forget
        return res.json({ success: true, message: "Processing started" });
    }

    res.status(400).json({ success: false, message: "Invalid input" });
});

app.post("/processPlayList", (req, res) => {
    const { playlistId, limit, skip } = req.body;

    if (channelId && !Number.isNaN(limit) && !Number.isNaN(skip)) {
        console.log("request received", channelId, limit, skip);
        processPlaylist(playlistId, skip, limit); // async, fire and forget
        return res.json({ success: true, message: "Processing started" });
    }

    res.status(400).json({ success: false, message: "Invalid input" });
});

app.listen(PORT, () => {
    console.log("server started at port ", PORT);
});
